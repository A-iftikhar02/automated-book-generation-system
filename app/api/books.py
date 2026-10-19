import csv
import io
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..catalog import get_category
from ..config import settings
from ..db.models import Book, Chapter, ChapterRevision, Outline
from ..db.session import get_db
from ..services import generation
from ..services import storage
from ..services.jobs import active_jobs, enqueue
from ..services.text import word_count
from .deps import book_progress, get_book, require_llm

router = APIRouter(tags=["books"])


def _cover_info(book: Book) -> dict:
    path = storage.resolve(book.cover_image_path)
    if path is None or not path.exists():
        return {"has_cover": False, "cover_version": None}
    return {"has_cover": True, "cover_version": path.stat().st_mtime_ns // 1_000_000}


def _summary(book: Book, progress: dict) -> dict:
    data = schemas.BookSummary.model_validate(book).model_dump()
    data.update(progress)
    data.update(_cover_info(book))
    return data


def book_detail(db: Session, book: Book) -> dict:
    progress = book_progress(db, [book.id])[book.id]
    data = schemas.BookDetail.model_validate(
        {**{c.name: getattr(book, c.name) for c in Book.__table__.columns}, **progress, **_cover_info(book)}
    ).model_dump()
    outline = generation.latest_outline(db, book.id)
    data["outline"] = schemas.OutlineOut.model_validate(outline).model_dump() if outline else None
    chapters = db.scalars(select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.number)).all()
    data["chapters"] = [schemas.ChapterBrief.model_validate(c).model_dump() for c in chapters]
    data["jobs"] = [schemas.JobOut.model_validate(j).model_dump() for j in active_jobs(db, book.id)]
    data["next_part"] = generation.next_chapter_number(db, book)
    return data


@router.get("/books", response_model=list[schemas.BookSummary])
def list_books(db: Session = Depends(get_db)):
    books = db.scalars(select(Book).order_by(Book.created_at.desc())).all()
    progress = book_progress(db, [b.id for b in books])
    return [_summary(b, progress[b.id]) for b in books]


def _create(db: Session, req: schemas.BookCreate) -> Book:
    category = get_category(req.category)
    if req.audience not in category.allowed_audiences:
        raise HTTPException(400, f"{category.label} supports audiences: {', '.join(category.allowed_audiences)}")
    words = req.target_word_count or category.default_words
    if not category.min_words * 0.5 <= words <= category.max_words * 1.5:
        raise HTTPException(400, f"Target length for a {category.label} should be {category.min_words:,}-{category.max_words:,} words.")
    parts = req.target_chapter_count or category.default_parts
    book = Book(
        **req.model_dump(exclude={"target_word_count", "target_chapter_count"}),
        target_word_count=words,
        target_chapter_count=parts,
        status="planning",
        story_bible={},
        keywords=[],
        store_categories=[],
        copyright_holder=req.author_name or None,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    enqueue(db, "plan_book", book.id)
    return book


@router.post("/books", response_model=schemas.BookDetail, status_code=201, dependencies=[Depends(require_llm)])
def create_book(req: schemas.BookCreate, db: Session = Depends(get_db)):
    return book_detail(db, _create(db, req))


@router.post("/books/import-csv", dependencies=[Depends(require_llm)])
def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Bulk-create books. Columns: title, category, genre, premise (+ any optional BookCreate field)."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file.")
    reader = csv.DictReader(io.StringIO(file.file.read().decode("utf-8-sig")))
    created, errors = [], []
    for i, row in enumerate(reader, start=2):
        row = {k.strip(): v.strip() for k, v in row.items() if k and v and v.strip()}
        try:
            for key in ("target_word_count", "target_chapter_count"):
                if key in row:
                    row[key] = int(row[key])
            book = _create(db, schemas.BookCreate(**row))
            created.append({"row": i, "id": str(book.id), "title": book.title})
        except Exception as e:
            db.rollback()
            errors.append({"row": i, "error": getattr(e, "detail", None) or str(e)})
    return {"created": created, "errors": errors}


