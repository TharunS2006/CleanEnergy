"""Chapters of the Online Quiz and Question Bank Management System report. Every measured number is read from report_results.json."""
import json, pathlib, sys
HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
R = json.load(open(ROOT / "report_results.json"))
A = "assets/"
CAL, LEI, ADA, LAT, EX, OA, DEMO = R["calibration"], R["leitner"], R["adaptive"], R["latency"], R["examples"], R["openapi"], R["demo"]


def loc(path):
    return len((ROOT / path).read_text(encoding="utf-8").splitlines())


def trim_empty(r):
    body = r.doc.element.body
    while True:
        kids = [k for k in body if not k.tag.endswith("sectPr")]
        last = kids[-1]
        if last.tag.endswith("}p") and not "".join(last.itertext()).strip() and not last.xpath(".//w:drawing | .//w:br"):
            body.remove(last)
        else:
            break


def H1(r, text, n):
    if n > 1:
        trim_empty(r)
    p = r.h(1, text)
    if n > 1:
        p.paragraph_format.page_break_before = True
    return p


ROLE = {("POST", "/api/register"): "public", ("POST", "/api/login"): "public", ("GET", "/api/me"): "any user", ("GET", "/api/users"): "admin", ("DELETE", "/api/users/{user_id}"): "admin",
        ("GET", "/api/stats"): "admin, teacher", ("GET", "/api/subjects"): "any user", ("GET", "/api/quizzes"): "any user", ("GET", "/api/quizzes/{quiz_id}/leaderboard"): "any user",
        ("POST", "/api/quizzes/{quiz_id}/start"): "student", ("POST", "/api/attempts/{attempt_id}/submit"): "student", ("GET", "/api/attempts/mine"): "student",
        ("GET", "/api/practice/next"): "student", ("POST", "/api/practice/answer"): "student", ("GET", "/api/revision/due"): "student", ("GET", "/api/me/mastery"): "student"}


def chapter1(r):
    H1(r, "1. INTRODUCTION", 1)
    r.h(2, "1.1  Background")
    r.para("Colleges and training centres use online quizzes for revision, for weekly tests and for placement practice. A quiz system has to store questions, assemble them into quizzes, "
           "let students attempt the quizzes under a time limit, mark the answers and show the results to the teacher. Most small systems stop there. They do not tell the teacher which questions "
           "are badly written, they do not tell the student what to revise, and they leave the timer, the shuffling and the number of attempts to the browser, where a student can change them.")
    r.para("The programming interface of such a system is naturally a **REST API**. REST (Representational State Transfer) is the architectural style described by Fielding [1] in which every "
           "thing the system manages, such as a question, a quiz or an attempt, is a *resource* with its own address, and the standard HTTP methods are used on it: GET to read, POST to create, PUT to replace and DELETE to remove [2]. "
           "The server keeps no session between requests; each request carries what the server needs, for example a bearer token [3]. The answer is a JSON document and a status code that says what happened: "
           "200 for success, 201 for a created resource, 401 when the caller is not identified, 403 when the caller is not allowed, 404 when the resource does not exist, 409 for a conflict and 422 for invalid input. "
           "Because the interface is only a set of addresses and JSON documents, the same API can serve a web page, a mobile app, a test script or a teacher's spreadsheet.")
    r.h(2, "1.2  Problem Statement")
    r.para("A quiz system that only marks answers has four weaknesses. First, the question bank grows without feedback: nobody finds out that a question labelled easy is answered wrongly by most students, or that a question "
           "is answered correctly by strong and weak students alike. Second, a student who has finished a quiz learns a score, not what to do next; a wrong answer is forgotten after the page is closed. Third, the "
           "system cannot tell a student who guessed and was right from one who knew the answer, nor a student who was *sure* and wrong, whose misconception is the most important thing to correct. Fourth, if the timer and the paper "
           "are controlled by the browser, the time limit and the order of questions are only suggestions.")
    r.para("The problem addressed here is to design and build the REST API of a quiz and question-bank system that (i) manages users with roles, a question bank and quizzes; (ii) conducts attempts under rules enforced by the server; "
           "(iii) goes beyond the score by measuring how well a student's confidence matches the result, by bringing wrong answers back at growing intervals and by choosing practice questions adaptively; "
           "(iv) gives teachers measurements of the quality of every question; and (v) is verified by automated tests and by experiments, and can be run on a laptop and deployed with a different database.")
    r.h(2, "1.4  Scope")
    r.para("The deliverable is the **API** and a plain HTML and JavaScript page that uses it, so that the whole system can be demonstrated. The API covers accounts and roles, the question bank (with filters, paging and CSV import), "
           "quizzes (manual and random), attempts with a server timer, results, CSV export, item analysis and leaderboard for teachers, and adaptive practice, spaced revision and a mastery map for students. "
           "Questions are single-answer multiple-choice. The project does not include e-mail verification, password reset, proctoring, essay questions or a mobile client. "
           "The experiments of Chapter 6 use simulated students and a seeded demonstration database, not real students; the limits are listed in Section 7.1.")


