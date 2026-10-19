"""Exercise the real multi-provider client against local mock servers (request shape, usage/cost, JSON, images,
provider prefixes, fallback chains and output-token caps)."""

import base64
import dataclasses
import importlib
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

import app.services.llm as llm_module
from app.config import settings


class MockServer:
    """OpenAI-compatible endpoint. `replies` are (status, body) pairs; the last one repeats when the queue empties."""

    def __init__(self):
        self.requests: list[dict] = []
        self.replies: list[tuple[int, dict]] = []
        self.get_reply: dict = {}
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                server.requests.append({"path": self.path, "body": body, "headers": {k.lower(): v for k, v in self.headers.items()}})
                status, reply = server.replies.pop(0) if len(server.replies) > 1 else server.replies[0]
                payload = json.dumps(reply).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("retry-after-ms", "1")
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):  # noqa: N802
                payload = json.dumps(server.get_reply).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/v1"


def _completion(content: str, cost: float = 0.0123, images: list | None = None) -> tuple[int, dict]:
    message = {"role": "assistant", "content": content}
    if images is not None:
        message["images"] = images
    return 200, {
        "id": "gen-1", "object": "chat.completion", "created": 0, "model": "test/model",
        "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33, "cost": cost},
    }


RATE_LIMITED = (429, {"error": {"message": "Rate limit exceeded: free-models-per-day", "code": 429}})


@pytest.fixture
def llm(monkeypatch):
    # The autouse fake_llm fixture patches complete()/complete_json(); reload to get the real implementations.
    real = importlib.reload(llm_module)
    for name in ("OPENROUTER", "GEMINI", "GROQ", "CEREBRAS", "MISTRAL"):
        monkeypatch.setattr(settings, f"{name}_API_KEY", "")
    monkeypatch.setattr(settings, "OLLAMA_ENABLED", False)
    real._clients.clear()
    yield real
    real._clients.clear()


@pytest.fixture
def openrouter(llm, monkeypatch):
    server = MockServer()
    monkeypatch.setattr(settings, "OPENROUTER_BASE_URL", server.url)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-or-test")
    yield server
    server.httpd.shutdown()


@pytest.fixture
def groq(llm, monkeypatch):
    server = MockServer()
    monkeypatch.setitem(llm.PROVIDERS, "groq", dataclasses.replace(llm.PROVIDERS["groq"], base_url=server.url))
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-test")
    yield server
    server.httpd.shutdown()


def _png_data_url() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (10, 15), (200, 10, 10)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_parse_model(llm):
    assert llm.parse_model("groq:llama-3.3-70b-versatile") == ("groq", "llama-3.3-70b-versatile")
    assert llm.parse_model("gemini:gemini-flash-latest") == ("gemini", "gemini-flash-latest")
    assert llm.parse_model("google/gemma-4-31b-it:free") == ("openrouter", "google/gemma-4-31b-it:free")
    assert llm.parse_model("openrouter:anthropic/claude-sonnet-5.5") == ("openrouter", "anthropic/claude-sonnet-5.5")
    assert llm.split_chain(" groq:a , ,mistral:b ") == ["groq:a", "mistral:b"]


