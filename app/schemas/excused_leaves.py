"""Excused leave (استئذان) schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class ExcusedLeaveCreate(BaseModel):
    student_id: str = Field(..., min_length=1)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    requested_at: str = Field(..., min_length=10)
    exit_time: str = Field(..., min_length=4)
    reason: str = Field(..., min_length=3, max_length=500)
    guardian_name: str = Field(..., min_length=2, max_length=255)
    guardian_relation: str = Field(..., min_length=2, max_length=30)
    guardian_phone: str = Field(..., min_length=4, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)


class ExcusedLeaveOut(BaseModel):
    id: str
    student_id: str
    section_id: str | None
    date: str
    requested_at: str
    exit_time: str
    reason: str
    guardian_name: str
    guardian_relation: str
    guardian_phone: str
    notes: str | None
    recorded_by: str | None
    created_at: datetime