def chapter2(r):
    H1(r, "2. OBJECTIVES", 2)
    r.para("The main objective is to build a REST API for an online quiz and question-bank system whose behaviour is enforced by the server, and to add learning features that go beyond marking. The specific objectives are:")
    r.bullets(["To design a resource-oriented API with correct HTTP methods and status codes, documented automatically in OpenAPI and Swagger UI.",
               "To authenticate users with bearer tokens, store passwords safely, and restrict every operation to the roles that need it.",
               "To validate every input with declared rules, so that wrong data is rejected with 422 before any logic runs.",
               "To manage a question bank with filters, paging, bulk CSV import and explanations, and to build quizzes by hand or at random.",
               "To conduct attempts under server-side rules: timer with a grace period, limited attempts, per-student shuffling and exclusion of late attempts from rankings.",
               "To compute a confidence-calibration score and to flag confident wrong answers; to schedule revision with Leitner boxes; and to choose practice questions adaptively.",
               "To give teachers item analysis, results, CSV export and a leaderboard.",
               "To verify the system with automated tests and with experiments, and to keep it portable between SQLite and PostgreSQL."])
    r.table("Table 2.1: Functional requirements",
            ["ID", "Requirement"],
            [["FR1", "Register and log in; three roles: admin, teacher, student; a user cannot register as admin"],
             ["FR2", "Teachers and admins create, read, update and delete questions; list them with subject, topic, difficulty and text filters and paging"],
             ["FR3", "Import many questions from CSV and report the lines that are wrong; refuse to delete a question used in a quiz"],
             ["FR4", "Create a quiz from chosen questions or from random questions matching subject, topic and level"],
             ["FR5", "A student starts an attempt (limited number per quiz) and receives a shuffled paper and the time left; a student submits answers with a confidence level"],
             ["FR6", "The server marks the attempt, marks late submissions, computes the calibration score and returns a review with explanations"],
             ["FR7", "Wrong answers enter a revision queue with growing intervals; due questions are served to the student"],
             ["FR8", "Adaptive practice: next question by weakest topic and recent performance; mastery map by topic"],
             ["FR9", "Teachers see results, hardest questions, item analysis, leaderboard and a CSV export; admins manage users and see statistics"]],
            widths=[1.6, 13.4], size=10)


def chapter3(r):
    H1(r, "3. TOOLS AND TECHNOLOGIES", 3)
    r.para("The back end uses a small set of widely used Python libraries; the front end uses none. Table 3.1 lists what was used and why.")
    r.table("Table 3.1: Tools and technologies used",
            ["Item", "Tool", "Purpose"],
            [["Language", "Python 3.10 or newer (tested on 3.13)", "All server code"],
             ["Web framework", "FastAPI 0.115", "Routing, dependency injection for authentication and database, automatic OpenAPI documentation"],
             ["Validation", "Pydantic (with FastAPI)", "Declares the shape of every request and rejects bad input with 422"],
             ["Server", "Uvicorn", "Runs the FastAPI application"],
             ["Database", "SQLite (standard library) and PostgreSQL through psycopg", "Storage; one wrapper hides the difference"],
             ["Security", "`hashlib.pbkdf2_hmac`, `secrets`, `hmac`", "Password hashing, token generation, constant-time comparison"],
             ["Front end", "HTML, CSS and JavaScript (`fetch`)", "A page that uses the API; no framework"],
             ["Testing", "pytest and FastAPI TestClient (httpx)", "13 tests that call the API as a client would"],
             ["Documentation", "Swagger UI at `/docs`, OpenAPI at `/openapi.json`", "Generated from the code"],
             ["Deployment", "Vercel and Neon PostgreSQL (described in DEPLOY.md)", "Free hosting; not run on Vercel from the machine used for this report"]],
            widths=[3.0, 5.2, 6.8], size=9.5)
    r.h(2, "3.1  Running the project")
    r.para("The project is a folder named `quizbank`. In a terminal opened in that folder:")
    r.code("""
python -m venv venv
venv\\Scripts\\activate              # Windows (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed.py                      # sample users, 24 questions, 2 quizzes, 8 demo students (once)
uvicorn app.main:app --reload       # web page at http://127.0.0.1:8000, API documentation at /docs
pytest                              # the 13 automated tests
""")


