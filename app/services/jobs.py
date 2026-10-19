"""Durable background jobs stored in Postgres.

The API enqueues rows in `jobs`; workers (`python -m app.worker`, or a thread inside the API when
RUN_WORKER_IN_PROCESS=true) claim them with SELECT ... FOR UPDATE SKIP LOCKED. Jobs for the same book run
one at a time so chapter writing, QA and exports never race each other.
"""

import logging
import threading
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, exists, select, text, update
from sqlalchemy.orm import Session, aliased

from ..config import settings
from ..db.models import Job
from ..db.session import SessionLocal, session_scope
from .notifications import notify

logger = logging.getLogger(__name__)

ACTIVE = ("queued", "running")
STALE_AFTER = timedelta(minutes=3)  # running jobs send a heartbeat every 30s


class JobConflict(Exception):
    pass


class JobCancelled(Exception):
    pass


@dataclass
class JobContext:
    job_id: uuid.UUID
    book_id: uuid.UUID | None
    type: str
    payload: dict
    db: Session

    def progress(self, fraction: float, message: str) -> None:
        with session_scope() as s:
            s.execute(
                update(Job)
                .where(Job.id == self.job_id)
                .values(progress=max(0.0, min(1.0, fraction)), message=message, heartbeat_at=datetime.now(timezone.utc))
            )
        self.check_cancelled()

    def check_cancelled(self) -> None:
        with session_scope() as s:
            if s.scalar(select(Job.cancel_requested).where(Job.id == self.job_id)):
                raise JobCancelled()


Handler = Callable[[JobContext], dict | None]
HANDLERS: dict[str, Handler] = {}


def handler(name: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[name] = fn
        return fn

    return register


def enqueue(db: Session, job_type: str, book_id: uuid.UUID | None, payload: dict | None = None) -> Job:
    """Queue a job. Raises JobConflict if an identical job is already queued or running for the book."""
    payload = payload or {}
    existing = db.scalars(select(Job).where(Job.book_id == book_id, Job.type == job_type, Job.status.in_(ACTIVE))).all()
    if any(j.payload == payload for j in existing):
        raise JobConflict(f"A '{job_type}' job is already queued or running for this book.")
    job = Job(type=job_type, book_id=book_id, payload=payload, status="queued", message="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def active_jobs(db: Session, book_id: uuid.UUID) -> list[Job]:
    return db.scalars(select(Job).where(Job.book_id == book_id, Job.status.in_(ACTIVE)).order_by(Job.created_at)).all()


def claim_next(db: Session) -> Job | None:
    """Claim the oldest queued job whose book has no running job."""
    # Serialise claims so two workers can't each start a job for the same book.
    db.execute(text("SELECT pg_advisory_xact_lock(424242)"))
    running = aliased(Job)
    job = db.scalars(
        select(Job)
        .where(
            Job.status == "queued",
            ~exists().where(and_(running.book_id == Job.book_id, running.status == "running")),
        )
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if job is None:
        db.commit()
        return None
    now = datetime.now(timezone.utc)
    job.status, job.started_at, job.heartbeat_at, job.message = "running", now, now, "Starting"
    db.commit()
    return job


def recover_stale(db: Session) -> int:
    """Fail running jobs whose worker stopped sending heartbeats (e.g. a crash or restart)."""
    cutoff = datetime.now(timezone.utc) - STALE_AFTER
    result = db.execute(
        update(Job)
        .where(Job.status == "running", Job.heartbeat_at < cutoff)
        .values(status="failed", error="Worker stopped responding (restart or crash). Re-run the action.", finished_at=datetime.now(timezone.utc))
    )
    db.commit()
    return result.rowcount or 0


def _heartbeat(job_id: uuid.UUID, done: threading.Event) -> None:
    while not done.wait(30):
        try:
            with session_scope() as s:
                s.execute(update(Job).where(Job.id == job_id).values(heartbeat_at=datetime.now(timezone.utc)))
        except Exception:
            logger.warning("Heartbeat failed for job %s", job_id)


def run_job(job_id: uuid.UUID) -> None:
    db = SessionLocal()
    done = threading.Event()
    threading.Thread(target=_heartbeat, args=(job_id, done), daemon=True).start()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        fn = HANDLERS.get(job.type)
        if fn is None:
            raise RuntimeError(f"No handler registered for job type '{job.type}'")
        ctx = JobContext(job_id=job.id, book_id=job.book_id, type=job.type, payload=job.payload or {}, db=db)
        result = fn(ctx) or {}
        db.commit()
        _finish(job_id, "completed", result=result, message="Done")
    except JobCancelled:
        db.rollback()
        _finish(job_id, "cancelled", message="Cancelled")
    except Exception as e:
        db.rollback()
        logger.error("Job %s failed: %s\n%s", job_id, e, traceback.format_exc())
        _finish(job_id, "failed", error=str(e) or e.__class__.__name__, message="Failed")
        try:
            with session_scope() as s:
                job = s.get(Job, job_id)
                notify(f"Job '{job.type if job else job_id}' failed: {e}")
        except Exception:
            pass
    finally:
        done.set()
        db.close()


def _finish(job_id: uuid.UUID, status: str, *, result: dict | None = None, error: str | None = None, message: str | None = None) -> None:
    values: dict = {"status": status, "finished_at": datetime.now(timezone.utc)}
    if status == "completed":
        values["progress"] = 1.0
    if result is not None:
        values["result"] = result
    if error is not None:
        values["error"] = error[:4000]
    if message is not None:
        values["message"] = message
    with session_scope() as s:
        s.execute(update(Job).where(Job.id == job_id).values(**values))


def worker_loop(stop: threading.Event, concurrency: int | None = None) -> None:
    """Poll for jobs and run up to `concurrency` at once (each in its own thread)."""
    from . import tasks  # noqa: F401  (registers handlers)

    concurrency = concurrency or settings.WORKER_CONCURRENCY
    slots = threading.Semaphore(concurrency)
    last_recovery = datetime.min.replace(tzinfo=timezone.utc)
    logger.info("Worker started (concurrency=%s)", concurrency)

    def run_and_release(jid: uuid.UUID) -> None:
        try:
            run_job(jid)
        finally:
            slots.release()

    while not stop.is_set():
        try:
            now = datetime.now(timezone.utc)
            if now - last_recovery > timedelta(minutes=1):
                with SessionLocal() as db:
                    if n := recover_stale(db):
                        logger.warning("Marked %s stale job(s) as failed", n)
                last_recovery = now
            if not slots.acquire(timeout=settings.WORKER_POLL_SECONDS):
                continue
            with SessionLocal() as db:
                job = claim_next(db)
            if job is None:
                slots.release()
                stop.wait(settings.WORKER_POLL_SECONDS)
                continue
            logger.info("Running job %s (%s)", job.id, job.type)
            threading.Thread(target=run_and_release, args=(job.id,), daemon=True, name=f"job-{job.type}").start()
        except Exception:
            logger.exception("Worker loop error")
            stop.wait(5)
