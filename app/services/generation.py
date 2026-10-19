"""Book generation pipeline: story bible -> outline -> chapters (with context chaining) -> summaries."""

import logging
import math
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..catalog import get_category
from ..config import settings
from ..db.models import Book, Chapter, ChapterRevision, Outline
from . import llm, prompts
from .notifications import notify
from .text import clean_generated_prose, tail_words, word_count

logger = logging.getLogger(__name__)

SEGMENT_WORDS = 2200  # longest stretch requested in a single call; longer chapters are written in segments
MIN_LENGTH_RATIO = 0.8  # below this fraction of the target, ask the model to continue
MAX_CONTINUATIONS = 2

ProgressFn = Callable[[float, str], None]


class GenerationError(RuntimeError):
    pass


def writer_model(book: Book) -> str:
    """The book's writer: its pinned model once prose exists, otherwise the configured fallback chain."""
    return book.writer_model or settings.WRITER_MODELS


def editor_model(book: Book) -> str:
    return book.editor_model or settings.EDITOR_MODELS


def _pin_writer(db: Session, book: Book, model: str) -> None:
    """Lock the book to the model that wrote its first prose, so every chapter keeps the same voice.

    Fallback between providers is fine for planning and editing, but switching writers mid-book changes the style."""
    if not book.writer_model or "," in book.writer_model:
        book.writer_model = model
        db.commit()
        logger.info("Pinned writer for '%s' to %s", book.title, model)


def latest_outline(db: Session, book_id) -> Outline | None:
    return db.scalars(select(Outline).where(Outline.book_id == book_id).order_by(Outline.version.desc()).limit(1)).first()


def get_chapter(db: Session, book_id, number: int) -> Chapter | None:
    return db.scalars(select(Chapter).where(Chapter.book_id == book_id, Chapter.number == number)).first()


