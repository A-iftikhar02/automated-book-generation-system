"""Runs QA over a book or a subset of its parts, persists issues and computes quality scores.

Issue lifecycle: open -> fixed | ignored. When a part is re-checked, its previous open issues from the same
sources are marked `superseded`; issues whose fingerprint was ignored before stay ignored.
"""

import logging
import math
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...catalog import get_category
from ...config import settings
from ...db.models import Book, Chapter, QAIssue, QARun
from .. import llm
from ..generation import editor_model, latest_outline
from ..text import paragraphs, word_count
from . import book_rules, editorial, grammar, rules
from .base import SEVERITY_ORDER, SEVERITY_WEIGHTS, Issue

logger = logging.getLogger(__name__)
ProgressFn = Callable[[float, str], None]

MECHANICAL_SOURCES = ("rule", "languagetool")


def grade_for(score: float) -> str:
    if score >= 90:
        return "Publish-ready"
    if score >= 80:
        return "Good: polish recommended"
    if score >= 65:
        return "Needs editing"
    return "Not ready"


def chapter_score(issues: list[Issue] | list[QAIssue], words: int) -> float:
    """100 minus a severity-weighted issue density per 1,000 words.

    Repeats of the same problem (same check, same text) are one editorial decision, so a group of n identical
    issues weighs 1 + log2(n) times a single issue instead of n times."""
    groups: dict[tuple[str, str], list] = {}
    for i in issues:
        groups.setdefault((i.check, (i.matched or i.message or "").lower()), []).append(i)
    weighted = sum(
        max(SEVERITY_WEIGHTS.get(i.severity, 0) for i in group) * (1 + math.log2(len(group))) for group in groups.values()
    )
    score = 100 - 3.0 * weighted / max(1.0, words / 1000)
    if any(i.severity == "critical" for i in issues):
        score = min(score, 69)
    return round(max(0.0, min(100.0, score)), 1)


def known_vocabulary(book: Book, chapters: list[Chapter]) -> set[str]:
    """Words that must not be flagged as misspellings: bible names/terms and frequent capitalised words."""
    bible = book.story_bible or {}
    vocab: set[str] = set()
    for key in ("characters", "settings", "glossary", "key_concepts"):
        for item in bible.get(key) or []:
            if isinstance(item, dict):
                for field in ("name", "term"):
                    if item.get(field):
                        vocab.update(w.lower().strip("’'") for w in str(item[field]).replace("-", " ").split())
    for w in (book.title + " " + (book.author_name or "")).split():
        vocab.add(w.lower().strip(".,:;!?’'"))
    proper = book_rules._proper_nouns([book_rules.PartText(c.number, c.title, c.content) for c in chapters])
    vocab.update(n.lower() for n, c in proper.items() if c >= 3)
    return vocab


def _dedupe(issues: list[Issue]) -> list[Issue]:
    """Drop rule-based span issues that LanguageTool already reported for the same span."""
    lt_spans = [(i.offset, i.offset + (i.length or 0)) for i in issues if i.source == "languagetool" and i.offset is not None]
    out = []
    for i in issues:
        if i.source == "rule" and i.offset is not None and i.check in ("repeated_word", "double_space", "space_before_punctuation"):
            if any(a <= i.offset < b or a < i.offset + (i.length or 0) <= b for a, b in lt_spans):
                continue
        out.append(i)
    return out