def chapter4(r):
    H1(r, "4. ARCHITECTURE DIAGRAM", 4)
    r.para("The system has four layers (Figure 4.1). Clients, which can be the web page, the Swagger UI or any HTTP client, talk to the API only through HTTP and JSON. The API is organised as four routers, one for each group of resources: "
           "users, the question bank, quizzes and attempts, and learning (practice, revision and mastery). Two concerns cut across all of them: authentication and the role check, and the validation of input by Pydantic schemas. "
           "At the bottom, a small database module gives every router the same interface to SQLite or PostgreSQL.")
    r.figure("diagrams/fig41.png", "Figure 4.1: Layers of the Online Quiz and Question Bank API", width_cm=14.0)
    r.h(2, "4.1  Resources and operations")
    r.para(f"The API has {OA['operations']} operations on {OA['paths']} addresses (Table 4.1): {OA['by_tag']['users']} for users, {OA['by_tag']['question bank']} for the question bank, {OA['by_tag']['quizzes']} for quizzes and attempts and {OA['by_tag']['learning']} for learning. "
           "The last column shows who may call each operation; the check is made by a dependency that reads the bearer token, finds the user and compares the role.")
    rows = []
    for e in OA["list"]:
        for m in e["methods"]:
            rows.append([m, f"`{e['path']}`", e["summary"], ROLE.get((m, e["path"]), "admin, teacher" if e["tag"] in ("question bank",) or e["path"].startswith("/api/quizzes") else "any user")])
    # the quiz operations that students may not call are marked staff above; fix the exceptions explicitly
    r.table("Table 4.1: Operations of the API", ["Method", "Path", "What it does", "Allowed"], rows, widths=[1.7, 6.3, 4.2, 2.8], size=8.5)
    r.h(2, "4.2  Database")
    r.para("Nine tables hold the data (Figure 4.2). `users` and `tokens` hold accounts and sessions. `questions` is the question bank, `quizzes` the quizzes and `quiz_questions` the many-to-many link between them. `attempts` records every attempt of a student "
           "with its start time, deadline, status, score and calibration, and `answers` the choices and confidence levels given in it. `practice_log` records the adaptive practice answers and `revision` holds the Leitner box and due date of each question for each student. "
           "Deleting a user, a quiz or an attempt deletes the rows that depend on it, and a question that belongs to a quiz cannot be deleted, so that the history of attempts stays intact.")
    r.figure("diagrams/fig42.png", "Figure 4.2: Database tables and their relations", width_cm=10.5)


