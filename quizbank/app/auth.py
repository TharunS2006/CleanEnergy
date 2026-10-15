import hashlib
import hmac
import os
import secrets

from fastapi import Depends, Header, HTTPException

from .db import get_db


def hash_password(password: str, salt: bytes = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + "$" + digest.hex()


def check_password(password: str, stored: str) -> bool:
    salt_hex, _ = stored.split("$")
    return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex)), stored)


def new_token(db, user_id: int) -> str:
    token = secrets.token_hex(24)
    db.execute("INSERT INTO tokens (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def current_user(authorization: str = Header(default=None), db=Depends(get_db)):
    """Reads 'Authorization: Bearer <token>' and returns the user row."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Please log in first")
    token = authorization[7:]
    row = db.execute(
        "SELECT users.* FROM tokens JOIN users ON users.id = tokens.user_id WHERE tokens.token = ?", (token,)
    ).fetchone()
    if row is None:
        raise HTTPException(401, "Invalid or expired token")
    return row


def need_role(*roles):
    def check(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Your role is not allowed to do this")
        return user
    return check
