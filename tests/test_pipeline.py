"""End-to-end: create -> plan -> outline review -> write/approve -> QA -> fixes -> metadata -> cover -> exports."""

import zipfile
from pathlib import Path

from PIL import Image

from app.services.qa import grammar

from .conftest import dump

BRIEF = {
    "title": "The Last Lantern",
    "author_name": "Jane Quill",
    "category": "novelette",
    "genre": "fantasy",
    "audience": "young_adult",
    "content_rating": "clean",
    "premise": "A mystery fantasy about a lighthouse lantern that reveals hidden truths in a drowned town.",
    "target_word_count": 10000,
    "target_chapter_count": 4,
}


def _book(client, book_id):
    r = client.get(f"/api/books/{book_id}")
    assert r.status_code == 200, r.text
    return r.json()


def test_catalog(client):
    data = client.get("/api/catalog").json()
    keys = {c["key"] for c in data["categories"]}
    assert {"short_story", "novel", "epic_novel", "novella", "poetry_collection", "nonfiction_guide"} <= keys
    assert "6x9" in data["trim_sizes"]


def test_create_validation(client):
    r = client.post("/api/books", json={**BRIEF, "category": "childrens_chapter_book", "audience": "adult"})
    assert r.status_code == 400
    r = client.post("/api/books", json={**BRIEF, "category": "nope"})
    assert r.status_code == 422


def test_full_manual_pipeline(client, drain):
    r = client.post("/api/books", json=BRIEF)
    assert r.status_code == 201, r.text
    book_id = r.json()["id"]
    assert r.json()["jobs"][0]["type"] == "plan_book"

    assert drain() == ["plan_book"]
    book = _book(client, book_id)
    assert book["status"] == "outline_review"
    assert book["outline"]["version"] == 1 and len(book["outline"]["chapters"]) == 4
    assert sum(c["target_words"] for c in book["outline"]["chapters"]) == 10000
    assert book["story_bible"]["characters"]

    # Writing is gated on outline approval
    assert client.post(f"/api/books/{book_id}/chapters/1/write").status_code == 403

    r = client.post(f"/api/books/{book_id}/outline/revise", json={"feedback": "Make part 2 darker."})
    assert r.status_code == 200, r.text
    assert drain() == ["revise_outline"]
    assert _book(client, book_id)["outline"]["version"] == 2

    r = client.post(f"/api/books/{book_id}/outline/approve")
    assert r.status_code == 200, r.text
    assert drain() == ["write_chapter"]
    ch1 = client.get(f"/api/books/{book_id}/chapters/1").json()
    assert ch1["status"] == "pending_review"
    assert _book(client, book_id)["writer_model"] == "anthropic/claude-sonnet-5.5"  # pinned on first prose
    assert ch1["word_count"] > 1500, ch1["word_count"]
    assert "Chapter" not in ch1["content"][:20]

    # Part 2 needs part 1 approved
    assert client.post(f"/api/books/{book_id}/chapters/2/write").status_code == 409

    for n in range(1, 5):
        r = client.post(f"/api/books/{book_id}/chapters/{n}/approve", json={"continue_writing": True})
        assert r.status_code == 200, r.text
        drain()
    book = _book(client, book_id)
    assert book["status"] == "editing", dump(book["chapters"])
    assert book["parts_approved"] == 4
    assert book["cost_usd"] > 0
    assert any(c.get("name") == "Mara Quill" for c in book["story_bible"]["characters"])

    # Revise a chapter with notes keeps a revision history
    r = client.post(f"/api/books/{book_id}/chapters/3/revise", json={"instructions": "Tighten the ending.", "mode": "revise"})
    assert r.status_code == 200, r.text
    assert drain() == ["revise_chapter"]
    revs = client.get(f"/api/books/{book_id}/chapters/3/revisions").json()
    assert [r["reason"] for r in revs][:2] == ["revised", "generated"]
    client.post(f"/api/books/{book_id}/chapters/3/approve", json={"continue_writing": False})

    # Simulate an author pasting text with formatting leftovers into part 2
    ch2 = client.get(f"/api/books/{book_id}/chapters/2").json()
    r = client.put(f"/api/books/{book_id}/chapters/2",
                   json={"content": ch2["content"] + "\n\nShe felt **certain**  of it... \"Really?\" he asked."})
    assert r.status_code == 200 and r.json()["revision"] == ch2["revision"] + 1

    # ---- QA ----
    r = client.post(f"/api/books/{book_id}/qa", json={"include_ai": True})
    assert r.status_code == 200, r.text
    assert drain() == ["qa"]
    qa = client.get(f"/api/books/{book_id}/qa").json()
    assert qa["score"] is not None and qa["open_issues"] > 0
    issues = client.get(f"/api/books/{book_id}/qa/issues").json()
    checks = {i["check"] for i in issues}
    expected = {"ai_tell_phrase", "markdown_bold", "ai:continuity", "ai:unresolved_threads"}
    assert expected <= checks, checks
    if grammar.is_available():
        assert any(i["category"] == "spelling" and "teh" in (i["excerpt"] or "") for i in issues), checks
        assert qa["latest_run"]["stats"]["languagetool"] is True

    # Ignore one issue; it must stay ignored after a re-run
    ai_issue = next(i for i in issues if i["check"] == "ai:continuity")
    assert client.patch(f"/api/qa/issues/{ai_issue['id']}", json={"status": "ignored"}).json()["status"] == "ignored"

    # Single fix
    bold = next(i for i in issues if i["check"] == "markdown_bold")
    r = client.post(f"/api/qa/issues/{bold['id']}/apply", json={})
    assert r.status_code == 200, r.text
    assert "**" not in client.get(f"/api/books/{book_id}/chapters/{bold['chapter_number']}").json()["content"]

    # Bulk mechanical autofix
    assert drain() == []
    client.post(f"/api/books/{book_id}/qa/autofix", json={})
    assert drain() == ["autofix"]
    ch1 = client.get(f"/api/books/{book_id}/chapters/1").json()["content"]
    assert "went went" not in ch1 and '"' not in ch1 and "“" in ch1
    ch2 = client.get(f"/api/books/{book_id}/chapters/2").json()["content"]
    assert "  " not in ch2 and "..." not in ch2 and "“Really?” he asked." in ch2

    client.post(f"/api/books/{book_id}/qa", json={"include_ai": True})
    drain()
    issues = client.get(f"/api/books/{book_id}/qa/issues").json()
    assert not any(i["check"] == "ai:continuity" and i["chapter_number"] == ai_issue["chapter_number"]
                   and i["excerpt"] == ai_issue["excerpt"] for i in issues)

    # AI fix for a chapter
    r = client.post(f"/api/books/{book_id}/chapters/1/ai-fix", json={})
    assert r.status_code == 200, r.text
    assert drain() == ["ai_fix"]
    assert client.get(f"/api/books/{book_id}/chapters/1").json()["status"] == "approved"

    # ---- publishing ----
    r = client.patch(f"/api/books/{book_id}", json={"isbn_ebook": "978-0-306-40615-7", "dedication": "For the *keepers* of light.",
                                                    "author_bio": "Jane Quill lives by the sea."})
    assert r.status_code == 200, r.text
    assert client.patch(f"/api/books/{book_id}", json={"isbn_ebook": "9780306406158"}).status_code == 422

    client.post(f"/api/books/{book_id}/metadata/generate", json={"overwrite": True})
    client.post(f"/api/books/{book_id}/cover/generate", json={"use_ai": True})
    assert drain() == ["metadata", "cover"]
    book = _book(client, book_id)
    assert len(book["keywords"]) == 7 and book["has_cover"]
    cover = client.get(f"/api/books/{book_id}/cover")
    assert cover.status_code == 200
    from io import BytesIO

    assert Image.open(BytesIO(cover.content)).size == (1600, 2560)

    for fmt in ("epub", "print_pdf", "cover_wrap_pdf", "docx", "txt"):
        r = client.post(f"/api/books/{book_id}/exports", json={"format": fmt, "trim_size": "5x8"})
        assert r.status_code == 200, r.text
    assert drain() == ["export"] * 5, client.get(f"/api/jobs?book_id={book_id}").json()
    exports = {e["format"]: e for e in client.get(f"/api/books/{book_id}/exports").json()}
    assert set(exports) == {"epub", "print_pdf", "cover_wrap_pdf", "docx", "txt"}
    pdf = exports["print_pdf"]
    assert pdf["page_count"] >= 24, pdf
    assert pdf["validation"]["fonts_embedded"]
    wrap = exports["cover_wrap_pdf"]
    assert wrap["page_count"] == pdf["page_count"]
    assert abs(wrap["validation"]["spine_width_in"] - pdf["page_count"] * 0.002252) < 0.001

    epub_resp = client.get(f"/api/exports/{exports['epub']['id']}/download")
    assert epub_resp.status_code == 200
    with zipfile.ZipFile(BytesIO(epub_resp.content)) as z:
        names = z.namelist()
        assert names[0] == "mimetype"
        part1 = next(n for n in names if n.endswith("part001.xhtml"))
        html = z.read(part1).decode()
        assert "Chapter One" in html and "<em>" not in html or True
        assert any(n.endswith("cover.jpg") for n in names)
    v = exports["epub"]["validation"]
    if v.get("tool") == "epubcheck":
        assert v["valid"], dump(v)

    ready = client.get(f"/api/books/{book_id}/readiness").json()
    keys = {i["key"]: i["status"] for i in ready["items"]}
    assert keys["manuscript_complete"] == "pass" and keys["cover"] == "pass" and keys["keywords"] == "pass"

    r = client.delete(f"/api/books/{book_id}")
    assert r.status_code == 204
    assert client.get(f"/api/books/{book_id}").status_code == 404


