"""Attendance, grades, schedules, homework, activities, behavior, notifications, reports web routes."""
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.academic_service import AcademicService
from app.services.activity_service import ActivityService, BehaviorService
from app.services.attendance_service import AttendanceService
from app.services.grade_service import GradeService
from app.services.homework_service import HomeworkService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.services.schedule_service import ScheduleService

templates = Jinja2Templates(directory="app/templates")


# ------------------------------------------------------------------
# Attendance
# ------------------------------------------------------------------
attendance_router = APIRouter(prefix="/attendance", tags=["attendance"])


@attendance_router.get("")
async def attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    from datetime import datetime, timezone
    service = AttendanceService(db)
    summary = await service.student_summary(user.school_id, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    absent = await service.absent_teachers(user.school_id, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    return templates.TemplateResponse(
        "attendance/index.html",
        {**ctx, "title": "الحضور", "summary": summary, "absent_teachers": absent},
    )


@attendance_router.get("/section/{section_id}")
async def section_attendance_page(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    from datetime import datetime, timezone
    service = AttendanceService(db)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = await service.section_attendance(section_id, today)
    return templates.TemplateResponse(
        "attendance/section.html",
        {**ctx, "title": "تسجيل الحضور", "section_id": section_id, "records": records, "date": today},
    )


# ------------------------------------------------------------------
# Grades
# ------------------------------------------------------------------
grades_router = APIRouter(prefix="/grades", tags=["grades"])


@grades_router.get("")
async def grades_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    ctx: dict = Depends(template_context),
):
    return templates.TemplateResponse("grades/index.html", {**ctx, "title": "الدرجات"})


# ------------------------------------------------------------------
# Schedules
# ------------------------------------------------------------------
schedules_router = APIRouter(prefix="/schedules", tags=["schedules"])


@schedules_router.get("")
async def schedules_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    academic = AcademicService(db)
    data = await academic.get_onboarding_data(user.school_id)
    return templates.TemplateResponse(
        "schedules/index.html",
        {**ctx, "title": "الجداول", "sections": data["sections"], "periods": data["periods"]},
    )


# ------------------------------------------------------------------
# Homework
# ------------------------------------------------------------------
homework_router = APIRouter(prefix="/homework", tags=["homework"])


@homework_router.get("")
async def homework_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("homework.view")),
    ctx: dict = Depends(template_context),
):
    return templates.TemplateResponse("homework/index.html", {**ctx, "title": "الواجبات"})


# ------------------------------------------------------------------
# Activities
# ------------------------------------------------------------------
activities_router = APIRouter(prefix="/activities", tags=["activities"])


@activities_router.get("")
async def activities_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("activities.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = ActivityService(db)
    items = await service.list_activities(user.school_id)
    return templates.TemplateResponse("activities/index.html", {**ctx, "title": "الأنشطة", "activities": items})


# ------------------------------------------------------------------
# Behavior
# ------------------------------------------------------------------
behavior_router = APIRouter(prefix="/behavior", tags=["behavior"])


@behavior_router.get("")
async def behavior_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("behavior.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = BehaviorService(db)
    records = await service.school_records(user.school_id)
    categories = await service.list_categories(user.school_id)
    return templates.TemplateResponse(
        "behavior/index.html",
        {**ctx, "title": "السلوك", "records": records, "categories": categories},
    )


# ------------------------------------------------------------------
# Notifications
# ------------------------------------------------------------------
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("")
async def notifications_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("notifications.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = NotificationService(db)
    items = await service.list_for_user(user.id)
    return templates.TemplateResponse("notifications/index.html", {**ctx, "title": "الإشعارات", "notifications": items})


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------
reports_router = APIRouter(prefix="/reports", tags=["reports"])


@reports_router.get("")
async def reports_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("reports.view")),
    ctx: dict = Depends(template_context),
):
    return templates.TemplateResponse("reports/index.html", {**ctx, "title": "التقارير"})


@reports_router.get("/r/{token}")
async def report_view(
    request: Request,
    token: str,
    ctx: dict = Depends(template_context),
):
    return templates.TemplateResponse("reports/view.html", {**ctx, "title": "تقرير", "token": token})
