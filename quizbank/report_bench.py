"""Experiments and real request/response examples for the report. Uses throw-away databases, never the demo one."""
import json, os, random, statistics as st, subprocess, sys, tempfile, time

tmp = tempfile.mkdtemp()
os.environ["QUIZ_DB"] = os.path.join(tmp, "bench.db")
from fastapi.testclient import TestClient
from app.main import app
from app.db import connect, now, parse, stamp
from app.learning import calibration_score, INTERVALS, update_revision, CONFIDENCE_CLAIM
from app.auth import hash_password

c = TestClient(app)
out = {}
ctr = [0]


def person(role):
    ctr[0] += 1
    email = f"{role}{ctr[0]}@bench.com"
    c.post("/api/register", json={"name": f"{role.title()} {ctr[0]}", "email": email, "password": "secret1", "role": role})
    t = c.post("/api/login", json={"email": email, "password": "secret1"}).json()["token"]
    return {"Authorization": "Bearer " + t}


def q(text, subject="REST API", topic="HTTP", difficulty="easy", answer="b"):
    return {"subject": subject, "topic": topic, "difficulty": difficulty, "text": text, "opt_a": "HEAD", "opt_b": "POST", "opt_c": "GET", "opt_d": "DELETE",
            "answer": answer, "explanation": "POST creates a new resource."}


# ---------------------------------------------------------------- A. real request / response examples
ex = []
def rec(label, method, path, resp, body=None, headers=None, show=None):
    data = resp.json() if resp.content and resp.headers.get("content-type", "").startswith("application/json") else None
    ex.append({"label": label, "method": method, "path": path, "status": resp.status_code, "request": body, "response": show(data) if (show and data is not None) else data})
    return data

r = c.post("/api/register", json={"name": "Asha", "email": "asha@example.com", "password": "secret1", "role": "student"}); rec("Register a student", "POST", "/api/register", r, {"name": "Asha", "email": "asha@example.com", "password": "secret1", "role": "student"})
r = c.post("/api/register", json={"name": "Asha", "email": "asha@example.com", "password": "secret1"}); rec("Register the same e-mail again", "POST", "/api/register", r, {"email": "asha@example.com"})
r = c.post("/api/register", json={"name": "Evil", "email": "evil@example.com", "password": "secret1", "role": "admin"}); rec("Try to register as admin", "POST", "/api/register", r, {"role": "admin"}, show=lambda d: {"detail": d["detail"][0]["msg"]})
r = c.post("/api/login", json={"email": "asha@example.com", "password": "wrong"}); rec("Login with a wrong password", "POST", "/api/login", r, {"email": "asha@example.com", "password": "wrong"})
r = c.post("/api/login", json={"email": "asha@example.com", "password": "secret1"}); d = rec("Login", "POST", "/api/login", r, {"email": "asha@example.com", "password": "secret1"}, show=lambda d: {"token": d["token"][:12] + "...", "name": d["name"], "role": d["role"]})
student = {"Authorization": "Bearer " + d["token"]}
teacher = person("teacher")
r = c.get("/api/me"); rec("Call a protected route without a token", "GET", "/api/me", r)
r = c.post("/api/questions", json=q("Which HTTP method creates a resource?"), headers=student); rec("A student tries to add a question", "POST", "/api/questions", r, {"...": "question"})
r = c.post("/api/questions", json=q("Which HTTP method creates a resource?"), headers=teacher); d = rec("A teacher adds a question", "POST", "/api/questions", r, {"subject": "REST API", "topic": "HTTP", "difficulty": "easy", "text": "Which HTTP method creates a resource?", "answer": "b", "...": "options, explanation"})
qid = d["id"]
r = c.post("/api/questions", json={**q("Short"), "difficulty": "extreme", "answer": "z"}, headers=teacher); rec("Add a question with wrong values", "POST", "/api/questions", r, {"difficulty": "extreme", "answer": "z"}, show=lambda d: {"errors": [x["msg"] for x in d["detail"]]})
for i in range(7):
    c.post("/api/questions", json=q(f"REST question number {i} about methods?", topic="HTTP", difficulty=["easy", "medium", "hard"][i % 3]), headers=teacher)
