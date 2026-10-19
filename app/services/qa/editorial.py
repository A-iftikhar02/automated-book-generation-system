"""LLM-based editorial checks: continuity, plot logic, pacing, outline adherence, audience fit, copyright risk,
and a whole-book acquisitions review."""

import re

from rapidfuzz import fuzz

from ...catalog import Category
from ...db.models import Book
from .. import llm, prompts
from ..generation import editor_model
from .base import Issue

CHECK_CATEGORY = {
    "outline_adherence": "structure",
    "continuity": "continuity",
    "timeline": "continuity",
    "anachronism": "continuity",
    "plot_logic": "plot",
    "characterization": "character",
    "pov_tense": "pov_tense",
    "dialogue": "dialogue",
    "pacing": "pacing",
    "show_vs_tell": "style",
    "accuracy": "accuracy",
    "fabrication": "accuracy",
    "clarity": "clarity",
    "structure": "structure",
    "actionability": "content",
    "legal_risk": "compliance",
    "audience_fit": "content",
    "copyright": "compliance",
    "ai_tells": "ai_artifact",
    "unresolved_threads": "plot",
    "arc": "character",
    "repetition": "repetition",
    "ending": "plot",
    "opening_hook": "marketability",
    "market_fit": "marketability",
}
VALID_SEVERITIES = {"critical", "major", "minor", "info"}


def locate(text: str, excerpt: str) -> tuple[int | None, int | None, str | None]:
    """Find the model's quoted excerpt in the text: exact, then whitespace-insensitive, then fuzzy."""
    if not excerpt:
        return None, None, None
    excerpt = excerpt.strip().strip("\"“”…").strip()
    idx = text.find(excerpt)
    if idx >= 0:
        return idx, len(excerpt), excerpt
    pattern = r"\s+".join(re.escape(w) for w in excerpt.split())
    m = re.search(pattern, text, re.IGNORECASE) if pattern else None
    if m:
        return m.start(), m.end() - m.start(), m.group(0)
    if len(excerpt) >= 20:
        al = fuzz.partial_ratio_alignment(excerpt, text, score_cutoff=85)
        if al is not None:
            start, end = al.dest_start, al.dest_end
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            return start, end - start, text[start:end]
    return None, None, None


def _to_issue(raw: dict, *, text: str | None, chapter_number: int | None) -> Issue | None:
    if not isinstance(raw, dict) or not raw.get("message"):
        return None
    check = str(raw.get("check") or "editorial").strip().lower().replace(" ", "_")
    severity = str(raw.get("severity") or "minor").lower()
    if severity not in VALID_SEVERITIES:
        severity = "minor"
    excerpt = str(raw.get("excerpt") or "").strip() or None
    offset = length = matched = None
    if text and excerpt:
        offset, length, matched = locate(text, excerpt)
    number = raw.get("chapter_number", chapter_number)
    return Issue(
        category=CHECK_CATEGORY.get(check, "editorial"),
        check=f"ai:{check}",
        severity=severity,
        source="ai",
        message=str(raw["message"]).strip(),
        excerpt=excerpt,
        suggestion=str(raw.get("suggestion") or "").strip() or None,
        offset=offset,
        length=length,
        matched=matched,
        chapter_number=int(number) if isinstance(number, (int, float)) or (isinstance(number, str) and number.isdigit()) else chapter_number,
    )


def review_chapter(
    *, book: Book, category: Category, bible: dict, plan: dict, previous: list[tuple[int, str, str]], number: int, text: str
) -> tuple[list[Issue], dict]:
    data = llm.complete_json(
        model=editor_model(book),
        system=prompts.EDITOR_SYSTEM,
        prompt=prompts.editorial_qa_prompt(book=book, category=category, bible=bible, chapter=plan, previous_summaries=previous, text=text),
        max_tokens=5000,
        temperature=0.2,
        book_id=book.id,
    )
    issues = [i for raw in (data.get("issues") or [])[:15] if (i := _to_issue(raw, text=text, chapter_number=number))]
    return issues, {"strengths": data.get("strengths") or [], "overall": data.get("overall") or ""}


def review_book(
    *, book: Book, category: Category, bible: dict, outline: list, summaries: list[tuple[int, str, str]], opening: str
) -> tuple[list[Issue], dict]:
    data = llm.complete_json(
        model=editor_model(book),
        system=prompts.EDITOR_SYSTEM,
        prompt=prompts.book_qa_prompt(book, category, bible, outline, summaries, opening),
        max_tokens=5000,
        temperature=0.2,
        book_id=book.id,
    )
    issues = []
    for raw in (data.get("issues") or [])[:12]:
        if isinstance(raw, dict):
            issue = _to_issue(raw, text=None, chapter_number=None)
            if issue:
                issues.append(issue)
    return issues, {"verdict": data.get("verdict"), "summary": data.get("summary") or ""}
