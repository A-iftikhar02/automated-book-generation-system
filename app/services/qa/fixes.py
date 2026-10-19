"""Applying QA fixes: single suggestions, bulk mechanical auto-fix and AI-assisted revision."""

import re
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import Book, Chapter, ChapterRevision, QAIssue
from ..generation import get_chapter, revise_chapter
from ..text import word_count

ProgressFn = Callable[[float, str], None]

# Categories where taking the (single) suggested replacement is safe without human review.
SAFE_CATEGORIES = {"typography", "punctuation", "spelling", "grammar", "capitalization", "repetition", "encoding", "ai_artifact"}
SAFE_CHECKS_ANY_REPLACEMENTS = {"double_space", "space_before_punctuation", "missing_space_after_punctuation", "repeated_punctuation",
                                "hyphen_as_dash", "repeated_word", "invisible_character", "markdown_bold", "code_or_html",
                                "inline_chapter_heading", "premature_the_end"}

MOJIBAKE_FIXES = {"â€™": "’", "â€˜": "‘", "â€œ": "“", "â€\x9d": "”", "â€”": "—", "â€“": "–", "â€¦": "…", "Ã©": "é", "Ã¨": "è"}
ELISIONS = re.compile(r"(?<![\w’'])'(?=(?:tis|twas|em|cause|til|n|round|bout|cept|nuff)\b|\d0s\b)", re.IGNORECASE)


class FixError(RuntimeError):
    pass


def smart_quotes(text: str) -> str:
    """Convert straight quotes to typographic quotes."""
    text = ELISIONS.sub("’", text)
    text = re.sub(r"(?<=\w)'(?=\w)", "’", text)  # contractions / possessives
    text = re.sub(r"(?<=[\w.,!?;:…—])'", "’", text)  # closing single / plural possessive
    text = re.sub(r"'", "‘", text)  # remaining are opening single quotes
    text = re.sub(r'(^|[\s(\[{—–-])"', r"\1“", text)
    text = text.replace('"', "”")
    return text


