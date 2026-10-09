from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import audit
from app.config import settings
from app.database import get_db
from app.deps import csrf_guard, current_user, workspaces_for
from app.models import Notification, User
from app.security import (
    COOKIE_NAME, clear_failures, create_session, end_all_sessions, end_session, hash_password,
    password_problem, record_failure, throttled, verify_password,
)

router = APIRouter(prefix="/api/auth", dependencies=[Depends(csrf_guard)])


def _set_cookie(response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.COOKIE_SECURE,
        max_age=settings.SESSION_HOURS * 3600, path="/",
    )


def _client(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() or (request.client.host if request.client else "?"))


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    keys = (f"email:{email}", f"ip:{_client(request)}")
    if throttled(*keys):
        raise HTTPException(429, "Too many attempts. Wait 15 minutes and try again.")
    user = db.query(User).filter_by(email=email).first()
    if (not user or user.is_demo or user.is_placeholder or user.disabled
            or not verify_password(body.password, user.password_hash)):
        record_failure(*keys)
        audit(db, request, user if user and not user.is_placeholder else None, "sign_in_failed", target=email)
        raise HTTPException(401, "That email and password don't match.")
    clear_failures(*keys)
    audit(db, request, user, "sign_in")
    _set_cookie(response, create_session(db, user))
    return {"ok": True, "must_change_password": user.must_change_password}


@router.post("/demo")
def demo(response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(is_demo=True, is_placeholder=False, disabled=False).first()
    if not settings.DEMO_ENABLED or user is None:
        raise HTTPException(404, "The demo isn't available on this server.")
    _set_cookie(response, create_session(db, user))
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    from app.security import user_for_token
    u = user_for_token(db, request.cookies.get(COOKIE_NAME))
    if u and not u.is_demo:
        audit(db, request, u, "sign_out")
    end_session(db, request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_admin": user.is_admin,
        "is_demo": user.is_demo,
        "must_change_password": user.must_change_password,
        "unread": db.query(Notification).filter(Notification.user_id == user.id,
                                                Notification.read_at.is_(None)).count(),
        "workspaces": [
            {"slug": w.slug, "name": w.name, "kind": w.kind,
             "role": role, "can_edit": (user.is_admin if w.kind == "demo" else role == "owner")}
            for w, role in workspaces_for(db, user)
        ],
    }


class PasswordIn(BaseModel):
    current: str = Field(max_length=256)
    new: str = Field(max_length=256)


@router.post("/password")
def change_password(body: PasswordIn, request: Request, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    if user.is_demo:
        raise HTTPException(403, "The demo account has no password.")
    if not verify_password(body.current, user.password_hash):
        raise HTTPException(400, "Your current password isn't right.")
    problem = password_problem(body.new)
    if problem:
        raise HTTPException(400, problem)
    if body.new == body.current:
        raise HTTPException(400, "Choose a password you haven't used here.")
    user.password_hash = hash_password(body.new)
    user.must_change_password = False
    db.commit()
    end_all_sessions(db, user.id, keep_token=request.cookies.get(COOKIE_NAME))
    audit(db, request, user, "password_changed")
    return {"ok": True}
