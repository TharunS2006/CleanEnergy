import os
import tempfile

# use a throw-away database for the tests (must be set before the app is imported)
os.environ["QUIZ_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def register_and_login(name, email, role):
    client.post("/api/register", json={"name": name, "email": email, "password": "secret1", "role": role})
    r = client.post("/api/login", json={"email": email, "password": "secret1"})
    return {"Authorization": "Bearer " + r.json()["token"]}


QUESTION = {"subject": "Python", "topic": "Basics", "difficulty": "easy", "text": "What is 2 + 2 in Python?",
            "opt_a": "3", "opt_b": "4", "opt_c": "5", "opt_d": "22", "answer": "b"}


def test_register_login_and_me():
    r = client.post("/api/register", json={"name": "Asha", "email": "asha@x.com", "password": "secret1"})
    assert r.status_code == 201 and r.json()["role"] == "student"
    assert client.post("/api/register", json={"name": "Asha", "email": "asha@x.com", "password": "secret1"}).status_code == 409
    assert client.post("/api/login", json={"email": "asha@x.com", "password": "wrong"}).status_code == 401
    h = register_and_login("Ravi", "ravi@x.com", "teacher")
    assert client.get("/api/me", headers=h).json()["role"] == "teacher"
    assert client.get("/api/me").status_code == 401


def test_cannot_register_as_admin():
    r = client.post("/api/register", json={"name": "Evil", "email": "e@x.com", "password": "secret1", "role": "admin"})
    assert r.status_code == 422


def test_question_crud_and_permissions():
    teacher = register_and_login("Teacher", "t1@x.com", "teacher")
    student = register_and_login("Student", "s1@x.com", "student")
    assert client.post("/api/questions", json=QUESTION, headers=student).status_code == 403
    r = client.post("/api/questions", json=QUESTION, headers=teacher)
    assert r.status_code == 201
    qid = r.json()["id"]
    assert client.get(f"/api/questions/{qid}", headers=teacher).json()["answer"] == "b"
    changed = dict(QUESTION, difficulty="hard")
    assert client.put(f"/api/questions/{qid}", json=changed, headers=teacher).json()["difficulty"] == "hard"
    assert client.delete(f"/api/questions/{qid}", headers=teacher).status_code == 204
    assert client.get(f"/api/questions/{qid}", headers=teacher).status_code == 404


def test_question_validation():
    teacher = register_and_login("Teacher", "t2@x.com", "teacher")
    bad = dict(QUESTION, answer="z")
    assert client.post("/api/questions", json=bad, headers=teacher).status_code == 422
    bad = dict(QUESTION, difficulty="impossible")
    assert client.post("/api/questions", json=bad, headers=teacher).status_code == 422


def test_search_filter_and_pagination():
    teacher = register_and_login("Teacher", "t3@x.com", "teacher")
    for i in range(12):
        client.post("/api/questions", json=dict(QUESTION, subject="Maths", text=f"Maths question number {i}"), headers=teacher)
    r = client.get("/api/questions?subject=Maths&size=5&page=2", headers=teacher).json()
    assert r["total"] == 12 and len(r["items"]) == 5 and r["page"] == 2
    r = client.get("/api/questions?subject=Maths&search=number 11", headers=teacher).json()
    assert r["total"] == 1


def test_full_quiz_flow():
    teacher = register_and_login("Teacher", "t4@x.com", "teacher")
    student = register_and_login("Student", "s4@x.com", "student")
    ids = [client.post("/api/questions", json=dict(QUESTION, subject="Flow", text=f"Flow question {i}"), headers=teacher).json()["id"]
           for i in range(3)]
    quiz = client.post("/api/quizzes", json={"title": "Flow quiz", "subject": "Flow", "minutes": 10, "question_ids": ids}, headers=teacher)
    assert quiz.status_code == 201
    qid = quiz.json()["id"]
    # a student sees the questions but not the answers
    view = client.get(f"/api/quizzes/{qid}", headers=student).json()
    assert len(view["questions"]) == 3 and "answer" not in view["questions"][0]
    assert "answer" in client.get(f"/api/quizzes/{qid}", headers=teacher).json()["questions"][0]
    # two right, one wrong
    answers = {str(ids[0]): "b", str(ids[1]): "b", str(ids[2]): "a"}
    res = client.post(f"/api/quizzes/{qid}/attempt", json={"answers": answers}, headers=student)
    assert res.status_code == 201 and res.json()["score"] == 2 and res.json()["total"] == 3
    assert client.post(f"/api/quizzes/{qid}/attempt", json={"answers": {}}, headers=teacher).status_code == 403
    mine = client.get("/api/attempts/mine", headers=student).json()
    assert mine[0]["score"] == 2
    results = client.get(f"/api/quizzes/{qid}/results", headers=teacher).json()
    assert len(results["attempts"]) == 1 and results["average_percent"] == 66.7
    assert results["hardest_questions"][0]["id"] == ids[2]


def test_random_quiz():
    teacher = register_and_login("Teacher", "t5@x.com", "teacher")
    for i in range(4):
        client.post("/api/questions", json=dict(QUESTION, subject="Rand", text=f"Random question {i}"), headers=teacher)
    ok = client.post("/api/quizzes/random", json={"title": "Random", "subject": "Rand", "minutes": 5, "count": 3}, headers=teacher)
    assert ok.status_code == 201 and ok.json()["questions"] == 3
    too_many = client.post("/api/quizzes/random", json={"title": "Random", "subject": "Rand", "minutes": 5, "count": 9}, headers=teacher)
    assert too_many.status_code == 400


def test_used_question_cannot_be_deleted():
    teacher = register_and_login("Teacher", "t6@x.com", "teacher")
    qid = client.post("/api/questions", json=QUESTION, headers=teacher).json()["id"]
    client.post("/api/quizzes", json={"title": "Keep it", "subject": "Python", "minutes": 5, "question_ids": [qid]}, headers=teacher)
    assert client.delete(f"/api/questions/{qid}", headers=teacher).status_code == 409


def test_admin_only_user_list():
    teacher = register_and_login("Teacher", "t7@x.com", "teacher")
    assert client.get("/api/users", headers=teacher).status_code == 403
