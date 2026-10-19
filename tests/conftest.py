import io
import json
import os
import re
import tempfile

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://bookpilot:bookpilot@localhost:5442/bookpilot_test")
os.environ["DATABASE_URL"] = TEST_DB
os.environ["OPENROUTER_API_KEY"] = "test-key"
# Isolate tests from the developer's own .env (models, provider keys): environment variables win over .env.
os.environ["WRITER_MODELS"] = "anthropic/claude-sonnet-5.5"
os.environ["EDITOR_MODELS"] = "anthropic/claude-haiku-5.5"
os.environ["IMAGE_MODEL"] = "google/gemini-3.1-flash-image"
for _provider in ("GEMINI", "GROQ", "CEREBRAS", "MISTRAL"):
    os.environ[f"{_provider}_API_KEY"] = ""
os.environ["OLLAMA_ENABLED"] = "false"
os.environ["SLACK_ENABLED"] = "false"
os.environ["RUN_WORKER_IN_PROCESS"] = "false"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="bookpilot-test-")

import psycopg  # noqa: E402
from PIL import Image  # noqa: E402


def _ensure_database() -> None:
    admin = TEST_DB.replace("postgresql+psycopg://", "postgresql://").rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin, autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = 'bookpilot_test'").fetchone():
            conn.execute("CREATE DATABASE bookpilot_test")


_ensure_database()

from app.db.models import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.services import llm  # noqa: E402
from app.services.llm import LLMResult  # noqa: E402

NAMES = ["Corwin Hale", "Ysolde Marr", "Tobiah Fenn"]

PROSE_SENTENCES = [
    "Corwin Hale pushed the lantern door open and the hinges complained in the cold.",
    "Rain hammered the harbour roofs while gulls wheeled above the black water.",
    "\"We should not be here,\" Ysolde said, pulling her coat tighter against the wind.",
    "He studied the brass frame, the scratched glass, the tiny flame that refused to die.",
    "Somewhere below them a bell rang twice and then fell silent.",
    "Tobiah Fenn counted the steps under his breath, as he always did when he was afraid.",
    "The light bent strangely across the floorboards and showed footprints that were not theirs.",
    "Ysolde knelt, touched the dust, and frowned at the shape of a small bare foot.",
]


def fake_prose(words: int, flawed: bool) -> str:
    paras, count, i = [], 0, 0
    while count < words:
        para = " ".join(PROSE_SENTENCES[(i + k) % len(PROSE_SENTENCES)] for k in range(4))
        paras.append(para)
        count += len(para.split())
        i += 3
    if flawed:
        paras[0] = paras[0] + " He decided to delve into teh mystery  at once."
        paras.insert(2, "* * *")
        paras.append("They went went down the stairs together, **certain** of nothing.")
    return "\n\n".join(paras)


def fake_complete(*, model, system, prompt, max_tokens=4000, temperature=0.8, book_id=None):
    if "image-generation prompt" in prompt:
        text = "A lone lighthouse on a storm-dark sea, glowing lantern, painterly, no text"
    elif "NOW WRITE" in prompt or "Continue seamlessly" in prompt:
        m = re.search(r"about (\d+) words", prompt)
        words = int(m.group(1)) if m else 400
        text = fake_prose(min(words, 1500), flawed=bool(re.search(r"NOW WRITE \w+ 1:", prompt)))
    elif "CURRENT DRAFT" in prompt:
        m = re.search(r"Keep it about (\d+) words", prompt)
        text = fake_prose(int(m.group(1)) if m else 500, flawed=False)
    else:
        text = "A summary of events."
    result = LLMResult(text=text, model=model, prompt_tokens=100, completion_tokens=200, cost=0.001)
    llm._record_usage(book_id, result)
    return result


def fake_complete_json(*, model, system, prompt, max_tokens=6000, temperature=0.4, book_id=None, retries=1):
    if "Create the STORY BIBLE" in prompt:
        return {
            "logline": "A lighthouse lantern reveals the hidden truths of a drowned town.",
            "synopsis": "Three friends uncover the secret of the lantern.",
            "themes": ["truth", "grief"],
            "voice": "atmospheric, close third person",
            "characters": [{"name": n, "role": "protagonist"} for n in NAMES],
            "settings": [{"name": "Gullmouth", "description": "a fishing harbour"}],
            "glossary": [{"term": "Lanternwright", "meaning": "a maker of lanterns"}],
        }
    if "Create a detailed outline" in prompt:
        n = int(re.search(r"exactly (\d+)", prompt).group(1))
        return {"synopsis": "Overall arc.", "chapters": [
            {"number": i, "title": f"The Lantern Part {i}", "synopsis": f"Things happen in part {i}.",
             "beats": ["arrive", "discover", "escape"], "target_words": 500} for i in range(1, n + 1)]}
    if '"new_characters"' in prompt:
        return {"summary": "Corwin and Ysolde explore the lighthouse.", "new_characters": [{"name": "Mara Quill", "role": "minor"}],
                "continuity_facts": ["The lantern flame never goes out."]}
    if "Review this" in prompt and "professional editor" in prompt:
        return {"issues": [{"check": "continuity", "severity": "major", "excerpt": "Rain hammered the harbour roofs",
                            "message": "Weather contradicts the clear night established earlier.", "suggestion": "Make it clear skies."}],
                "strengths": ["Atmosphere"], "overall": "Solid."}
    if "acquisitions editor" in prompt:
        return {"issues": [{"check": "unresolved_threads", "severity": "minor", "chapter_number": None,
                            "message": "The bell is never explained.", "suggestion": "Pay it off."}],
                "verdict": "needs_work", "summary": "Promising."}
    if "retail metadata" in prompt:
        return {"description": "<p><b>A lantern that shows the truth.</b></p><p>" + "Gripping mystery. " * 30 + "</p>",
                "back_cover_copy": "When the lantern burns, secrets surface.", "subtitle": "",
                "keywords": ["cozy fantasy mystery", "lighthouse mystery", "magic lantern", "found family adventure",
                             "small town secrets", "atmospheric mystery", "fantasy whodunit"],
                "store_categories": ["Fiction / Fantasy / Paranormal", "Fiction / Mystery & Detective / Cozy", "Fiction / Fantasy / Urban"]}
    raise AssertionError(f"Unexpected JSON prompt: {prompt[:200]}")


def fake_image(*, prompt, model=None, aspect_ratio="2:3", book_id=None) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (832, 1248), (40, 90, 140)).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    monkeypatch.setattr(llm, "complete", fake_complete)
    monkeypatch.setattr(llm, "complete_json", fake_complete_json)
    monkeypatch.setattr(llm, "generate_image", fake_image)


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture
def drain():
    """Run queued jobs synchronously, like the worker would."""
    from app.db.session import SessionLocal
    from app.services import tasks  # noqa: F401
    from app.services.jobs import claim_next, run_job

    def run(max_jobs: int = 50) -> list[str]:
        ran = []
        for _ in range(max_jobs):
            with SessionLocal() as db:
                job = claim_next(db)
            if job is None:
                break
            run_job(job.id)
            ran.append(job.type)
        return ran

    return run


def dump(obj) -> str:
    return json.dumps(obj, indent=1, default=str)
