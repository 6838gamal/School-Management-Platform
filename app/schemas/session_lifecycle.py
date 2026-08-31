"""Session lifecycle + substitute schemas."""
from pydantic import BaseModel, Field


class SessionTransitionRequest(BaseModel):
    schedule_entry_id: str = Field(..., min_length=1)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    to_status: str
    notes: str | None = Field(default=None, max_length=500)
    substitute_teacher_id: str | None = None


class SubstituteAssignmentCreate(BaseModel):
    schedule_entry_id: str
    absent_teacher_id: str
    substitute_teacher_id: str
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    reason: str | None = Field(default=None, max_length=500)


class SubstituteRespond(BaseModel):
    accept: bool
    reason: str | None = Field(default=None, max_length=500)
