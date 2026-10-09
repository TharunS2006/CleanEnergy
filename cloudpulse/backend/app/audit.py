"""Who did what, when. Written for sign-ins, account changes, connections,
budgets, imports, syncs and every change to a finding."""
from __future__ import annotations

import json

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else None)


def audit(db: Session, request: Request | None, user: User | None, action: str,
          target: str | None = None, detail: dict | str | None = None, workspace_id: int | None = None,
          actor: str | None = None, commit: bool = True):
    db.add(AuditLog(
        actor_id=user.id if user else None,
        actor=actor or (user.email if user else "anonymous"),
        workspace_id=workspace_id,
        action=action,
        target=target,
        detail=json.dumps(detail, default=str) if isinstance(detail, dict) else detail,
        ip=client_ip(request),
    ))
    if commit:
        db.commit()