@router.get("/books/{book_id}", response_model=schemas.BookDetail)
def get_book_detail(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return book_detail(db, book)


@router.patch("/books/{book_id}", response_model=schemas.BookDetail)
def update_book(req: schemas.BookUpdate, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(book, key, value)
    db.commit()
    return book_detail(db, book)


@router.delete("/books/{book_id}", status_code=204)
def delete_book(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    book_id = book.id
    db.delete(book)
    db.commit()
    shutil.rmtree(Path(settings.STORAGE_DIR) / "books" / str(book_id), ignore_errors=True)


@router.post("/books/{book_id}/replan", response_model=schemas.JobOut, dependencies=[Depends(require_llm)])
def replan(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    """Re-run planning (story bible + new outline version), e.g. after a failed planning job."""
    if db.scalars(select(Chapter.id).where(Chapter.book_id == book.id).limit(1)).first():
        raise HTTPException(409, "Parts have already been written; revise the outline instead.")
    return enqueue(db, "plan_book", book.id)


@router.put("/books/{book_id}/story-bible", response_model=schemas.BookDetail)
def edit_story_bible(req: schemas.StoryBibleEdit, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    book.story_bible = req.story_bible
    db.commit()
    return book_detail(db, book)


# ---------- outline ----------

@router.get("/books/{book_id}/outlines", response_model=list[schemas.OutlineOut])
def list_outlines(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return db.scalars(select(Outline).where(Outline.book_id == book.id).order_by(Outline.version.desc())).all()


@router.put("/books/{book_id}/outline", response_model=schemas.OutlineOut)
def edit_outline(req: schemas.OutlineEdit, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    outline = generation.latest_outline(db, book.id)
    if outline is None:
        raise HTTPException(404, "No outline yet.")
    written = {c.number for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()}
    chapters = []
    for i, ch in enumerate(req.chapters, start=1):
        title = str(ch.get("title") or "").strip()
        if not title:
            raise HTTPException(400, f"Part {i} needs a title.")
        chapters.append({
            "number": i,
            "title": title,
            "synopsis": str(ch.get("synopsis") or "").strip(),
            "beats": [str(b).strip() for b in ch.get("beats") or [] if str(b).strip()],
            "target_words": max(100, int(ch.get("target_words") or 1000)),
        })
    if written:
        old = {c["number"]: c for c in outline.chapters}
        for n in written:
            if n > len(chapters) or (old.get(n, {}).get("title") != chapters[n - 1]["title"]):
                raise HTTPException(409, f"Part {n} is already written; you can only change parts that haven't been written.")
    outline.chapters = chapters
    if req.synopsis is not None:
        outline.synopsis = req.synopsis
    book.target_chapter_count = len(chapters)
    book.target_word_count = sum(c["target_words"] for c in chapters)
    db.commit()
    return outline


@router.post("/books/{book_id}/outline/approve", response_model=schemas.BookDetail)
def approve_outline(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    outline = generation.latest_outline(db, book.id)
    if outline is None:
        raise HTTPException(409, "No outline to approve yet.")
    if outline.status == "approved":
        raise HTTPException(409, "Outline is already approved.")
    if active_jobs(db, book.id):
        raise HTTPException(409, "Wait for the running job to finish.")
    outline.status = "approved"
    book.status = "writing"
    db.commit()
    if settings.llm_configured:
        if book.review_mode == "autopilot":
            enqueue(db, "write_book", book.id)
        elif generation.next_chapter_number(db, book) == 1:
            enqueue(db, "write_chapter", book.id, {"number": 1})
    return book_detail(db, book)


@router.post("/books/{book_id}/outline/revise", response_model=schemas.JobOut, dependencies=[Depends(require_llm)])
def revise_outline(req: schemas.Feedback, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    outline = generation.latest_outline(db, book.id)
    if outline is None:
        raise HTTPException(409, "No outline yet.")
    if db.scalars(select(Chapter.id).where(Chapter.book_id == book.id).limit(1)).first():
        raise HTTPException(409, "Parts have already been written; edit unwritten parts of the outline directly instead.")
    outline.status = "changes_requested"
    outline.feedback = req.feedback
    db.commit()
    return enqueue(db, "revise_outline", book.id, {"feedback": req.feedback})


# ---------- chapters ----------

def _chapter(db: Session, book: Book, number: int) -> Chapter:
    chapter = generation.get_chapter(db, book.id, number)
    if chapter is None:
        raise HTTPException(404, f"Part {number} has not been written.")
    return chapter


@router.get("/books/{book_id}/chapters/{number}", response_model=schemas.ChapterOut)
def get_chapter(number: int, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return _chapter(db, book, number)


@router.put("/books/{book_id}/chapters/{number}", response_model=schemas.ChapterOut)
def edit_chapter(number: int, req: schemas.ChapterEdit, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    chapter = _chapter(db, book, number)
    if req.title is not None:
        chapter.title = req.title.strip()
    if req.content is not None:
        chapter.content = req.content.replace("\r\n", "\n").strip()
        chapter.word_count = word_count(chapter.content)
    chapter.revision += 1
    db.add(ChapterRevision(chapter_id=chapter.id, revision=chapter.revision, title=chapter.title, content=chapter.content,
                           reason="manual_edit"))
    db.commit()
    return chapter


@router.post("/books/{book_id}/chapters/{number}/write", response_model=schemas.JobOut, dependencies=[Depends(require_llm)])
def write_chapter(number: int, req: schemas.WriteRequest | None = None, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    outline = generation.latest_outline(db, book.id)
    if outline is None or outline.status != "approved":
        raise HTTPException(403, "Approve the outline before writing.")
    if not any(c["number"] == number for c in outline.chapters):
        raise HTTPException(404, f"The outline has no part {number}.")
    if generation.get_chapter(db, book.id, number):
        raise HTTPException(409, f"Part {number} already exists; use revise instead.")
    if any(j.type in ("write_chapter", "write_book") for j in active_jobs(db, book.id)):
        raise HTTPException(409, "A part is already being written for this book.")
    if number > 1:
        prev = generation.get_chapter(db, book.id, number - 1)
        if prev is None:
            raise HTTPException(409, f"Write part {number - 1} first.")
        if prev.status != "approved":
            raise HTTPException(409, f"Approve part {number - 1} before writing part {number} (it is '{prev.status}').")
    return enqueue(db, "write_chapter", book.id, {"number": number, "notes": req.notes if req else None})


@router.post("/books/{book_id}/write-all", response_model=schemas.JobOut, dependencies=[Depends(require_llm)])
def write_all(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    outline = generation.latest_outline(db, book.id)
    if outline is None or outline.status != "approved":
        raise HTTPException(403, "Approve the outline before writing.")
    if any(j.type in ("write_chapter", "write_book") for j in active_jobs(db, book.id)):
        raise HTTPException(409, "Writing is already in progress for this book.")
    if generation.next_chapter_number(db, book) is None:
        raise HTTPException(409, "Every part is already written.")
    return enqueue(db, "write_book", book.id)


@router.post("/books/{book_id}/chapters/{number}/approve", response_model=schemas.BookDetail)
def approve_chapter(number: int, req: schemas.ApproveChapter | None = None, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    chapter = _chapter(db, book, number)
    chapter.status = "approved"
    chapter.feedback = None
    db.commit()
    generation.refresh_book_status(db, book)
    cont = req.continue_writing if req else True
    nxt = generation.next_chapter_number(db, book)
    if cont and settings.llm_configured and nxt == number + 1 and not any(j.type in ("write_chapter", "write_book") for j in active_jobs(db, book.id)):
        enqueue(db, "write_chapter", book.id, {"number": nxt})
    return book_detail(db, book)


@router.post("/books/{book_id}/chapters/{number}/revise", response_model=schemas.JobOut, dependencies=[Depends(require_llm)])
def revise_chapter(number: int, req: schemas.ReviseChapter, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    chapter = _chapter(db, book, number)
    chapter.status = "changes_requested"
    chapter.feedback = req.instructions
    db.commit()
    return enqueue(db, "revise_chapter", book.id, {"number": number, "instructions": req.instructions, "mode": req.mode})


@router.get("/books/{book_id}/chapters/{number}/revisions", response_model=list[schemas.RevisionOut])
def list_revisions(number: int, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    chapter = _chapter(db, book, number)
    revs = db.scalars(select(ChapterRevision).where(ChapterRevision.chapter_id == chapter.id).order_by(ChapterRevision.revision.desc())).all()
    return [{**schemas.RevisionOut.model_validate(r).model_dump(), "word_count": word_count(r.content)} for r in revs]


@router.get("/books/{book_id}/chapters/{number}/revisions/{revision_id}")
def get_revision(number: int, revision_id: uuid.UUID, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    chapter = _chapter(db, book, number)
    rev = db.get(ChapterRevision, revision_id)
    if rev is None or rev.chapter_id != chapter.id:
        raise HTTPException(404, "Revision not found")
    return {"revision": rev.revision, "title": rev.title, "content": rev.content, "reason": rev.reason, "created_at": rev.created_at}


@router.post("/books/{book_id}/chapters/{number}/revisions/{revision_id}/restore", response_model=schemas.ChapterOut)
def restore_revision(number: int, revision_id: uuid.UUID, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    chapter = _chapter(db, book, number)
    rev = db.get(ChapterRevision, revision_id)
    if rev is None or rev.chapter_id != chapter.id:
        raise HTTPException(404, "Revision not found")
    chapter.title, chapter.content = rev.title, rev.content
    chapter.word_count = word_count(rev.content)
    chapter.revision += 1
    db.add(ChapterRevision(chapter_id=chapter.id, revision=chapter.revision, title=rev.title, content=rev.content, reason="restored"))
    db.commit()
    return chapter