def run_qa(
    db: Session,
    book: Book,
    *,
    chapter_numbers: list[int] | None,
    include_ai: bool,
    progress: ProgressFn,
) -> QARun:
    category = get_category(book.category)
    all_chapters = db.scalars(select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.number)).all()
    targets = [c for c in all_chapters if chapter_numbers is None or c.number in chapter_numbers]
    full_book = chapter_numbers is None
    outline = latest_outline(db, book.id)
    plans = {p["number"]: p for p in (outline.chapters if outline else [])}
    warnings: list[str] = []
    if include_ai and not llm.chain_available(editor_model(book)):
        warnings.append("No AI provider is configured for the editor model: AI editorial checks were skipped.")
        include_ai = False

    run = QARun(book_id=book.id, chapter_numbers=[c.number for c in targets], include_ai=include_ai, status="running")
    db.add(run)
    db.commit()

    lt_ok = grammar.is_available()
    if not lt_ok:
        warnings.append(f"LanguageTool is not reachable at {settings.LANGUAGETOOL_URL}: spelling/grammar checks were skipped. "
                        "Start it with `docker compose up -d languagetool`.")

    vocab = known_vocabulary(book, all_chapters)
    bible = book.story_bible or {}
    issues: list[Issue] = []
    chapter_stats: dict[str, dict] = {}
    editorial_notes: dict[str, dict] = {}
    total_steps = len(targets) + (1 if full_book else 0)

    for idx, ch in enumerate(targets):
        progress(0.05 + 0.85 * idx / max(1, total_steps), f"Checking {category.part_label.lower()} {ch.number}")
        plan = plans.get(ch.number, {"number": ch.number, "title": ch.title})
        ctx = rules.ChapterContext(
            number=ch.number, title=ch.title, target_words=int(plan.get("target_words") or 0),
            is_last=ch.number == max(plans or {ch.number: None}), fiction=category.fiction, structure=category.structure,
            audience=book.audience, content_rating=book.content_rating, pov=book.pov, tense=book.tense,
            language=book.language, known_names=vocab,
        )
        ch_issues, stats = rules.check_chapter(ch.content, ctx)
        if lt_ok and ch.content.strip():
            try:
                lt = grammar.check(ch.content, language=book.language, ignore_words=vocab, poetry=category.structure == "poems")
                for i in lt:
                    i.chapter_number = ch.number
                ch_issues = _dedupe(lt + ch_issues)
            except grammar.LanguageToolUnavailable as e:
                lt_ok = False
                warnings.append(str(e))
        if include_ai and ch.content.strip():
            try:
                previous = [(c.number, c.title, c.summary) for c in all_chapters if c.number < ch.number and c.summary]
                ai_issues, notes = editorial.review_chapter(
                    book=book, category=category, bible=bible, plan=plan, previous=previous, number=ch.number, text=ch.content
                )
                ch_issues += ai_issues
                editorial_notes[str(ch.number)] = notes
            except Exception as e:
                logger.warning("Editorial review failed for part %s: %s", ch.number, e)
                warnings.append(f"AI editorial review failed for part {ch.number}: {e}")
        stats["score"] = chapter_score([i for i in ch_issues if i.chapter_number == ch.number], stats["words"])
        stats["issues"] = len(ch_issues)
        chapter_stats[str(ch.number)] = stats
        issues += ch_issues

    book_summary: dict = {}
    if full_book:
        progress(0.9, "Whole-book checks")
        parts = [book_rules.PartText(c.number, c.title, c.content) for c in all_chapters]
        issues += book_rules.check_book(book, category, parts, len(plans), bible)
        if include_ai and all_chapters:
            try:
                opening = "\n\n".join(paragraphs(all_chapters[0].content)[:12])
                ai_issues, book_summary = editorial.review_book(
                    book=book, category=category, bible=bible, outline=outline.chapters if outline else [],
                    summaries=[(c.number, c.title, c.summary) for c in all_chapters], opening=opening,
                )
                issues += ai_issues
            except Exception as e:
                logger.warning("Whole-book editorial review failed: %s", e)
                warnings.append(f"AI whole-book review failed: {e}")

    sources = list(MECHANICAL_SOURCES) + (["ai"] if include_ai else [])
    _persist(db, book, run, issues, [c.number for c in targets], full_book, sources)

    # Book score from all currently open issues, so partial re-runs update it correctly.
    current = db.scalars(select(QAIssue).where(QAIssue.book_id == book.id, QAIssue.status == "open")).all()
    words_by_ch = {c.number: c.word_count or word_count(c.content) for c in all_chapters}
    per_chapter = {}
    for n, w in words_by_ch.items():
        per_chapter[n] = chapter_score([i for i in current if i.chapter_number == n], w)
    total_words = sum(words_by_ch.values())
    weighted_avg = sum(per_chapter[n] * words_by_ch[n] for n in per_chapter) / max(1, total_words) if per_chapter else 0
    book_level = [i for i in current if i.chapter_number is None]
    penalty = min(30.0, sum({"critical": 8, "major": 3, "minor": 1}.get(i.severity, 0) for i in book_level))
    score = round(max(0.0, weighted_avg - penalty), 1)
    if any(i.severity == "critical" for i in current):
        score = min(score, 69.0)

    run.score = score
    run.stats = {
        "scope": "book" if full_book else "parts",
        "chapters": chapter_stats,
        "chapter_scores": {str(k): v for k, v in per_chapter.items()},
        "total_words": total_words,
        "grade": grade_for(score),
        "editorial": editorial_notes,
        "book_review": book_summary,
        "languagetool": lt_ok,
    }
    run.warnings = warnings
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    progress(1.0, f"QA complete: score {score} ({grade_for(score)})")
    return run


def _persist(db: Session, book: Book, run: QARun, issues: list[Issue], numbers: list[int], full_book: bool, sources: list[str]) -> None:
    scope = QAIssue.chapter_number.in_(numbers)
    if full_book:
        scope = scope | QAIssue.chapter_number.is_(None)
    db.execute(
        update(QAIssue)
        .where(QAIssue.book_id == book.id, QAIssue.status == "open", QAIssue.source.in_(sources), scope)
        .values(status="superseded")
    )
    ignored = set(db.scalars(select(QAIssue.fingerprint).where(QAIssue.book_id == book.id, QAIssue.status == "ignored")).all())
    issues.sort(key=lambda i: (i.chapter_number or 0, SEVERITY_ORDER.get(i.severity, 9), i.offset or 0))
    seen: set[str] = set()
    for i in issues:
        fp = i.fingerprint()
        if fp in seen and i.offset is None:
            continue
        seen.add(fp)
        if fp in ignored:
            continue
        db.add(QAIssue(
            run_id=run.id, book_id=book.id, chapter_number=i.chapter_number, category=i.category, check=i.check,
            severity=i.severity, source=i.source, message=i.message[:4000], excerpt=(i.excerpt or None),
            suggestion=i.suggestion, offset=i.offset, length=i.length, matched=i.matched,
            replacements=i.replacements, fingerprint=fp, status="open",
        ))
    db.commit()
