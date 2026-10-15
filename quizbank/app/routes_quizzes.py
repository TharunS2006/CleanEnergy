import csv
import io
import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .auth import current_user, need_role
from .db import get_db, now, parse, stamp
from .learning import calibration_score, update_revision
from .schemas import QuizIn, RandomQuizIn, SubmitIn

router = APIRouter(prefix="/api", tags=["quizzes"])
STAFF = need_role("admin", "teacher")
GRACE = timedelta(seconds=30)      # small allowance for network delay after the timer ends


def make_quiz(db, user, title, subject, minutes, max_attempts, question_ids):
    quiz_id = db.insert("INSERT INTO quizzes (title, subject, minutes, max_attempts, created_by) VALUES (?, ?, ?, ?, ?)",
                        (title, subject, minutes, max_attempts, user["id"]))
    for qid in question_ids:
        db.execute("INSERT INTO quiz_questions (quiz_id, question_id) VALUES (?, ?)", (quiz_id, qid))
    return {"id": quiz_id, "title": title, "subject": subject, "minutes": minutes,
            "max_attempts": max_attempts, "questions": len(question_ids)}


@router.post("/quizzes", status_code=201)
def create_quiz(data: QuizIn, user=Depends(STAFF), db=Depends(get_db)):
    ids = list(dict.fromkeys(data.question_ids))
    marks = ",".join("?" * len(ids))
    if db.scalar(f"SELECT COUNT(*) FROM questions WHERE id IN ({marks})", ids) != len(ids):
        raise HTTPException(400, "Some question ids do not exist")
    return make_quiz(db, user, data.title, data.subject, data.minutes, data.max_attempts, ids)


@router.post("/quizzes/random", status_code=201)
def random_quiz(data: RandomQuizIn, user=Depends(STAFF), db=Depends(get_db)):
    where, args = ["subject = ?"], [data.subject]
    if data.topic:
        where.append("topic = ?"); args.append(data.topic)
    if data.difficulty:
        where.append("difficulty = ?"); args.append(data.difficulty)
    rows = db.execute("SELECT id FROM questions WHERE " + " AND ".join(where) + " ORDER BY RANDOM() LIMIT ?",
                      args + [data.count]).fetchall()
    if len(rows) < data.count:
        raise HTTPException(400, f"Only {len(rows)} matching questions are available, you asked for {data.count}")
    return make_quiz(db, user, data.title, data.subject, data.minutes, data.max_attempts, [r["id"] for r in rows])


@router.get("/quizzes")
def list_quizzes(user=Depends(current_user), db=Depends(get_db)):
    rows = db.execute(
        "SELECT q.id, q.title, q.subject, q.minutes, q.max_attempts, COUNT(qq.question_id) AS questions "
        "FROM quizzes q LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id GROUP BY q.id ORDER BY q.id DESC").fetchall()
    out = [dict(r) for r in rows]
    if user["role"] == "student":
        for q in out:
            q["my_attempts"] = db.scalar("SELECT COUNT(*) FROM attempts WHERE quiz_id = ? AND user_id = ?", (q["id"], user["id"]))
    return out


@router.get("/quizzes/{quiz_id}")
def get_quiz(quiz_id: int, user=Depends(STAFF), db=Depends(get_db)):
    """Teacher view of a quiz, with the correct answers."""
    quiz = db.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    qs = db.execute("SELECT q.id, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d, q.answer, q.explanation FROM questions q "
                    "JOIN quiz_questions qq ON qq.question_id = q.id WHERE qq.quiz_id = ? ORDER BY q.id", (quiz_id,)).fetchall()
    return {**dict(quiz), "questions": [dict(r) for r in qs]}


@router.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(quiz_id: int, user=Depends(STAFF), db=Depends(get_db)):
    if db.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,)).rowcount == 0:
        raise HTTPException(404, "Quiz not found")