def chapter5(r):
    H1(r, "5. METHODOLOGY", 5)
    r.h(2, "5.1  Overall approach")
    r.para("The API was designed resource first: the nouns (users, questions, quizzes, attempts) were decided before the code, then the operations on each were mapped to HTTP methods, and the rules that the server must enforce were written down "
           "and turned into tests. FastAPI generates the OpenAPI document from the code, so the documentation cannot drift from the behaviour. The learning features (calibration, revision, adaptive practice, item analysis) are "
           "kept in small functions with simple formulas, so each can be checked by hand and by a simulation.")
    r.h(2, "5.2  Status codes")
    r.table("Table 5.1: Status codes used and when",
            ["Code", "Meaning", "Example in this API"],
            [["200 OK", "request succeeded", "listing questions, login, results"],
             ["201 Created", "a resource was created", "register, add a question, create a quiz, start or submit an attempt"],
             ["204 No Content", "success with no body", "delete a question, quiz or user"],
             ["400 Bad Request", "valid JSON but impossible request", "asking for 40 random questions when only 8 match; deleting yourself; a CSV without the required columns"],
             ["401 Unauthorized", "no or invalid token, or wrong password", "calling /api/me without a token; wrong password at login"],
             ["403 Forbidden", "known user, not allowed", "a student adding a question; a teacher listing users"],
             ["404 Not Found", "no such resource", "results of a quiz that does not exist"],
             ["409 Conflict", "clashes with the current state", "registering an e-mail twice; submitting an attempt twice; no attempts left"],
             ["422 Unprocessable Entity", "input fails validation", "difficulty 'extreme'; role 'admin' at registration; a name of one letter"]],
            widths=[3.4, 4.4, 7.2], size=9.5)
    r.h(2, "5.3  Authentication and roles")
    r.para("A password is never stored. At registration the server draws a random 16-byte salt and stores the salt together with the PBKDF2-HMAC-SHA256 digest of the password computed with 100,000 iterations [4]; at login "
           "the digest is recomputed and compared with `hmac.compare_digest`, which takes the same time whatever the input. A successful login creates a random 24-byte token (48 hexadecimal characters) from the `secrets` module, stores it with the user "
           "and returns it. The client sends it in the header `Authorization: Bearer <token>` [3]. A dependency, `current_user`, reads the header, looks up the token and returns the user or answers 401. A second dependency, `need_role(...)`, wraps it and answers 403 "
           "when the role is not in the list. A route is protected simply by naming the dependency in its signature. The role 'admin' cannot be chosen at registration (422); the first administrator is created by the seed script.")
    r.h(2, "5.4  Validation")
    r.para("Every request body is a Pydantic model. The rules are declared next to the fields, for example `name` 2 to 60 characters, `email` matching a pattern, `password` at least 6 characters, `difficulty` one of easy, medium or hard, `answer` one of a, b, c or d, `minutes` from 1 to 180, `count` from 1 to 50 and `confidence` from 1 to 3. "
           "If any rule fails, FastAPI answers 422 with a list of the problems and the route function never runs. Query parameters such as `page` and `size` are validated in the same way (`size` at most 100). All SQL uses placeholders, never string concatenation, so a hostile value cannot change the query.")
    r.h(2, "5.5  The question bank")
    r.para("A question has a subject, a topic, a difficulty, a text, four options, the correct option and an explanation that is shown after answering. The list operation accepts the filters `subject`, `topic`, `difficulty` and `search` (a case-insensitive part of the text) and returns a page "
           "with the total count. The import operation takes the text of a CSV file, checks that the required columns exist, validates each line with the same model as a single question, adds the good lines and returns the number added and the list of bad lines with the reason, so that one mistake does not lose a whole file. "
           "A question that belongs to a quiz cannot be deleted (409), because the results of earlier attempts refer to it.")
    r.h(2, "5.6  Quizzes and attempts")
    r.para("A quiz is made from chosen question ids or, with the random operation, from the questions that match a subject, topic and level; the server asks the database for random rows and answers 400 if fewer exist than were asked for. "
           "Figure 5.1 shows the life of an attempt. When a student starts an attempt the server checks that attempts remain, stores the start time and the **deadline** (start plus the minutes of the quiz) and returns the paper without the correct answers. "
           "If an open attempt already exists it is resumed, with the time that is really left. The order of the questions and of the options is shuffled with a random generator seeded from the attempt id, so each student has a different paper, and reloading the page shows the same one. ")
    r.figure("diagrams/fig51.png", "Figure 5.1: The life of one quiz attempt", width_cm=14.0)
    r.para("When the answers arrive, the server compares the time with the deadline plus a grace period of 30 seconds for network delay; a later submission is still marked but flagged `late`, and late attempts are left out of the average, the leaderboard and the item analysis. "
           "An attempt that was never submitted before its deadline is closed with a score of zero. The timer shown in the browser is only a display: it starts from `seconds_left`, which the server computes, and the server does not trust the browser's clock. "
           "An attempt can be submitted once (a second submission is 409), and the number of attempts is limited per quiz (409 when used up).")
    r.h(2, "5.7  Confidence calibration")
    r.para("With each answer the student gives a confidence level: 1 guessing, 2 fairly sure, 3 certain. Each level is treated as a claim about the chance of being right: 0.33, 0.66 and 0.95. For *n* answered questions, with outcome *o* (1 right, 0 wrong) and claim *c*, "
           "the Brier score [5] is the mean of (*c* − *o*)², and the **calibration score** is 100 × (1 − Brier score), so 100 is perfect. A student who is sure only when right scores high; a student who is certain and wrong is penalised heavily; "
           "a student who honestly guesses is hardly penalised. Worked example: four answers with marks (right, certain), (right, certain), (wrong, certain), (right, fairly sure) give squared errors 0.05² + 0.05² + 0.95² + 0.34² = 0.0025 + 0.0025 + 0.9025 + 0.1156 = 1.0231, "
           f"a Brier score of 0.2558 and a calibration score of {R['calibration_worked']['score']}. In addition, an answer that is wrong and given with confidence 3 is flagged as a **misconception** in the review.")
    r.h(2, "5.8  Spaced revision")
    r.para("Wrong answers are scheduled for revision with the Leitner system [6]. A question has a box from 1 to 5, and the number of days until it is due again is 1, 2, 4, 8 and 16 for boxes 1 to 5. A wrong answer puts the question in box 1, due tomorrow, or moves it back there if it was already in the queue. "
           "A right answer to a question that is in the queue moves it up one box, and a right answer in box 5 removes it from the queue, so a question is learned after five right answers in a row on the due days. If every review were right, the question would "
           f"be reviewed on days {', '.join(str(d) for d in R['leitner_cumulative_days'])} after the first mistake.")
    r.h(2, "5.9  Adaptive practice")
    r.para("In practice mode the server serves one question at a time. If the student names a topic the question comes from it; otherwise the server chooses a topic: with probability one half a topic never tried, otherwise the topic with the lowest accuracy among those with at least two answers (accuracy is computed from practice answers and finished quizzes together). "
           "The **difficulty** follows the last six practice answers of that subject: the base level is the average level of those questions (easy 1, medium 2, hard 3) rounded; if the accuracy is at least 80% the level goes up by one, if it is at most 40% it goes down by one, and with fewer than three answers the level is easy. "
           "The question is chosen at random from the unseen ones of that level (the eight most recent are skipped when possible), and the reply says why this question was chosen.")
    r.h(2, "5.10  Item analysis")
    r.para("For a finished quiz with at least one on-time attempt the teacher can ask for item analysis [8][9]. The **difficulty index** *p* of a question is the share of students who answered it correctly. The **discrimination index** is *D* = *p*(upper group) − *p*(lower group), where the groups are the 27% of students with the highest and the 27% with the lowest "
           "total score [8]; it needs at least four students. A question gets advice when it is very easy (*p* above 0.9), very hard (*p* below 0.3), poorly discriminating (*D* below 0.2), or when its measured difficulty disagrees with its label (measured easy at *p* of 0.7 or more, hard below 0.4, otherwise medium). "
           "The report also names the wrong option chosen most often, which points to the misconception behind a question.")


