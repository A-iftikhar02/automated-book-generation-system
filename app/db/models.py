import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Book(TimestampMixin, Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Creative brief
    title: Mapped[str] = mapped_column(String(300))
    subtitle: Mapped[str | None] = mapped_column(String(300))
    author_name: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[str] = mapped_column(String(50))
    genre: Mapped[str] = mapped_column(String(50))
    audience: Mapped[str] = mapped_column(String(30), default="adult")
    content_rating: Mapped[str] = mapped_column(String(20), default="moderate")
    pov: Mapped[str] = mapped_column(String(30), default="third_limited")
    tense: Mapped[str] = mapped_column(String(20), default="past")
    tone: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10), default="en-US")
    premise: Mapped[str] = mapped_column(Text)
    style_notes: Mapped[str | None] = mapped_column(Text)
    target_word_count: Mapped[int] = mapped_column(Integer)
    target_chapter_count: Mapped[int] = mapped_column(Integer)

    # Workflow
    status: Mapped[str] = mapped_column(String(30), default="planning")
    review_mode: Mapped[str] = mapped_column(String(20), default="manual")  # manual | autopilot
    writer_model: Mapped[str | None] = mapped_column(String(500))  # a model chain until the first prose pins one
    editor_model: Mapped[str | None] = mapped_column(String(500))
    story_bible: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Publishing metadata (Amazon KDP / Apple Books)
    description: Mapped[str | None] = mapped_column(Text)
    back_cover_copy: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    store_categories: Mapped[list] = mapped_column(JSONB, default=list)
    series_name: Mapped[str | None] = mapped_column(String(200))
    series_number: Mapped[int | None] = mapped_column(Integer)
    edition: Mapped[str | None] = mapped_column(String(50))
    publisher: Mapped[str | None] = mapped_column(String(200))
    copyright_holder: Mapped[str | None] = mapped_column(String(200))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    isbn_ebook: Mapped[str | None] = mapped_column(String(20))
    isbn_print: Mapped[str | None] = mapped_column(String(20))
    dedication: Mapped[str | None] = mapped_column(Text)
    acknowledgments: Mapped[str | None] = mapped_column(Text)
    author_bio: Mapped[str | None] = mapped_column(Text)
    cover_image_path: Mapped[str | None] = mapped_column(String(500))

    # LLM spend tracking
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    outlines: Mapped[list["Outline"]] = relationship(back_populates="book", cascade="all, delete-orphan", order_by="Outline.version")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="book", cascade="all, delete-orphan", order_by="Chapter.number")


class Outline(Base):
    __tablename__ = "outlines"
    __table_args__ = (UniqueConstraint("book_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    synopsis: Mapped[str] = mapped_column(Text, default="")
    # [{number, title, synopsis, beats: [str], target_words}]
    chapters: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(30), default="pending_review")  # pending_review | changes_requested | approved
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    book: Mapped[Book] = relationship(back_populates="outlines")


class Chapter(TimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    # pending_review | changes_requested | approved
    status: Mapped[str] = mapped_column(String(30), default="pending_review")
    feedback: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)

    book: Mapped[Book] = relationship(back_populates="chapters")
    revisions: Mapped[list["ChapterRevision"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan", order_by="ChapterRevision.revision"
    )


class ChapterRevision(Base):
    __tablename__ = "chapter_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(50))  # generated | revised | rewritten | manual_edit | qa_fix | restored
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chapter: Mapped[Chapter] = relationship(back_populates="revisions")


class QARun(Base):
    __tablename__ = "qa_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    chapter_numbers: Mapped[list] = mapped_column(JSONB, default=list)
    include_ai: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | completed | failed
    score: Mapped[float | None] = mapped_column(Float)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QAIssue(Base):
    __tablename__ = "qa_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qa_runs.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    chapter_number: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(40))
    check: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20))  # critical | major | minor | info
    source: Mapped[str] = mapped_column(String(20))  # languagetool | rule | ai
    message: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    offset: Mapped[int | None] = mapped_column(Integer)
    length: Mapped[int | None] = mapped_column(Integer)
    matched: Mapped[str | None] = mapped_column(Text)  # exact text at offset when detected; guards stale fixes
    replacements: Mapped[list] = mapped_column(JSONB, default=list)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | fixed | ignored | superseded
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued | running | completed | failed | cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    format: Mapped[str] = mapped_column(String(30))
    options: Mapped[dict] = mapped_column(JSONB, default=dict)
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer)
    validation: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
