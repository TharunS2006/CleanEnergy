import os
import tempfile

# use a throw-away database for the tests (must be set before the app is imported)
os.environ.setdefault("QUIZ_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from datetime import timedelta  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.db import connect, now, stamp  # noqa: E402
from app.learning import calibration_score  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
COUNTER = [0]


def person(role):
    """Registers a fresh user and returns the auth header."""
    COUNTER[0] += 1
    email = f"{role}{COUNTER[0]}@x.com"
    client.post("/api/register", json={"name": f"{role.title()} {COUNTER[0]}", "email": email, "password": "secret1", "role": role})
    token = client.post("/api/login", json={"email": email, "password": "secret1"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def question(text, subject="Python", topic="Basics", difficulty="easy", answer="b"):
    return {"subject": subject, "topic": topic, "difficulty": difficulty, "text": text, "opt_a": "one", "opt_b": "two",
            "opt_c": "three", "opt_d": "four", "answer": answer, "explanation": "Because two is the answer."}


def add_questions(teacher, subject, count, **kw):
    return [client.post("/api/questions", json=question(f"{subject} question {i}", subject=subject, **kw), headers=teacher).json()["id"]
            for i in range(count)]


def make_quiz(teacher, ids, subject, minutes=10, attempts=2):
    return client.post("/api/quizzes", json={"title": "Test quiz", "subject": subject, "minutes": minutes,
                                             "max_attempts": attempts, "question_ids": ids}, headers=teacher).json()["id"]


# ---------------------------------------------------------------- accounts
def test_register_login_roles():
    assert client.post("/api/register", json={"name": "Asha", "email": "asha@x.com", "password": "secret1"}).status_code == 201
    assert client.post("/api/register", json={"name": "Asha", "email": "asha@x.com", "password": "secret1"}).status_code == 409
    assert client.post("/api/login", json={"email": "asha@x.com", "password": "wrong"}).status_code == 401
    assert client.get("/api/me").status_code == 401
    r = client.post("/api/register", json={"name": "Evil", "email": "e@x.com", "password": "secret1", "role": "admin"})
    assert r.status_code == 422
    assert client.get("/api/users", headers=person("teacher")).status_code == 403


# ---------------------------------------------------------------- question bank
def test_question_crud_validation_and_filters():
    teacher, student = person("teacher"), person("student")
    assert client.post("/api/questions", json=question("A fine question?"), headers=student).status_code == 403
    qid = client.post("/api/questions", json=question("What is 1 + 1 here?", subject="Maths"), headers=teacher).json()["id"]
    assert client.get(f"/api/questions/{qid}", headers=teacher).json()["explanation"].startswith("Because")
    assert client.put(f"/api/questions/{qid}", json=question("Changed question?", subject="Maths", difficulty="hard"),
                      headers=teacher).json()["difficulty"] == "hard"
    assert client.post("/api/questions", json=question("Bad answer", answer="z"), headers=teacher).status_code == 422
    assert client.post("/api/questions", json=question("Bad level", difficulty="insane"), headers=teacher).status_code == 422
    for i in range(11):
        client.post("/api/questions", json=question(f"Filter question number {i}", subject="Filt"), headers=teacher)
    page = client.get("/api/questions?subject=Filt&size=5&page=3", headers=teacher).json()
    assert page["total"] == 11 and len(page["items"]) == 1
    assert client.get("/api/questions?subject=Filt&search=NUMBER 10", headers=teacher).json()["total"] == 1   # case-insensitive
    assert client.delete(f"/api/questions/{qid}", headers=teacher).status_code == 204
    assert client.get(f"/api/questions/{qid}", headers=teacher).status_code == 404


def test_csv_import_reports_bad_lines():
    teacher = person("teacher")
    text = ("subject,topic,difficulty,text,opt_a,opt_b,opt_c,opt_d,answer,explanation\n"
            "CsvSub,T1,easy,Is this row fine?,a,b,c,d,a,fine\n"
            "CsvSub,T1,easy,Is this row bad?,a,b,c,d,x,wrong answer letter\n"
            "CsvSub,T2,hard,Another good one?,1,2,3,4,d,\n")
    r = client.post("/api/questions/import", json={"csv": text}, headers=teacher).json()
    assert r["added"] == 2 and len(r["errors"]) == 1 and r["errors"][0]["line"] == 3
    assert client.post("/api/questions/import", json={"csv": "name,age\nx,1\n"}, headers=teacher).status_code == 400


def test_used_question_cannot_be_deleted():
    teacher = person("teacher")
    ids = add_questions(teacher, "Used", 1)
    make_quiz(teacher, ids, "Used")
    assert client.delete(f"/api/questions/{ids[0]}", headers=teacher).status_code == 409


# ---------------------------------------------------------------- quizzes and attempts
def test_random_quiz():
    teacher = person("teacher")
    add_questions(teacher, "Rand", 4)
    ok = client.post("/api/quizzes/random", json={"title": "Random", "subject": "Rand", "minutes": 5, "count": 3}, headers=teacher)
    assert ok.status_code == 201 and ok.json()["questions"] == 3
    assert client.post("/api/quizzes/random", json={"title": "Random", "subject": "Rand", "minutes": 5, "count": 9}, headers=teacher).status_code == 400


def test_full_quiz_flow_with_confidence_and_revision():
    teacher, student = person("teacher"), person("student")
    ids = add_questions(teacher, "Flow", 4)
    qid = make_quiz(teacher, ids, "Flow")
    start = client.post(f"/api/quizzes/{qid}/start", headers=student)
    assert start.status_code == 201
    paper = start.json()
    assert len(paper["questions"]) == 4 and paper["seconds_left"] > 590
    assert "answer" not in paper["questions"][0] and len(paper["questions"][0]["options"]) == 4
    # starting again resumes the same attempt instead of burning a second one
    assert client.post(f"/api/quizzes/{qid}/start", headers=student).json()["attempt_id"] == paper["attempt_id"]
    answers = {str(ids[0]): {"choice": "b", "confidence": 3}, str(ids[1]): {"choice": "b", "confidence": 2},
               str(ids[2]): {"choice": "a", "confidence": 3},            # confidently wrong -> misconception
               str(ids[3]): {"choice": "c", "confidence": 1}}           # honest guess, wrong
    res = client.post(f"/api/attempts/{paper['attempt_id']}/submit", json={"answers": answers}, headers=student).json()
    assert res["score"] == 2 and res["total"] == 4 and res["late"] is False
    flagged = [r for r in res["review"] if r["misconception"]]
    assert len(flagged) == 1 and flagged[0]["question_id"] == ids[2]
    assert res["review"][0]["explanation"].startswith("Because")
    assert res["calibration"] is not None
    assert client.post(f"/api/attempts/{paper['attempt_id']}/submit", json={"answers": {}}, headers=student).status_code == 409
    # the two wrong answers are now waiting in the revision queue, due tomorrow
    mastery = client.get("/api/me/mastery", headers=student).json()
    assert mastery["topics"][0]["answered"] == 4
    db = connect()
    assert db.scalar("SELECT COUNT(*) FROM revision") >= 2
    db.close()


def test_attempt_limit_and_roles():
    teacher, student = person("teacher"), person("student")
    qid = make_quiz(teacher, add_questions(teacher, "Lim", 2), "Lim", attempts=1)
    a = client.post(f"/api/quizzes/{qid}/start", headers=student).json()
    client.post(f"/api/attempts/{a['attempt_id']}/submit", json={"answers": {}}, headers=student)
    assert client.post(f"/api/quizzes/{qid}/start", headers=student).status_code == 409
    assert client.post(f"/api/quizzes/{qid}/start", headers=teacher).status_code == 403
    assert client.get(f"/api/quizzes/{qid}", headers=student).status_code == 403   # students never get the answer key


def test_timer_is_enforced_by_the_server():
    teacher, student = person("teacher"), person("student")
    ids = add_questions(teacher, "Late", 2)
    qid = make_quiz(teacher, ids, "Late", minutes=5)
    a = client.post(f"/api/quizzes/{qid}/start", headers=student).json()
    # pretend the student started 10 minutes ago on a 5 minute quiz
    db = connect()
    db.execute("UPDATE attempts SET started_at = ?, deadline = ? WHERE id = ?",
               (stamp(now() - timedelta(minutes=10)), stamp(now() - timedelta(minutes=5)), a["attempt_id"]))
    db.commit(); db.close()
    res = client.post(f"/api/attempts/{a['attempt_id']}/submit",
                      json={"answers": {str(ids[0]): {"choice": "b"}}}, headers=student).json()
    assert res["late"] is True
    board = client.get(f"/api/quizzes/{qid}/leaderboard", headers=student).json()
    assert board["players"] == 0       # late attempts are kept out of the leaderboard


def test_item_analysis_and_leaderboard():
    teacher = person("teacher")
    ids = add_questions(teacher, "Item", 4)
    qid = make_quiz(teacher, ids, "Item", attempts=3)
    # five students: scores 4, 3, 2, 1, 0 out of 4 (q0 easy for all but the weakest, q3 only the best get)
    plan = [[1, 1, 1, 1], [1, 1, 1, 0], [1, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0]]
    heads = []
    for row in plan:
        s = person("student")
        heads.append(s)
        a = client.post(f"/api/quizzes/{qid}/start", headers=s).json()
        ans = {str(ids[i]): {"choice": "b" if right else "a", "confidence": 2} for i, right in enumerate(row)}
        client.post(f"/api/attempts/{a['attempt_id']}/submit", json={"answers": ans}, headers=s)
    an = client.get(f"/api/quizzes/{qid}/analysis", headers=teacher).json()
    assert an["students"] == 5
    by_id = {i["question_id"]: i for i in an["items"]}
    assert by_id[ids[0]]["difficulty_index"] == 0.8 and by_id[ids[3]]["difficulty_index"] == 0.2
    assert by_id[ids[3]]["discrimination"] is not None and by_id[ids[3]]["discrimination"] > 0.5
    assert by_id[ids[3]]["most_chosen_wrong_option"] == "a"
    assert any("very hard" in f for f in by_id[ids[3]]["flags"])
    board = client.get(f"/api/quizzes/{qid}/leaderboard", headers=heads[0]).json()
    assert board["top"][0]["score"] == 4 and board["your_rank"] == 1
    res = client.get(f"/api/quizzes/{qid}/results", headers=teacher).json()
    assert len(res["attempts"]) == 5 and res["average_percent"] == 50.0
    csv_text = client.get(f"/api/quizzes/{qid}/results.csv", headers=teacher)
    assert csv_text.headers["content-type"].startswith("text/csv") and csv_text.text.count("\n") == 6


# ---------------------------------------------------------------- learning features
def test_calibration_score():
    assert calibration_score([]) is None
    honest = calibration_score([(1, 3), (1, 3), (0, 1)])           # sure when right, unsure when wrong
    overconfident = calibration_score([(1, 3), (0, 3), (0, 3)])     # sure even when wrong
    assert honest > overconfident
    assert calibration_score([(1, 3)]) > 99 - 1


def test_practice_adapts_and_revision_spaces_questions():
    teacher, student = person("teacher"), person("student")
    easy = add_questions(teacher, "Adapt", 4, difficulty="easy", topic="Warmup")
    hard = add_questions(teacher, "Adapt", 4, difficulty="hard", topic="Warmup")
    first = client.get("/api/practice/next?subject=Adapt", headers=student).json()
    assert first["id"] in easy and "answer" not in first                     # new students start easy
    for _ in range(4):                                                        # answer four questions correctly
        q = client.get("/api/practice/next?subject=Adapt", headers=student).json()
        r = client.post("/api/practice/answer", json={"question_id": q["id"], "choice": "b", "confidence": 3}, headers=student).json()
        assert r["correct"] is True and r["explanation"]
    nxt = client.get("/api/practice/next?subject=Adapt", headers=student).json()
    assert nxt["id"] in hard                                                  # doing well -> harder questions
    # a wrong, confident answer is flagged and enters the revision queue
    wrong = client.post("/api/practice/answer", json={"question_id": nxt["id"], "choice": "a", "confidence": 3}, headers=student).json()
    assert wrong["correct"] is False and wrong["misconception"] is True
    db = connect()
    assert db.scalar("SELECT box FROM revision WHERE question_id = ?", (nxt["id"],)) == 1
    db.execute("UPDATE revision SET due = '2000-01-01' WHERE question_id = ?", (nxt["id"],))    # make it due today
    db.commit(); db.close()
    due = client.get("/api/revision/due", headers=student).json()
    assert due["due"] == 1 and due["questions"][0]["id"] == nxt["id"]
    client.post("/api/practice/answer", json={"question_id": nxt["id"], "choice": "b"}, headers=student)    # now right
    db = connect()
    assert db.scalar("SELECT box FROM revision WHERE question_id = ?", (nxt["id"],)) == 2     # moved up a box
    db.close()
    assert client.get("/api/practice/next?subject=Nothing", headers=student).status_code == 404


def test_mastery_points_to_weak_topics():
    teacher, student = person("teacher"), person("student")
    good = add_questions(teacher, "Map", 3, topic="Strong")
    bad = add_questions(teacher, "Map", 3, topic="Weak")
    for q in good:
        client.post("/api/practice/answer", json={"question_id": q, "choice": "b"}, headers=student)
    for q in bad:
        client.post("/api/practice/answer", json={"question_id": q, "choice": "a"}, headers=student)
    m = client.get("/api/me/mastery", headers=student).json()
    levels = {t["topic"]: t["level"] for t in m["topics"]}
    assert levels == {"Strong": "strong", "Weak": "weak"}
    assert m["focus_on"][0]["topic"] == "Weak" and m["practice_answers"] == 6


def test_home_page_and_docs_are_served():
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200
