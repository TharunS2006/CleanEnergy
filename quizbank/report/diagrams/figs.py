from svglib import *

# ============ Figure 4.1: layers ============
W, H = 900, 660
s = Svg(W, H)
s.text(450, 34, "Layers of the Online Quiz and Question Bank API", 21, "700", INK, "middle")
def layer(y, h, title, color, light):
    s.rect(30, y, 840, h, light, color, 2, 12, dash="7 5")
    s.rect(46, y - 14, 10.4 * len(title) + 30, 28, color, color, 1, 6); s.text(60, y + 6, title, 15.5, "700", "#fff")
layer(66, 112, "CLIENTS", USR_D, USR_L)
s.box(60, 90, 250, 78, "Web page", ["public/index.html, app.js", "fetch() with a bearer token"], USR_D, "#fff", i_doc)
s.box(340, 90, 250, 78, "Swagger UI", ["/docs, generated from the code", "try every endpoint"], USR_D, "#fff", i_gear)
s.box(620, 90, 220, 78, "Any HTTP client", ["curl, Postman, tests", "JSON in and out"], USR_D, "#fff", i_server)
layer(214, 150, "REST API (FastAPI)", APP_D, APP_L)
s.box(60, 240, 175, 100, "users", ["register, login,", "me, users, stats"], APP_D, "#fff", i_user)
s.box(250, 240, 175, 100, "questions", ["CRUD, filters,", "CSV import"], APP_D, "#fff", i_db)
s.box(440, 240, 175, 100, "quizzes", ["create, start, submit,", "results, analysis"], APP_D, "#fff", i_clock)
s.box(630, 240, 210, 100, "learning", ["practice, revision,", "mastery map"], APP_D, "#fff", i_chart)
layer(404, 100, "CROSS-CUTTING", SEC_D, SEC_L)
s.rect(60, 430, 360, 56, "#fff", SEC_D, 1.8, 8); s.text(240, 454, "auth.py: bearer token, role check", 14.5, "700", INK, "middle"); s.text(240, 474, "pbkdf2-sha256 password hashing", 12.5, "400", MUTE, "middle")
s.rect(450, 430, 390, 56, "#fff", SEC_D, 1.8, 8); s.text(645, 454, "schemas.py: Pydantic validation", 14.5, "700", INK, "middle"); s.text(645, 474, "wrong input gets 422 before any code runs", 12.5, "400", MUTE, "middle")
layer(540, 90, "DATA", DATA_D, DATA_L)
s.rect(60, 564, 360, 52, "#fff", DATA_D, 1.8, 8); s.text(240, 586, "db.py: one wrapper, one SQL dialect", 14.5, "700", INK, "middle"); s.text(240, 606, "'?' placeholders adapted per database", 12.5, "400", MUTE, "middle")
s.rect(450, 564, 390, 52, DATA_L, DATA_D, 1.8, 8); s.text(645, 586, "SQLite (laptop)  or  PostgreSQL (Vercel)", 14.5, "700", INK, "middle"); s.text(645, 606, "chosen by the DATABASE_URL variable", 12.5, "400", MUTE, "middle")
for x in (300, 465, 730):
    s.line([(x, 178), (x, 240)], INK, 2)
for x in (300, 465, 600, 735):
    s.line([(x, 340), (x, 404)], INK, 1.8, dash="5 4")
s.line([(450, 504), (450, 540)], DATA_D, 2.2, marker="arr", start=True)
open("fig41.svg", "w").write(s.render())

# ============ Figure 4.2: database ============
W2, H2 = 900, 700
d = Svg(W2, H2)
d.text(450, 28, "Database tables and their relations", 21, "700", INK, "middle")
def table(x, y, name, cols, color, light, w=190):
    h = 46 + 21 * len(cols)
    d.rect(x, y, w, h, "#fff", color, 2, 8); d.rect(x, y, w, 30, light, color, 2, 8); d.text(x + w / 2, y + 21, name, 15.5, "700", INK, "middle")
    for i, c in enumerate(cols): d.text(x + 10, y + 52 + 21 * i, c, 12.5, "400" if not c.startswith("*") else "700", INK if not c.startswith("*") else color)
    return h