r = c.get("/api/questions", params={"subject": "REST API", "difficulty": "easy"}, headers=teacher); rec("List questions with filters", "GET", "/api/questions?subject=REST API&difficulty=easy", r, show=lambda d: {"total": d["total"], "page": d["page"], "items": f"{len(d['items'])} questions"})
r = c.post("/api/quizzes/random", json={"title": "Methods quiz", "subject": "REST API", "minutes": 5, "count": 40}, headers=teacher); rec("Ask for more questions than exist", "POST", "/api/quizzes/random", r, {"count": 40})
r = c.post("/api/quizzes/random", json={"title": "Methods quiz", "subject": "REST API", "minutes": 5, "count": 4, "max_attempts": 2}, headers=teacher); d = rec("Create a random quiz", "POST", "/api/quizzes/random", r, {"title": "Methods quiz", "subject": "REST API", "minutes": 5, "count": 4, "max_attempts": 2})
quiz = d["id"]
r = c.post(f"/api/quizzes/{quiz}/start", headers=student); d = rec("Start an attempt", "POST", f"/api/quizzes/{quiz}/start", r, show=lambda d: {"attempt_id": d["attempt_id"], "seconds_left": d["seconds_left"], "questions": [{"id": x["id"], "options": [o["key"] for o in x["options"]]} for x in d["questions"][:2]] + ["..."]})
paper = c.post(f"/api/quizzes/{quiz}/start", headers=student).json()          # same attempt resumed: same paper
ans = {}
for i, qq in enumerate(paper["questions"]):
    ans[str(qq["id"])] = {"choice": "b" if i != 1 else "a", "confidence": 3 if i in (1, 2) else 2}
r = c.post(f"/api/attempts/{paper['attempt_id']}/submit", json={"answers": ans}, headers=student)
d = rec("Submit the answers with confidence levels", "POST", f"/api/attempts/{paper['attempt_id']}/submit", r, {"answers": {"<question id>": {"choice": "b", "confidence": 3}, "...": "..."}},
        show=lambda d: {"score": d["score"], "total": d["total"], "percent": d["percent"], "late": d["late"], "calibration": d["calibration"], "review": [{"correct": x["correct"], "misconception": x["misconception"]} for x in d["review"]]})
r = c.post(f"/api/attempts/{paper['attempt_id']}/submit", json={"answers": ans}, headers=student); rec("Submit the same attempt twice", "POST", f"/api/attempts/{paper['attempt_id']}/submit", r)
r = c.get("/api/revision/due", headers=student); rec("Questions waiting for revision", "GET", "/api/revision/due", r, show=lambda d: {"due": d["due"], "in_queue": d["in_queue"]})
r = c.get(f"/api/quizzes/{quiz}/results", headers=teacher); rec("Teacher: results of a quiz", "GET", f"/api/quizzes/{quiz}/results", r, show=lambda d: {"quiz": d["quiz"], "attempts": len(d["attempts"]), "average_percent": d["average_percent"]})
r = c.get("/api/users", headers=teacher); rec("A teacher asks for the user list", "GET", "/api/users", r)
r = c.get("/api/quizzes/9999/results", headers=teacher); rec("Results of a quiz that does not exist", "GET", "/api/quizzes/9999/results", r)
out["examples"] = ex
out["status_codes"] = sorted({(e["status"]) for e in ex})

# ---------------------------------------------------------------- B. calibration experiment
rng = random.Random(11)
def attempt(profile, n=10):
    marks = []
    for _ in range(n):
        p = rng.uniform(0.2, 1.0)                       # how likely this student is to be right on this question
        ok = 1 if rng.random() < p else 0
        if profile == "calibrated": conf = 3 if p >= 0.85 else 2 if p >= 0.5 else 1
        elif profile == "overconfident": conf = 3
        elif profile == "underconfident": conf = 1
        else: conf = rng.randint(1, 3)
        marks.append((ok, conf))
    return calibration_score(marks), sum(m[0] for m in marks) / n
