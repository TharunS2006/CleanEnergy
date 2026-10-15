"""Database layer.

Locally the app uses a SQLite file. If the environment variable DATABASE_URL is set
(for example a Neon / Vercel Postgres connection string) it uses PostgreSQL instead,
because Vercel has no disk that survives between requests.
All queries are written once with '?' placeholders; this wrapper adapts them.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_PG = bool(DATABASE_URL)
SQLITE_PATH = os.environ.get("QUIZ_DB", os.path.join(os.path.dirname(os.path.dirname(__file__)), "quiz.db"))

if IS_PG:
    import psycopg
    from psycopg.rows import dict_row

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def stamp(dt: datetime) -> str:
    return dt.strftime(TIME_FORMAT)


def parse(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def today_plus(days: int) -> str:
    return (now() + timedelta(days=days)).strftime("%Y-%m-%d")


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id {PK},
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student'))
);
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    id {PK},
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    text TEXT NOT NULL,
    opt_a TEXT NOT NULL,
    opt_b TEXT NOT NULL,
    opt_c TEXT NOT NULL,
    opt_d TEXT NOT NULL,
    answer TEXT NOT NULL CHECK (answer IN ('a', 'b', 'c', 'd')),
    explanation TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS quizzes (
    id {PK},
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    minutes INTEGER NOT NULL,
    max_attempts INTEGER NOT NULL DEFAULT 2,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS quiz_questions (
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    PRIMARY KEY (quiz_id, question_id)
);
CREATE TABLE IF NOT EXISTS attempts (
    id {PK},
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    deadline TEXT NOT NULL,
    submitted_at TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    score INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    late INTEGER NOT NULL DEFAULT 0,
    calibration INTEGER
);
CREATE TABLE IF NOT EXISTS answers (
    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL,
    chosen TEXT,
    correct INTEGER NOT NULL,
    confidence INTEGER
);
CREATE TABLE IF NOT EXISTS practice_log (
    id {PK},
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    chosen TEXT,
    correct INTEGER NOT NULL,
    confidence INTEGER,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revision (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    box INTEGER NOT NULL,
    due TEXT NOT NULL,
    PRIMARY KEY (user_id, question_id)
);
"""


class DB:
    """Thin wrapper so the route code does not care which database is underneath."""

    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, args=()):
        if IS_PG:
            cur = self.conn.cursor()
            cur.execute(sql.replace("?", "%s"), tuple(args))
            return cur
        return self.conn.execute(sql, tuple(args))

    def insert(self, sql, args=()):
        """Runs an INSERT and returns the new row id."""
        cur = self.execute(sql + " RETURNING id", args)
        return cur.fetchone()["id"]

    def scalar(self, sql, args=()):
        row = self.execute(sql, args).fetchone()
        return next(iter(row.values())) if IS_PG else row[0]

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def connect() -> DB:
    if IS_PG:
        return DB(psycopg.connect(DATABASE_URL, row_factory=dict_row))
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return DB(conn)


def get_db():
    """FastAPI dependency: one connection per request, committed only if nothing failed."""
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    db = connect()
    pk = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    for statement in SCHEMA.replace("{PK}", pk).split(";"):
        if statement.strip():
            db.execute(statement)
    db.commit()
    db.close()
