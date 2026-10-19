"""Background job handlers. Imported by the worker to register them."""

import uuid

from ..db.models import Book
from . import generation
from .jobs import JobConflict, JobContext, enqueue, handler
from .notifications import notify
from .publishing import service as publishing
from .qa import fixes
from .qa.runner import run_qa


def _book(ctx: JobContext) -> Book:
    book = ctx.db.get(Book, ctx.book_id)
    if book is None:
        raise RuntimeError("Book not found")
    return book


@handler("plan_book")
def plan_book(ctx: JobContext) -> dict:
    book = _book(ctx)
    outline = generation.plan_book(ctx.db, book, ctx.progress)
    return {"outline_version": outline.version, "parts": len(outline.chapters)}


@handler("revise_outline")
def revise_outline(ctx: JobContext) -> dict:
    book = _book(ctx)
    outline = generation.revise_outline(ctx.db, book, ctx.payload["feedback"], ctx.progress)
    return {"outline_version": outline.version}


@handler("write_chapter")
def write_chapter(ctx: JobContext) -> dict:
    book = _book(ctx)
    number = int(ctx.payload["number"])
    if generation.get_chapter(ctx.db, book.id, number) is not None:
        return {"number": number, "skipped": "already written"}  # e.g. a duplicate request; use revise to change it
    chapter = generation.write_chapter(ctx.db, book, int(ctx.payload["number"]), ctx.progress, notes=ctx.payload.get("notes"))
    if ctx.payload.get("run_qa", True):
        ctx.progress(0.92, "Quick quality check")
        run_qa(ctx.db, book, chapter_numbers=[chapter.number], include_ai=False, progress=lambda f, m: None)
    return {"number": chapter.number, "words": chapter.word_count}


@handler("write_book")
def write_book(ctx: JobContext) -> dict:
    """Autopilot: write every remaining part in order, with a quick QA pass after each."""
    book = _book(ctx)
    written = []
    while (number := generation.next_chapter_number(ctx.db, book)) is not None:
        total = len(generation.latest_outline(ctx.db, book.id).chapters)
        base = (number - 1) / total

        def scaled(fraction: float, message: str, base=base, total=total) -> None:
            ctx.progress(base + fraction / total, message)

        chapter = generation.write_chapter(ctx.db, book, number, scaled)
        run_qa(ctx.db, book, chapter_numbers=[chapter.number], include_ai=False, progress=lambda f, m: None)
        written.append(number)
    generation.refresh_book_status(ctx.db, book)
    if ctx.payload.get("full_qa", True) and written:
        try:
            enqueue(ctx.db, "qa", book.id, {"chapters": None, "include_ai": True})
        except JobConflict:
            pass
    notify(f"Autopilot finished writing '{book.title}' ({len(written)} parts).")
    return {"written": written}


@handler("revise_chapter")
def revise_chapter(ctx: JobContext) -> dict:
    book = _book(ctx)
    chapter = generation.revise_chapter(
        ctx.db, book, int(ctx.payload["number"]), ctx.payload["instructions"], ctx.payload.get("mode", "revise"), ctx.progress
    )
    run_qa(ctx.db, book, chapter_numbers=[chapter.number], include_ai=False, progress=lambda f, m: None)
    return {"number": chapter.number, "words": chapter.word_count}


@handler("qa")
def qa(ctx: JobContext) -> dict:
    book = _book(ctx)
    run = run_qa(ctx.db, book, chapter_numbers=ctx.payload.get("chapters"), include_ai=bool(ctx.payload.get("include_ai", True)),
                 progress=ctx.progress)
    if ctx.payload.get("chapters") is None:
        notify(f"Quality check for '{book.title}': score {run.score} ({run.stats.get('grade')}).")
    return {"run_id": str(run.id), "score": run.score}


@handler("autofix")
def autofix(ctx: JobContext) -> dict:
    book = _book(ctx)
    chapters = ctx.payload.get("chapters")
    report = fixes.autofix_mechanical(ctx.db, book, chapters, ctx.progress)
    touched = [int(n) for n in report]
    if touched:
        ctx.progress(0.95, "Re-checking fixed parts")
        run_qa(ctx.db, book, chapter_numbers=touched, include_ai=False, progress=lambda f, m: None)
    return {"fixed": report}


@handler("ai_fix")
def ai_fix(ctx: JobContext) -> dict:
    book = _book(ctx)
    number = int(ctx.payload["number"])
    ids = [uuid.UUID(i) for i in ctx.payload.get("issue_ids") or []] or None
    result = fixes.ai_fix_chapter(ctx.db, book, number, ids, ctx.progress)
    ctx.progress(0.9, "Re-checking")
    run_qa(ctx.db, book, chapter_numbers=[number], include_ai=bool(ctx.payload.get("recheck_ai", True)), progress=lambda f, m: None)
    return result


@handler("metadata")
def metadata(ctx: JobContext) -> dict:
    return publishing.generate_metadata(ctx.db, _book(ctx), bool(ctx.payload.get("overwrite", True)))


@handler("cover")
def cover(ctx: JobContext) -> dict:
    return publishing.generate_cover(ctx.db, _book(ctx), bool(ctx.payload.get("use_ai", True)), ctx.payload.get("prompt"), ctx.progress)


@handler("export")
def export(ctx: JobContext) -> dict:
    e = publishing.run_export(ctx.db, _book(ctx), ctx.payload["format"], ctx.payload.get("options") or {}, ctx.progress)
    return {"export_id": str(e.id), "page_count": e.page_count}
