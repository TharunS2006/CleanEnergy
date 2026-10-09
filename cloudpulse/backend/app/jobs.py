"""Background syncs, so the page never waits on cloud APIs."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CollectionRun, Workspace

log = logging.getLogger("cloudpulse")
scheduler = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600})
STALE_AFTER = timedelta(minutes=20)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def active_run(db: Session, ws_id: int) -> CollectionRun | None:
    return db.query(CollectionRun).filter(
        CollectionRun.workspace_id == ws_id,
        CollectionRun.status.in_(("queued", "running")),
        CollectionRun.started_at > _now() - STALE_AFTER,
    ).order_by(CollectionRun.id.desc()).first()


def enqueue(db: Session, ws: Workspace, requested_by: str = "schedule") -> CollectionRun:
    """Start a sync unless one is already running for this workspace."""
    existing = active_run(db, ws.id)
    if existing:
        return existing
    run = CollectionRun(workspace_id=ws.id, status="queued", step="Waiting to start",
                        requested_by=requested_by, started_at=_now())
    db.add(run)
    db.commit()
    if scheduler.running:
        scheduler.add_job(run_now, args=[run.id], id=f"sync-{run.id}", replace_existing=True)
    else:  # tests and command-line use
        run_now(run.id)
        db.refresh(run)
    return run


def run_now(run_id: int):
    from app.services.collection_orchestrator import sync_workspace

    with SessionLocal() as db:
        run = db.get(CollectionRun, run_id)
        ws = db.get(Workspace, run.workspace_id) if run else None
        if not run or not ws:
            return
        try:
            sync_workspace(db, ws, run)
        except Exception as e:  # noqa: BLE001
            log.exception("sync %s failed", run_id)
            db.rollback()
            run = db.get(CollectionRun, run_id)
            run.status, run.step, run.finished_at = "failed", None, _now()
            run.detail = '{"error": "%s"}' % str(e).replace('"', "'")[:300]
            db.commit()


def sync_everything():
    with SessionLocal() as db:
        for ws in db.query(Workspace).all():
            enqueue(db, ws, "schedule")


def mark_interrupted():
    """Runs that were in flight when the server stopped will never finish."""
    with SessionLocal() as db:
        for run in db.query(CollectionRun).filter(CollectionRun.status.in_(("queued", "running"))).all():
            run.status, run.step, run.finished_at = "failed", None, _now()
            run.detail = '{"error": "The server restarted during this sync."}'
        db.commit()
