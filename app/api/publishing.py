import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..db.models import Book, Export
from ..db.session import get_db
from ..services.jobs import enqueue
from ..services import storage
from ..services.publishing import service as publishing
from .deps import get_book, require_llm

router = APIRouter(tags=["publishing"])

MEDIA_TYPES = {
    "epub": "application/epub+zip",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
}
MAX_COVER_BYTES = 25 * 1024 * 1024


@router.get("/books/{book_id}/readiness")
def readiness(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return publishing.readiness(db, book)


@router.post("/books/{book_id}/metadata/generate", response_model=schemas.JobOut, dependencies=[Depends(require_llm)])
def generate_metadata(req: schemas.MetadataRequest, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return enqueue(db, "metadata", book.id, {"overwrite": req.overwrite})


@router.post("/books/{book_id}/cover/generate", response_model=schemas.JobOut)
def generate_cover(req: schemas.CoverRequest, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    if req.use_ai:
        require_llm()
    return enqueue(db, "cover", book.id, {"use_ai": req.use_ai, "prompt": req.prompt})


@router.post("/books/{book_id}/cover")
def upload_cover(
    file: UploadFile = File(...),
    finished_design: bool = Form(True, description="True if the image already contains title/author text."),
    book: Book = Depends(get_book),
    db: Session = Depends(get_db),
):
    data = file.file.read(MAX_COVER_BYTES + 1)
    if len(data) > MAX_COVER_BYTES:
        raise HTTPException(413, "Cover image must be under 25 MB.")
    return publishing.save_uploaded_cover(db, book, data, finished_design)


@router.get("/books/{book_id}/cover")
def get_cover(book: Book = Depends(get_book)):
    cover = storage.resolve(book.cover_image_path)
    if cover is None or not cover.exists():
        raise HTTPException(404, "No cover yet")
    return FileResponse(cover, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


@router.delete("/books/{book_id}/cover", status_code=204)
def delete_cover(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    for path in publishing.cover_paths(book).values():
        path.unlink(missing_ok=True)
    book.cover_image_path = None
    db.commit()


@router.post("/books/{book_id}/exports", response_model=schemas.JobOut)
def create_export(req: schemas.ExportRequest, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    options = {}
    if req.format in ("print_pdf", "cover_wrap_pdf"):
        options = {"trim_size": req.trim_size, "large_print": req.large_print}
        if req.format == "cover_wrap_pdf":
            options["paper"] = req.paper
    return enqueue(db, "export", book.id, {"format": req.format, "options": options})


@router.get("/books/{book_id}/exports", response_model=list[schemas.ExportOut])
def list_exports(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    exports = db.scalars(select(Export).where(Export.book_id == book.id).order_by(Export.created_at.desc())).all()
    return [{**schemas.ExportOut.model_validate(e).model_dump(), "file_name": Path(e.file_path).name} for e in exports]


def _export(db: Session, export_id: uuid.UUID) -> Export:
    export = db.get(Export, export_id)
    if export is None:
        raise HTTPException(404, "Export not found")
    return export


@router.get("/exports/{export_id}/download")
def download_export(export_id: uuid.UUID, db: Session = Depends(get_db)):
    export = _export(db, export_id)
    path = storage.resolve(export.file_path)
    if path is None or not path.exists():
        raise HTTPException(410, "The export file is missing; export again.")
    return FileResponse(path, filename=path.name, media_type=MEDIA_TYPES.get(path.suffix.lstrip("."), "application/octet-stream"))


@router.delete("/exports/{export_id}", status_code=204)
def delete_export(export_id: uuid.UUID, db: Session = Depends(get_db)):
    export = _export(db, export_id)
    if (path := storage.resolve(export.file_path)) is not None:
        path.unlink(missing_ok=True)
    db.delete(export)
    db.commit()
