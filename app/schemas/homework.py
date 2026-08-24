"""Homework schemas."""
from pydantic import Field

from app.schemas.common import ORMBase


class HomeworkCreate(BaseModel):
    section_id: str
    subject_id: str
    teacher_id: str
    title: str
    description: str | None = None
    due_date: str
    is_graded: bool = False
    max_score: float = 10


class HomeworkUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    is_graded: bool | None = None
    max_score: float | None = None


class HomeworkOut(ORMBase):
    id: str
    section_id: str
    subject_id: str
    teacher_id: str
    title: str
    description: str | None = None
    due_date: str
    is_graded: bool
    max_score: float


class SubmissionUpdate(BaseModel):
    status: str | None = None
    score: float | None = None
    note: str | None = None


class SubmissionOut(ORMBase):
    id: str
    homework_id: str
    student_id: str
    status: str
    submitted_at: str | None = None
    score: float | None = None
    note: str | None = None
