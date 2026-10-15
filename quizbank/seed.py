"""Fills the database with sample users, questions (with explanations), two quizzes
and some 'Demo Student' attempts so the teacher's analysis pages have data to show.
Run once:  python seed.py      (it is safe to run again, it does nothing if data exists)
"""
import random

from app.auth import hash_password
from app.db import connect, init_db, now, stamp
from datetime import timedelta

init_db()
db = connect()

if db.scalar("SELECT COUNT(*) FROM users") == 0:
    for name, email, pw, role in [
        ("Admin", "admin@quiz.com", "admin123", "admin"),
        ("Teacher One", "teacher@quiz.com", "teacher123", "teacher"),
        ("Student One", "student@quiz.com", "student123", "student"),
        ("Student Two", "student2@quiz.com", "student123", "student"),
    ]:
        db.execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", (name, email, hash_password(pw), role))
    teacher_id = db.scalar("SELECT id FROM users WHERE email = 'teacher@quiz.com'")

    # subject, topic, level, question, a, b, c, d, answer, explanation
    questions = [
        ("Python", "Basics", "easy", "Which keyword is used to define a function in Python?", "func", "def", "define", "fun", "b",
         "Functions are created with the def keyword followed by the name and parentheses."),
        ("Python", "Basics", "easy", "What is the output of len([1, 2, 3])?", "2", "3", "4", "Error", "b",
         "len() counts the items in the list, and the list has three items."),
        ("Python", "Basics", "easy", "Which of these is an immutable data type?", "list", "dict", "tuple", "set", "c",
         "A tuple cannot be changed after it is created. Lists, dictionaries and sets can be changed."),
        ("Python", "Basics", "medium", "What does the expression 3 // 2 give?", "1.5", "1", "2", "0", "b",
         "// is floor division: it divides and rounds down to the whole number, so 3 // 2 is 1."),
        ("Python", "Loops", "easy", "Which loop is used when the number of repetitions is not known in advance?", "for", "while", "do-while", "repeat", "b",
         "A while loop keeps running as long as its condition is true. Python has no do-while loop."),
        ("Python", "Loops", "medium", "What is printed by: for i in range(3): print(i, end='')?", "123", "012", "0123", "321", "b",
         "range(3) gives 0, 1, 2 (it starts at 0 and stops before 3), and end='' keeps them on one line."),
        ("Python", "Functions", "medium", "What does a function return if it has no return statement?", "0", "False", "None", "Error", "c",
         "Without a return statement Python returns None automatically."),
        ("Python", "Functions", "hard", "What is the output of print(type(lambda x: x))?", "<class 'lambda'>", "<class 'function'>", "<class 'method'>", "<class 'type'>", "b",
         "A lambda is just an anonymous function, so its type is function. There is no separate lambda type."),
        ("Python", "Functions", "hard", "What happens with def f(x, items=[]): items.append(x); return items when f(1) is called twice?", "Returns [1] both times", "Returns [1] then [1, 1]", "Raises an error", "Returns [] both times", "b",
         "The default list is created once when the function is defined, so it is shared between calls. This is a classic Python trap."),
        ("DBMS", "SQL", "easy", "Which SQL command removes all rows but keeps the table structure?", "DROP", "DELETE TABLE", "TRUNCATE", "REMOVE", "c",
         "TRUNCATE empties the table. DROP would remove the table itself."),
        ("DBMS", "SQL", "easy", "Which clause is used to filter rows in a SELECT statement?", "ORDER BY", "WHERE", "GROUP BY", "HAVING", "b",
         "WHERE filters individual rows before grouping. HAVING filters groups after GROUP BY."),
        ("DBMS", "SQL", "medium", "Which join returns only the rows that match in both tables?", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL JOIN", "c",
         "INNER JOIN keeps only matching rows. The outer joins also keep unmatched rows from one or both sides."),
        ("DBMS", "SQL", "hard", "What does SELECT COUNT(col) count when some values of col are NULL?", "All rows", "Only non-NULL values", "Only NULL values", "Distinct values", "b",
         "COUNT(column) ignores NULLs. COUNT(*) counts every row."),
        ("DBMS", "Normalization", "medium", "A table is in 1NF when it has no:", "primary key", "repeating groups", "foreign key", "index", "b",
         "First normal form requires atomic values, so no repeating groups or lists inside a column."),
        ("DBMS", "Normalization", "hard", "Which normal form removes transitive dependency?", "1NF", "2NF", "3NF", "BCNF only", "c",
         "3NF removes dependencies of non-key attributes on other non-key attributes."),
        ("DBMS", "Transactions", "medium", "In ACID, what does the letter A stand for?", "Availability", "Atomicity", "Accuracy", "Authorization", "b",
         "Atomicity means a transaction is all or nothing."),
        ("DBMS", "Transactions", "hard", "Which ACID property makes sure committed data survives a crash?", "Atomicity", "Consistency", "Isolation", "Durability", "d",
         "Durability: once a transaction is committed, it stays committed even after a power failure."),
        ("REST API", "HTTP", "easy", "Which HTTP method is normally used to create a new resource?", "GET", "POST", "DELETE", "HEAD", "b",
         "POST sends data to the server to create a new resource."),
        ("REST API", "HTTP", "easy", "Which status code means a resource was not found?", "200", "401", "404", "500", "c",
         "404 Not Found. 401 means you are not logged in and 500 is a server error."),
        ("REST API", "HTTP", "medium", "Which status code is returned after a resource is created successfully?", "200", "201", "204", "302", "b",
         "201 Created is the correct answer to a successful POST that creates something."),
        ("REST API", "Design", "medium", "In REST, which method is idempotent (repeating it has the same effect as doing it once)?", "POST", "PUT", "PATCH always", "none of them", "b",
         "PUT replaces a resource with the same content every time. POST usually creates a new one on each call."),
        ("REST API", "Design", "hard", "Which header carries a bearer token?", "Content-Type", "Accept", "Authorization", "Cookie", "c",
         "The Authorization header is used as: Authorization: Bearer <token>."),
        ("REST API", "Design", "hard", "Which status code should an API send when a logged-in user is not allowed to do something?", "401", "403", "404", "409", "b",
         "403 Forbidden: the server knows who you are but you do not have permission. 401 means not authenticated."),
        ("REST API", "Security", "medium", "Why should passwords be stored as salted hashes?", "To make login faster", "So stolen data does not reveal passwords", "To save disk space", "Because SQL requires it", "b",
         "A salted hash cannot be turned back into the password, and the salt stops attackers from using ready-made hash tables."),
    ]
    for q in questions:
        db.execute("INSERT INTO questions (subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, explanation, created_by) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (*q, teacher_id))

    def make_quiz(title, subject, minutes):
        qid = db.insert("INSERT INTO quizzes (title, subject, minutes, max_attempts, created_by) VALUES (?, ?, ?, 3, ?)",
                        (title, subject, minutes, teacher_id))
        for r in db.execute("SELECT id FROM questions WHERE subject = ? ORDER BY id", (subject,)).fetchall():
            db.execute("INSERT INTO quiz_questions (quiz_id, question_id) VALUES (?, ?)", (qid, r["id"]))
        return qid

    quiz_rest = make_quiz("REST API Fundamentals", "REST API", 10)
    make_quiz("Python Basics Check", "Python", 10)

    # Demo students with believable results: stronger students answer more questions correctly,
    # hard questions are missed more often, and some students are overconfident.
    rng = random.Random(42)
    ability = [0.95, 0.85, 0.75, 0.7, 0.6, 0.5, 0.4, 0.3]
    qs = db.execute("SELECT q.id, q.answer, q.difficulty FROM questions q JOIN quiz_questions qq ON qq.question_id = q.id WHERE qq.quiz_id = ?", (quiz_rest,)).fetchall()
    chance = {"easy": 0.15, "medium": 0.0, "hard": -0.2}
    for i, a in enumerate(ability, start=1):
        uid = db.insert("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'student')",
                        (f"Demo Student {i}", f"demo{i}@quiz.com", hash_password("demo1234")))
        start = now() - timedelta(days=rng.randint(1, 6), minutes=rng.randint(0, 600))
        aid = db.insert("INSERT INTO attempts (quiz_id, user_id, started_at, deadline, status) VALUES (?, ?, ?, ?, 'done')",
                        (quiz_rest, uid, stamp(start), stamp(start + timedelta(minutes=10))))
        score, marked = 0, []
        for q in qs:
            right = rng.random() < max(0.05, min(0.98, a + chance[q["difficulty"]]))
            chosen = q["answer"] if right else rng.choice([c for c in "abcd" if c != q["answer"]])
            conf = 3 if (i >= 6 and rng.random() < 0.7) else rng.choice([1, 2, 3]) if right else rng.choice([1, 1, 2])
            score += right
            marked.append((int(right), conf))
            db.execute("INSERT INTO answers (attempt_id, question_id, chosen, correct, confidence) VALUES (?, ?, ?, ?, ?)",
                       (aid, q["id"], chosen, int(right), conf))
        from app.learning import calibration_score
        db.execute("UPDATE attempts SET submitted_at = ?, score = ?, total = ?, calibration = ? WHERE id = ?",
                   (stamp(start + timedelta(minutes=rng.randint(4, 9))), score, len(qs), calibration_score(marked), aid))
db.commit()
db.close()
print("Done. Logins: admin@quiz.com / admin123, teacher@quiz.com / teacher123, student@quiz.com / student123")
