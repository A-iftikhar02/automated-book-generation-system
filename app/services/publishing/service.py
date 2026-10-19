"""Publishing orchestration: store metadata, covers, exports and the readiness checklist."""

import io
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...catalog import TRIM_SIZES, get_category
from ...config import settings
from ...db.models import Book, Chapter, Export, QAIssue, QARun
from .. import llm, prompts
from .. import storage
from ..generation import editor_model, latest_outline
from ..notifications import notify
from . import cover as covers
from .docx_export import build_docx, build_txt
from .epub import build_epub
from .manuscript import build_manuscript
from .print_pdf import build_print_pdf

EXTENSIONS = {"epub": "epub", "print_pdf": "pdf", "cover_wrap_pdf": "pdf", "docx": "docx", "txt": "txt"}
ALLOWED_DESCRIPTION_TAGS = {"p", "b", "i", "em", "strong", "br", "ul", "ol", "li", "h4", "h5", "h6", "u"}


class PublishingError(RuntimeError):
    pass


def book_dir(book_id) -> Path:
    path = Path(settings.STORAGE_DIR) / "books" / str(book_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "book"


def _chapters(db: Session, book: Book) -> list[Chapter]:
    return db.scalars(select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.number)).all()


# ---------- metadata ----------

def generate_metadata(db: Session, book: Book, overwrite: bool) -> dict:
    category = get_category(book.category)
    chapters = _chapters(db, book)
    data = llm.complete_json(
        model=editor_model(book),
        system="You are a book marketing expert who writes retail listings that convert browsers into buyers.",
        prompt=prompts.metadata_prompt(book, category, book.story_bible or {}, [(c.number, c.title, c.summary) for c in chapters]),
        max_tokens=3000,
        temperature=0.7,
        book_id=book.id,
    )
    updated = []
    if overwrite or not book.description:
        book.description = str(data.get("description") or "").strip()[:4000] or book.description
        updated.append("description")
    if overwrite or not book.back_cover_copy:
        book.back_cover_copy = str(data.get("back_cover_copy") or "").strip() or book.back_cover_copy
        updated.append("back_cover_copy")
    if (overwrite or not book.subtitle) and data.get("subtitle"):
        book.subtitle = str(data["subtitle"]).strip()[:200] or None
        updated.append("subtitle")
    if overwrite or not book.keywords:
        book.keywords = [str(k).strip()[:50] for k in (data.get("keywords") or []) if str(k).strip()][:7]
        updated.append("keywords")
    if overwrite or not book.store_categories:
        book.store_categories = [str(c).strip() for c in (data.get("store_categories") or []) if str(c).strip()][:3]
        updated.append("store_categories")
    db.commit()
    return {"updated": updated}


# ---------- covers ----------

def cover_paths(book: Book) -> dict[str, Path]:
    d = book_dir(book.id)
    return {"cover": d / "cover.jpg", "art": d / "cover-art.png", "upload": d / "cover-upload.png"}


def save_uploaded_cover(db: Session, book: Book, data: bytes, finished_design: bool) -> dict:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:
        raise PublishingError(f"Not a valid image: {e}") from e
    paths = cover_paths(book)
    img.convert("RGB").save(paths["upload"] if finished_design else paths["art"], "PNG")
    if finished_design:
        paths["art"].unlink(missing_ok=True)
    final = covers._fit_cover(img, covers.EBOOK_SIZE) if finished_design else covers.compose_cover(book, img.convert("RGB"))
    covers.save_jpeg(final, paths["cover"])
    book.cover_image_path = str(paths["cover"])
    db.commit()
    return {"width": img.width, "height": img.height, "warnings": _cover_size_warnings(img)}


def _cover_size_warnings(img: Image.Image) -> list[str]:
    warnings = []
    if img.width < 1000 or img.height < 1600:
        warnings.append("Image is smaller than recommended (1600 x 2560); it may look blurry on stores and in print.")
    ratio = img.height / max(1, img.width)
    if not 1.4 <= ratio <= 1.7:
        warnings.append(f"Aspect ratio {ratio:.2f}:1 will be cropped to 1.6:1.")
    return warnings


def generate_cover(db: Session, book: Book, use_ai: bool, prompt: str | None, progress) -> dict:
    paths = cover_paths(book)
    art = None
    source = "gradient"
    if use_ai:
        if not llm.image_available():
            raise PublishingError("AI cover art needs an OpenRouter key (IMAGE_MODEL uses OpenRouter). "
                                  "Use the typographic cover or upload artwork instead.")
        progress(0.2, "Painting cover art")
        art = covers.generate_art(book, prompt)
        art.save(paths["art"], "PNG")
        paths["upload"].unlink(missing_ok=True)
        source = "ai"
    elif paths["art"].exists():
        art = Image.open(paths["art"]).convert("RGB")
        source = "existing_art"
    progress(0.8, "Typesetting cover")
    covers.save_jpeg(covers.compose_cover(book, art), paths["cover"])
    book.cover_image_path = str(paths["cover"])
    db.commit()
    return {"source": source, "path": str(paths["cover"])}


