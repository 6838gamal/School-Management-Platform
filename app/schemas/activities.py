"""Activities schemas."""
from pydantic import BaseModel

from app.schemas.common import ORMBase


class ActivityCreate(BaseModel):
    title: str
    description: str | None = None
    activity_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    supervisor_id: str | None = None


class ActivityUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    activity_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    status: str | None = None


class ActivityOut(ORMBase):
    id: str
    school_id: str
    title: str
    description: str | None = None
    activity_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    status: str
    supervisor_id: str | None = None
    is_active: bool


class ParticipantAdd(BaseModel):
    student_id: str
    role: str = "participant"
    result: str | None = None
    note: str | None = None


class ParticipantOut(ORMBase):
    id: str
    activity_id: str
    student_id: str
    role: str | None = None
    result: str | None = None
    note: str | None = None
