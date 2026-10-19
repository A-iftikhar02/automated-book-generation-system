import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import Book, Chapter, Job, QARun
from ..db.session import get_db
from ..services.jobs import ACTIVE


def get_book(book_id: uuid.UUID, db: Session = Depends(get_db)) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    return book


def require_llm() -> None:
    if not settings.llm_configured:
        raise HTTPException(
            503,
            "No AI provider is configured for the writer/editor models. Add an API key (OpenRouter, Gemini, Groq, "
            "Cerebras or Mistral) to .env, make sure WRITER_MODELS/EDITOR_MODELS use that provider, and restart.",
        )


def book_progress(db: Session, book_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Aggregate per-book chapter stats, latest QA score and active job in three queries."""
    out: dict[uuid.UUID, dict] = {bid: {"words_written": 0, "parts_written": 0, "parts_approved": 0,
                                        "quality_score": None, "active_job": None} for bid in book_ids}
    if not book_ids:
        return out
    rows = db.execute(
        select(Chapter.book_id, func.count(), func.coalesce(func.sum(Chapter.word_count), 0),
               func.count().filter(Chapter.status == "approved"))
        .where(Chapter.book_id.in_(book_ids)).group_by(Chapter.book_id)
    ).all()
    for bid, n, words, approved in rows:
        out[bid].update(parts_written=n, words_written=int(words), parts_approved=approved)
    latest = (
        select(QARun.book_id, QARun.score, func.row_number().over(partition_by=QARun.book_id, order_by=QARun.created_at.desc()).label("rn"))
        .where(QARun.book_id.in_(book_ids), QARun.status == "completed").subquery()
    )
    for bid, score, _ in db.execute(select(latest).where(latest.c.rn == 1)).all():
        out[bid]["quality_score"] = score
    for bid, jtype in db.execute(
        select(Job.book_id, Job.type).where(Job.book_id.in_(book_ids), Job.status.in_(ACTIVE)).order_by(Job.created_at)
    ).all():
        out[bid]["active_job"] = out[bid]["active_job"] or jtype
    return out
