import os
import sqlite3

# the database file sits next to the project unless QUIZ_DB says otherwise (the tests use this)
DB_PATH = os.environ.get("QUIZ_DB", os.path.join(os.path.dirname(os.path.dirname(__file__)), "quiz.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student'))
);
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    text TEXT NOT NULL,
    opt_a TEXT NOT NULL,
    opt_b TEXT NOT NULL,
    opt_c TEXT NOT NULL,
    opt_d TEXT NOT NULL,
    answer TEXT NOT NULL CHECK (answer IN ('a', 'b', 'c', 'd')),
    created_by INTEGER REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    minutes INTEGER NOT NULL,
    created_by INTEGER REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS quiz_questions (
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    PRIMARY KEY (quiz_id, question_id)
);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    score INTEGER NOT NULL,
    total INTEGER NOT NULL,
    taken_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS answers (
    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL,
    chosen TEXT,
    correct INTEGER NOT NULL
);
"""


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
