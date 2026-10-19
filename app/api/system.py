import shutil
from datetime import datetime, timezone
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import schemas
from ..catalog import catalog_payload
from ..config import settings
from ..db.models import Job
from ..db.session import get_db
from ..services import llm
from ..services.jobs import enqueue
from ..services.notifications import notify
from ..services.qa import grammar

router = APIRouter(tags=["system"])
_models_cache: tuple[float, list] | None = None


@router.get("/health")
def health():
    return {"status": "ok", "version": settings.VERSION}


@router.get("/catalog")
def catalog():
    return catalog_payload()


@router.get("/system/status")
def status(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    worker_seen = db.scalar(select(Job.heartbeat_at).where(Job.heartbeat_at.is_not(None)).order_by(Job.heartbeat_at.desc()).limit(1))
    queued = db.scalar(select(func.count()).select_from(Job).where(Job.status == "queued"))
    oldest_queued = db.scalar(select(func.min(Job.created_at)).where(Job.status == "queued"))
    epubcheck = bool(settings.EPUBCHECK_JAR and Path(settings.EPUBCHECK_JAR).exists() and shutil.which("java"))
    return {
        "version": settings.VERSION,
        "database": db_ok,
        "ai": {
            "configured": settings.llm_configured,
            "writer_models": llm.split_chain(settings.WRITER_MODELS),
            "editor_models": llm.split_chain(settings.EDITOR_MODELS),
            "image_model": settings.IMAGE_MODEL,
            "image_configured": llm.image_available(),
            "providers": llm.provider_status(),
        },
        "languagetool": {"url": settings.LANGUAGETOOL_URL, "available": grammar.is_available()},
        "slack": {"enabled": settings.SLACK_ENABLED, "configured": bool(settings.SLACK_WEBHOOK_URL.strip()), "active": settings.slack_active},
        "epubcheck": {"available": epubcheck},
        "worker": {
            "in_process": settings.RUN_WORKER_IN_PROCESS,
            "last_heartbeat": worker_seen,
            "queued_jobs": queued,
            # A queued job older than a minute or so usually means no worker is running.
            "oldest_queued_seconds": int((datetime.now(timezone.utc) - oldest_queued).total_seconds()) if oldest_queued else None,
        },
    }


@router.get("/system/models")
def models():
    global _models_cache
    if _models_cache and time.time() - _models_cache[0] < 3600:
        return _models_cache[1]
    try:
        data = llm.list_models()
    except Exception as e:
        raise HTTPException(502, f"Could not load OpenRouter models: {e}")
    _models_cache = (time.time(), data)
    return data


@router.post("/system/test-notification")
def test_notification():
    if not settings.SLACK_ENABLED:
        return {"sent": False, "reason": "Slack is disabled (set SLACK_ENABLED=true and SLACK_WEBHOOK_URL in .env)."}
    if not settings.SLACK_WEBHOOK_URL.strip():
        return {"sent": False, "reason": "SLACK_WEBHOOK_URL is not set."}
    sent = notify(f"Test notification from {settings.PROJECT_NAME}.")
    return {"sent": sent, "reason": None if sent else "Slack rejected the request; check the webhook URL and logs."}


# ---------- jobs ----------

@router.get("/jobs", response_model=list[schemas.JobOut])
def list_jobs(book_id: uuid.UUID | None = None, active: bool = False, limit: int = 50, db: Session = Depends(get_db)):
    q = select(Job).order_by(Job.created_at.desc()).limit(min(limit, 200))
    if book_id:
        q = q.where(Job.book_id == book_id)
    if active:
        q = q.where(Job.status.in_(("queued", "running")))
    return db.scalars(q).all()


def _job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return _job(db, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=schemas.JobOut)
def cancel_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = _job(db, job_id)
    if job.status == "queued":
        job.status, job.message = "cancelled", "Cancelled"
    elif job.status == "running":
        job.cancel_requested = True
        job.message = "Cancelling after the current step…"
    db.commit()
    return job


@router.post("/jobs/{job_id}/retry", response_model=schemas.JobOut)
def retry_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = _job(db, job_id)
    if job.status not in ("failed", "cancelled"):
        raise HTTPException(409, "Only failed or cancelled jobs can be retried.")
    return enqueue(db, job.type, job.book_id, job.payload)
