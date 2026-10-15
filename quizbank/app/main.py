import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routes_learn import router as learn_router
from .routes_questions import router as questions_router
from .routes_quizzes import router as quizzes_router
from .routes_users import router as users_router

app = FastAPI(
    title="Online Quiz and Question Bank Management System",
    description="REST API for a question bank, timed quizzes, adaptive practice, spaced-repetition revision "
                "and confidence-calibrated marking.")

init_db()
app.include_router(users_router)
app.include_router(questions_router)
app.include_router(quizzes_router)
app.include_router(learn_router)

# The web page lives in /public. On Vercel the files in /public are served directly;
# when running locally with uvicorn this mount does the same job.
PUBLIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
if os.path.isdir(PUBLIC):
    app.mount("/", StaticFiles(directory=PUBLIC, html=True), name="public")
