"""Multi-provider LLM client (OpenRouter, Google Gemini, Groq, Cerebras, Mistral).

All providers speak the OpenAI chat-completions protocol, so one client class serves them all.
Models are written as "provider:model-id"; a bare id (e.g. "anthropic/claude-sonnet-5.5" or
"google/gemma-4-31b-it:free") means OpenRouter. A *chain* is a comma-separated list of models: each
call tries them in order and moves on when a provider is out of quota, rate-limited, down or not configured.
"""

import base64
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
import openai
from openai import OpenAI
from sqlalchemy import text as sql_text, update

from ..config import settings
from ..db.models import Book
from ..db.session import session_scope

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    base_url: str
    key_url: str
    free_tier: str
    max_output_tokens: int | None = None  # clamp for providers whose models cap output length
    link_label: str = "Get an API key"
    env_hint: str = ""


PROVIDERS: dict[str, Provider] = {
    p.name: p
    for p in [
        Provider("openrouter", "OpenRouter", "", "https://openrouter.ai/keys",
                 "Models ending in :free: 50 requests/day (1,000/day after a one-time $10 credit purchase)."),
        Provider("gemini", "Google AI Studio (Gemini)", "https://generativelanguage.googleapis.com/v1beta/openai/",
                 "https://aistudio.google.com/apikey", "Free tier on Flash models; limits per account at aistudio.google.com/rate-limit."),
        Provider("groq", "Groq", "https://api.groq.com/openai/v1", "https://console.groq.com/keys",
                 "Free tier, no card; about 30 requests/minute per model with per-model daily caps.", max_output_tokens=8192),
        Provider("cerebras", "Cerebras", "https://api.cerebras.ai/v1", "https://cloud.cerebras.ai",
                 "Free tier; about 5 requests/minute and ~1M tokens/day.", max_output_tokens=8192),
        Provider("mistral", "Mistral", "https://api.mistral.ai/v1", "https://console.mistral.ai/api-keys",
                 "Free 'Experiment' plan (phone verification; requests may be used for training)."),
        Provider("ollama", "Ollama (local)", "", "https://ollama.com/download",
                 "Runs on your own computer: free, private and unlimited, but slow without a supported GPU.",
                 link_label="Download Ollama", env_hint="OLLAMA_ENABLED=true"),
    ]
}

# Errors worth trying the next model in the chain for.
FALLBACK_STATUS = {401, 402, 403, 404, 408, 409, 413, 422, 429, 500, 502, 503, 504, 529}
RATE_LIMIT_ROUNDS = 3  # when every model is rate-limited, wait and retry the whole chain this many times
MAX_BACKOFF_SECONDS = 60


class LLMError(RuntimeError):
    pass