def _normalize_outline(raw: dict, expected: int, target_total: int) -> tuple[str, list[dict]]:
    chapters = raw.get("chapters") if isinstance(raw, dict) else None
    if not isinstance(chapters, list) or not chapters:
        raise GenerationError("The model did not return any outline chapters.")
    default_words = max(200, target_total // max(1, len(chapters)))
    normalized = []
    for i, ch in enumerate(chapters, start=1):
        if not isinstance(ch, dict):
            continue
        beats = ch.get("beats") or []
        normalized.append(
            {
                "number": i,
                "title": str(ch.get("title") or f"Part {i}").strip(),
                "synopsis": str(ch.get("synopsis") or "").strip(),
                "beats": [str(b).strip() for b in beats if str(b).strip()] if isinstance(beats, list) else [],
                "target_words": int(ch.get("target_words") or default_words),
            }
        )
    # Rescale targets so the total matches the book target.
    total = sum(c["target_words"] for c in normalized) or 1
    scale = target_total / total
    for c in normalized:
        c["target_words"] = max(150, int(round(c["target_words"] * scale / 50.0) * 50))
    if abs(len(normalized) - expected) > max(2, expected // 5):
        logger.warning("Outline has %s parts, expected %s", len(normalized), expected)
    return str(raw.get("synopsis") or "").strip(), normalized


def plan_book(db: Session, book: Book, progress: ProgressFn) -> Outline:
    """Create the story bible and the first outline version."""
    category = get_category(book.category)
    progress(0.05, "Building story bible")
    bible = llm.complete_json(
        model=writer_model(book),
        system=prompts.WRITER_SYSTEM,
        prompt=prompts.story_bible_prompt(book, category),
        max_tokens=6000,
        temperature=0.9,
        book_id=book.id,
    )
    if not isinstance(bible, dict):
        raise GenerationError("Story bible must be a JSON object.")
    book.story_bible = bible
    db.commit()

    progress(0.5, "Outlining")
    outline = _generate_outline(db, book, feedback=None, previous=None)
    book.status = "outline_review"
    db.commit()
    notify(f"Outline ready for review: '{book.title}'")
    return outline


def _generate_outline(db: Session, book: Book, feedback: str | None, previous: Outline | None) -> Outline:
    category = get_category(book.category)
    raw = llm.complete_json(
        model=writer_model(book),
        system=prompts.WRITER_SYSTEM,
        prompt=prompts.outline_prompt(book, category, book.story_bible or {}, feedback, previous.chapters if previous else None),
        max_tokens=12000,
        temperature=0.8,
        book_id=book.id,
    )
    synopsis, chapters = _normalize_outline(raw, book.target_chapter_count, book.target_word_count)
    version = (previous.version + 1) if previous else 1
    outline = Outline(book_id=book.id, version=version, synopsis=synopsis, chapters=chapters, status="pending_review")
    db.add(outline)
    book.target_chapter_count = len(chapters)
    db.commit()
    return outline


def revise_outline(db: Session, book: Book, feedback: str, progress: ProgressFn) -> Outline:
    previous = latest_outline(db, book.id)
    if previous is None:
        raise GenerationError("No outline to revise.")
    progress(0.1, "Revising outline")
    outline = _generate_outline(db, book, feedback=feedback, previous=previous)
    book.status = "outline_review"
    db.commit()
    notify(f"Revised outline (v{outline.version}) ready for review: '{book.title}'")
    return outline


def _previous_context(db: Session, book: Book, number: int) -> tuple[list[tuple[int, str, str]], str]:
    prev = db.scalars(
        select(Chapter).where(Chapter.book_id == book.id, Chapter.number < number).order_by(Chapter.number)
    ).all()
    summaries = [(c.number, c.title, c.summary) for c in prev if c.summary]
    tail = tail_words(prev[-1].content, 600) if prev and prev[-1].number == number - 1 else ""
    return summaries, tail


def _split_beats(beats: list[str], parts: int) -> list[list[str]]:
    if not beats:
        return [["Continue the chapter according to its synopsis."] for _ in range(parts)]
    size = math.ceil(len(beats) / parts)
    return [beats[i : i + size] for i in range(0, len(beats), size)]


def _draft_text(
    db: Session, book: Book, plan: dict, outline_chapters: list, progress: ProgressFn, notes: str | None = None
) -> str:
    category = get_category(book.category)
    target = int(plan.get("target_words") or 1500)
    beats = plan.get("beats") or []
    part_count = max(1, math.ceil(target / SEGMENT_WORDS))
    if beats:
        part_count = min(part_count, len(beats))
    beat_groups = _split_beats(beats, part_count)
    part_count = len(beat_groups)
    summaries, prev_tail = _previous_context(db, book, plan["number"])
    keep_breaks = category.structure == "poems"

    text = ""
    for i, group in enumerate(beat_groups):
        words = max(150, target // part_count)
        progress(0.1 + 0.6 * i / part_count, f"Writing {category.part_label.lower()} {plan['number']} ({i + 1}/{part_count})")
        result = llm.complete(
            model=writer_model(book),
            system=prompts.WRITER_SYSTEM,
            prompt=prompts.chapter_prompt(
                book=book,
                category=category,
                bible=book.story_bible or {},
                outline_chapters=outline_chapters,
                chapter=plan,
                previous_summaries=summaries,
                previous_tail=prev_tail,
                part_index=i,
                part_count=part_count,
                beats=group,
                words=words,
                written_so_far=tail_words(text, 900) if text else "",
                notes=notes,
            ),
            max_tokens=min(16000, int(words * 2.2) + 1500),
            temperature=0.85,
            book_id=book.id,
        )
        _pin_writer(db, book, result.model)
        segment = clean_generated_prose(result.text, keep_line_breaks=keep_breaks, title=plan.get("title"))
        text = f"{text}\n\n{segment}".strip() if text else segment

    for attempt in range(MAX_CONTINUATIONS):
        current = word_count(text)
        if current >= target * MIN_LENGTH_RATIO or category.structure == "poems":
            break
        progress(0.75, f"Extending {category.part_label.lower()} {plan['number']} ({current}/{target} words)")
        result = llm.complete(
            model=writer_model(book),
            system=prompts.WRITER_SYSTEM,
            prompt=prompts.continue_prompt(book, category, plan, tail_words(text, 1200), target - current),
            max_tokens=min(12000, int((target - current) * 2.2) + 1500),
            temperature=0.85,
            book_id=book.id,
        )
        text = f"{text}\n\n{clean_generated_prose(result.text, keep_line_breaks=keep_breaks)}".strip()
    if not text.strip():
        raise GenerationError("The model returned no usable text.")
    return text


def _summarize_and_track(db: Session, book: Book, plan: dict, text: str) -> str:
    """Summarise the chapter and merge newly established facts into the story bible."""
    category = get_category(book.category)
    bible = dict(book.story_bible or {})
    try:
        data = llm.complete_json(
            model=editor_model(book),
            system=prompts.EDITOR_SYSTEM,
            prompt=prompts.summary_prompt(book, category, plan, text, bible),
            max_tokens=4000,
            temperature=0.2,
            book_id=book.id,
        )
    except llm.LLMError:
        logger.warning("Summary JSON failed; falling back to plain summary")
        data = {"summary": llm.complete(
            model=editor_model(book), system=prompts.EDITOR_SYSTEM,
            prompt=f"Summarise this text in 3-5 sentences, including the ending state:\n\n{text}",
            max_tokens=600, temperature=0.2, book_id=book.id,
        ).text}

    if category.structure in ("chapters", "scenes"):
        characters = list(bible.get("characters") or [])
        known = {str(c.get("name", "")).lower() for c in characters if isinstance(c, dict)}
        new_characters = data.get("new_characters")
        for nc in new_characters if isinstance(new_characters, list) else []:
            if isinstance(nc, dict) and nc.get("name") and str(nc["name"]).lower() not in known:
                characters.append({**nc, "introduced_in": plan["number"]})
                known.add(str(nc["name"]).lower())
        bible["characters"] = characters
        facts = [f for f in bible.get("continuity_facts") or [] if not (isinstance(f, dict) and f.get("chapter") == plan["number"])]
        new_facts = data.get("continuity_facts")
        new_facts = new_facts if isinstance(new_facts, list) else []
        facts.extend({"chapter": plan["number"], "fact": str(f)} for f in new_facts[:12])
        bible["continuity_facts"] = facts[-250:]
        book.story_bible = bible
        flag_modified(book, "story_bible")
    return str(data.get("summary") or "").strip()


def _save_chapter(db: Session, book: Book, plan: dict, text: str, summary: str, reason: str, status: str) -> Chapter:
    chapter = get_chapter(db, book.id, plan["number"])
    if chapter is None:
        chapter = Chapter(book_id=book.id, number=plan["number"], revision=0)
        db.add(chapter)
    chapter.title = plan.get("title") or chapter.title
    chapter.content = text
    chapter.summary = summary
    chapter.word_count = word_count(text)
    chapter.status = status
    chapter.revision = (chapter.revision or 0) + 1
    db.flush()
    db.add(ChapterRevision(chapter_id=chapter.id, revision=chapter.revision, title=chapter.title, content=text, reason=reason))
    db.commit()
    return chapter


def _approved_outline_plan(db: Session, book: Book, number: int) -> tuple[Outline, dict]:
    outline = latest_outline(db, book.id)
    if outline is None or outline.status != "approved":
        raise GenerationError("The outline must be approved before writing.")
    plan = next((c for c in outline.chapters if c.get("number") == number), None)
    if plan is None:
        raise GenerationError(f"The outline has no part {number}.")
    return outline, plan


def write_chapter(db: Session, book: Book, number: int, progress: ProgressFn, notes: str | None = None, reason: str = "generated") -> Chapter:
    outline, plan = _approved_outline_plan(db, book, number)
    text = _draft_text(db, book, plan, outline.chapters, progress, notes=notes)
    progress(0.85, "Summarising for continuity")
    summary = _summarize_and_track(db, book, plan, text)
    status = "approved" if book.review_mode == "autopilot" else "pending_review"
    chapter = _save_chapter(db, book, plan, text, summary, reason, status)
    if book.status in ("outline_review", "planning"):
        book.status = "writing"
    refresh_book_status(db, book)
    if book.review_mode == "manual":
        notify(f"{get_category(book.category).part_label} {number} of '{book.title}' is ready for review ({chapter.word_count:,} words).")
    return chapter


def revise_chapter(
    db: Session, book: Book, number: int, instructions: str, mode: str, progress: ProgressFn, keep_status: bool = False
) -> Chapter:
    """mode='revise' edits the existing draft; mode='rewrite' drafts it again from the outline with the notes applied.

    keep_status=True keeps an approved chapter approved (used for QA fixes that don't change the story)."""
    outline, plan = _approved_outline_plan(db, book, number)
    chapter = get_chapter(db, book.id, number)
    if chapter is None:
        raise GenerationError(f"Part {number} has not been written yet.")
    if mode == "rewrite":
        return write_chapter(db, book, number, progress, notes=instructions, reason="rewritten")

    category = get_category(book.category)
    summaries, _ = _previous_context(db, book, number)
    target = max(int(plan.get("target_words") or 0), chapter.word_count)
    progress(0.2, f"Revising {category.part_label.lower()} {number}")
    result = llm.complete(
        model=writer_model(book),
        system=prompts.WRITER_SYSTEM,
        prompt=prompts.revise_prompt(
            book=book, category=category, bible=book.story_bible or {}, chapter=plan,
            previous_summaries=summaries, current_text=chapter.content, instructions=instructions, target_words=target,
        ),
        max_tokens=min(20000, int(target * 2.2) + 2000),
        temperature=0.7,
        book_id=book.id,
    )
    text = clean_generated_prose(result.text, keep_line_breaks=category.structure == "poems", title=plan.get("title"))
    if word_count(text) < 0.5 * chapter.word_count:
        raise GenerationError("The revision came back much shorter than the original (likely truncated); kept the original.")
    progress(0.8, "Summarising for continuity")
    summary = _summarize_and_track(db, book, plan, text)
    if keep_status and chapter.status == "approved":
        status = "approved"
    else:
        status = "approved" if book.review_mode == "autopilot" else "pending_review"
    saved = _save_chapter(db, book, plan, text, summary, "qa_fix" if keep_status else "revised", status)
    refresh_book_status(db, book)
    return saved


def next_chapter_number(db: Session, book: Book) -> int | None:
    outline = latest_outline(db, book.id)
    if outline is None:
        return None
    written = {c.number for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()}
    for plan in outline.chapters:
        if plan["number"] not in written:
            return plan["number"]
    return None


def refresh_book_status(db: Session, book: Book) -> None:
    """Derive the workflow status from outline/chapter state."""
    outline = latest_outline(db, book.id)
    chapters = db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()
    if outline is None:
        book.status = "planning"
    elif outline.status != "approved":
        book.status = "outline_review"
    elif len(chapters) >= len(outline.chapters) and all(c.status == "approved" for c in chapters):
        if book.status != "editing":
            notify(f"Manuscript complete for '{book.title}': all parts approved.")
        book.status = "editing"
    else:
        book.status = "writing"
    db.commit()
