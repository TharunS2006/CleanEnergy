import json, pathlib
R = json.load(open(pathlib.Path(__file__).parent.parent / "report_results.json"))
C = R["calibration"]; L = R["leitner"]; A = R["adaptive"]; O = R["openapi"]
ABSTRACT = (
    "Online quizzes are usually little more than a list of questions and a score. Teachers get no help in keeping a good question bank, "
    "students get no advice on what to study next, and timing and cheating are easy to abuse. This mini project builds the back end of an "
    f"Online Quiz and Question Bank Management System as a REST API with {O['operations']} operations on {O['paths']} resources, written in Python with FastAPI and Pydantic, "
    "with SQLite on a laptop and PostgreSQL when deployed. Three roles (admin, teacher, student) use bearer-token authentication, and passwords are stored with salted PBKDF2. "
    "Teachers keep a question bank with filters, bulk import from CSV and an explanation for every answer, and build quizzes by hand or at random. "
    "A quiz attempt is controlled by the server: the timer, the number of attempts, a per-student shuffle of questions and options, and the exclusion of late attempts from the leaderboard. "
    "Beyond marking, the system asks each student how sure they are of every answer and computes a calibration score from it (100 minus the Brier score); wrong answers given with certainty are flagged as likely misconceptions "
    "and, like every wrong answer, return for revision after 1, 2, 4, 8 and 16 days (Leitner boxes). An adaptive practice mode chooses the weakest topic and a difficulty that follows the last six answers, and teachers get item analysis "
    "(difficulty and discrimination index) that shows which questions are mislabelled or do not separate strong from weak students. "
    f"The system is checked by 13 automated tests. In a simulation of 3,000 attempts for each of four kinds of student, the calibration score separated an honest student ({C['calibrated']['calibration_mean']:.0f}) from an always-certain one ({C['overconfident']['calibration_mean']:.0f}) although both answered "
    f"{C['calibrated']['accuracy_mean']:.0f}% of the questions correctly; adaptive practice gave a strong student {A['strong']['share_late']['3']:.0f}% hard questions and a weak student only {A['weak']['share_late']['3']:.0f}%.")
