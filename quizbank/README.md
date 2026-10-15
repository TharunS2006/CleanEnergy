# Online Quiz and Question Bank Management System

REST API (FastAPI) with a plain web page on top. Runs on SQLite on your laptop and on PostgreSQL when deployed (see DEPLOY.md).

## What makes it more than a quiz app

| Feature | What it does |
|---|---|
| Confidence marking | Student says guessing / fairly sure / certain for each answer. A calibration score shows how honest that confidence was, and confidently wrong answers are flagged as misconceptions. |
| Adaptive practice | One question at a time. Difficulty follows the last six answers and the weakest topic is chosen first. |
| Spaced revision | Wrong answers come back after 1, 2, 4, 8 and 16 days until answered correctly each time. |
| Topic mastery map | Strong / learning / weak per topic, with the topics to focus on next. |
| Fair timed quizzes | Timer enforced on the server, shuffled questions and options per student, limited attempts, late attempts kept out of the leaderboard. |
| Item analysis | For teachers: how hard each question really was, whether it separates strong and weak students, and which wrong option attracts most students. |
| CSV import / export | Upload many questions at once, download results. |
| Explanations | Every question can carry a "why" shown after answering. |

## Run it on your laptop

```bash
python -m venv venv
venv\Scripts\activate          # Windows      (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed.py                 # sample users, 24 questions, 2 quizzes, 8 demo students (run once)
uvicorn app.main:app --reload
```

* Web page: http://127.0.0.1:8000
* Swagger API documentation: http://127.0.0.1:8000/docs
* Tests: `pytest`  (13 tests)

## Sample logins (created by seed.py)

| Role | Email | Password |
|---|---|---|
| admin | admin@quiz.com | admin123 |
| teacher | teacher@quiz.com | teacher123 |
| student | student@quiz.com | student123 |

The 8 "Demo Student" accounts (demo1@quiz.com ... demo8@quiz.com, password demo1234) only exist to give the teacher's analysis pages data.
Delete them from the Admin page if you do not want them.

## Folders

* `app/` the API: `routes_*.py` for each part, `db.py` database layer, `learning.py` spaced repetition and calibration
* `public/` the web page (plain HTML, CSS, JavaScript)
* `tests/` automated tests, `seed.py` sample data, `index.py` Vercel entry point
