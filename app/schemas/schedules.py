"""Schedule schemas."""
from pydantic import BaseModel,Field

from app.schemas.common import ORMBase


class ScheduleEntryCreate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    period_id: str
    subject_id: str
    teacher_id: str
    room_id: str | None = None
    section_id: str


class ScheduleEntryUpdate(BaseModel):
    subject_id: str | None = None
    teacher_id: str | None = None
    room_id: str | None = None


class ScheduleEntryOut(ORMBase):
    id: str
    schedule_id: str
    day_of_week: int
    period_id: str
    subject_id: str
    teacher_id: str
    room_id: str | None = None
    section_id: str


class ScheduleOut(ORMBase):
    id: str
    school_id: str
    year_id: str
    section_id: str | None = None
    name: str
    is_active: bool
    entries: list[ScheduleEntryOut] = []


class ConflictReport(BaseModel):
    teacher_conflicts: list[dict] = []
    room_conflicts: list[dict] = []
    section_conflicts: list[dict] = []


class ReplacementSuggestion(BaseModel):
    teacher_id: str
    teacher_name: str
    free_periods: list[int] = []
    reason: str = ""