cal = {}
for prof in ("calibrated", "overconfident", "underconfident", "random"):
    rows = [attempt(prof) for _ in range(3000)]
    cal[prof] = {"calibration_mean": st.mean(r[0] for r in rows), "calibration_sd": st.pstdev(r[0] for r in rows), "accuracy_mean": 100 * st.mean(r[1] for r in rows)}
out["calibration"] = cal
out["calibration_claims"] = CONFIDENCE_CLAIM
worked = [(1, 3), (1, 3), (0, 3), (1, 2)]
out["calibration_worked"] = {"marks": worked, "score": calibration_score(worked)}

# ---------------------------------------------------------------- C. Leitner simulation with the real update_revision
db = connect()
uid = db.insert("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", ("Sim", "sim@bench.com", hash_password("secret1"), "student"))
qrow = db.insert("INSERT INTO questions (subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, explanation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("Sim", "T", "easy", "Simulation question?", "a", "b", "c", "d", "b", ""))
db.commit()
def learn(p, rng):
    """A learner who recalls the answer with probability p at every review. Returns (days until the question leaves the queue, reviews)."""
    update_revision(db, uid, qrow, False)                   # first wrong answer puts it in box 1
    day, reviews = 0, 0
    while True:
        row = db.execute("SELECT box, due FROM revision WHERE user_id = ? AND question_id = ?", (uid, qrow)).fetchone()
        if row is None: return day, reviews
        gap = (parse(row["due"] + " 00:00:00") - parse(stamp(now())[:10] + " 00:00:00")).days
        day += gap; reviews += 1
        update_revision(db, uid, qrow, rng.random() < p)
        if reviews > 400: return day, reviews
rng = random.Random(3)
leit = {}
for p in (0.5, 0.7, 0.9, 0.97):
    runs = [learn(p, rng) for _ in range(400)]
    leit[str(p)] = {"days_mean": st.mean(r[0] for r in runs), "days_median": st.median(r[0] for r in runs), "reviews_mean": st.mean(r[1] for r in runs), "reviews_max": max(r[1] for r in runs)}
out["leitner"] = leit
out["leitner_intervals"] = INTERVALS
cum, tot = [], 0
for i in INTERVALS: tot += i; cum.append(tot)
out["leitner_cumulative_days"] = cum
db.execute("DELETE FROM revision"); db.commit(); db.close()

# ---------------------------------------------------------------- D. adaptive practice through the API
t = person("teacher")
for lvl in ("easy", "medium", "hard"):
    for i in range(30):
        c.post("/api/questions", json=q(f"Adaptive {lvl} question {i}?", subject="Adapt", topic="T", difficulty=lvl), headers=t)
LV = {"easy": 1, "medium": 2, "hard": 3}
profiles = {"weak": (0.80, 0.45, 0.15), "average": (0.92, 0.70, 0.40), "strong": (0.98, 0.90, 0.75)}
ad = {}
for name, probs in profiles.items():
    served = {1: 0, 2: 0, 3: 0}; late = {1: 0, 2: 0, 3: 0}
    for rep in range(12):
        s = person("student")
        for step in range(30):
            nq = c.get("/api/practice/next", params={"subject": "Adapt"}, headers=s).json()
            lvl = LV[c.get(f"/api/questions/{nq['id']}", headers=t).json()["difficulty"]]
            ok = rng.random() < probs[lvl - 1]
            c.post("/api/practice/answer", json={"question_id": nq["id"], "choice": "b" if ok else "a", "confidence": 2}, headers=s)
            served[lvl] += 1
            if step >= 10: late[lvl] += 1
    tot = sum(served.values()); tl = sum(late.values())
    ad[name] = {"probabilities": probs, "share_all": {k: 100 * v / tot for k, v in served.items()}, "share_late": {k: 100 * v / tl for k, v in late.items()}}
out["adaptive"] = ad

# ---------------------------------------------------------------- E. latency
def timeit(fn, n=60):
    xs = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); xs.append((time.perf_counter() - t0) * 1000)
    return {"median_ms": st.median(xs), "p95_ms": sorted(xs)[int(0.95 * n) - 1]}
