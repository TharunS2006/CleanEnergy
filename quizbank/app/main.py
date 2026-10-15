import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routes_questions import router as questions_router
from .routes_quizzes import router as quizzes_router
from .routes_users import router as users_router

app = FastAPI(title="Online Quiz and Question Bank Management System",
              description="Mini project: REST API for managing a question bank, building quizzes and taking them.")

init_db()
app.include_router(users_router)
app.include_router(questions_router)
app.include_router(quizzes_router)

STATIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(os.path.join(STATIC, "index.html"))