class ProviderNotConfigured(LLMError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str  # the full "provider:model" spec that produced the answer
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    finish_reason: str | None = None


def parse_model(spec: str) -> tuple[str, str]:
    """'groq:llama-3.3-70b' -> ('groq', 'llama-3.3-70b'); 'google/gemma:free' -> ('openrouter', 'google/gemma:free')."""
    spec = spec.strip()
    prefix, sep, rest = spec.partition(":")
    if sep and prefix.lower() in PROVIDERS and rest:
        return prefix.lower(), rest.strip()
    return "openrouter", spec


def model_spec(provider: str, model: str) -> str:
    return model if provider == "openrouter" else f"{provider}:{model}"


def split_chain(chain: str | list[str] | None) -> list[str]:
    if not chain:
        return []
    items = chain if isinstance(chain, list) else chain.split(",")
    return [m.strip() for m in items if m and m.strip()]


def provider_configured(provider: str) -> bool:
    return bool(settings.provider_key(provider))


def chain_available(chain: str | list[str] | None) -> bool:
    return any(provider_configured(parse_model(m)[0]) for m in split_chain(chain))


_clients: dict[str, OpenAI] = {}


def _client(provider: str) -> OpenAI:
    key = settings.provider_key(provider)
    if not key:
        raise ProviderNotConfigured(f"{PROVIDERS[provider].label} has no API key ({provider.upper()}_API_KEY).")
    base_url = settings.OPENROUTER_BASE_URL if provider == "openrouter" else PROVIDERS[provider].base_url
    cache_key = f"{provider}|{base_url}|{key}"
    if cache_key not in _clients:
        headers = {"HTTP-Referer": settings.APP_URL, "X-Title": settings.PROJECT_NAME} if provider == "openrouter" else None
        # One SDK retry for transient blips; longer waits are handled by the chain logic below.
        _clients[cache_key] = OpenAI(base_url=base_url, api_key=key, timeout=settings.LLM_TIMEOUT_SECONDS, max_retries=1,
                                     default_headers=headers)
    return _clients[cache_key]


def _record_usage(book_id: uuid.UUID | None, result: LLMResult) -> None:
    if not book_id:
        return
    try:
        with session_scope() as db:
            # Never wait long on the book row lock: a caller's open transaction may hold it.
            db.execute(sql_text("SET LOCAL lock_timeout = '3s'"))
            db.execute(
                update(Book)
                .where(Book.id == book_id)
                .values(
                    prompt_tokens=Book.prompt_tokens + result.prompt_tokens,
                    completion_tokens=Book.completion_tokens + result.completion_tokens,
                    cost_usd=Book.cost_usd + result.cost,
                )
            )
    except Exception:  # usage tracking must never break generation
        logger.exception("Failed to record LLM usage")


def _retry_after(error: Exception) -> float | None:
    response = getattr(error, "response", None)
    value = response.headers.get("retry-after") if response is not None else None
    try:
        return float(value) if value else None
    except ValueError:
        return None


_ollama_capabilities: dict[str, list[str]] = {}


def _ollama_supports_thinking(model: str) -> bool:
    """Ask Ollama once per model whether it has a 'thinking' mode (sending `think` to other models is an error)."""
    if model not in _ollama_capabilities:
        try:
            resp = httpx.post(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/show", json={"model": model}, timeout=30)
            _ollama_capabilities[model] = resp.json().get("capabilities") or [] if resp.status_code == 200 else []
        except httpx.HTTPError:
            return False
    return "thinking" in _ollama_capabilities[model]


def _call_ollama(spec: str, model: str, system: str, prompt: str, max_tokens: int, temperature: float) -> LLMResult:
    """Ollama's native chat API: unlike its OpenAI-compatible endpoint it lets us set the context window."""
    if not provider_configured("ollama"):
        raise ProviderNotConfigured("Ollama is not enabled (OLLAMA_ENABLED=true).")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_ctx": settings.OLLAMA_NUM_CTX, "num_predict": max_tokens, "temperature": temperature},
    }
    if _ollama_supports_thinking(model):
        payload["think"] = settings.OLLAMA_THINK
    try:
        resp = httpx.post(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat", json=payload, timeout=settings.OLLAMA_TIMEOUT_SECONDS)
    except httpx.HTTPError as e:
        raise LLMError(f"{spec}: Ollama unreachable at {settings.OLLAMA_BASE_URL} ({e.__class__.__name__}). Is `ollama serve` running?") from e
    if resp.status_code != 200:
        raise LLMError(f"{spec}: Ollama HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    text = ((data.get("message") or {}).get("content") or "")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()  # models that inline their reasoning
    if not text:
        raise LLMError(f"{spec} returned an empty response (done_reason={data.get('done_reason')}).")
    return LLMResult(text=text, model=spec, prompt_tokens=data.get("prompt_eval_count") or 0,
                     completion_tokens=data.get("eval_count") or 0, cost=0.0, finish_reason=data.get("done_reason"))


def _call_one(spec: str, system: str, prompt: str, max_tokens: int, temperature: float) -> LLMResult:
    provider, model = parse_model(spec)
    if provider == "ollama":
        return _call_ollama(spec, model, system, prompt, max_tokens, temperature)
    client = _client(provider)
    cap = PROVIDERS[provider].max_output_tokens
    if cap:
        max_tokens = min(max_tokens, cap)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if provider == "openrouter":
        kwargs["extra_body"] = {"usage": {"include": True}}
    try:
        resp = client.chat.completions.create(**kwargs)
    except openai.BadRequestError as e:
        # Some models cap output length below what we ask for; retry once with a safe ceiling.
        if "token" in str(e).lower() and max_tokens > 8192:
            kwargs["max_tokens"] = 8192
            resp = client.chat.completions.create(**kwargs)
        else:
            raise

    if not resp.choices:
        raise LLMError(f"{spec} returned no choices.")
    choice = resp.choices[0]
    text = (choice.message.content or "").strip()
    if not text:
        raise LLMError(f"{spec} returned an empty response (finish_reason={choice.finish_reason}).")
    usage = resp.usage
    cost = 0.0
    if usage is not None:
        extra = getattr(usage, "model_extra", None) or {}
        cost = float(extra.get("cost") or getattr(usage, "cost", 0) or 0)
    return LLMResult(
        text=text,
        model=spec,
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        cost=cost,
        finish_reason=choice.finish_reason,
    )


def complete(
    *,
    model: str,
    system: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.8,
    book_id: uuid.UUID | None = None,
) -> LLMResult:
    """Chat completion over a model chain. Raises LLMError when every model in the chain fails."""
    chain = split_chain(model)
    if not chain:
        raise LLMError("No model configured.")
    errors: list[str] = []
    for round_no in range(RATE_LIMIT_ROUNDS):
        rate_limited_only = True
        wait = 0.0
        for spec in chain:
            try:
                result = _call_one(spec, system, prompt, max_tokens, temperature)
                if errors:
                    logger.info("Fell back to %s after: %s", spec, "; ".join(errors[-3:]))
                _record_usage(book_id, result)
                return result
            except ProviderNotConfigured as e:
                errors.append(str(e))
                rate_limited_only = False
            except openai.RateLimitError as e:
                errors.append(f"{spec}: rate limited / out of quota")
                wait = max(wait, _retry_after(e) or 10.0 * (round_no + 1))
            except openai.APIStatusError as e:
                if e.status_code not in FALLBACK_STATUS:
                    raise LLMError(f"{spec} request failed: {e}") from e
                errors.append(f"{spec}: HTTP {e.status_code}")
                rate_limited_only = False
            except (openai.APIConnectionError, openai.APITimeoutError) as e:
                errors.append(f"{spec}: {e.__class__.__name__}")
                rate_limited_only = False
            except LLMError as e:  # empty answers etc.
                errors.append(str(e))
                rate_limited_only = False
        if not rate_limited_only or round_no == RATE_LIMIT_ROUNDS - 1:
            break
        logger.warning("All models rate-limited; waiting %.0fs before retrying the chain", min(wait, MAX_BACKOFF_SECONDS))
        time.sleep(min(wait, MAX_BACKOFF_SECONDS))
    hint = " Add another provider to the chain, wait for the quota to reset, or change the model." if len(chain) == 1 else ""
    raise LLMError("All models failed: " + "; ".join(errors[-len(chain) * 2:]) + "." + hint)


def extract_json(text: str, expect: type = dict) -> Any:
    """Parse JSON of the expected top-level type from a model response.

    Tolerates code fences, surrounding prose and a single-object list wrapper (`[{...}]`). It never returns a
    nested fragment: a truncated object must not be mistaken for one of the lists inside it."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    candidates = [cleaned]
    open_ch, close_ch = ("{", "}") if expect is dict else ("[", "]")
    start, end = cleaned.find(open_ch), cleaned.rfind(close_ch)
    if start != -1 and end > start:
        candidates.append(cleaned[start : end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if expect is dict and isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
            value = value[0]
        if isinstance(value, expect):
            return value
    raise LLMError(f"Model response was not a valid JSON {'object' if expect is dict else 'array'}.")


def complete_json(
    *,
    model: str,
    system: str,
    prompt: str,
    max_tokens: int = 6000,
    temperature: float = 0.4,
    book_id: uuid.UUID | None = None,
    retries: int = 1,
    expect: type = dict,
) -> Any:
    """Completion that must return JSON of type `expect`. Retries with a stricter reminder on parse failure."""
    system = system + "\n\nRespond with valid JSON only. No markdown fences, no commentary."
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        p = prompt if attempt == 0 else prompt + "\n\nIMPORTANT: your previous reply was not valid, complete JSON. Return ONLY the JSON, and keep it short."
        result = complete(model=model, system=system, prompt=p, max_tokens=max_tokens, temperature=temperature, book_id=book_id)
        try:
            return extract_json(result.text, expect)
        except LLMError as e:
            last_error = e
            logger.warning("JSON parse failed (attempt %s) for model %s (finish_reason=%s)", attempt + 1, result.model, result.finish_reason)
    raise LLMError(str(last_error))


def image_available() -> bool:
    return provider_configured(parse_model(settings.IMAGE_MODEL)[0])


def generate_image(*, prompt: str, model: str | None = None, aspect_ratio: str = "2:3", book_id: uuid.UUID | None = None) -> bytes:
    """Generate an image via an OpenRouter image-output model. Returns raw image bytes."""
    spec = model or settings.IMAGE_MODEL
    provider, model_id = parse_model(spec)
    if provider != "openrouter":
        raise LLMError("Cover art generation currently uses OpenRouter image models only (set IMAGE_MODEL to an OpenRouter id).")
    client = _client(provider)
    try:
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"modalities": ["image", "text"], "image_config": {"aspect_ratio": aspect_ratio}, "usage": {"include": True}},
        )
    except Exception as e:
        raise LLMError(f"Image generation failed ({spec}): {e}") from e

    message = resp.choices[0].message if resp.choices else None
    images = (getattr(message, "model_extra", None) or {}).get("images") or getattr(message, "images", None) or []
    for image in images:
        url = (image.get("image_url") or {}).get("url", "") if isinstance(image, dict) else ""
        if url.startswith("data:") and "," in url:
            usage = resp.usage
            if usage is not None:
                extra = getattr(usage, "model_extra", None) or {}
                _record_usage(book_id, LLMResult(text="", model=spec, prompt_tokens=usage.prompt_tokens or 0,
                                                 completion_tokens=usage.completion_tokens or 0, cost=float(extra.get("cost") or 0)))
            return base64.b64decode(url.split(",", 1)[1])
    raise LLMError(f"Model {spec} did not return an image.")


def _openrouter_models() -> list[dict]:
    resp = httpx.get(f"{settings.OPENROUTER_BASE_URL}/models", timeout=20)
    resp.raise_for_status()
    out = []
    for m in resp.json().get("data", []):
        pricing = m.get("pricing") or {}
        arch = m.get("architecture") or {}
        prompt_price = round(float(pricing.get("prompt") or 0) * 1_000_000, 4)
        completion_price = round(float(pricing.get("completion") or 0) * 1_000_000, 4)
        out.append({
            "id": m["id"],
            "provider": "openrouter",
            "name": m.get("name", m["id"]),
            "context_length": m.get("context_length"),
            "prompt_price_per_million": prompt_price,
            "completion_price_per_million": completion_price,
            "free": prompt_price == 0 and completion_price == 0,
            "output_modalities": arch.get("output_modalities") or ["text"],
        })
    return out


def list_models() -> dict:
    """Models from OpenRouter's public catalogue plus every configured provider's own model list
    (for Ollama: the models already downloaded on this machine)."""
    models: list[dict] = []
    errors: dict[str, str] = {}
    try:
        models += _openrouter_models()
    except Exception as e:
        errors["openrouter"] = str(e)
    for name in PROVIDERS:
        if name == "openrouter" or not provider_configured(name):
            continue
        if name == "ollama":
            try:
                resp = httpx.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=10)
                resp.raise_for_status()
                for m in resp.json().get("models", []):
                    details = m.get("details") or {}
                    models.append({
                        "id": model_spec("ollama", m["name"]), "provider": "ollama",
                        "name": f"Ollama: {m['name']} ({details.get('parameter_size', '?')}, {details.get('quantization_level', '?')})",
                        "context_length": None, "prompt_price_per_million": None, "completion_price_per_million": None,
                        "free": True, "output_modalities": ["text"],
                    })
            except Exception as e:
                errors[name] = str(e)[:300]
            continue
        try:
            for m in _client(name).models.list():
                mid = m.id.removeprefix("models/")  # Gemini returns "models/<id>"
                models.append({
                    "id": model_spec(name, mid),
                    "provider": name,
                    "name": f"{PROVIDERS[name].label}: {mid}",
                    "context_length": getattr(m, "context_window", None) or (getattr(m, "model_extra", None) or {}).get("context_window"),
                    "prompt_price_per_million": None,
                    "completion_price_per_million": None,
                    "free": True,  # used on the provider's free tier with your key
                    "output_modalities": ["text"],
                })
        except Exception as e:
            errors[name] = str(e)[:300]
    return {"models": models, "errors": errors}


def provider_status() -> list[dict]:
    return [
        {"name": p.name, "label": p.label, "configured": provider_configured(p.name), "key_url": p.key_url,
         "free_tier": p.free_tier, "env_var": p.env_hint or f"{p.name.upper()}_API_KEY=…", "link_label": p.link_label}
        for p in PROVIDERS.values()
    ]