def _print_front(book: Book, trim_key: str) -> Image.Image:
    """Front panel for print at 300 DPI including bleed, recomposed from art when available."""
    paths = cover_paths(book)
    w, h = TRIM_SIZES[trim_key]
    size = (int((w + covers.BLEED) * 300), int((h + 2 * covers.BLEED) * 300))
    if paths["upload"].exists():
        return Image.open(paths["upload"]).convert("RGB")
    art = Image.open(paths["art"]).convert("RGB") if paths["art"].exists() else None
    if art is None and storage.exists(book.cover_image_path) and not paths["art"].exists():
        return Image.open(storage.resolve(book.cover_image_path)).convert("RGB")
    return covers.compose_cover(book, art, size=size)


# ---------- exports ----------

def run_export(db: Session, book: Book, fmt: str, options: dict, progress) -> Export:
    if fmt not in EXTENSIONS:
        raise PublishingError(f"Unknown export format '{fmt}'")
    chapters = _chapters(db, book)
    if not chapters:
        raise PublishingError("Nothing to export yet: no parts have been written.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"{slugify(book.title)}-{fmt.replace('_', '-')}"
    if fmt in ("print_pdf", "cover_wrap_pdf"):
        name += f"-{options.get('trim_size', '6x9')}"
    output = book_dir(book.id) / "exports" / f"{name}-{stamp}.{EXTENSIONS[fmt]}"
    kind = "print" if fmt in ("print_pdf", "cover_wrap_pdf") else "ebook"
    ms = build_manuscript(book, chapters, kind=kind)
    page_count = None
    progress(0.2, f"Building {fmt}")

    if fmt == "epub":
        cover_bytes = None
        if storage.exists(book.cover_image_path):
            cover_bytes = storage.resolve(book.cover_image_path).read_bytes()
        validation = build_epub(ms, output, cover_bytes)
        if not cover_bytes:
            validation["warnings"] = ["No cover image: stores require a cover. Generate or upload one, then export again."]
    elif fmt == "print_pdf":
        trim = options.get("trim_size", "6x9")
        validation = build_print_pdf(ms, output, trim_key=trim, large_print=bool(options.get("large_print")))
        page_count = validation["page_count"]
    elif fmt == "cover_wrap_pdf":
        trim = options.get("trim_size", "6x9")
        if trim not in TRIM_SIZES:
            raise PublishingError(f"Unknown trim size '{trim}'")
        progress(0.3, "Measuring interior page count")
        interior = db.scalars(
            select(Export).where(Export.book_id == book.id, Export.format == "print_pdf").order_by(Export.created_at.desc())
        ).all()
        match = next((e for e in interior if e.options.get("trim_size", "6x9") == trim
                      and bool(e.options.get("large_print")) == bool(options.get("large_print"))
                      and e.created_at >= max(c.updated_at for c in chapters)), None)
        if match and match.page_count:
            page_count = match.page_count
        else:
            tmp = output.with_suffix(".interior.pdf")
            page_count = build_print_pdf(build_manuscript(book, chapters, kind="print"), tmp, trim_key=trim,
                                         large_print=bool(options.get("large_print")))["page_count"]
            tmp.unlink(missing_ok=True)
        progress(0.7, "Laying out full-wrap cover")
        validation = covers.build_wrap_cover_pdf(
            book, front=_print_front(book, trim), page_count=page_count, trim_key=trim,
            paper=options.get("paper", "white"), output=output,
        )
    elif fmt == "docx":
        validation = build_docx(ms, output)
    else:
        validation = build_txt(ms, output)

    export = Export(book_id=book.id, format=fmt, options=options, file_path=str(output), file_size=output.stat().st_size,
                    page_count=page_count, validation=validation)
    db.add(export)
    db.commit()
    notify(f"Export ready for '{book.title}': {fmt}" + (f" ({page_count} pages)" if page_count else ""))
    return export


# ---------- readiness ----------

def _check(key: str, label: str, status: str, detail: str, store: str = "all") -> dict:
    return {"key": key, "label": label, "status": status, "detail": detail, "store": store}


def readiness(db: Session, book: Book) -> dict:
    """Checklist for uploading to Amazon KDP and Apple Books. status: pass | warn | fail | info."""
    category = get_category(book.category)
    chapters = _chapters(db, book)
    outline = latest_outline(db, book.id)
    planned = len(outline.chapters) if outline else book.target_chapter_count
    total_words = sum(c.word_count for c in chapters)
    items: list[dict] = []

    approved = sum(1 for c in chapters if c.status == "approved")
    items.append(_check("manuscript_complete", "All parts written and approved",
                        "pass" if chapters and approved == planned else "fail", f"{approved}/{planned} approved"))
    in_range = category.min_words <= total_words <= category.max_words
    items.append(_check("length", f"Length fits a {category.label}",
                        "pass" if in_range else ("fail" if total_words < category.min_words * 0.7 else "warn"),
                        f"{total_words:,} words (expected {category.min_words:,}-{category.max_words:,})"))

    last_run = db.scalars(select(QARun).where(QARun.book_id == book.id, QARun.status == "completed")
                          .order_by(QARun.created_at.desc()).limit(1)).first()
    last_edit = max((c.updated_at for c in chapters), default=None)
    if last_run is None:
        items.append(_check("qa_run", "Quality check run", "fail", "Run a full quality check before publishing."))
    else:
        stale = last_edit is not None and last_run.completed_at is not None and last_edit > last_run.completed_at
        items.append(_check("qa_run", "Quality check is up to date", "warn" if stale else "pass",
                            "Text changed since the last check; re-run QA." if stale else f"Last run scored {last_run.score}"))
        open_issues = db.scalars(select(QAIssue).where(QAIssue.book_id == book.id, QAIssue.status == "open")).all()
        critical = sum(1 for i in open_issues if i.severity == "critical")
        major = sum(1 for i in open_issues if i.severity == "major")
        items.append(_check("qa_critical", "No critical quality issues", "pass" if critical == 0 else "fail",
                            f"{critical} critical, {major} major open issues"))
        items.append(_check("qa_score", "Quality score ≥ 80", "pass" if (last_run.score or 0) >= 80 else "warn",
                            f"Score {last_run.score}"))

    items.append(_check("author", "Author / pen name set", "pass" if (book.author_name or "").strip() else "fail",
                        book.author_name or "Required by every store"))
    desc = book.description or ""
    plain = re.sub(r"<[^>]+>", "", desc)
    bad_tags = {t.lower() for t in re.findall(r"</?\s*([a-zA-Z0-9]+)", desc)} - ALLOWED_DESCRIPTION_TAGS
    if not desc.strip():
        items.append(_check("description", "Book description", "fail", "Generate or write a product description."))
    elif len(desc) > 4000 or bad_tags:
        items.append(_check("description", "Book description", "fail",
                            "Over KDP's 4,000-character limit." if len(desc) > 4000 else f"Unsupported HTML tags: {', '.join(sorted(bad_tags))}"))
    else:
        items.append(_check("description", "Book description", "pass" if len(plain) >= 300 else "warn", f"{len(plain)} characters"))
    kws = book.keywords or []
    long_kw = [k for k in kws if len(k) > 50]
    items.append(_check("keywords", "7 search keywords (KDP)", "pass" if len(kws) == 7 and not long_kw else "warn",
                        f"{len(kws)} keywords" + (f"; {len(long_kw)} over 50 chars" if long_kw else ""), "kdp"))
    items.append(_check("categories", "Store categories chosen", "pass" if book.store_categories else "warn",
                        ", ".join(book.store_categories or []) or "Pick up to 3 browse categories"))

    cover_ok = storage.exists(book.cover_image_path)
    if cover_ok:
        with Image.open(storage.resolve(book.cover_image_path)) as img:
            dims = f"{img.width} x {img.height}px"
            ok = img.width >= 1400 and img.height >= 2240
        items.append(_check("cover", "Ebook cover (≥1600x2560 recommended)", "pass" if ok else "warn", dims))
    else:
        items.append(_check("cover", "Ebook cover", "fail", "Generate or upload a cover."))

    exports = db.scalars(select(Export).where(Export.book_id == book.id).order_by(Export.created_at.desc())).all()
    latest = {}
    for e in exports:
        latest.setdefault(e.format, e)
    epub_e = latest.get("epub")
    fresh = lambda e: e is not None and (last_edit is None or e.created_at >= last_edit)  # noqa: E731
    if epub_e is None:
        items.append(_check("epub", "EPUB exported", "warn", "Export an EPUB for Apple Books / KDP."))
    else:
        valid = epub_e.validation.get("valid")
        status = "pass" if fresh(epub_e) and valid is not False else "warn"
        detail = "Validated with epubcheck" if valid else ("epubcheck errors found" if valid is False else "Exported (not validated)")
        items.append(_check("epub", "EPUB exported", status, detail + ("" if fresh(epub_e) else "; text changed since export")))
    pdf_e = latest.get("print_pdf")
    if pdf_e is None:
        items.append(_check("print_pdf", "Paperback interior PDF", "info", "Optional: export for a KDP paperback.", "kdp"))
    else:
        pages = pdf_e.page_count or 0
        items.append(_check("print_pdf", "Paperback interior PDF", "pass" if 24 <= pages <= 828 and fresh(pdf_e) else "warn",
                            f"{pages} pages, {pdf_e.options.get('trim_size', '6x9')}", "kdp"))
    items.append(_check("isbn", "ISBN", "info",
                        "Optional for ebooks (KDP assigns an ASIN; Apple doesn't require one). KDP offers a free ISBN for paperbacks."))
    items.append(_check("ai_disclosure", "AI-generated content disclosure", "info",
                        "KDP asks during upload whether text, images or translations are AI-generated; answer accurately. "
                        "Review and edit the book yourself before publishing.", "kdp"))
    items.append(_check("kdp_limits", "KDP publishing limits", "info",
                        "KDP limits how many new titles an account can publish per day and removes low-content duplicates.", "kdp"))

    blocking = [i for i in items if i["status"] == "fail"]
    return {"ready": not blocking, "blocking": len(blocking), "items": items, "total_words": total_words}
