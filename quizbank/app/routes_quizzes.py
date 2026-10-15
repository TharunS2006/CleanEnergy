from fastapi import APIRouter, Depends, HTTPException

from .auth import current_user, need_role
from .db import get_db
from .schemas import AttemptIn, QuizIn, RandomQuizIn

router = APIRouter(prefix="/api", tags=["quizzes"])


def make_quiz(db, user, title, subject, minutes, question_ids):
    cur = db.execute(
        "INSERT INTO quizzes (title, subject, minutes, created_by) VALUES (?, ?, ?, ?)",
        (title, subject, minutes, user["id"]),
    )
    quiz_id = cur.lastrowid
    for qid in question_ids:
        db.execute("INSERT INTO quiz_questions (quiz_id, question_id) VALUES (?, ?)", (quiz_id, qid))
    return {"id": quiz_id, "title": title, "subject": subject, "minutes": minutes, "questions": len(question_ids)}


@router.post("/quizzes", status_code=201)
def create_quiz(data: QuizIn, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    ids = list(dict.fromkeys(data.question_ids))  # drop duplicates, keep order
    marks = ",".join("?" * len(ids))
    found = db.execute(f"SELECT COUNT(*) FROM questions WHERE id IN ({marks})", ids).fetchone()[0]
    if found != len(ids):
        raise HTTPException(400, "Some question ids do not exist")
    return make_quiz(db, user, data.title, data.subject, data.minutes, ids)


@router.post("/quizzes/random", status_code=201)
def random_quiz(data: RandomQuizIn, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    where, args = ["subject = ?"], [data.subject]
    if data.topic:
        where.append("topic = ?"); args.append(data.topic)
    if data.difficulty:
        where.append("difficulty = ?"); args.append(data.difficulty)
    rows = db.execute(
        "SELECT id FROM questions WHERE " + " AND ".join(where) + " ORDER BY RANDOM() LIMIT ?", args + [data.count]
    ).fetchall()
    if len(rows) < data.count:
        raise HTTPException(400, f"Only {len(rows)} matching questions are available, you asked for {data.count}")
    return make_quiz(db, user, data.title, data.subject, data.minutes, [r["id"] for r in rows])


@router.get("/quizzes")
def list_quizzes(user=Depends(current_user), db=Depends(get_db)):
    rows = db.execute(
        "SELECT q.id, q.title, q.subject, q.minutes, COUNT(qq.question_id) AS questions "
        "FROM quizzes q LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id GROUP BY q.id ORDER BY q.id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/quizzes/{quiz_id}")
def get_quiz(quiz_id: int, user=Depends(current_user), db=Depends(get_db)):
    quiz = db.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    cols = "q.id, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d"
    if user["role"] != "student":
        cols += ", q.answer"            # students must never see the answers
    qs = db.execute(
        f"SELECT {cols} FROM questions q JOIN quiz_questions qq ON qq.question_id = q.id "
        "WHERE qq.quiz_id = ? ORDER BY q.id", (quiz_id,)
    ).fetchall()
    return {"id": quiz["id"], "title": quiz["title"], "subject": quiz["subject"], "minutes": quiz["minutes"],
            "questions": [dict(r) for r in qs]}


@router.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(quiz_id: int, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    cur = db.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Quiz not found")


@router.post("/quizzes/{quiz_id}/attempt", status_code=201)
def submit_attempt(quiz_id: int, data: AttemptIn, user=Depends(need_role("student")), db=Depends(get_db)):
    quiz = db.execute("SELECT id FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    rows = db.execute(
        "SELECT q.id, q.answer FROM questions q JOIN quiz_questions qq ON qq.question_id = q.id WHERE qq.quiz_id = ?",
        (quiz_id,),
    ).fetchall()
    score = 0
    marked = []
    for r in rows:
        chosen = data.answers.get(str(r["id"]))
        ok = 1 if chosen == r["answer"] else 0
        score += ok
        marked.append((r["id"], chosen, ok, r["answer"]))
    cur = db.execute(
        "INSERT INTO attempts (quiz_id, user_id, score, total) VALUES (?, ?, ?, ?)", (quiz_id, user["id"], score, len(rows))
    )
    for qid, chosen, ok, _ in marked:
        db.execute("INSERT INTO answers (attempt_id, question_id, chosen, correct) VALUES (?, ?, ?, ?)",
                   (cur.lastrowid, qid, chosen, ok))
    return {
        "attempt_id": cur.lastrowid, "score": score, "total": len(rows),
        "percent": round(100 * score / len(rows), 1) if rows else 0,
        "review": [{"question_id": qid, "your_answer": chosen, "correct_answer": right, "correct": bool(ok)}
                   for qid, chosen, ok, right in marked],
    }


@router.get("/attempts/mine")
def my_attempts(user=Depends(need_role("student")), db=Depends(get_db)):
    rows = db.execute(
        "SELECT a.id, q.title, a.score, a.total, a.taken_at FROM attempts a JOIN quizzes q ON q.id = a.quiz_id "
        "WHERE a.user_id = ? ORDER BY a.id DESC", (user["id"],)
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/quizzes/{quiz_id}/results")
def quiz_results(quiz_id: int, user=Depends(need_role("admin", "teacher")), db=Depends(get_db)):
    quiz = db.execute("SELECT title FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    rows = db.execute(
        "SELECT u.name, a.score, a.total, a.taken_at FROM attempts a JOIN users u ON u.id = a.user_id "
        "WHERE a.quiz_id = ? ORDER BY a.score DESC", (quiz_id,)
    ).fetchall()
    attempts = [dict(r) for r in rows]
    avg = round(sum(100 * r["score"] / r["total"] for r in attempts if r["total"]) / len(attempts), 1) if attempts else 0
    hardest = db.execute(
        "SELECT q.id, q.text, COUNT(*) AS times, SUM(ans.correct) AS right_count FROM answers ans "
        "JOIN attempts a ON a.id = ans.attempt_id JOIN questions q ON q.id = ans.question_id "
        "WHERE a.quiz_id = ? GROUP BY q.id ORDER BY (1.0 * SUM(ans.correct) / COUNT(*)) ASC LIMIT 3", (quiz_id,)
    ).fetchall()
    return {"quiz": quiz["title"], "attempts": attempts, "average_percent": avg,
            "hardest_questions": [dict(r) for r in hardest]}
