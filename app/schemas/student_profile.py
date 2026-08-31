"""Student profile schemas (basic + window + performance + attachments)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StudentBasicOut(BaseModel):
    id: str
    student_number: str
    full_name: str
    first_name: str
    last_name: str
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_email: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool = True
    section_id: Optional[str] = None
    section_name: Optional[str] = None
    grade_name: Optional[str] = None
    stage_name: Optional[str] = None
    year_id: Optional[str] = None
    academic_year: Optional[str] = None
    health_status: Optional[str] = None
    health_notes: Optional[str] = None


class AttendanceTimelineEntry(BaseModel):
    date: str
    status: Optional[str] = None
    late_minutes: Optional[int] = None
    note: Optional[str] = None


class AttendanceWindowOut(BaseModel):
    date_from: str
    date_to: str
    timeline: list[AttendanceTimelineEntry]
    counts: dict


class StudentAttendanceFilter(BaseModel):
    date_from: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    preset: Optional[str] = Field(
        default=None,
        description="One of: last_30_days (default), this_month, custom",
    )


class AttachmentCreate(BaseModel):
    student_id: str
    kind: str = Field(..., pattern=r"^(health_report|medical_clearance|parent_consent|other)$")
    title: str = Field(..., min_length=2, max_length=200)
    file_name: str = Field(..., min_length=1, max_length=255)
    file_url: str = Field(..., min_length=1, max_length=500)
    mime_type: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=1000)


class AttachmentOut(BaseModel):
    id: str
    kind: str
    title: str
    file_name: str
    file_url: str
    mime_type: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
