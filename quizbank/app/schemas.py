from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

LEVELS = ("easy", "medium", "hard")


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=60)
    role: str = "student"

    @field_validator("role")
    @classmethod
    def role_ok(cls, v):
        if v not in ("student", "teacher"):
            raise ValueError("role must be student or teacher")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class QuestionIn(BaseModel):
    subject: str = Field(min_length=1, max_length=40)
    topic: str = Field(min_length=1, max_length=40)
    difficulty: str
    text: str = Field(min_length=5, max_length=500)
    opt_a: str = Field(min_length=1)
    opt_b: str = Field(min_length=1)
    opt_c: str = Field(min_length=1)
    opt_d: str = Field(min_length=1)
    answer: str
    explanation: str = Field(default="", max_length=800)

    @field_validator("difficulty")
    @classmethod
    def diff_ok(cls, v):
        if v not in LEVELS:
            raise ValueError("difficulty must be easy, medium or hard")
        return v

    @field_validator("answer")
    @classmethod
    def ans_ok(cls, v):
        if v not in ("a", "b", "c", "d"):
            raise ValueError("answer must be a, b, c or d")
        return v


class ImportIn(BaseModel):
    csv: str = Field(min_length=10)


class QuizIn(BaseModel):
    title: str = Field(min_length=3, max_length=80)
    subject: str
    minutes: int = Field(ge=1, le=180)
    max_attempts: int = Field(default=2, ge=1, le=10)
    question_ids: List[int] = Field(min_length=1)


class RandomQuizIn(BaseModel):
    title: str = Field(min_length=3, max_length=80)
    subject: str
    minutes: int = Field(ge=1, le=180)
    max_attempts: int = Field(default=2, ge=1, le=10)
    count: int = Field(ge=1, le=50)
    topic: Optional[str] = None
    difficulty: Optional[str] = None


class AnswerIn(BaseModel):
    choice: Optional[str] = Field(default=None, pattern="^[abcd]$")
    confidence: Optional[int] = Field(default=None, ge=1, le=3)   # 1 guessing, 2 fairly sure, 3 certain


class SubmitIn(BaseModel):
    answers: Dict[str, AnswerIn]


class PracticeAnswerIn(BaseModel):
    question_id: int
    choice: str = Field(pattern="^[abcd]$")
    confidence: Optional[int] = Field(default=None, ge=1, le=3)