lat = {}
lat["POST /api/login"] = timeit(lambda: c.post("/api/login", json={"email": "asha@example.com", "password": "secret1"}), 30)
lat["GET /api/questions"] = timeit(lambda: c.get("/api/questions", headers=teacher))
lat["GET /api/quizzes"] = timeit(lambda: c.get("/api/quizzes", headers=student))
prs = person("student")
lat["GET /api/practice/next"] = timeit(lambda: c.get("/api/practice/next", params={"subject": "Adapt"}, headers=prs), 40)
q_ids = [c.post("/api/questions", json=q(f"Latency question {i}?", subject="Lat"), headers=teacher).json()["id"] for i in range(20)]
lq = c.post("/api/quizzes", json={"title": "Latency quiz", "subject": "Lat", "minutes": 10, "max_attempts": 10, "question_ids": q_ids}, headers=teacher).json()["id"]
ss = person("student")
def one_attempt():
    p = c.post(f"/api/quizzes/{lq}/start", headers=ss).json()
    c.post(f"/api/attempts/{p['attempt_id']}/submit", json={"answers": {str(x['id']): {"choice": "b", "confidence": 2} for x in p["questions"]}}, headers=ss)
lat["start + submit a 20-question quiz"] = timeit(one_attempt, 8)
lat["GET /api/quizzes/{id}/analysis"] = timeit(lambda: c.get(f"/api/quizzes/{lq}/analysis", headers=teacher), 20)
out["latency"] = lat

# ---------------------------------------------------------------- F. item analysis of the seeded demo quiz (fresh database)
demo = os.path.join(tmp, "demo.db")
env = dict(os.environ, QUIZ_DB=demo)
subprocess.run([sys.executable, "seed.py"], env=env, check=True, capture_output=True)
code = ("import os;os.environ['QUIZ_DB']=%r\nfrom fastapi.testclient import TestClient\nfrom app.main import app\nimport json\nc=TestClient(app)\n"
        "t=c.post('/api/login',json={'email':'teacher@quiz.com','password':'teacher123'}).json()['token']\nh={'Authorization':'Bearer '+t}\n"
        "qs=c.get('/api/quizzes',headers=h).json()\nq=[x for x in qs if x['title']=='REST API Fundamentals'][0]['id']\n"
        "print(json.dumps({'analysis':c.get(f'/api/quizzes/{q}/analysis',headers=h).json(),'results':c.get(f'/api/quizzes/{q}/results',headers=h).json(),'stats':c.get('/api/stats',headers=h).json()}))") % demo
res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
out["demo"] = json.loads(res.stdout.strip().splitlines()[-1])
from app.main import app as _a
spec = _a.openapi()
out["openapi"] = {"paths": len(spec["paths"]), "operations": sum(len(v) for v in spec["paths"].values()),
                  "by_tag": {}, "list": [{"methods": [m.upper() for m in v], "path": p, "tag": list(v.values())[0].get("tags", [""])[0], "summary": list(v.values())[0].get("summary", "")} for p, v in spec["paths"].items()]}
for e in out["openapi"]["list"]:
    out["openapi"]["by_tag"][e["tag"]] = out["openapi"]["by_tag"].get(e["tag"], 0) + len(e["methods"])
json.dump(out, open("report_results.json", "w"), indent=1, default=str)
print(json.dumps({k: out[k] for k in ("calibration", "calibration_worked", "leitner", "leitner_cumulative_days", "adaptive", "latency", "status_codes")}, indent=1, default=str)[:6000])
print(out["openapi"]["by_tag"], out["openapi"]["operations"])
