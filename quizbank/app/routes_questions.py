import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from .auth import current_user, need_role
from .db import get_db
from .schemas import ImportIn, QuestionIn

router = APIRouter(prefix="/api", tags=["question bank"])

COLUMNS = "id, subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, explanation"
STAFF = need_role("admin", "teacher")


@router.get("/subjects")
def subjects(user=Depends(current_user), db=Depends(get_db)):
    """Subjects and topics with question counts (students use this to pick what to practise)."""
    rows = db.execute("SELECT subject, topic, COUNT(*) AS n FROM questions GROUP BY subject, topic ORDER BY subject, topic").fetchall()
    return [dict(r) for r in rows]


@router.get("/questions")
def list_questions(
    subject: Optional[str] = None, topic: Optional[str] = None, difficulty: Optional[str] = None,
    search: Optional[str] = None, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100),
    user=Depends(STAFF), db=Depends(get_db),
):
    where, args = [], []
    if subject:
        where.append("subject = ?"); args.append(subject)
    if topic:
        where.append("topic = ?"); args.append(topic)
    if difficulty:
        where.append("difficulty = ?"); args.append(difficulty)
    if search:
        where.append("LOWER(text) LIKE ?"); args.append(f"%{search.lower()}%")
    cond = (" WHERE " + " AND ".join(where)) if where else ""
    total = db.scalar("SELECT COUNT(*) FROM questions" + cond, args)
    rows = db.execute(f"SELECT {COLUMNS} FROM questions{cond} ORDER BY id LIMIT ? OFFSET ?",
                      args + [size, (page - 1) * size]).fetchall()
    return {"total": total, "page": page, "size": size, "items": [dict(r) for r in rows]}


@router.post("/questions/import")
def import_questions(data: ImportIn, user=Depends(STAFF), db=Depends(get_db)):
    """Bulk upload. CSV header: subject,topic,difficulty,text,opt_a,opt_b,opt_c,opt_d,answer,explanation"""
    reader = csv.DictReader(io.StringIO(data.csv))
    needed = {"subject", "topic", "difficulty", "text", "opt_a", "opt_b", "opt_c", "opt_d", "answer"}
    if not reader.fieldnames or not needed.issubset({f.strip() for f in reader.fieldnames}):
        raise HTTPException(400, "CSV must have the columns: " + ", ".join(sorted(needed)) + " (and optionally explanation)")
    added, errors = 0, []
    for line, row in enumerate(reader, start=2):
        try:
            q = QuestionIn(**{k.strip(): (v or "").strip() for k, v in row.items() if k})
        except ValidationError as e:
            errors.append({"line": line, "problem": "; ".join(f"{x['loc'][0]}: {x['msg']}" for x in e.errors())})
            continue
        db.execute("INSERT INTO questions (subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, explanation, created_by) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (q.subject, q.topic, q.difficulty, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d, q.answer, q.explanation, user["id"]))
        added += 1
    return {"added": added, "errors": errors}


@router.get("/questions/{question_id}")
def get_question(question_id: int, user=Depends(STAFF), db=Depends(get_db)):
    row = db.execute(f"SELECT {COLUMNS} FROM questions WHERE id = ?", (question_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Question not found")
    return dict(row)


@router.post("/questions", status_code=201)
def add_question(q: QuestionIn, user=Depends(STAFF), db=Depends(get_db)):
    qid = db.insert(
        "INSERT INTO questions (subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, explanation, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (q.subject, q.topic, q.difficulty, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d, q.answer, q.explanation, user["id"]))
    return {"id": qid, **q.model_dump()}


@router.put("/questions/{question_id}")
def update_question(question_id: int, q: QuestionIn, user=Depends(STAFF), db=Depends(get_db)):
    cur = db.execute(
        "UPDATE questions SET subject=?, topic=?, difficulty=?, text=?, opt_a=?, opt_b=?, opt_c=?, opt_d=?, answer=?, explanation=? "
        "WHERE id = ?",
        (q.subject, q.topic, q.difficulty, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d, q.answer, q.explanation, question_id))
    if cur.rowcount == 0:
        raise HTTPException(404, "Question not found")
    return {"id": question_id, **q.model_dump()}


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: int, user=Depends(STAFF), db=Depends(get_db)):
    if db.scalar("SELECT COUNT(*) FROM quiz_questions WHERE question_id = ?", (question_id,)):
        raise HTTPException(409, "This question is used in a quiz, remove it from the quiz first")
    cur = db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Question not found")