def test_openrouter_request_and_usage(llm, openrouter):
    openrouter.replies.append(_completion("Once upon a time."))
    result = llm.complete(model="anthropic/claude-sonnet-5.5", system="sys", prompt="hi", max_tokens=50)
    assert (result.text, result.model) == ("Once upon a time.", "anthropic/claude-sonnet-5.5")
    assert (result.prompt_tokens, result.completion_tokens, result.cost) == (11, 22, 0.0123)
    req = openrouter.requests[0]
    assert req["path"] == "/v1/chat/completions"
    assert req["headers"]["authorization"] == "Bearer sk-or-test"
    assert req["headers"]["x-title"] == settings.PROJECT_NAME
    assert req["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert req["body"]["usage"] == {"include": True}


def test_fallback_to_next_provider_on_quota(llm, openrouter, groq):
    openrouter.replies.append(RATE_LIMITED)
    groq.replies.append(_completion("From Groq."))
    result = llm.complete(model="google/gemma-4-31b-it:free, groq:llama-3.3-70b-versatile", system="s", prompt="p", max_tokens=20000)
    assert result.text == "From Groq." and result.model == "groq:llama-3.3-70b-versatile"
    body = groq.requests[0]["body"]
    assert body["model"] == "llama-3.3-70b-versatile"
    assert body["max_tokens"] == 8192  # clamped to Groq's output cap
    assert "usage" not in body  # OpenRouter-only parameter
    assert groq.requests[0]["headers"]["authorization"] == "Bearer gsk-test"


def test_unconfigured_provider_is_skipped(llm, groq):
    groq.replies.append(_completion("ok"))
    result = llm.complete(model="mistral:mistral-small-latest,groq:llama", system="s", prompt="p")
    assert result.model == "groq:llama"


def test_all_failed_raises_with_reasons(llm, groq, monkeypatch):
    monkeypatch.setattr(llm, "RATE_LIMIT_ROUNDS", 1)
    groq.replies.append(RATE_LIMITED)
    with pytest.raises(llm.LLMError) as e:
        llm.complete(model="groq:llama", system="s", prompt="p")
    assert "rate limited" in str(e.value) and "Add another provider" in str(e.value)
    assert llm.chain_available("mistral:x") is False and llm.chain_available("mistral:x,groq:y") is True


def test_complete_json_handles_fences_and_retries(llm, openrouter):
    openrouter.replies += [_completion("not json at all"), _completion('Here you go:\n```json\n{"a": [1, 2]}\n```')]
    assert llm.complete_json(model="m", system="s", prompt="p") == {"a": [1, 2]}
    assert "not valid, complete JSON" in openrouter.requests[1]["body"]["messages"][1]["content"]


def test_empty_response_raises(llm, openrouter):
    openrouter.replies.append(_completion(""))
    with pytest.raises(llm.LLMError):
        llm.complete(model="m", system="s", prompt="p")


def test_generate_image(llm, openrouter):
    openrouter.replies.append(_completion("", images=[{"type": "image_url", "image_url": {"url": _png_data_url()}}]))
    data = llm.generate_image(prompt="a lighthouse", model="google/gemini-3.1-flash-image")
    assert Image.open(io.BytesIO(data)).size == (10, 15)
    body = openrouter.requests[0]["body"]
    assert body["modalities"] == ["image", "text"]
    assert body["image_config"] == {"aspect_ratio": "2:3"}


def test_extract_json_never_returns_a_nested_fragment(llm):
    # Regression: a truncated object used to come back as its inner list -> "'list' object has no attribute 'get'".
    truncated = 'Sure! {"summary": "They flee the house.", "continuity_facts": ["door is locked", "Mara is hurt"], "new_char'
    with pytest.raises(llm.LLMError):
        llm.extract_json(truncated)
    assert llm.extract_json('[{"summary": "x"}]') == {"summary": "x"}
    assert llm.extract_json('Here you go:\n{"a": [1, 2]} hope that helps') == {"a": [1, 2]}
    assert llm.extract_json('["a", "b"]', expect=list) == ["a", "b"]
    with pytest.raises(llm.LLMError):
        llm.extract_json('["just", "a", "list"]')


def test_complete_json_retries_truncated_object(llm, openrouter):
    openrouter.replies += [
        _completion('{"summary": "They flee.", "continuity_facts": ["door locked"], "new_characters": [{"name": "Ma'),
        _completion('{"summary": "They flee.", "continuity_facts": ["door locked"], "new_characters": []}'),
    ]
    data = llm.complete_json(model="m", system="s", prompt="p")
    assert data["summary"] == "They flee." and len(openrouter.requests) == 2


@pytest.fixture
def ollama(llm, monkeypatch):
    server = MockServer()
    monkeypatch.setattr(settings, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", server.url.removesuffix("/v1"))
    monkeypatch.setattr(settings, "OLLAMA_NUM_CTX", 32768)
    yield server
    server.httpd.shutdown()


def test_ollama_native_chat_sets_context_window(llm, ollama):
    llm._ollama_capabilities.clear()
    ollama.replies.append((200, {"capabilities": ["completion", "thinking"]}))
    ollama.replies.append((200, {"model": "gemma4:26b-a4b", "message": {"role": "assistant", "content": "<think>plan</think>The house waited."},
                                 "done": True, "done_reason": "stop", "prompt_eval_count": 120, "eval_count": 9}))
    result = llm.complete(model="ollama:gemma4:26b-a4b", system="s", prompt="p", max_tokens=5000, temperature=0.9)
    assert (result.text, result.model, result.cost, result.completion_tokens) == ("The house waited.", "ollama:gemma4:26b-a4b", 0.0, 9)
    assert [r["path"] for r in ollama.requests] == ["/api/show", "/api/chat"]
    req = ollama.requests[1]
    assert req["body"]["think"] is False  # the mock reports a thinking-capable model
    assert req["body"]["model"] == "gemma4:26b-a4b" and req["body"]["stream"] is False
    assert req["body"]["options"] == {"num_ctx": 32768, "num_predict": 5000, "temperature": 0.9}


def test_ollama_down_falls_back(llm, groq, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:9")  # nothing listens here
    groq.replies.append(_completion("cloud answer"))
    assert llm.complete(model="ollama:gemma4:26b-a4b, groq:llama", system="s", prompt="p").model == "groq:llama"


def test_ollama_models_listed(llm, ollama):
    ollama.get_reply = {"models": [{"name": "gemma4:26b-a4b", "details": {"parameter_size": "25.8B", "quantization_level": "Q4_K_M"}}]}
    catalog = llm.list_models()
    ids = [m["id"] for m in catalog["models"] if m["provider"] == "ollama"]
    assert ids == ["ollama:gemma4:26b-a4b"]