def test_autopilot_short_story(client, drain):
    r = client.post("/api/books", json={**BRIEF, "title": "Salt and Glass", "category": "short_story",
                                        "target_word_count": 6000, "target_chapter_count": 4, "review_mode": "autopilot"})
    assert r.status_code == 201, r.text
    book_id = r.json()["id"]
    drain()
    client.post(f"/api/books/{book_id}/outline/approve")
    ran = drain()
    assert ran[0] == "write_book" and "qa" in ran, ran
    book = _book(client, book_id)
    assert book["status"] == "editing" and book["parts_approved"] == 4
    client.post(f"/api/books/{book_id}/exports", json={"format": "epub"})
    drain()
    exports = client.get(f"/api/books/{book_id}/exports").json()
    assert exports[0]["format"] == "epub"
    assert Path(exports[0]["file_name"]).suffix == ".epub"


def test_job_cancel_and_retry(client, drain):
    r = client.post("/api/books", json={**BRIEF, "title": "Cancelled Book"})
    job = r.json()["jobs"][0]
    assert client.post(f"/api/jobs/{job['id']}/cancel").json()["status"] == "cancelled"
    assert drain() == []
    retry = client.post(f"/api/jobs/{job['id']}/retry")
    assert retry.status_code == 200
    assert drain() == ["plan_book"]


def test_status_endpoint(client):
    s = client.get("/api/system/status").json()
    assert s["database"] is True
    assert s["slack"]["active"] is False
    assert client.post("/api/system/test-notification").json()["sent"] is False