# ---------------------------------------------------------------- taking a quiz
def paper_for(db, attempt_id, quiz_id):
    """The questions of an attempt in a per-attempt random order, options shuffled too.
    The order is derived from the attempt id, so reloading the page shows the same paper."""
    rows = db.execute("SELECT q.id, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d FROM questions q "
                      "JOIN quiz_questions qq ON qq.question_id = q.id WHERE qq.quiz_id = ? ORDER BY q.id", (quiz_id,)).fetchall()
    rng = random.Random(attempt_id * 7919)
    rows = list(rows)
    rng.shuffle(rows)
    paper = []
    for r in rows:
        keys = ["a", "b", "c", "d"]
        random.Random(attempt_id * 104729 + r["id"]).shuffle(keys)
        paper.append({"id": r["id"], "text": r["text"], "options": [{"key": k, "text": r["opt_" + k]} for k in keys]})
    return paper


def close_expired(db, attempt):
    """An attempt that ran out of time without being submitted is closed with score 0."""
    total = db.scalar("SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = ?", (attempt["quiz_id"],))
    db.execute("UPDATE attempts SET status = 'done', late = 1, total = ?, submitted_at = ? WHERE id = ?",
               (total, stamp(now()), attempt["id"]))


@router.post("/quizzes/{quiz_id}/start", status_code=201)
def start_attempt(quiz_id: int, user=Depends(need_role("student")), db=Depends(get_db)):
    quiz = db.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    open_one = db.execute("SELECT * FROM attempts WHERE quiz_id = ? AND user_id = ? AND status = 'open'", (quiz_id, user["id"])).fetchone()
    if open_one is not None:
        if now() <= parse(open_one["deadline"]) + GRACE:           # resume the same attempt
            attempt = open_one
        else:
            close_expired(db, open_one)
            attempt = None
    else:
        attempt = None
    if attempt is None:
        used = db.scalar("SELECT COUNT(*) FROM attempts WHERE quiz_id = ? AND user_id = ?", (quiz_id, user["id"]))
        if used >= quiz["max_attempts"]:
            raise HTTPException(409, f"You have used all {quiz['max_attempts']} attempts of this quiz")
        started = now()
        aid = db.insert("INSERT INTO attempts (quiz_id, user_id, started_at, deadline, status) VALUES (?, ?, ?, ?, 'open')",
                        (quiz_id, user["id"], stamp(started), stamp(started + timedelta(minutes=quiz["minutes"]))))
        attempt = db.execute("SELECT * FROM attempts WHERE id = ?", (aid,)).fetchone()
    left = int((parse(attempt["deadline"]) - now()).total_seconds())
    return {"attempt_id": attempt["id"], "title": quiz["title"], "subject": quiz["subject"],
            "seconds_left": max(0, left), "questions": paper_for(db, attempt["id"], quiz_id)}


@router.post("/attempts/{attempt_id}/submit", status_code=201)
def submit_attempt(attempt_id: int, data: SubmitIn, user=Depends(need_role("student")), db=Depends(get_db)):
    attempt = db.execute("SELECT * FROM attempts WHERE id = ? AND user_id = ?", (attempt_id, user["id"])).fetchone()
    if attempt is None:
        raise HTTPException(404, "Attempt not found")
    if attempt["status"] != "open":
        raise HTTPException(409, "This attempt was already submitted")
    late = now() > parse(attempt["deadline"]) + GRACE
    questions = db.execute(
        "SELECT q.id, q.text, q.answer, q.explanation, q.topic FROM questions q JOIN quiz_questions qq ON qq.question_id = q.id "
        "WHERE qq.quiz_id = ?", (attempt["quiz_id"],)).fetchall()
    score, marked, review = 0, [], []
    for q in questions:
        given = data.answers.get(str(q["id"]))
        chosen = given.choice if given else None
        conf = given.confidence if given else None
        ok = 1 if chosen == q["answer"] else 0
        score += ok
        db.execute("INSERT INTO answers (attempt_id, question_id, chosen, correct, confidence) VALUES (?, ?, ?, ?, ?)",
                   (attempt_id, q["id"], chosen, ok, conf))
        if chosen is not None:
            if conf:
                marked.append((ok, conf))
            update_revision(db, user["id"], q["id"], bool(ok))
        elif not ok:
            update_revision(db, user["id"], q["id"], False)
        review.append({"question_id": q["id"], "text": q["text"], "topic": q["topic"], "your_answer": chosen,
                       "correct_answer": q["answer"], "correct": bool(ok), "confidence": conf, "explanation": q["explanation"],
                       "misconception": bool(chosen and not ok and conf == 3)})
    cal = calibration_score(marked)
    db.execute("UPDATE attempts SET status = 'done', submitted_at = ?, score = ?, total = ?, late = ?, calibration = ? WHERE id = ?",
               (stamp(now()), score, len(questions), 1 if late else 0, cal, attempt_id))
    return {"attempt_id": attempt_id, "score": score, "total": len(questions),
            "percent": round(100 * score / len(questions), 1) if questions else 0,
            "late": late, "calibration": cal, "review": review}