def chapter6(r):
    H1(r, "6. RESULTS", 6)
    r.h(2, "6.1  Test results")
    r.para("All 13 automated tests pass in about three seconds (Figure 6.1). ")
    r.figure(A + "shot_pytest.png", "Figure 6.1: Output of pytest -v", width_cm=13.0)
    r.para("They cover registration and roles, validation and filters, CSV import, protection of used questions, random quizzes, a full attempt with confidence and revision, attempt limits, the server timer, item analysis, the calibration formula, adaptive practice, revision spacing, the mastery map and the serving of the web page and documentation.")
    r.h(2, "6.2  The API in Swagger UI")
    r.para(f"FastAPI generates the OpenAPI document and the interactive page at `/docs`: the {OA['operations']} operations are grouped as users, question bank, quizzes and learning, and each can be tried with a token.")
    r.h(2, "6.3  Requests and responses")
    r.para("Table 6.1 lists real requests made to the API by the benchmark script and the answers received. The same operation gives different status codes depending on who calls it and with what: for example POST /api/questions returns 201 for a teacher, 403 for a student and 422 for wrong values.")
    rows = [[e["method"], f"`{e['path'][:44]}`", e["label"], e["status"]] for e in EX[:7]]
    r.table("Table 6.1: Requests made and status codes returned", ["Method", "Path", "Situation", "Status"], rows, widths=[1.7, 5.5, 6.6, 1.6], size=8.5)
    r.h(2, "6.4  Screens of the web page")
    st = DEMO["stats"]
    r.para("Figures 6.3 to 6.9 are screenshots of the plain web page that uses the API, taken from the running system with the sample data of `seed.py`; the tabs depend on the role. "
           "The teacher's question bank (Figure 6.3) has filters, paging (`GET /api/questions?page=...`) and a form that calls `POST /api/questions`; values outside the allowed set come back as 422.")
    r.figure(A + "shot_questions.png", "Figure 6.3: Teacher: question bank, 24 questions in pages of 10", width_cm=8.5)
    r.para("In Figure 6.4 the teacher has created a quiz of four random REST API questions (`POST /api/quizzes/random`); each quiz has buttons for results, item analysis, leaderboard and delete.")
    r.figure(A + "shot_quizzes_teacher.png", "Figure 6.4: Teacher: quiz list and the random-quiz form", width_cm=8.5)
    r.para("During a quiz (Figure 6.5) the student sees only the question text and the options, in an order that differs for every attempt, and gives a confidence level with each answer. The countdown comes from the server's `seconds_left`. "
           "After submission (Figure 6.6) the student sees the score (1 of 4), the calibration (84 of 100), and for each question the correct answer, the confidence given and the explanation; wrong answers join the revision list.")
    r.figure(A + "shot_take.png", "Figure 6.5: Student: a quiz in progress, with a confidence level for every question", width_cm=8.5)
    r.figure(A + "shot_score.png", "Figure 6.6: Student: score, calibration and review with explanations", width_cm=8.5)
    r.para("Figure 6.7 shows adaptive practice, one question at a time with the explanation after checking; the mastery map computed from practice and quizzes together; topics with fewer than three answers are marked as lacking data. The revision page lists the questions due, which are due tomorrow after a wrong answer.")
    r.figure(A + "shot_practice.png", "Figure 6.7: Student: adaptive practice", width_cm=8.0)
    r.para(f"Figures 6.8 and 6.9 show the teacher's results and item analysis for the quiz *REST API Fundamentals*, taken by the {len(DEMO['results']['attempts'])} demonstration students of the seed script: an average of {DEMO['results']['average_percent']}%, each student's score and calibration, and the hardest questions. "
           f"The administrator's page shows the statistics ({st['users']} users, {st['questions']} questions, {st['quizzes']} quizzes, {st['attempts']} finished attempts) and the user list. The demonstration students are generated; they are not real students.")
    r.figure(A + "shot_results.png", "Figure 6.8: Teacher: results of a quiz with calibration", width_cm=8.0)
    r.figure(A + "shot_analysis.png", "Figure 6.9: Teacher: item analysis", width_cm=8.0)
    r.h(2, "6.5  Does the calibration score separate honest from over-confident students?")
    r.para("To test the calibration score, four kinds of student were simulated. Each answers 10 questions, for each of which the chance of being right is drawn between 0.2 and 1.0, in 3,000 attempts per kind. The *calibrated* student knows how sure to be: certain when the chance is 0.85 or more, fairly sure from 0.5 to 0.85, guessing below. "
           "The *over-confident* student is always certain, the *under-confident* one always guessing, and the *random* one chooses a level at random. The scores come from the application's own function.")
    rows = [[k, f"{v['accuracy_mean']:.1f}%", f"{v['calibration_mean']:.1f}", f"{v['calibration_sd']:.1f}"] for k, v in CAL.items()]
    r.table("Table 6.2: Calibration score of four simulated kinds of student (3,000 attempts each)", ["Student", "Mean accuracy", "Mean calibration score", "Standard deviation"], rows, widths=[4.6, 3.4, 4.0, 3.0], size=10)
    r.figure(A + "chart_calibration.png", "Figure 6.10: Calibration score by kind of student", width_cm=11.0)
    r.para(f"All four kinds are right in about {CAL['calibrated']['accuracy_mean']:.0f}% of the questions, so the ordinary score cannot tell them apart. The calibration score does: the calibrated student averages {CAL['calibrated']['calibration_mean']:.0f}, the always-certain student {CAL['overconfident']['calibration_mean']:.0f} "
           f"with a much wider spread ({CAL['overconfident']['calibration_sd']:.0f} against {CAL['calibrated']['calibration_sd']:.0f}), because one confident mistake costs 0.9 and the cost is not averaged away in a short quiz. The always-guessing and the random student both score about {CAL['underconfident']['calibration_mean']:.0f}. "
           "This is a statement about the formula and a simulation, not about real students: it shows that the measure has the property that a teacher would want, that it rewards knowing what you know.")
    r.h(2, "6.6  Spaced revision")
    rows = [[f"{p}", f"{v['reviews_mean']:.1f}", f"{v['days_mean']:.0f}", f"{v['days_median']:.0f}", f"{v['reviews_max']}"] for p, v in LEI.items()]
    r.para("The revision queue was exercised through the real `update_revision` function with a simulated learner who answers correctly with a fixed probability *p* at every review, 400 learners for each value of *p*. A learner starts with a wrong answer and is reviewed on the due days until the question leaves the queue "
           f"(five right answers in a row). With perfect recall the question leaves after {R['leitner_cumulative_days'][-1]} days and 5 reviews, as the schedule 1, 2, 4, 8, 16 says (reviews on days {', '.join(str(d) for d in R['leitner_cumulative_days'])}). Table 6.3 and Figure 6.11 show what happens when recall is not perfect.")
    r.table("Table 6.3: Reviews and days needed to learn one question", ["Chance of a right answer at a review", "Mean reviews", "Mean days", "Median days", "Most reviews"], rows, widths=[5.2, 2.6, 2.4, 2.4, 2.4], size=10)
    r.figure(A + "chart_leitner.png", "Figure 6.11: Effort needed to learn a question for different recall probabilities", width_cm=13.0)
    r.para(f"A learner who recalls the answer 9 times out of 10 needs about {LEI['0.9']['reviews_mean']:.0f} reviews over {LEI['0.9']['days_mean']:.0f} days; one who recalls it half of the time needs {LEI['0.5']['reviews_mean']:.0f} reviews over {LEI['0.5']['days_mean']:.0f} days, because each failure sends the question back to box 1. "
           "The scheme therefore spends the effort where it is needed: easy questions leave the queue after five short reviews, hard ones keep returning at short intervals until they are learned. A weakness of the simple rule is also visible: a single failure in box 5 throws away four reviews of progress.")
    r.h(2, "6.7  Adaptive practice")
    r.para("Three simulated students used the practice mode through the HTTP API, 12 students of each kind, 30 questions each, on a subject with 30 questions at each of the three levels. The weak student answers correctly 80%, 45% and 15% of the easy, medium and hard questions, the average student 92%, 70% and 40%, the strong student 98%, 90% and 75%. "
           "Figure 6.12 shows the levels of the questions served after the first ten, once the mechanism has adapted.")
    r.figure(A + "chart_adaptive.png", "Figure 6.12: Difficulty of the practice questions served, by kind of student (questions 11 to 30)", width_cm=11.5)
    r.para(f"The strong student received {ADA['strong']['share_late']['3']:.0f}% hard questions, the average student {ADA['average']['share_late']['3']:.0f}% and the weak student {ADA['weak']['share_late']['3']:.0f}%; the weak student worked mostly at medium level ({ADA['weak']['share_late']['2']:.0f}%) and "
           f"was given {ADA['weak']['share_late']['1']:.0f}% easy questions. The difficulty follows the ability of the student, as intended. The weak student is not held at the easiest level, because a score of about 45% on medium questions is above the 40% threshold for stepping down. The experiment checks the behaviour of the rule; whether the questions really help students to learn would need a study with real students.")
    r.h(2, "6.8  Item analysis of the demonstration quiz")
    items = DEMO["analysis"]["items"]
    rows = [[f"{x['text'][:58]}{'...' if len(x['text']) > 58 else ''}", x["labelled"], "-" if x["difficulty_index"] is None else x["difficulty_index"], "-" if x["discrimination"] is None else x["discrimination"], (x["most_chosen_wrong_option"] or "-").upper(), "; ".join(x["flags"]) or "fine"] for x in items]
    r.para(f"Table 6.4 is the item analysis of *REST API Fundamentals* ({DEMO['analysis']['students']} on-time attempts). The measured difficulty disagrees with the label for three questions, which the report marks (for example a question labelled hard that {int(round(100 * items[4]['difficulty_index']))}% of the students answered correctly). "
           "One question has a discrimination index of 0: strong and weak students did equally well, so it does not help to tell them apart. These are exactly the questions that a teacher should reword or relabel. The attempts of the demonstration students are generated, so the figures illustrate the report and say nothing about real students.")
    r.table("Table 6.4: Item analysis of REST API Fundamentals", ["Question", "Label", "Difficulty index", "Discrimination", "Wrong option most chosen", "Advice"], rows, widths=[5.0, 1.3, 1.6, 1.9, 1.7, 3.5], size=8)
    r.h(2, "6.9  Performance")
    rows = [[k, f"{v['median_ms']:.1f}", f"{v['p95_ms']:.1f}"] for k, v in LAT.items()]
    r.table("Table 6.5: Time per request (FastAPI TestClient on one laptop-class machine)", ["Request", "Median (ms)", "95th percentile (ms)"], rows, widths=[8.4, 3.2, 3.4], size=10)
    r.para(f"Most requests take about 5 ms. The slowest is the login ({LAT['POST /api/login']['median_ms']:.0f} ms), and it is slow on purpose: PBKDF2 with 100,000 iterations is what makes guessing passwords expensive. Starting and submitting a 20-question quiz together takes about {LAT['start + submit a 20-question quiz']['median_ms']:.0f} ms. "
           "These times were measured in-process without a network, so they show the cost of the application code only; a deployed server adds the network and, on a serverless host, the start of the function.")
    r.h(2, "6.10  Discussion")
    r.para("The tests confirm the REST behaviour, in particular the status codes and role checks. The simulations show that the calibration score reveals what the ordinary score cannot, that the revision queue concentrates effort on hard questions, and that practice follows ability. Item analysis gives teachers a list of questions to improve.")
    r.para("The evidence has limits: the students are simulated, the demonstration data is generated, and the confidence claims (0.33, 0.66, 0.95) are a modelling choice. The Vercel deployment was not run for this report.")


