"""Request-level access checks shared by the API routers."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Membership, User, Workspace
from app.security import COOKIE_NAME, user_for_token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = user_for_token(db, request.cookies.get(COOKIE_NAME))
    if user is None:
        raise HTTPException(401, "Please sign in.")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Only an administrator can do that.")
    return user


def csrf_guard(request: Request):
    """State-changing requests must come from our own page (it sets this
    header; a cross-site form can't)."""
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("x-cloudpulse") != "1":
        raise HTTPException(403, "Request blocked.")


@dataclass
class Access:
    user: User
    workspace: Workspace
    role: str  # owner | viewer

    @property
    def can_edit(self) -> bool:
        if self.workspace.kind == "demo":
            return self.user.is_admin
        return self.role == "owner"


def workspaces_for(db: Session, user: User) -> list[tuple[Workspace, str]]:
    if user.is_admin:
        rows = db.query(Workspace).order_by(Workspace.kind.desc(), Workspace.name).all()
        return [(w, "owner") for w in rows]
    rows = (
        db.query(Workspace, Membership.role)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .filter(Membership.user_id == user.id)
        .order_by(Workspace.kind.desc(), Workspace.name)
        .all()
    )
    return [(w, "viewer" if user.is_demo else r) for w, r in rows]


def workspace_access(
    ws: str = Query(..., description="Workspace slug"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Access:
    for w, role in workspaces_for(db, user):
        if w.slug == ws:
            return Access(user=user, workspace=w, role=role)
    # Same answer whether it doesn't exist or isn't theirs.
    raise HTTPException(404, "Workspace not found.")


def editable(access: Access = Depends(workspace_access)) -> Access:
    if not access.can_edit:
        raise HTTPException(403, "This workspace is read-only for your account.")
    return access
