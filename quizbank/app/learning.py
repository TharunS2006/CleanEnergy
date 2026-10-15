"""Shared learning logic: spaced repetition (Leitner boxes) and the confidence calibration score."""
from .db import today_plus

# days until the next review after reaching box 1..5
INTERVALS = [1, 2, 4, 8, 16]

# what each confidence level "claims" about the chance of being right
CONFIDENCE_CLAIM = {1: 0.33, 2: 0.66, 3: 0.95}


def update_revision(db, user_id, question_id, correct):
    """Wrong answer -> question goes to box 1 and returns tomorrow.
    Right answer on a question that is in the queue -> it moves up a box and waits longer.
    After box 5 the question has been learned and leaves the queue."""
    row = db.execute("SELECT box FROM revision WHERE user_id = ? AND question_id = ?", (user_id, question_id)).fetchone()
    if not correct:
        if row is None:
            db.execute("INSERT INTO revision (user_id, question_id, box, due) VALUES (?, ?, 1, ?)",
                       (user_id, question_id, today_plus(INTERVALS[0])))
        else:
            db.execute("UPDATE revision SET box = 1, due = ? WHERE user_id = ? AND question_id = ?",
                       (today_plus(INTERVALS[0]), user_id, question_id))
        return
    if row is None:
        return
    box = row["box"] + 1
    if box > len(INTERVALS):
        db.execute("DELETE FROM revision WHERE user_id = ? AND question_id = ?", (user_id, question_id))
    else:
        db.execute("UPDATE revision SET box = ?, due = ? WHERE user_id = ? AND question_id = ?",
                   (box, today_plus(INTERVALS[box - 1]), user_id, question_id))


def calibration_score(marked):
    """marked = list of (correct 0/1, confidence 1..3). Returns 0-100, or None if no confidence was given.
    It is 100 minus the Brier score: a student who says 'certain' and is right scores well,
    one who says 'certain' and is wrong is penalised heavily, and honest guessing is not punished."""
    rated = [(c, CONFIDENCE_CLAIM[conf]) for c, conf in marked if conf in CONFIDENCE_CLAIM]
    if not rated:
        return None
    brier = sum((claim - c) ** 2 for c, claim in rated) / len(rated)
    return round(100 * (1 - brier))
