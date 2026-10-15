from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import current_user, need_role
from .db import get_db
from .schemas import QuestionIn

router = APIRouter(prefix="/api/questions", tags=["question bank"])

COLUMNS = "id, subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer"


@router.get("")
def list_questions(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user=Depends(need_role("admin", "teacher")),
    db=Depends(get_db),
):
    where, args = [], []
    if subject:
        where.append("subject = ?"); args.append(subject)
    if topic:
        where.append("topic = ?"); args.append(topic)
    if difficulty:
        where.append("difficulty = ?"); args.append(difficulty)
    if search:
        where.append("text LIKE ?"); args.append(f"%{search}%")
    cond = (" WHERE " + " AND ".join(where)) if where else ""
    total = db.execute("SELECT COUNT(*) FROM questions" + cond, args).fetchone()[0]
    rows = db.execute(
        f"SELECT {COLUMNS} FROM questions{cond} ORDER BY id LIMIT ? OFFSET ?", args + [size, (page - 1) * size]
    ).fetchall()
    return {"total": total, "page": page, "size": size, "items": [dict(r) for r in rows]}


@router.get("/{question_id}")
def get_question(question_id: int, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    row = db.execute(f"SELECT {COLUMNS} FROM questions WHERE id = ?", (question_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Question not found")
    return dict(row)


@router.post("", status_code=201)
def add_question(q: QuestionIn, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    cur = db.execute(
        "INSERT INTO questions (subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (q.subject, q.topic, q.difficulty, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d, q.answer, user["id"]),
    )
    return {"id": cur.lastrowid, **q.model_dump()}


@router.put("/{question_id}")
def update_question(question_id: int, q: QuestionIn, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    cur = db.execute(
        "UPDATE questions SET subject=?, topic=?, difficulty=?, text=?, opt_a=?, opt_b=?, opt_c=?, opt_d=?, answer=? "
        "WHERE id = ?",
        (q.subject, q.topic, q.difficulty, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d, q.answer, question_id),
    )
    if cur.rowcount == 0:
        raise HTTPException(404, "Question not found")
    return {"id": question_id, **q.model_dump()}


@router.delete("/{question_id}", status_code=204)
def delete_question(question_id: int, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    used = db.execute("SELECT COUNT(*) FROM quiz_questions WHERE question_id = ?", (question_id,)).fetchone()[0]
    if used:
        raise HTTPException(409, "This question is used in a quiz, remove it from the quiz first")
    cur = db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Question not found")
