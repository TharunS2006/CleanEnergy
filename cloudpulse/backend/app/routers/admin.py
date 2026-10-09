import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import jobs
from app.audit import audit
from app.bootstrap import unique_slug
from app.database import get_db
from app.deps import csrf_guard, require_admin
from app.models import AuditLog, CloudConnection, CollectionRun, Membership, SessionToken, User, Workspace
from app.security import encrypt, end_all_sessions, generate_password, hash_password
from app.services.connections import describe

router = APIRouter(prefix="/api/admin", dependencies=[Depends(csrf_guard), Depends(require_admin)])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _uuid(value: str, what: str) -> str:
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError as e:
        raise HTTPException(400, f"{what} should look like xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.") from e


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    workspaces = []
    for w in db.query(Workspace).order_by(Workspace.kind.desc(), Workspace.name).all():
        run = db.query(CollectionRun).filter(
            CollectionRun.workspace_id == w.id, CollectionRun.finished_at.isnot(None)
        ).order_by(CollectionRun.id.desc()).first()
        detail = json.loads(run.detail or "{}") if run else {}
        conns = []
        for c in db.query(CloudConnection).filter_by(workspace_id=w.id).all():
            d = describe(c)
            d["status"] = detail.get(str(c.id), {"state": "not_synced"})
            conns.append(d)
        members = (
            db.query(User, Membership.role)
            .join(Membership, Membership.user_id == User.id)
            .filter(Membership.workspace_id == w.id).all()
        )
        workspaces.append({
            "id": w.id, "slug": w.slug, "name": w.name, "kind": w.kind,
            "last_run": (run.finished_at.isoformat() + "Z") if run else None,
            "status": run.status if run else None,
            "connections": conns,
            "members": [{"id": u.id, "email": u.email, "name": u.name, "role": r, "example": u.is_placeholder}
                        for u, r in members],
        })
    users = []
    for u in db.query(User).filter(User.is_placeholder.is_(False)).order_by(User.is_admin.desc(), User.email).all():
        m = (
            db.query(Workspace.name, Membership.role)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .filter(Membership.user_id == u.id).all()
        )
        users.append({
            "id": u.id, "email": u.email, "name": u.name, "is_admin": u.is_admin, "is_demo": u.is_demo,
            "disabled": u.disabled, "must_change_password": u.must_change_password,
            "last_login_at": (u.last_login_at.isoformat() + "Z") if u.last_login_at else None,
            "workspaces": [{"name": n, "role": r} for n, r in m],
        })
    return {"workspaces": workspaces, "users": users}


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)


@router.post("/workspaces")
def create_workspace(body: WorkspaceIn, request: Request, admin: User = Depends(require_admin),
                     db: Session = Depends(get_db)):
    ws = Workspace(slug=unique_slug(db, body.name), name=body.name.strip(), kind="customer")
    db.add(ws)
    db.commit()
    audit(db, request, admin, "workspace_created", ws.slug, workspace_id=ws.id)
    return {"id": ws.id, "slug": ws.slug}


@router.delete("/workspaces/{ws_id}")
def delete_workspace(ws_id: int, request: Request, admin: User = Depends(require_admin),
                     db: Session = Depends(get_db)):
    from app.models import (
        CostSnapshot, Finding, FindingEvent, Notification, ResourceCost, ResourceOwner, Setting,
    )

    ws = db.get(Workspace, ws_id)
    if not ws:
        raise HTTPException(404, "Workspace not found.")
    if ws.kind == "demo":
        raise HTTPException(400, "The demo workspace can be turned off with DEMO_ENABLED=false instead.")
    if db.query(CloudConnection).filter_by(workspace_id=ws.id, auth="env").first():
        raise HTTPException(400, "This workspace uses the server's own cloud settings. Remove those settings first.")
    for model in (FindingEvent, Notification, Finding, CostSnapshot, ResourceCost, ResourceOwner,
                  CollectionRun, Setting, CloudConnection, Membership):
        db.query(model).filter(model.workspace_id == ws.id).delete()
    slug = ws.slug
    db.delete(ws)
    db.commit()
    audit(db, request, admin, "workspace_deleted", slug)
    return {"ok": True}


class AzureIn(BaseModel):
    label: str = Field(default="Azure subscription", max_length=80)
    subscription_id: str
    tenant_id: str
    client_id: str
    client_secret: str = Field(min_length=8, max_length=512)


@router.post("/workspaces/{ws_id}/azure")
def add_azure(ws_id: int, body: AzureIn, request: Request, admin: User = Depends(require_admin),
              db: Session = Depends(get_db)):
    ws = db.get(Workspace, ws_id)
    if not ws or ws.kind == "demo":
        raise HTTPException(404, "Workspace not found.")
    cfg = {
        "subscription_id": _uuid(body.subscription_id, "Subscription ID"),
        "tenant_id": _uuid(body.tenant_id, "Tenant ID"),
        "client_id": _uuid(body.client_id, "Client (app) ID"),
    }
    conn = CloudConnection(
        workspace_id=ws.id, provider="azure", auth="service_principal",
        label=body.label.strip() or "Azure subscription",
        config=json.dumps(cfg), secret=encrypt(body.client_secret.strip()),
    )
    db.add(conn)
    db.commit()
    audit(db, request, admin, "connection_added", f"azure {cfg['subscription_id']}", workspace_id=ws.id)
    # Test the sign-in right away (fast), then sync in the background.
    from app.services import azure_collector
    from app.services.connections import build_target
    try:
        ok, info = azure_collector.check_connection(build_target(conn))
    except Exception as e:  # noqa: BLE001
        ok, info = False, str(e)
    if ok:
        jobs.enqueue(db, ws, admin.email)
    return {"id": conn.id, "status": {"state": "connected" if ok else "error",
                                      "identity" if ok else "message": info}}


