"""Schedules schemas."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ScheduleCreate(BaseModel):
    """Schema لإنشاء جدول جديد"""
    name: str = Field(..., min_length=1, max_length=100, description="اسم الجدول")
    section_id: str = Field(..., description="معرف الشعبة")
    academic_year_id: str = Field(..., description="معرف العام الدراسي")
    is_active: bool = Field(default=True, description="حالة التفعيل")

    @field_validator('section_id')
    @classmethod
    def validate_section_id(cls, v: str) -> str:
        if not v or len(v) != 36:
            raise ValueError('معرف الشعبة غير صحيح')
        return v

    @field_validator('academic_year_id')
    @classmethod
    def validate_academic_year_id(cls, v: str) -> str:
        if not v or len(v) != 36:
            raise ValueError('معرف العام الدراسي غير صحيح')
        return v


class ScheduleUpdate(BaseModel):
    """Schema لتحديث جدول"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    section_id: Optional[str] = None
    academic_year_id: Optional[str] = None
    is_active: Optional[bool] = None


class ScheduleEntryCreate(BaseModel):
    """Schema لإضافة حصة إلى الجدول"""
    day_of_week: int = Field(..., ge=0, le=4, description="اليوم (0-4)")
    period_id: str = Field(..., description="معرف الفترة")
    subject_id: str = Field(..., description="معرف المادة")
    teacher_id: str = Field(..., description="معرف المعلم")
    room_id: str = Field(..., description="معرف القاعة")
    note: Optional[str] = Field(None, description="ملاحظة")


class ScheduleEntryUpdate(BaseModel):
    """Schema لتحديث حصة"""
    day_of_week: Optional[int] = Field(None, ge=0, le=4)
    period_id: Optional[str] = None
    subject_id: Optional[str] = None
    teacher_id: Optional[str] = None
    room_id: Optional[str] = None
    note: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Schema لعرض الجدول"""
    id: str
    name: str
    school_id: str
    section_id: str
    section_name: Optional[str] = None
    year_id: str
    academic_year_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    entries_count: Optional[int] = 0
    entries: Optional[list] = []


class ScheduleEntryResponse(BaseModel):
    """Schema لعرض الحصة"""
    id: str
    day_of_week: int
    period_id: str
    period_name: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None
    teacher_id: str
    teacher_name: Optional[str] = None
    room_id: str
    room_name: Optional[str] = None
    note: Optional[str] = None
