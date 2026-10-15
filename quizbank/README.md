# Online Quiz and Question Bank Management System

Mini project for the REST API subject. A REST API (FastAPI + SQLite) with a small web page on top of it.

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # Windows      (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed.py                 # sample users and questions, run once
uvicorn app.main:app --reload
```

* Web page: http://127.0.0.1:8000
* API documentation (Swagger): http://127.0.0.1:8000/docs
* Tests: `pytest`

## Sample logins (created by seed.py)

| Role | Email | Password |
|---|---|---|
| admin | admin@quiz.com | admin123 |
| teacher | teacher@quiz.com | teacher123 |
| student | student@quiz.com | student123 |
