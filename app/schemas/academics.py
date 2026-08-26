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


# ============= Academic Year =============
class AcademicYearCreate(BaseModel):
    name: str
    start_date: str
    end_date: str
    is_current: bool = True


class AcademicYearUpdate(BaseModel):
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool | None = None
    is_active: bool | None = None


class AcademicYearOut(ORMBase):
    id: str
    school_id: str
    name: str
    start_date: str
    end_date: str
    is_current: bool
    is_active: bool


# ============= Stage =============
class StageCreate(BaseModel):
    year_id: str
    name: str
    name_en: str | None = None
    order: int = 0


class StageUpdate(BaseModel):
    year_id: str | None = None
    name: str | None = None
    name_en: str | None = None
    order: int | None = None


class StageOut(ORMBase):
    id: str
    school_id: str
    year_id: str
    name: str
    name_en: str | None = None
    order: int


# ============= Grade =============
class GradeCreate(BaseModel):
    stage_id: str
    name: str
    name_en: str | None = None
    order: int = 0


class GradeUpdate(BaseModel):
    stage_id: str | None = None
    name: str | None = None
    name_en: str | None = None
    order: int | None = None


class GradeOut(ORMBase):
    id: str
    school_id: str
    stage_id: str
    name: str
    name_en: str | None = None
    order: int


# ============= Section =============
class SectionCreate(BaseModel):
    grade_id: str
    name: str
    capacity: int = 30


class SectionUpdate(BaseModel):
    grade_id: str | None = None
    name: str | None = None
    capacity: int | None = None
    is_active: bool | None = None


class SectionOut(ORMBase):
    id: str
    school_id: str
    grade_id: str
    name: str
    capacity: int
    is_active: bool


# ============= Subject =============
class SubjectCreate(BaseModel):
    name: str
    name_en: str | None = None
    code: str | None = None
    color: str | None = None


class SubjectUpdate(BaseModel):
    name: str | None = None
    name_en: str | None = None
    code: str | None = None
    color: str | None = None
    is_active: bool | None = None


class SubjectOut(ORMBase):
    id: str
    school_id: str
    name: str
    name_en: str | None = None
    code: str | None = None
    color: str | None = None
    is_active: bool


# ============= Room =============
class RoomCreate(BaseModel):
    name: str
    building: str | None = None
    floor: str | None = None
    capacity: int = 30


class RoomUpdate(BaseModel):
    name: str | None = None
    building: str | None = None
    floor: str | None = None
    capacity: int | None = None
    is_active: bool | None = None


class RoomOut(ORMBase):
    id: str
    school_id: str
    name: str
    building: str | None = None
    floor: str | None = None
    capacity: int
    is_active: bool


# ============= Period =============
class PeriodCreate(BaseModel):
    name: str
    order: int
    start_time: str
    end_time: str
    is_break: bool = False


class PeriodUpdate(BaseModel):
    name: str | None = None
    order: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_break: bool | None = None


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
