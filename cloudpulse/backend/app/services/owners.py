"""Who owns a resource: audit log first, owner tag second, cached."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import ResourceOwner

log = logging.getLogger("cloudpulse")
OWNER_TAG_KEYS = ("owner", "createdby", "created-by", "created_by", "contact", "team")
RECHECK_UNKNOWN_AFTER = timedelta(hours=24)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def tag_owner(tags: dict | None) -> str | None:
    for k, v in (tags or {}).items():
        if k.lower() in OWNER_TAG_KEYS and v:
            return str(v)
    return None


def resolve(db: Session, ws_id: int, resource_id: str, tags: dict | None, lookup, now: datetime | None = None) -> dict:
    """Returns {principal, principal_type, event, at, source}.

    Order: cached audit-log answer -> fresh audit-log lookup (unknowns are
    retried at most once a day) -> owner-style tag -> unknown.
    """
    now = now or _now()
    rid = (resource_id or "").lower()
    if not rid:
        return {"principal": None, "source": "unknown"}
    row = db.query(ResourceOwner).filter_by(workspace_id=ws_id, resource_id=rid).first()
    fresh_needed = row is None or (row.source == "unknown" and (now - row.checked_at) > RECHECK_UNKNOWN_AFTER)
    if fresh_needed and lookup is not None:
        try:
            who = lookup(resource_id)
        except Exception as e:  # noqa: BLE001
            log.info("owner lookup failed for %s: %s", resource_id, e)
            who = {"principal": None, "source": "unknown"}
        if row is None:
            row = ResourceOwner(workspace_id=ws_id, resource_id=rid)
            db.add(row)
        row.principal = who.get("principal")
        row.principal_type = who.get("principal_type")
        row.event = who.get("event")
        row.event_at = who.get("at")
        row.source = who.get("source") or ("unknown" if not who.get("principal") else "activity_log")
        row.checked_at = now
        db.commit()
    if row is not None and row.principal:
        return {"principal": row.principal, "principal_type": row.principal_type, "event": row.event,
                "at": row.event_at, "source": row.source}
    tagged = tag_owner(tags)
    if tagged:
        return {"principal": tagged, "principal_type": "tag", "event": None, "at": None, "source": "tag"}
    return {"principal": None, "principal_type": None, "event": None, "at": None, "source": "unknown"}


def attach(db: Session, ws_id: int, signals: list[dict], lookup, now=None):
    """Adds owner fields to resource signals (in place)."""
    for s in signals:
        if not s.get("resource_id"):
            continue
        who = resolve(db, ws_id, s["resource_id"], s.get("tags"), lookup, now)
        s["owner"], s["owner_source"] = who["principal"], who["source"]
        s.setdefault("evidence", {})["owner_trail"] = who