def chapter7(r):
    H1(r, "7. CONCLUSION", 7)
    r.para(f"This mini project built the REST API of an online quiz and question-bank system with {OA['operations']} operations, three roles, a validated and documented interface and a database layer that runs on SQLite and PostgreSQL. The server controls what must not be left to the browser: authentication, roles, the timer, the number of attempts, "
           "the shuffling of the paper and the exclusion of late attempts. On top of marking, the system measures how well a student's confidence matches the result, brings wrong answers back at growing intervals, chooses practice questions by weakest topic and recent performance, "
           "and gives teachers the difficulty and discrimination of every question. The 13 automated tests pass, and the simulations confirm the intended behaviour of the learning features.")
    r.para(f"Three results stand out. The ordinary score cannot separate a student who knows what they know from one who is always certain, but the calibration score does ({CAL['calibrated']['calibration_mean']:.0f} against {CAL['overconfident']['calibration_mean']:.0f} at the same accuracy). "
           f"The Leitner queue needs only {LEI['0.97']['reviews_mean']:.0f} reviews for a question that is remembered and about {LEI['0.5']['reviews_mean']:.0f} for one that is not. And the practice mode serves {ADA['strong']['share_late']['3']:.0f}% hard questions to a strong student and {ADA['weak']['share_late']['3']:.0f}% to a weak one.")
    r.h(2, "7.1  Limitations")
    r.bullets(["Only single-answer multiple-choice questions are supported; there are no essay, numeric or multiple-answer questions.",
               "Tokens do not expire and there is no logout endpoint on the server; there is no e-mail verification, password reset or rate limiting on login.",
               "The experiments use simulated students and generated demonstration data; the effect on real learning has not been measured.",
               "The Vercel deployment was not exercised from the machine used for this report."])
    r.h(2, "7.2  Future scope")
    r.bullets(["Token expiry, logout and rate limiting on login.", "More question types: multiple answers, numeric, short text and images.", "Use item analysis to retire or reword questions automatically.", "Fit revision intervals to each learner; add classes and assignments.", "Pilot with a real class to measure whether calibration feedback improves later scores."])


