"""Academic structure schemas."""
from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class SchoolOut(ORMBase):
    id: str
    name: str
    name_en: str | None = None
    code: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    language: str
    onboarding_complete: bool
    onboarding_step: str | None = None
    is_active: bool


class SchoolUpdate(BaseModel):
    name: str | None = None
    name_en: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    language: str | None = None


class AcademicYearCreate(BaseModel):
    name: str
    start_date: str
    end_date: str
    is_current: bool = True


class AcademicYearOut(ORMBase):
    id: str
    school_id: str
    name: str
    start_date: str
    end_date: str
    is_current: bool
    is_active: bool


class StageCreate(BaseModel):
    year_id: str
    name: str
    name_en: str | None = None
    order: int = 0


class StageOut(ORMBase):
    id: str
    school_id: str
    year_id: str
    name: str
    name_en: str | None = None
    order: int


class GradeCreate(BaseModel):
    stage_id: str
    name: str
    name_en: str | None = None
    order: int = 0


class GradeOut(ORMBase):
    id: str
    school_id: str
    stage_id: str
    name: str
    name_en: str | None = None
    order: int


class SectionCreate(BaseModel):
    grade_id: str
    name: str
    capacity: int = 30


class SectionOut(ORMBase):
    id: str
    school_id: str
    grade_id: str
    name: str
    capacity: int
    is_active: bool


class SubjectCreate(BaseModel):
    name: str
    name_en: str | None = None
    code: str | None = None
    color: str | None = None


class SubjectOut(ORMBase):
    id: str
    school_id: str
    name: str
    name_en: str | None = None
    code: str | None = None
    color: str | None = None
    is_active: bool


class RoomCreate(BaseModel):
    name: str
    building: str | None = None
    floor: str | None = None
    capacity: int = 30


class RoomOut(ORMBase):
    id: str
    school_id: str
    name: str
    building: str | None = None
    floor: str | None = None
    capacity: int
    is_active: bool


class PeriodCreate(BaseModel):
    name: str
    order: int
    start_time: str
    end_time: str
    is_break: bool = False


class PeriodOut(ORMBase):
    id: str
    school_id: str
    name: str
    order: int
    start_time: str
    end_time: str
    is_break: bool


# Composite view for onboarding / tree display
class AcademicTree(ORMBase):
    year: AcademicYearOut
    stages: list[dict] = []
