import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .auth import need_role
from .db import get_db, now, stamp, today_plus
from .learning import update_revision
from .schemas import PracticeAnswerIn

router = APIRouter(prefix="/api", tags=["learning"])
STUDENT = need_role("student")
LEVEL = {"easy": 1, "medium": 2, "hard": 3}
NAME = {1: "easy", 2: "medium", 3: "hard"}


def topic_accuracy(db, user_id, subject=None):
    """Accuracy per (subject, topic) from practice answers and finished quiz answers together."""
    rows = db.execute(
        "SELECT q.subject, q.topic, p.correct FROM practice_log p JOIN questions q ON q.id = p.question_id WHERE p.user_id = ? "
        "UNION ALL "
        "SELECT q.subject, q.topic, a.correct FROM answers a JOIN attempts t ON t.id = a.attempt_id "
        "JOIN questions q ON q.id = a.question_id WHERE t.user_id = ? AND t.status = 'done' AND a.chosen IS NOT NULL",
        (user_id, user_id)).fetchall()
    stats = {}
    for r in rows:
        if subject and r["subject"] != subject:
            continue
        s = stats.setdefault((r["subject"], r["topic"]), [0, 0])
        s[0] += 1
        s[1] += r["correct"]
    return stats


def target_level(db, user_id, subject):
    """Adaptive difficulty: look at the last 6 practice answers in this subject.
    Mostly right -> step up from the level they have been working at; mostly wrong -> step down."""
    rows = db.execute(
        "SELECT q.difficulty, p.correct FROM practice_log p JOIN questions q ON q.id = p.question_id "
        "WHERE p.user_id = ? AND q.subject = ? ORDER BY p.id DESC LIMIT 6", (user_id, subject)).fetchall()
    if len(rows) < 3:
        return 1
    accuracy = sum(r["correct"] for r in rows) / len(rows)
    base = round(sum(LEVEL[r["difficulty"]] for r in rows) / len(rows))
    if accuracy >= 0.8:
        base += 1
    elif accuracy <= 0.4:
        base -= 1
    return max(1, min(3, base))


def hide_answer(q, shuffle_seed):
    keys = ["a", "b", "c", "d"]
    random.Random(shuffle_seed).shuffle(keys)
    return {"id": q["id"], "subject": q["subject"], "topic": q["topic"], "text": q["text"],
            "options": [{"key": k, "text": q["opt_" + k]} for k in keys]}


@router.get("/practice/next")
def practice_next(subject: str, topic: Optional[str] = None, user=Depends(STUDENT), db=Depends(get_db)):
    """Picks the next practice question: weakest topic first (when no topic is chosen), difficulty adapted to recent results."""
    pool = db.execute("SELECT * FROM questions WHERE subject = ?" + (" AND topic = ?" if topic else ""),
                      (subject, topic) if topic else (subject,)).fetchall()
    if not pool:
        raise HTTPException(404, "No questions for this subject yet")
    recent = {r["question_id"] for r in db.execute(
        "SELECT question_id FROM practice_log WHERE user_id = ? ORDER BY id DESC LIMIT 8", (user["id"],)).fetchall()}
    fresh = [q for q in pool if q["id"] not in recent] or pool
    chosen_topic = topic
    if not topic:
        stats = topic_accuracy(db, user["id"], subject)
        known = {t: (c / n) for (s, t), (n, c) in stats.items() if n >= 2}
        in_pool = {q["topic"] for q in fresh}
        weak = [t for t in sorted(known, key=known.get) if t in in_pool]
        unseen = [t for t in in_pool if (subject, t) not in stats]
        pick = unseen[0] if unseen and random.random() < 0.5 else (weak[0] if weak else None)
        if pick:
            fresh = [q for q in fresh if q["topic"] == pick]
            chosen_topic = pick
    level = target_level(db, user["id"], subject)
    near = [q for q in fresh if LEVEL[q["difficulty"]] == level] or \
           sorted(fresh, key=lambda q: abs(LEVEL[q["difficulty"]] - level))[:3]
    q = random.choice(near)
    out = hide_answer(q, q["id"] * 31 + int(now().timestamp()) % 1000)
    out["why_this_question"] = f"topic {chosen_topic or q['topic']}, level {NAME[level]} chosen from your recent answers"
    return out


@router.post("/practice/answer")
def practice_answer(data: PracticeAnswerIn, user=Depends(STUDENT), db=Depends(get_db)):
    q = db.execute("SELECT * FROM questions WHERE id = ?", (data.question_id,)).fetchone()
    if q is None:
        raise HTTPException(404, "Question not found")
    ok = 1 if data.choice == q["answer"] else 0
    db.execute("INSERT INTO practice_log (user_id, question_id, chosen, correct, confidence, at) VALUES (?, ?, ?, ?, ?, ?)",
               (user["id"], q["id"], data.choice, ok, data.confidence, stamp(now())))
    update_revision(db, user["id"], q["id"], bool(ok))
    return {"correct": bool(ok), "correct_answer": q["answer"], "explanation": q["explanation"],
            "misconception": bool(not ok and data.confidence == 3)}


@router.get("/revision/due")
def revision_due(user=Depends(STUDENT), db=Depends(get_db)):
    """Questions that are due for review today (spaced repetition)."""
    rows = db.execute(
        "SELECT q.*, r.box FROM revision r JOIN questions q ON q.id = r.question_id "
        "WHERE r.user_id = ? AND r.due <= ? ORDER BY r.due, r.box", (user["id"], today_plus(0))).fetchall()
    waiting = db.scalar("SELECT COUNT(*) FROM revision WHERE user_id = ?", (user["id"],))
    return {"due": len(rows), "in_queue": waiting,
            "questions": [{**hide_answer(q, q["id"] * 17), "box": q["box"]} for q in rows[:10]]}


@router.get("/me/mastery")
def mastery(user=Depends(STUDENT), db=Depends(get_db)):
    """Topic mastery map, weak-topic advice and the calibration trend."""
    stats = topic_accuracy(db, user["id"])
    topics = []
    for (subject, topic), (n, c) in sorted(stats.items()):
        pct = round(100 * c / n)
        level = "not enough data" if n < 3 else "strong" if pct >= 75 else "learning" if pct >= 50 else "weak"
        topics.append({"subject": subject, "topic": topic, "answered": n, "correct": c, "percent": pct, "level": level})
    weak = sorted([t for t in topics if t["answered"] >= 3 and t["percent"] < 75], key=lambda t: t["percent"])[:3]
    cal = [r["calibration"] for r in db.execute(
        "SELECT calibration FROM attempts WHERE user_id = ? AND status = 'done' AND calibration IS NOT NULL ORDER BY id DESC LIMIT 5",
        (user["id"],)).fetchall()]
    return {"topics": topics, "focus_on": weak,
            "calibration_recent": cal,
            "calibration_average": round(sum(cal) / len(cal)) if cal else None,
            "revision_due": db.scalar("SELECT COUNT(*) FROM revision WHERE user_id = ? AND due <= ?", (user["id"], today_plus(0))),
            "practice_answers": db.scalar("SELECT COUNT(*) FROM practice_log WHERE user_id = ?", (user["id"],))}