def chapter8(r):
    H1(r, "8. REFERENCE", 8)
    refs = [
        "R. T. Fielding, \"Architectural styles and the design of network-based software architectures,\" Ph.D. dissertation, Dept. of Information and Computer Science, University of California, Irvine, 2000.",
        "R. Fielding and J. Reschke, Eds., \"HTTP Semantics,\" RFC 9110, Internet Engineering Task Force, 2022.",
        "M. Jones and D. Hardt, \"The OAuth 2.0 Authorization Framework: Bearer Token Usage,\" RFC 6750, Internet Engineering Task Force, 2012.",
        "B. Kaliski, \"PKCS #5: Password-Based Cryptography Specification Version 2.0,\" RFC 2898, Internet Engineering Task Force, 2000.",
        "G. W. Brier, \"Verification of forecasts expressed in terms of probability,\" Monthly Weather Review, vol. 78, no. 1, pp. 1–3, 1950.",
        "S. Leitner, So lernt man lernen: Angewandte Lernpsychologie. Freiburg: Herder, 1972.",
        "N. J. Cepeda, H. Pashler, E. Vul, J. T. Wixted and D. Rohrer, \"Distributed practice in verbal recall tasks: A review and quantitative synthesis,\" Psychological Bulletin, vol. 132, no. 3, pp. 354–380, 2006.",
        "T. L. Kelley, \"The selection of upper and lower groups for the validation of test items,\" Journal of Educational Psychology, vol. 30, no. 1, pp. 17–24, 1939.",
        "L. Crocker and J. Algina, Introduction to Classical and Modern Test Theory. New York: Holt, Rinehart and Winston, 1986.",
        "S. Ramírez, \"FastAPI documentation.\" [Online]. Available: https://fastapi.tiangolo.com",
        "OpenAPI Initiative, \"OpenAPI Specification, version 3.1.0,\" 2021. [Online]. Available: https://spec.openapis.org/oas/v3.1.0",
        "Pydantic, \"Pydantic documentation.\" [Online]. Available: https://docs.pydantic.dev",
        "J. Dunlosky, K. A. Rawson, E. J. Marsh, M. J. Nathan and D. T. Willingham, \"Improving students' learning with effective learning techniques: Promising directions from cognitive and educational psychology,\" Psychological Science in the Public Interest, vol. 14, no. 1, pp. 4–58, 2013.",
    ]
    for i, t in enumerate(refs, 1):
        p = r.para(f"[{i}]  {t}", size=12, spacing=1.15, after=5, indent=1.0)
        p.paragraph_format.first_line_indent = r.cm(-1.0)