def normalize_typography(text: str) -> str:
    for bad, good in MOJIBAKE_FIXES.items():
        text = text.replace(bad, good)
    text = re.sub(r"[​-‍﻿]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", text)
    text = re.sub(r"(?<=\w)[ \t]+(?=[,.;:!?](?:\s|$))", "", text)
    text = re.sub(r"\.{4,}", "…", text)
    text = re.sub(r"(?<!\.)\.\.\.(?!\.)", "…", text)
    text = re.sub(r"(?<=\w) ?-- ?(?=\w)|(?<=\w) - (?=\w)", "—", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = smart_quotes(text)
    return text


def _save(db: Session, chapter: Chapter, new_text: str, reason: str) -> None:
    chapter.content = new_text
    chapter.word_count = word_count(new_text)
    chapter.revision = (chapter.revision or 0) + 1
    db.add(ChapterRevision(chapter_id=chapter.id, revision=chapter.revision, title=chapter.title, content=new_text, reason=reason))


def _shift_offsets(db: Session, book_id, chapter_number: int, after: int, delta: int, exclude: uuid.UUID) -> None:
    if delta == 0:
        return
    for other in db.scalars(select(QAIssue).where(QAIssue.book_id == book_id, QAIssue.chapter_number == chapter_number,
                                                  QAIssue.status == "open", QAIssue.offset.is_not(None), QAIssue.id != exclude)).all():
        if other.offset >= after:
            other.offset += delta


def apply_issue_fix(db: Session, issue: QAIssue, replacement: str | None) -> Chapter:
    """Replace the issue's exact span with `replacement` (default: first suggestion)."""
    if issue.status != "open":
        raise FixError("Issue is not open.")
    if issue.chapter_number is None or issue.offset is None or issue.length is None or issue.matched is None:
        raise FixError("This issue is not tied to an exact span of text; edit the chapter manually or use AI fix.")
    if replacement is None:
        if not issue.replacements:
            raise FixError("No suggested replacement for this issue.")
        replacement = issue.replacements[0]
    chapter = get_chapter(db, issue.book_id, issue.chapter_number)
    if chapter is None:
        raise FixError("Chapter not found.")
    start, end = issue.offset, issue.offset + issue.length
    if chapter.content[start:end] != issue.matched:
        raise FixError("The text changed since this check ran. Re-run QA for this chapter.")
    _save(db, chapter, chapter.content[:start] + replacement + chapter.content[end:], "qa_fix")
    issue.status = "fixed"
    _shift_offsets(db, issue.book_id, issue.chapter_number, end, len(replacement) - issue.length, issue.id)
    db.commit()
    return chapter


def autofix_mechanical(db: Session, book: Book, chapter_numbers: list[int] | None, progress: ProgressFn) -> dict:
    """Apply safe suggested replacements plus typography normalisation. Returns counts per chapter."""
    chapters = db.scalars(select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.number)).all()
    targets = [c for c in chapters if chapter_numbers is None or c.number in chapter_numbers]
    report: dict[str, int] = {}
    for idx, ch in enumerate(targets):
        progress(0.05 + 0.9 * idx / max(1, len(targets)), f"Auto-fixing part {ch.number}")
        open_issues = db.scalars(select(QAIssue).where(
            QAIssue.book_id == book.id, QAIssue.chapter_number == ch.number, QAIssue.status == "open",
            QAIssue.offset.is_not(None), QAIssue.matched.is_not(None),
        )).all()
        candidates = []
        for i in open_issues:
            check_name = i.check.split(":", 1)[-1]
            if i.source == "ai" or i.category not in SAFE_CATEGORIES:
                continue
            if check_name in SAFE_CHECKS_ANY_REPLACEMENTS and i.replacements:
                candidates.append(i)
            elif len(i.replacements) == 1 and i.source == "languagetool":
                candidates.append(i)
        text = ch.content
        applied = 0
        last_start = len(text) + 1
        for i in sorted(candidates, key=lambda x: x.offset, reverse=True):
            start, end = i.offset, i.offset + i.length
            if end > last_start or text[start:end] != i.matched:
                continue  # overlapping or stale
            text = text[:start] + i.replacements[0] + text[end:]
            last_start = start
            i.status = "fixed"
            applied += 1
        normalized = normalize_typography(text)
        if normalized != ch.content:
            _save(db, ch, normalized, "qa_fix")
            # Typography-only issues without spans are resolved by normalisation.
            for i in db.scalars(select(QAIssue).where(
                QAIssue.book_id == book.id, QAIssue.chapter_number == ch.number, QAIssue.status == "open",
                QAIssue.check.in_(["mixed_double_quotes", "straight_quotes", "mixed_apostrophes", "mixed_ellipses"]),
            )).all():
                i.status = "fixed"
                applied += 1
        report[str(ch.number)] = applied
        db.commit()
    return report


def ai_fix_chapter(db: Session, book: Book, number: int, issue_ids: list[uuid.UUID] | None, progress: ProgressFn) -> dict:
    """Ask the writer model to revise the chapter addressing the selected (or all open major/critical) issues."""
    q = select(QAIssue).where(QAIssue.book_id == book.id, QAIssue.chapter_number == number, QAIssue.status == "open")
    if issue_ids:
        q = q.where(QAIssue.id.in_(issue_ids))
    else:
        q = q.where(QAIssue.severity.in_(["critical", "major", "minor"]))
    issues = db.scalars(q).all()
    if not issues:
        raise FixError("No open issues to fix in this part.")
    issues = sorted(issues, key=lambda i: {"critical": 0, "major": 1, "minor": 2, "info": 3}.get(i.severity, 4))[:40]
    lines = []
    for i in issues:
        line = f"- [{i.severity}/{i.category}] {i.message}"
        if i.excerpt:
            line += f' Text: "{i.excerpt[:200]}"'
        if i.suggestion:
            line += f" Fix: {i.suggestion}"
        lines.append(line)
    instructions = "Fix every problem below found by the copy-editor and QA tools. Do not introduce new problems.\n" + "\n".join(lines)
    revise_chapter(db, book, number, instructions, "revise", progress, keep_status=True)
    for i in issues:
        i.status = "fixed"
    db.commit()
    return {"fixed": len(issues)}
