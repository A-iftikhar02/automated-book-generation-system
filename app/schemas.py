"""API request/response models."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .catalog import AUDIENCES, CATEGORIES, CONTENT_RATINGS, POVS, TENSES, TRIM_SIZES


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- books ----------

class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=200)
    author_name: str = Field(default="", max_length=200)
    category: str
    genre: str = Field(min_length=1, max_length=50)
    audience: str = "adult"
    content_rating: str = "moderate"
    pov: str = "third_limited"
    tense: str = "past"
    tone: str | None = Field(default=None, max_length=200)
    language: str = "en-US"
    premise: str = Field(min_length=20, description="What the book is about and any direction for the writer.")
    style_notes: str | None = None
    target_word_count: int | None = Field(default=None, ge=300, le=200_000)
    target_chapter_count: int | None = Field(default=None, ge=1, le=120)
    review_mode: Literal["manual", "autopilot"] = "manual"
    writer_model: str | None = None
    editor_model: str | None = None

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"Unknown category. Choose one of: {', '.join(CATEGORIES)}")
        return v

    @field_validator("audience")
    @classmethod
    def _audience(cls, v: str) -> str:
        if v not in AUDIENCES:
            raise ValueError(f"Unknown audience. Choose one of: {', '.join(AUDIENCES)}")
        return v

    @field_validator("content_rating")
    @classmethod
    def _rating(cls, v: str) -> str:
        if v not in CONTENT_RATINGS:
            raise ValueError(f"Unknown content rating. Choose one of: {', '.join(CONTENT_RATINGS)}")
        return v

    @field_validator("pov")
    @classmethod
    def _pov(cls, v: str) -> str:
        if v not in POVS:
            raise ValueError(f"Unknown POV. Choose one of: {', '.join(POVS)}")
        return v

    @field_validator("tense")
    @classmethod
    def _tense(cls, v: str) -> str:
        if v not in TENSES:
            raise ValueError(f"Unknown tense. Choose one of: {', '.join(TENSES)}")
        return v


class BookUpdate(BaseModel):
    """Every field optional; only provided fields change."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=200)
    author_name: str | None = Field(default=None, max_length=200)
    tone: str | None = None
    style_notes: str | None = None
    review_mode: Literal["manual", "autopilot"] | None = None
    writer_model: str | None = None
    editor_model: str | None = None
    language: str | None = None
    description: str | None = Field(default=None, max_length=4000)
    back_cover_copy: str | None = None
    keywords: list[str] | None = Field(default=None, max_length=7)
    store_categories: list[str] | None = Field(default=None, max_length=3)
    series_name: str | None = None
    series_number: int | None = Field(default=None, ge=1)
    edition: str | None = None
    publisher: str | None = None
    copyright_holder: str | None = None
    publication_year: int | None = Field(default=None, ge=1900, le=2200)
    isbn_ebook: str | None = None
    isbn_print: str | None = None
    dedication: str | None = None
    acknowledgments: str | None = None
    author_bio: str | None = None

    @field_validator("isbn_ebook", "isbn_print")
    @classmethod
    def _isbn(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        digits = v.replace("-", "").replace(" ", "")
        if not (len(digits) == 13 and digits.isdigit()) and not (len(digits) == 10 and digits[:9].isdigit()):
            raise ValueError("ISBN must have 10 or 13 digits")
        if len(digits) == 13:
            total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
            if (10 - total % 10) % 10 != int(digits[12]):
                raise ValueError("ISBN-13 check digit is invalid")
        return digits

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        cleaned = [k.strip() for k in v if k.strip()]
        if any(len(k) > 50 for k in cleaned):
            raise ValueError("Each keyword must be 50 characters or fewer")
        return cleaned


class BookSummary(ORM):
    id: uuid.UUID
    title: str
    subtitle: str | None
    author_name: str
    category: str
    genre: str
    audience: str
    status: str
    review_mode: str
    target_word_count: int
    target_chapter_count: int
    cost_usd: float
    created_at: datetime
    updated_at: datetime
    words_written: int = 0
    parts_written: int = 0
    parts_approved: int = 0
    has_cover: bool = False
    cover_version: int | None = None  # changes whenever the cover file changes; use as a cache-buster
    quality_score: float | None = None
    active_job: str | None = None


class OutlineOut(ORM):
    id: uuid.UUID
    version: int
    synopsis: str
    chapters: list[dict]
    status: str
    feedback: str | None
    created_at: datetime


class ChapterBrief(ORM):
    number: int
    title: str
    summary: str
    word_count: int
    status: str
    feedback: str | None
    revision: int
    updated_at: datetime


class ChapterOut(ChapterBrief):
    content: str


class RevisionOut(ORM):
    id: uuid.UUID
    revision: int
    title: str
    reason: str
    created_at: datetime
    word_count: int = 0


class JobOut(ORM):
    id: uuid.UUID
    book_id: uuid.UUID | None
    type: str
    payload: dict
    status: str
    progress: float
    message: str | None
    error: str | None
    result: dict
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ExportOut(ORM):
    id: uuid.UUID
    format: str
    options: dict
    file_size: int
    page_count: int | None
    validation: dict
    created_at: datetime
    file_name: str = ""


class BookDetail(BookSummary):
    tone: str | None
    language: str
    content_rating: str
    pov: str
    tense: str
    premise: str
    style_notes: str | None
    writer_model: str | None
    editor_model: str | None
    story_bible: dict
    description: str | None
    back_cover_copy: str | None
    keywords: list
    store_categories: list
    series_name: str | None
    series_number: int | None
    edition: str | None
    publisher: str | None
    copyright_holder: str | None
    publication_year: int | None
    isbn_ebook: str | None
    isbn_print: str | None
    dedication: str | None
    acknowledgments: str | None
    author_bio: str | None
    prompt_tokens: int
    completion_tokens: int
    outline: OutlineOut | None = None
    chapters: list[ChapterBrief] = []
    jobs: list[JobOut] = []
    next_part: int | None = None


# ---------- workflow requests ----------

class Feedback(BaseModel):
    feedback: str = Field(min_length=3)


class OutlineEdit(BaseModel):
    synopsis: str | None = None
    chapters: list[dict] = Field(min_length=1)


class ChapterEdit(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    content: str | None = None


class ApproveChapter(BaseModel):
    continue_writing: bool = True


class ReviseChapter(BaseModel):
    instructions: str = Field(min_length=3)
    mode: Literal["revise", "rewrite"] = "revise"


class WriteRequest(BaseModel):
    notes: str | None = None


class StoryBibleEdit(BaseModel):
    story_bible: dict


# ---------- QA ----------

class QARequest(BaseModel):
    chapters: list[int] | None = None
    include_ai: bool = True


class AutofixRequest(BaseModel):
    chapters: list[int] | None = None


class AIFixRequest(BaseModel):
    issue_ids: list[uuid.UUID] | None = None


class IssueUpdate(BaseModel):
    status: Literal["open", "ignored", "fixed"]


class ApplyFix(BaseModel):
    replacement: str | None = None


class IssueOut(ORM):
    id: uuid.UUID
    chapter_number: int | None
    category: str
    check: str
    severity: str
    source: str
    message: str
    excerpt: str | None
    suggestion: str | None
    offset: int | None
    length: int | None
    matched: str | None
    replacements: list
    status: str
    created_at: datetime


class QARunOut(ORM):
    id: uuid.UUID
    chapter_numbers: list
    include_ai: bool
    status: str
    score: float | None
    stats: dict
    warnings: list
    created_at: datetime
    completed_at: datetime | None


# ---------- publishing ----------

class MetadataRequest(BaseModel):
    overwrite: bool = True


class CoverRequest(BaseModel):
    use_ai: bool = True
    prompt: str | None = Field(default=None, max_length=1500)


class ExportRequest(BaseModel):
    format: Literal["epub", "print_pdf", "cover_wrap_pdf", "docx", "txt"]
    trim_size: str = "6x9"
    paper: Literal["white", "cream"] = "white"
    large_print: bool = False

    @field_validator("trim_size")
    @classmethod
    def _trim(cls, v: str) -> str:
        if v not in TRIM_SIZES:
            raise ValueError(f"Unknown trim size. Choose one of: {', '.join(TRIM_SIZES)}")
        return v
