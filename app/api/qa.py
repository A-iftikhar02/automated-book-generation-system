import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..db.models import Book, QAIssue, QARun
from ..db.session import get_db
from ..services.jobs import enqueue
from ..services.qa import fixes
from ..services.qa.base import SEVERITY_ORDER
from ..services.qa.runner import grade_for
from .deps import get_book, require_llm

router = APIRouter(tags=["quality"])


@router.post("/books/{book_id}/qa", response_model=schemas.JobOut)
def start_qa(req: schemas.QARequest, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return enqueue(db, "qa", book.id, {"chapters": req.chapters, "include_ai": req.include_ai})


@router.get("/books/{book_id}/qa")
def qa_overview(book: Book = Depends(get_book), db: Session = Depends(get_db)):
    runs = db.scalars(select(QARun).where(QARun.book_id == book.id).order_by(QARun.created_at.desc()).limit(10)).all()
    latest = next((r for r in runs if r.status == "completed"), None)
    latest_full = next((r for r in runs if r.status == "completed" and r.stats.get("scope") == "book"), None)
    open_issues = db.scalars(select(QAIssue).where(QAIssue.book_id == book.id, QAIssue.status == "open")).all()
    by_severity = Counter(i.severity for i in open_issues)
    by_category = Counter(i.category for i in open_issues)
    by_chapter = Counter("book" if i.chapter_number is None else str(i.chapter_number) for i in open_issues)
    fixable = sum(1 for i in open_issues if i.source != "ai" and i.replacements and i.offset is not None)
    # Merge per-chapter stats across runs: the newest stats for each chapter win.
    chapter_stats: dict[str, dict] = {}
    for r in reversed(runs):
        if r.status == "completed":
            chapter_stats.update(r.stats.get("chapters", {}))
    return {
        "score": latest.score if latest else None,
        "grade": grade_for(latest.score) if latest and latest.score is not None else None,
        "latest_run": schemas.QARunOut.model_validate(latest).model_dump() if latest else None,
        "book_review": (latest_full.stats.get("book_review") if latest_full else None) or None,
        "chapter_scores": latest.stats.get("chapter_scores", {}) if latest else {},
        "chapter_stats": chapter_stats,
        "open_issues": len(open_issues),
        "auto_fixable": fixable,
        "by_severity": {k: by_severity.get(k, 0) for k in SEVERITY_ORDER},
        "by_category": dict(by_category.most_common()),
        "by_chapter": dict(by_chapter),
        "runs": [schemas.QARunOut.model_validate(r).model_dump(exclude={"stats"}) for r in runs],
    }


@router.get("/books/{book_id}/qa/issues", response_model=list[schemas.IssueOut])
def list_issues(
    book: Book = Depends(get_book),
    db: Session = Depends(get_db),
    status: str = "open",
    severity: str | None = None,
    category: str | None = None,
    chapter: int | None = None,
    book_level: bool = False,
    source: str | None = None,
    limit: int = Query(200, le=1000),
    offset: int = 0,
):
    q = select(QAIssue).where(QAIssue.book_id == book.id)
    if status != "all":
        q = q.where(QAIssue.status == status)
    if severity:
        q = q.where(QAIssue.severity.in_(severity.split(",")))
    if category:
        q = q.where(QAIssue.category.in_(category.split(",")))
    if book_level:
        q = q.where(QAIssue.chapter_number.is_(None))
    elif chapter is not None:
        q = q.where(QAIssue.chapter_number == chapter)
    if source:
        q = q.where(QAIssue.source == source)
    issues = db.scalars(q).all()
    issues.sort(key=lambda i: (SEVERITY_ORDER.get(i.severity, 9), i.chapter_number or 0, i.offset or 0))
    return issues[offset : offset + limit]


def _issue(db: Session, issue_id: uuid.UUID) -> QAIssue:
    issue = db.get(QAIssue, issue_id)
    if issue is None:
        raise HTTPException(404, "Issue not found")
    return issue


@router.patch("/qa/issues/{issue_id}", response_model=schemas.IssueOut)
def update_issue(issue_id: uuid.UUID, req: schemas.IssueUpdate, db: Session = Depends(get_db)):
    issue = _issue(db, issue_id)
    issue.status = req.status
    db.commit()
    return issue


@router.post("/qa/issues/{issue_id}/apply", response_model=schemas.IssueOut)
def apply_fix(issue_id: uuid.UUID, req: schemas.ApplyFix, db: Session = Depends(get_db)):
    issue = _issue(db, issue_id)
    fixes.apply_issue_fix(db, issue, req.replacement)
    return issue


@router.post("/books/{book_id}/qa/autofix", response_model=schemas.JobOut)
def autofix(req: schemas.AutofixRequest, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return enqueue(db, "autofix", book.id, {"chapters": req.chapters})


@router.post("/books/{book_id}/chapters/{number}/ai-fix", response_model=schemas.JobOut, dependencies=[Depends(require_llm)])
def ai_fix(number: int, req: schemas.AIFixRequest, book: Book = Depends(get_book), db: Session = Depends(get_db)):
    return enqueue(db, "ai_fix", book.id, {"number": number, "issue_ids": [str(i) for i in req.issue_ids or []]})