@router.get("/attempts/mine")
def my_attempts(user=Depends(need_role("student")), db=Depends(get_db)):
    rows = db.execute(
        "SELECT a.id, q.title, a.score, a.total, a.late, a.calibration, a.submitted_at FROM attempts a "
        "JOIN quizzes q ON q.id = a.quiz_id WHERE a.user_id = ? AND a.status = 'done' ORDER BY a.id DESC", (user["id"],)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- results for teachers
def finished(db, quiz_id):
    return db.execute(
        "SELECT a.id, a.user_id, u.name, a.score, a.total, a.late, a.calibration, a.started_at, a.submitted_at "
        "FROM attempts a JOIN users u ON u.id = a.user_id WHERE a.quiz_id = ? AND a.status = 'done' ORDER BY a.score DESC, a.id",
        (quiz_id,)).fetchall()


@router.get("/quizzes/{quiz_id}/results")
def quiz_results(quiz_id: int, user=Depends(STAFF), db=Depends(get_db)):
    quiz = db.execute("SELECT title FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    attempts = [dict(r) for r in finished(db, quiz_id)]
    valid = [a for a in attempts if a["total"] and not a["late"]]
    avg = round(sum(100 * a["score"] / a["total"] for a in valid) / len(valid), 1) if valid else 0
    hardest = db.execute(
        "SELECT q.id, q.text, COUNT(*) AS times, SUM(ans.correct) AS right_count FROM answers ans "
        "JOIN attempts a ON a.id = ans.attempt_id JOIN questions q ON q.id = ans.question_id "
        "WHERE a.quiz_id = ? AND a.status = 'done' GROUP BY q.id ORDER BY (1.0 * SUM(ans.correct) / COUNT(*)) ASC LIMIT 3",
        (quiz_id,)).fetchall()
    return {"quiz": quiz["title"], "attempts": attempts, "average_percent": avg, "hardest_questions": [dict(r) for r in hardest]}


@router.get("/quizzes/{quiz_id}/results.csv")
def results_csv(quiz_id: int, user=Depends(STAFF), db=Depends(get_db)):
    if db.execute("SELECT 1 FROM quizzes WHERE id = ?", (quiz_id,)).fetchone() is None:
        raise HTTPException(404, "Quiz not found")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["student", "score", "total", "percent", "calibration", "late", "submitted_at"])
    for a in finished(db, quiz_id):
        w.writerow([a["name"], a["score"], a["total"], round(100 * a["score"] / a["total"], 1) if a["total"] else 0,
                    a["calibration"] if a["calibration"] is not None else "", "yes" if a["late"] else "no", a["submitted_at"]])
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=quiz-{quiz_id}-results.csv"})


@router.get("/quizzes/{quiz_id}/analysis")
def item_analysis(quiz_id: int, user=Depends(STAFF), db=Depends(get_db)):
    """Classical item analysis: how hard was each question really, and does it separate strong from weak students?
    difficulty index  p = share of students who got it right (0..1)
    discrimination    D = p(top 27% of students) - p(bottom 27%), needs at least 4 students"""
    quiz = db.execute("SELECT title FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    attempts = [a for a in finished(db, quiz_id) if not a["late"] and a["total"]]
    ids = [a["id"] for a in attempts]
    qs = db.execute("SELECT q.id, q.text, q.difficulty, q.answer FROM questions q JOIN quiz_questions qq ON qq.question_id = q.id "
                    "WHERE qq.quiz_id = ? ORDER BY q.id", (quiz_id,)).fetchall()
    rows = []
    if ids:
        marks = ",".join("?" * len(ids))
        rows = db.execute(f"SELECT attempt_id, question_id, chosen, correct FROM answers WHERE attempt_id IN ({marks})", ids).fetchall()
    score_of = {a["id"]: a["score"] for a in attempts}
    ranked = sorted(ids, key=lambda i: -score_of[i])
    k = max(1, round(0.27 * len(ranked)))
    upper, lower = set(ranked[:k]), set(ranked[-k:])
    items = []
    for q in qs:
        mine = [r for r in rows if r["question_id"] == q["id"]]
        n = len(mine)
        p = sum(r["correct"] for r in mine) / n if n else None
        d = None
        if len(attempts) >= 4 and n:
            pu = [r["correct"] for r in mine if r["attempt_id"] in upper]
            pl = [r["correct"] for r in mine if r["attempt_id"] in lower]
            if pu and pl:
                d = round(sum(pu) / len(pu) - sum(pl) / len(pl), 2)
        wrong = {}
        for r in mine:
            if r["chosen"] and r["chosen"] != q["answer"]:
                wrong[r["chosen"]] = wrong.get(r["chosen"], 0) + 1
        flags = []
        if n < 3:
            p_for_flags = None
        else:
            p_for_flags = p
        if p_for_flags is not None and p_for_flags > 0.9:
            flags.append("very easy: almost everyone got it right")
        if p_for_flags is not None and p_for_flags < 0.3:
            flags.append("very hard: check the question and the answer key")
        if d is not None and d < 0.2:
            flags.append("poor discrimination: strong students do not do better than weak ones")
        if p_for_flags is not None:
            real = "easy" if p >= 0.7 else "hard" if p < 0.4 else "medium"
            if real != q["difficulty"]:
                flags.append(f"labelled {q['difficulty']} but behaves like {real}")
        top_wrong = max(wrong, key=wrong.get) if wrong else None
        items.append({"question_id": q["id"], "text": q["text"], "labelled": q["difficulty"], "answered": n,
                      "difficulty_index": round(p, 2) if p is not None else None, "discrimination": d,
                      "most_chosen_wrong_option": top_wrong, "flags": flags})
    return {"quiz": quiz["title"], "students": len(attempts), "items": items}


@router.get("/quizzes/{quiz_id}/leaderboard")
def leaderboard(quiz_id: int, user=Depends(current_user), db=Depends(get_db)):
    if db.execute("SELECT 1 FROM quizzes WHERE id = ?", (quiz_id,)).fetchone() is None:
        raise HTTPException(404, "Quiz not found")
    best = {}
    for a in finished(db, quiz_id):
        if a["late"] or not a["total"]:
            continue
        seconds = int((parse(a["submitted_at"]) - parse(a["started_at"])).total_seconds())
        key = (-a["score"], seconds)
        if a["user_id"] not in best or key < best[a["user_id"]][0]:
            best[a["user_id"]] = (key, a["name"], a["score"], a["total"], seconds)
    ordered = sorted(best.items(), key=lambda kv: kv[1][0])
    board = [{"rank": i + 1, "name": v[1], "score": v[2], "total": v[3], "seconds": v[4], "you": uid == user["id"]}
             for i, (uid, v) in enumerate(ordered)]
    return {"top": board[:10], "your_rank": next((b["rank"] for b in board if b["you"]), None), "players": len(board)}
