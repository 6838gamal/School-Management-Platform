"""Report schemas."""
from pydantic import BaseModel

from app.schemas.common import ORMBase


class ReportGenerateRequest(BaseModel):
    report_type: str  # students/attendance/teachers/grades/behavior/activities/schedules
    parameters: dict = {}
    format: str = "web"  # web/pdf


class ReportLinkOut(ORMBase):
    id: str
    token: str
    report_type: str
    expires_at: str
    is_active: bool


class DashboardStats(BaseModel):
    total_students: int = 0
    total_teachers: int = 0
    total_sections: int = 0
    total_subjects: int = 0
    attendance_today: dict = {}
    teacher_attendance_today: dict = {}
    affected_lessons: int = 0
    upcoming_activities: int = 0
    recent_behavior: int = 0
    unread_notifications: int = 0
