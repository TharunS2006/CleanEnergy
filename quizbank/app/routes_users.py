from fastapi import APIRouter, Depends, HTTPException

from .auth import check_password, current_user, hash_password, need_role, new_token
from .db import get_db
from .schemas import LoginIn, RegisterIn

router = APIRouter(prefix="/api", tags=["users"])


@router.post("/register", status_code=201)
def register(data: RegisterIn, db=Depends(get_db)):
    email = data.email.lower()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise HTTPException(409, "This email is already registered")
    uid = db.insert("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (data.name, email, hash_password(data.password), data.role))
    return {"id": uid, "name": data.name, "email": email, "role": data.role}


@router.post("/login")
def login(data: LoginIn, db=Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email = ?", (data.email.lower(),)).fetchone()
    if user is None or not check_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    return {"token": new_token(db, user["id"]), "name": user["name"], "role": user["role"]}


@router.get("/me")
def me(user=Depends(current_user)):
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}


@router.get("/users")
def list_users(user=Depends(need_role("admin")), db=Depends(get_db)):
    return [dict(r) for r in db.execute("SELECT id, name, email, role FROM users ORDER BY id").fetchall()]


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, admin=Depends(need_role("admin")), db=Depends(get_db)):
    if user_id == admin["id"]:
        raise HTTPException(400, "You cannot delete yourself")
    cur = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "User not found")


@router.get("/stats")
def stats(user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    return {
        "users": db.scalar("SELECT COUNT(*) FROM users"),
        "questions": db.scalar("SELECT COUNT(*) FROM questions"),
        "quizzes": db.scalar("SELECT COUNT(*) FROM quizzes"),
        "attempts": db.scalar("SELECT COUNT(*) FROM attempts WHERE status = 'done'"),
        "practice_answers": db.scalar("SELECT COUNT(*) FROM practice_log"),
    }