table(30, 50, "users", ["*id (PK)", "name", "email (unique)", "password_hash", "role: admin | teacher | student"], USR_D, USR_L, 230)
table(30, 230, "tokens", ["*token (PK)", "user_id (FK)", "created_at"], USR_D, USR_L, 230)
table(310, 50, "questions", ["*id (PK)", "subject, topic", "difficulty: easy | medium | hard", "text, opt_a, opt_b, opt_c, opt_d", "answer: a | b | c | d", "explanation", "created_by (FK)"], APP_D, APP_L, 250)
table(310, 290, "quiz_questions", ["*quiz_id (FK)", "*question_id (FK)"], APP_D, APP_L, 250)
table(310, 410, "quizzes", ["*id (PK)", "title, subject", "minutes, max_attempts", "created_by (FK)"], APP_D, APP_L, 250)
table(620, 50, "attempts", ["*id (PK)", "quiz_id (FK), user_id (FK)", "started_at, deadline", "submitted_at, status", "score, total, late", "calibration"], AZ_D, AZ_L, 250)
table(620, 270, "answers", ["attempt_id (FK)", "question_id", "chosen, correct", "confidence: 1 | 2 | 3"], AZ_D, AZ_L, 250)
table(620, 420, "practice_log", ["*id (PK)", "user_id (FK), question_id (FK)", "chosen, correct, confidence", "at"], DATA_D, DATA_L, 250)
table(620, 570, "revision", ["*user_id, *question_id (PK)", "box: 1 to 5", "due (date)"], DATA_D, DATA_L, 250)
d.line([(145, 190), (145, 230)], INK, 1.8)                                     # users - tokens
d.line([(435, 242), (435, 290)], INK, 1.8)                                      # questions - quiz_questions
d.line([(435, 354), (435, 410)], INK, 1.8)                                      # quiz_questions - quizzes
d.line([(560, 470), (592, 470), (592, 130), (620, 130)], INK, 1.8)              # quizzes - attempts
d.line([(745, 198), (745, 270)], INK, 1.8)                                      # attempts - answers
d.rect(30, 560, 560, 120, "#fff", LINE, 1.4, 8)
d.lines(44, 586, ["Also related (not drawn): users - attempts, users - practice_log, users - revision,",
                  "questions - answers, questions - practice_log, questions - revision.",
                  "PK primary key, FK foreign key. Deleting a user, a quiz or an attempt removes the",
                  "rows that depend on it (ON DELETE CASCADE). A question used in a quiz cannot be deleted."], 13, 22, fill=MUTE)
open("fig42.svg", "w").write(d.render())

# ============ Figure 5.1: the life of one quiz attempt ============
W3, H3 = 900, 620
f = Svg(W3, H3)
f.text(450, 28, "One quiz attempt, from start to review", 21, "700", INK, "middle")
for x, name, c, l in ((30, "Student (browser)", USR_D, USR_L), (330, "API", APP_D, APP_L), (630, "Database", DATA_D, DATA_L)):
    f.rect(x, 50, 240, 36, l, c, 2, 8); f.text(x + 120, 74, name, 15.5, "700", c, "middle"); f.line([(x + 120, 86), (x + 120, 600)], c, 1.4, dash="5 5", marker=None)
def msg(y, x1, x2, text, color=INK, dash=None):
    f.line([(x1, y), (x2, y)], color, 2.2, dash=dash, marker="arr" if color == INK else ("arrG" if color == APP_D else "arrR"))
    f.text((x1 + x2) / 2, y - 8, text, 12.5, "700", color, "middle")
msg(120, 150, 450, "POST /quizzes/{id}/start")
msg(150, 450, 750, "attempts left? create the attempt", INK)
msg(180, 450, 150, "shuffled paper + seconds_left", APP_D, "6 4")
f.rect(60, 196, 180, 44, "#fff", LINE, 1.4, 6); f.text(150, 216, "student answers,", 12.5, "400", MUTE, "middle"); f.text(150, 232, "marks how sure", 12.5, "400", MUTE, "middle")
msg(270, 150, 450, "POST /attempts/{id}/submit  (answers + confidence)")
msg(300, 450, 750, "read attempt, deadline, answer key", INK)
f.rect(340, 316, 220, 62, "#fff", APP_D, 1.6, 6); f.text(450, 338, "late = now > deadline + 30 s", 12.5, "700", INK, "middle"); f.text(450, 356, "score, calibration (Brier)", 12.5, "700", INK, "middle"); f.text(450, 372, "misconception = certain and wrong", 12, "400", MUTE, "middle")
msg(410, 450, 750, "save answers, score, status = done", INK)
msg(440, 450, 750, "wrong answers: Leitner box 1, due tomorrow", INK)
msg(480, 450, 150, "score, calibration, review + explanations", APP_D, "6 4")
f.rect(30, 520, 840, 70, "#fff", LINE, 1.4, 8)
f.text(46, 546, "Errors on the way: 409 if the attempt was already submitted or all attempts are used, 404 for an unknown attempt,", 13.5, "400", MUTE)
f.text(46, 568, "403 if the caller is not a student, 401 without a token. A closed late attempt does not appear in the leaderboard.", 13.5, "400", MUTE)
open("fig51.svg", "w").write(f.render())
