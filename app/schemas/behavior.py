"""Behavior schemas."""
from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class BehaviorCategoryCreate(BaseModel):
    name: str
    name_en: str | None = None
    type: str = Field(..., pattern="^(positive|negative)$")
    default_severity: int = Field(1, ge=1, le=5)


class BehaviorCategoryOut(ORMBase):
    id: str
    school_id: str
    name: str
    name_en: str | None = None
    type: str
    default_severity: int


class BehaviorRecordCreate(BaseModel):
    student_id: str
    category_id: str | None = None
    type: str = Field(..., pattern="^(positive|negative)$")
    severity: int = Field(1, ge=1, le=5)
    title: str
    description: str | None = None
    action_taken: str | None = None
    date: str


class BehaviorRecordUpdate(BaseModel):
    severity: int | None = None
    title: str | None = None
    description: str | None = None
    action_taken: str | None = None


class BehaviorRecordOut(ORMBase):
    id: str
    student_id: str
    category_id: str | None = None
    type: str
    severity: int
    title: str
    description: str | None = None
    action_taken: str | None = None
    date: str
    recorded_by: str | None = None
