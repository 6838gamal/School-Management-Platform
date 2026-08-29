"""Grades schemas."""
from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class AssessmentCreate(BaseModel):
    section_id: str
    subject_id: str
    teacher_id: str | None = None
    title: str
    assessment_type: str = Field(..., pattern="^(exam|quiz|assignment|homework|activity|participation)$")
    max_score: float = 100
    passing_score: float = 50
    weight: float = 1.0
    date: str | None = None
    description: str | None = None
    # ✅ إضافة الحقول المطلوبة
    school_id: str | None = None
    year_id: str | None = None


class AssessmentUpdate(BaseModel):
    title: str | None = None
    section_id: str | None = None
    subject_id: str | None = None
    teacher_id: str | None = None
    assessment_type: str | None = Field(None, pattern="^(exam|quiz|assignment|homework|activity|participation)$")
    max_score: float | None = None
    passing_score: float | None = None
    weight: float | None = None
    date: str | None = None
    description: str | None = None
    year_id: str | None = None


class AssessmentOut(ORMBase):
    id: str
    section_id: str
    subject_id: str
    teacher_id: str | None = None
    title: str
    assessment_type: str
    max_score: float
    passing_score: float
    weight: float
    date: str | None = None
    description: str | None = None
    school_id: str | None = None
    year_id: str | None = None


class GradeRecordCreate(BaseModel):
    assessment_id: str
    student_id: str
    score: float
    note: str | None = None


class GradeRecordBatch(BaseModel):
    assessment_id: str
    records: list[dict] = []  # [{student_id, score, note}]


class GradeRecordOut(ORMBase):
    id: str
    assessment_id: str
    student_id: str
    score: float | None = None
    note: str | None = None
    graded_by: str | None = None


class StudentGradeSummary(BaseModel):
    student_id: str
    student_name: str
    assessments: list[dict] = []
    total_weighted: float = 0
    average: float = 0
    rank: int | None = None
