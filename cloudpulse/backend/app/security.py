"""Passwords, sessions and encryption of stored cloud secrets."""
import base64
import hashlib
import hmac
import secrets
import string
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SessionToken, User

COOKIE_NAME = "cp_session"
_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), **_SCRYPT)
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


def generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isdigit() for c in pw) and any(c.isupper() for c in pw) and any(c.islower() for c in pw):
            return pw


def password_problem(pw: str) -> str | None:
    if len(pw) < 10:
        return "Use at least 10 characters."
    if pw.lower() == pw or pw.upper() == pw or not any(c.isdigit() for c in pw):
        return "Mix upper and lower case letters and at least one number."
    return None


# --------------------------------------------------------------------------
# Sessions (server-side; the cookie only holds a random token)
# --------------------------------------------------------------------------
def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(SessionToken(
        token_hash=_digest(token), user_id=user.id,
        expires_at=_now() + timedelta(hours=settings.SESSION_HOURS),
    ))
    user.last_login_at = _now()
    # Housekeeping: drop expired sessions.
    db.query(SessionToken).filter(SessionToken.expires_at < _now()).delete()
    db.commit()
    return token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    row = db.query(SessionToken).filter_by(token_hash=_digest(token)).first()
    if not row or row.expires_at < _now():
        return None
    user = db.get(User, row.user_id)
    if not user or user.disabled:
        return None
    return user


def end_session(db: Session, token: str | None):
    if token:
        db.query(SessionToken).filter_by(token_hash=_digest(token)).delete()
        db.commit()


def end_all_sessions(db: Session, user_id: int, keep_token: str | None = None):
    q = db.query(SessionToken).filter(SessionToken.user_id == user_id)
    if keep_token:
        q = q.filter(SessionToken.token_hash != _digest(keep_token))
    q.delete()
    db.commit()


# --------------------------------------------------------------------------
# Login throttling (per email and per client address, in memory)
# --------------------------------------------------------------------------
_attempts: dict[str, deque] = defaultdict(deque)
WINDOW_SECONDS = 15 * 60
MAX_FAILURES = 8


def throttled(*keys: str) -> bool:
    cutoff = time.monotonic() - WINDOW_SECONDS
    for k in keys:
        q = _attempts[k]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= MAX_FAILURES:
            return True
    return False


def record_failure(*keys: str):
    now = time.monotonic()
    for k in keys:
        _attempts[k].append(now)


def clear_failures(*keys: str):
    for k in keys:
        _attempts.pop(k, None)


# --------------------------------------------------------------------------
# Encryption for stored cloud secrets
# --------------------------------------------------------------------------
def _fernet() -> Fernet:
    key = hashlib.sha256(("cloudpulse:" + settings.APP_SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return None
