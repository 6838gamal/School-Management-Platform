"""Schedule schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List

from app.schemas.common import ORMBase


# ============= إنشاء =============

class ScheduleCreate(BaseModel):
    name: str = Field(..., description="اسم الجدول")
    section_id: str = Field(..., description="معرف الشعبة")
    academic_year_id: str = Field(..., description="معرف العام الدراسي")
    is_active: bool = Field(True, description="هل الجدول مفعل")


class ScheduleEntryCreate(BaseModel):
    day_of_week: int = Field(..., description="اليوم (0=الأحد, 1=الإثنين, ...)")
    period_id: str = Field(..., description="معرف الفترة")
    subject_id: str = Field(..., description="معرف المادة")
    teacher_id: str = Field(..., description="معرف المعلم")
    room_id: str = Field(..., description="معرف القاعة")
    note: Optional[str] = Field(None, description="ملاحظة")


# ============= تحديث =============

class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="اسم الجدول")
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    academic_year_id: Optional[str] = Field(None, description="معرف العام الدراسي")
    is_active: Optional[bool] = Field(None, description="هل الجدول مفعل")


class ScheduleEntryUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, description="اليوم")
    period_id: Optional[str] = Field(None, description="معرف الفترة")
    subject_id: Optional[str] = Field(None, description="معرف المادة")
    teacher_id: Optional[str] = Field(None, description="معرف المعلم")
    room_id: Optional[str] = Field(None, description="معرف القاعة")
    note: Optional[str] = Field(None, description="ملاحظة")


# ============= خرج =============

class ScheduleEntryOut(ORMBase):
    id: str
    schedule_id: str
    day_of_week: int
    period_id: str
    subject_id: str
    teacher_id: str
    room_id: str
    note: Optional[str] = None


class ScheduleOut(ORMBase):
    id: str
    school_id: str
    name: str
    section_id: str
    academic_year_id: str
    is_active: bool
    entries: Optional[List[ScheduleEntryOut]] = []
