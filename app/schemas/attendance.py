"""Attendance schemas."""
from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class StudentAttendanceCreate(BaseModel):
    student_id: str
    section_id: str | None = None
    period_id: str | None = None
    schedule_entry_id: str | None = None
    date: str
    status: str = Field(..., pattern="^(present|absent|late|excused)$")
    note: str | None = None


class StudentAttendanceBatch(BaseModel):
    date: str
    section_id: str
    period_id: str | None = None
    records: list[dict] = []  # [{student_id, status, note}]


class StudentAttendanceOut(ORMBase):
    id: str
    student_id: str
    section_id: str | None = None
    period_id: str | None = None
    date: str
    status: str
    note: str | None = None
    recorded_by: str | None = None


class TeacherAttendanceCreate(BaseModel):
    teacher_id: str
    date: str
    status: str = Field(..., pattern="^(present|absent|late|leave)$")
    note: str | None = None


class TeacherAttendanceOut(ORMBase):
    id: str
    teacher_id: str
    date: str
    status: str
    note: str | None = None
    recorded_by: str | None = None


class AttendanceSummary(BaseModel):
    date: str
    total: int
    present: int
    absent: int
    late: int
    excused: int
    rate: float
