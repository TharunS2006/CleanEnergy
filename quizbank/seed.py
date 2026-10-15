"""Fills the database with a few users and questions so the demo is not empty.
Run once:  python seed.py
"""
import sqlite3

from app.auth import hash_password
from app.db import DB_PATH, init_db

init_db()
db = sqlite3.connect(DB_PATH)

users = [
    ("Admin", "admin@quiz.com", "admin123", "admin"),
    ("Teacher One", "teacher@quiz.com", "teacher123", "teacher"),
    ("Student One", "student@quiz.com", "student123", "student"),
    ("Student Two", "student2@quiz.com", "student123", "student"),
]
for name, email, pw, role in users:
    db.execute("INSERT OR IGNORE INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
               (name, email, hash_password(pw), role))

# subject, topic, difficulty, question, a, b, c, d, answer
questions = [
    ("Python", "Basics", "easy", "Which keyword is used to define a function in Python?", "func", "def", "define", "fun", "b"),
    ("Python", "Basics", "easy", "What is the output of len([1, 2, 3])?", "2", "3", "4", "Error", "b"),
    ("Python", "Basics", "easy", "Which of these is an immutable data type?", "list", "dict", "tuple", "set", "c"),
    ("Python", "Basics", "medium", "What does the expression 3 // 2 give?", "1.5", "1", "2", "0", "b"),
    ("Python", "Loops", "easy", "Which loop is used when the number of repetitions is not known in advance?", "for", "while", "do-while", "repeat", "b"),
    ("Python", "Loops", "medium", "What is printed by: for i in range(3): print(i, end='')?", "123", "012", "0123", "321", "b"),
    ("Python", "Functions", "medium", "What does a function return if it has no return statement?", "0", "False", "None", "Error", "c"),
    ("Python", "Functions", "hard", "What is the output of print(type(lambda x: x))?", "<class 'lambda'>", "<class 'function'>", "<class 'method'>", "<class 'type'>", "b"),
    ("DBMS", "SQL", "easy", "Which SQL command is used to remove all rows but keep the table structure?", "DROP", "DELETE TABLE", "TRUNCATE", "REMOVE", "c"),
    ("DBMS", "SQL", "easy", "Which clause is used to filter rows in a SELECT statement?", "ORDER BY", "WHERE", "GROUP BY", "HAVING", "b"),
    ("DBMS", "SQL", "medium", "Which join returns only the rows that match in both tables?", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL JOIN", "c"),
    ("DBMS", "Normalization", "medium", "A table is in 1NF when it has no:", "primary key", "repeating groups", "foreign key", "index", "b"),
    ("DBMS", "Normalization", "hard", "Which normal form removes transitive dependency?", "1NF", "2NF", "3NF", "BCNF only", "c"),
    ("REST API", "HTTP", "easy", "Which HTTP method is normally used to create a new resource?", "GET", "POST", "DELETE", "HEAD", "b"),
    ("REST API", "HTTP", "easy", "Which status code means a resource was not found?", "200", "401", "404", "500", "c"),
    ("REST API", "HTTP", "medium", "Which status code is returned after a resource is created successfully?", "200", "201", "204", "302", "b"),
    ("REST API", "Design", "medium", "In REST, which method is idempotent?", "POST", "PUT", "PATCH always", "none of them", "b"),
    ("REST API", "Design", "hard", "Which header carries a bearer token?", "Content-Type", "Accept", "Authorization", "Cookie", "c"),
]
have = db.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
if have == 0:
    for q in questions:
        db.execute("INSERT INTO questions (subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, created_by) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 2)", q)
db.commit()
print("Done. Logins: admin@quiz.com / admin123, teacher@quiz.com / teacher123, student@quiz.com / student123")