@router.delete("/connections/{conn_id}")
def delete_connection(conn_id: int, request: Request, admin: User = Depends(require_admin),
                      db: Session = Depends(get_db)):
    conn = db.get(CloudConnection, conn_id)
    if not conn:
        raise HTTPException(404, "Connection not found.")
    if conn.auth == "env":
        raise HTTPException(400, "This connection comes from the server's settings. Change those instead.")
    ws_id = conn.workspace_id
    db.delete(conn)
    db.commit()
    audit(db, request, admin, "connection_removed", str(conn_id), workspace_id=ws_id)
    return {"ok": True}


@router.post("/workspaces/{ws_id}/sync")
def sync(ws_id: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ws = db.get(Workspace, ws_id)
    if not ws:
        raise HTTPException(404, "Workspace not found.")
    run = jobs.enqueue(db, ws, admin.email)
    audit(db, request, admin, "sync_requested", ws.slug, workspace_id=ws.id)
    return {"run_id": run.id, "status": run.status}


class UserIn(BaseModel):
    email: str = Field(max_length=254)
    name: str = Field(default="", max_length=80)
    is_admin: bool = False
    workspace_id: int | None = None
    role: str = Field(default="viewer", pattern="^(owner|viewer)$")


@router.post("/users")
def create_user(body: UserIn, request: Request, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "That doesn't look like an email address.")
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(400, "A user with that email already exists.")
    if not body.is_admin:
        ws = db.get(Workspace, body.workspace_id) if body.workspace_id else None
        if not ws or ws.kind == "demo":
            raise HTTPException(400, "Pick the customer workspace this person belongs to.")
    password = generate_password()
    user = User(email=email, name=body.name.strip() or email.split("@")[0],
                password_hash=hash_password(password), is_admin=body.is_admin, must_change_password=True)
    db.add(user)
    db.commit()
    if not body.is_admin:
        db.add(Membership(user_id=user.id, workspace_id=body.workspace_id, role=body.role))
        db.commit()
    audit(db, request, admin, "user_created", email,
          {"admin": body.is_admin, "workspace_id": body.workspace_id, "role": body.role},
          workspace_id=body.workspace_id)
    return {"id": user.id, "email": email, "temporary_password": password}


class MemberIn(BaseModel):
    workspace_id: int
    role: str = Field(default="viewer", pattern="^(owner|viewer|none)$")


@router.post("/users/{user_id}/membership")
def set_membership(user_id: int, body: MemberIn, request: Request, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    ws = db.get(Workspace, body.workspace_id)
    if not user or not ws or user.is_demo or ws.kind == "demo":
        raise HTTPException(404, "User or workspace not found.")
    m = db.query(Membership).filter_by(user_id=user.id, workspace_id=ws.id).first()
    if body.role == "none":
        if m:
            db.delete(m)
    elif m:
        m.role = body.role
    else:
        db.add(Membership(user_id=user.id, workspace_id=ws.id, role=body.role))
    db.commit()
    audit(db, request, admin, "membership_changed", user.email, {"role": body.role}, workspace_id=ws.id)
    return {"ok": True}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, request: Request, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.is_demo or user.is_placeholder:
        raise HTTPException(404, "User not found.")
    password = generate_password()
    user.password_hash = hash_password(password)
    user.must_change_password = True
    db.commit()
    end_all_sessions(db, user.id)
    audit(db, request, admin, "password_reset", user.email)
    return {"temporary_password": password}


class DisableIn(BaseModel):
    disabled: bool


@router.post("/users/{user_id}/disabled")
def set_disabled(user_id: int, body: DisableIn, request: Request, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.is_placeholder:
        raise HTTPException(404, "User not found.")
    if user.id == admin.id:
        raise HTTPException(400, "You can't disable your own account.")
    if body.disabled and user.is_admin and db.query(User).filter_by(is_admin=True, disabled=False).count() <= 1:
        raise HTTPException(400, "Keep at least one active administrator.")
    user.disabled = body.disabled
    db.commit()
    if body.disabled:
        db.query(SessionToken).filter_by(user_id=user.id).delete()
        db.commit()
    audit(db, request, admin, "user_disabled" if body.disabled else "user_enabled", user.email)
    return {"ok": True}


@router.get("/audit")
def audit_log(db: Session = Depends(get_db), limit: int = Query(200, ge=1, le=1000),
              workspace_id: int | None = None, action: str | None = None):
    q = db.query(AuditLog)
    if workspace_id:
        q = q.filter(AuditLog.workspace_id == workspace_id)
    if action:
        q = q.filter(AuditLog.action == action)
    names = {w.id: w.name for w in db.query(Workspace).all()}
    return [{
        "id": a.id, "at": a.at.isoformat() + "Z", "actor": a.actor, "action": a.action, "target": a.target,
        "workspace": names.get(a.workspace_id), "detail": a.detail, "ip": a.ip,
    } for a in q.order_by(AuditLog.id.desc()).limit(limit)]
