"""Attendance, grades, schedules, homework, activities, behavior, notifications, reports web routes."""
from datetime import datetime, timezone
from typing import Optional
import json

from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

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
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.schemas.attendance import (
    StudentAttendanceBatch,
    StudentAttendanceCreate,
    TeacherAttendanceCreate,
)

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
    """الصفحة الرئيسية للحضور."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    service = AttendanceService(db)
    summary = await service.student_summary(user.school_id, today)
    absent = await service.absent_teachers(user.school_id, today)
    
    return templates.TemplateResponse(
        "attendance/index.html",
        {
            **ctx,
            "title": "الحضور",
            "summary": summary or {"total": 0, "present": 0, "absent": 0},
            "absent_teachers": absent,
            "selected_date": today,
            "today": today,
        },
    )


@attendance_router.get("/students")
async def student_attendance_list(
    request: Request,
    date: Optional[str] = Query(None, description="التاريخ (YYYY-MM-DD)"),
    section_id: Optional[str] = Query(None, description="معرف المجموعة"),
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة حضور الطلاب."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    selected_date = date or today
    
    service = AttendanceService(db)
    summary = await service.student_summary(user.school_id, selected_date)
    
    records = []
    if section_id:
        records = await service.section_attendance(section_id, selected_date)
    
    # Get sections for filter - استخدام AcademicService
    academic_service = AcademicService(db)
    onboarding_data = await academic_service.get_onboarding_data(user.school_id)
    sections = onboarding_data.get("sections", [])
    
    return templates.TemplateResponse(
        "attendance/students/list.html",
        {
            **ctx,
            "title": "حضور الطلاب",
            "records": records,
            "summary": summary or {"total": 0, "present": 0, "absent": 0},
            "total": summary.get("total", 0) if summary else 0,
            "sections": sections,
            "selected_date": selected_date,
            "selected_section": section_id,
            "today": today,
        },
    )


@attendance_router.get("/students/new")
async def student_attendance_create_form(
    request: Request,
    section_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض نموذج إضافة حضور طلاب."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    selected_date = date or today
    
    # Get sections - استخدام AcademicService
    academic_service = AcademicService(db)
    onboarding_data = await academic_service.get_onboarding_data(user.school_id)
    sections = onboarding_data.get("sections", [])
    
    students = []
    if section_id:
        student_service = StudentService(db)
        # استخدام الدالة المناسبة من StudentService
        students = await student_service.get_students_by_section(user.school_id, section_id)
    
    return templates.TemplateResponse(
        "attendance/students/form.html",
        {
            **ctx,
            "title": "تسجيل حضور",
            "sections": sections,
            "students": students,
            "selected_section": section_id,
            "selected_date": selected_date,
            "today": today,
        },
    )


@attendance_router.post("/students")
async def student_attendance_create(
    request: Request,
    date: str = Form(...),
    section_id: str = Form(...),
    records: str = Form(...),  # JSON string
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    """إنشاء حضور طلاب (دفعة واحدة)."""
    try:
        records_data = json.loads(records)
        
        batch_data = StudentAttendanceBatch(
            date=date,
            section_id=section_id,
            records=records_data,
        )
        
        service = AttendanceService(db)
        result = await service.batch_record(
            school_id=user.school_id,
            user_id=user.id,
            req=batch_data,
        )
        
        return RedirectResponse(
            f"/attendance/students?date={date}&section_id={section_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except Exception as e:
        academic_service = AcademicService(db)
        onboarding_data = await academic_service.get_onboarding_data(user.school_id)
        sections = onboarding_data.get("sections", [])
        
        return templates.TemplateResponse(
            "attendance/students/form.html",
            {
                "request": request,
                "title": "تسجيل حضور",
                "error": str(e),
                "sections": sections,
                "selected_date": date,
                "selected_section": section_id,
                "today": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            },
            status_code=400,
        )


@attendance_router.get("/teachers")
async def teacher_attendance_list(
    request: Request,
    date: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة حضور المعلمين."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    selected_date = date or today
    
    service = AttendanceService(db)
    absent_teachers = await service.absent_teachers(user.school_id, selected_date)
    
    return templates.TemplateResponse(
        "attendance/teachers/list.html",
        {
            **ctx,
            "title": "حضور المعلمين",
            "absent_teachers": absent_teachers,
            "selected_date": selected_date,
            "today": today,
        },
    )


@attendance_router.get("/teachers/new")
async def teacher_attendance_create_form(
    request: Request,
    date: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض نموذج إضافة حضور معلمين."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    selected_date = date or today
    
    teacher_service = TeacherService(db)
    teachers = await teacher_service.get_teachers(user.school_id, is_active=True)
    
    return templates.TemplateResponse(
        "attendance/teachers/form.html",
        {
            **ctx,
            "title": "تسجيل حضور معلم",
            "teachers": teachers,
            "selected_date": selected_date,
            "statuses": ["present", "absent", "late", "leave"],
            "today": today,
        },
    )


@attendance_router.post("/teachers")
async def teacher_attendance_create(
    request: Request,
    teacher_id: str = Form(...),
    date: str = Form(...),
    status: str = Form(...),
    note: Optional[str] = Form(None),
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    """إنشاء حضور معلم."""
    try:
        attendance_data = TeacherAttendanceCreate(
            teacher_id=teacher_id,
            date=date,
            status=status,
            note=note,
        )
        
        service = AttendanceService(db)
        result = await service.record_teacher(
            school_id=user.school_id,
            user_id=user.id,
            req=attendance_data,
        )
        
        return RedirectResponse(
            f"/attendance/teachers?date={date}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except Exception as e:
        teacher_service = TeacherService(db)
        teachers = await teacher_service.get_teachers(user.school_id, is_active=True)
        
        return templates.TemplateResponse(
            "attendance/teachers/form.html",
            {
                "request": request,
                "title": "تسجيل حضور معلم",
                "error": str(e),
                "teachers": teachers,
                "teacher_id": teacher_id,
                "selected_date": date,
                "status": status,
                "note": note,
                "statuses": ["present", "absent", "late", "leave"],
                "today": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            },
            status_code=400,
        )


@attendance_router.get("/reports/daily")
async def attendance_daily_report(
    request: Request,
    date: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_any_permission("attendance.view_reports")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """تقرير الحضور اليومي."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    selected_date = date or today
    
    service = AttendanceService(db)
    student_summary = await service.student_summary(user.school_id, selected_date)
    teacher_summary = await service.absent_teachers(user.school_id, selected_date)
    
    return templates.TemplateResponse(
        "attendance/reports/daily.html",
        {
            **ctx,
            "title": "تقرير الحضور اليومي",
            "date": selected_date,
            "student_summary": student_summary or {"total": 0, "present": 0, "absent": 0},
            "teacher_summary": teacher_summary,
            "today": today,
        },
    )


@attendance_router.get("/section/{section_id}")
async def section_attendance_page(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تسجيل حضور لمجموعة محددة."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    service = AttendanceService(db)
    records = await service.section_attendance(section_id, today)
    
    return templates.TemplateResponse(
        "attendance/section.html",
        {
            **ctx,
            "title": "تسجيل الحضور",
            "section_id": section_id,
            "records": records,
            "date": today,
        },
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
        "schedules/list.html",
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
