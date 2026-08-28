"""Web routes for modules."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, Query, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_async_db
from app.core.auth import get_current_user, require_permission
from app.models.uses import User
from app.models.studens import Student
from app.models.teachers import Teacher
from app.models.academics import Section
from app.models.academics import Period
from app.schemas.attendance import (
    StudentAttendanceCreate,
    StudentAttendanceBatch,
    StudentAttendanceStatus,
    TeacherAttendanceCreate,
    TeacherAttendanceStatus,
)
from app.services.attendance import AttendanceService
from app.services.student import StudentService
from app.services.teacher import TeacherService
from app.services.section import SectionService

router = APIRouter(prefix="/attendance", tags=["Attendance"])
templates = Jinja2Templates(directory="app/templates")


# ==================== Main Attendance Page ====================

@router.get("")
async def attendance_page(
    request: Request,
    date: Optional[str] = Query(None, description="التاريخ (YYYY-MM-DD)"),
    section_id: Optional[str] = Query(None, description="معرف المجموعة"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """الصفحة الرئيسية لإدارة الحضور."""
    # Get current date for default value
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    # Get school_id from user
    school_id = current_user.school_id
    
    # Get attendance summary
    service = AttendanceService(db)
    summary = await service.student_summary(school_id, selected_date)
    
    # Get sections for filter
    section_service = SectionService(db)
    sections = await section_service.get_all(school_id)
    
    # Get attendance records for the selected date
    records = []
    if section_id:
        records = await service.section_attendance(section_id, selected_date)
    
    context = {
        "request": request,
        "records": records,
        "summary": summary,
        "total": summary.get("total", 0) if summary else 0,
        "sections": sections,
        "selected_date": selected_date,
        "selected_section": section_id,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/index.html", context)


# ==================== Student Attendance ====================

@router.get("/students")
async def student_attendance_list(
    request: Request,
    date: Optional[str] = Query(None, description="التاريخ (YYYY-MM-DD)"),
    section_id: Optional[str] = Query(None, description="معرف المجموعة"),
    period_id: Optional[str] = Query(None, description="معرف الحصة"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """عرض قائمة حضور الطلاب."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    # Get school_id from user
    school_id = current_user.school_id
    
    # Get attendance service
    service = AttendanceService(db)
    
    # Get summary for the date
    summary = await service.student_summary(school_id, selected_date)
    
    # Get records for the section if specified
    records = []
    if section_id:
        records = await service.section_attendance(section_id, selected_date)
    
    # Get sections for filters
    section_service = SectionService(db)
    sections = await section_service.get_all(school_id)
    
    # Get periods
    periods = await db.query(Period).filter(Period.is_active == True).all()
    
    context = {
        "request": request,
        "records": records,
        "summary": summary,
        "total": summary.get("total", 0) if summary else 0,
        "sections": sections,
        "periods": periods,
        "selected_date": selected_date,
        "selected_section": section_id,
        "selected_period": period_id,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/students/list.html", context)


@router.get("/students/new")
async def student_attendance_create_form(
    request: Request,
    section_id: Optional[str] = Query(None),
    period_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """عرض نموذج إضافة حضور طلاب."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    school_id = current_user.school_id
    
    # Get sections for dropdowns
    section_service = SectionService(db)
    sections = await section_service.get_all(school_id)
    
    # Get periods
    periods = await db.query(Period).filter(Period.is_active == True).all()
    
    # If section_id provided, get students
    students = []
    if section_id:
        student_service = StudentService(db)
        students = await student_service.get_by_section(school_id, section_id, is_active=True)
    
    context = {
        "request": request,
        "sections": sections,
        "periods": periods,
        "students": students,
        "selected_section": section_id,
        "selected_period": period_id,
        "selected_date": selected_date,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/students/form.html", context)


@router.post("/students")
async def student_attendance_create(
    request: Request,
    date: str = Form(...),
    section_id: str = Form(...),
    period_id: Optional[str] = Form(None),
    records: str = Form(...),  # JSON string
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """إنشاء حضور طلاب (دفعة واحدة)."""
    import json
    
    try:
        # Parse records JSON
        records_data = json.loads(records)
        
        # Prepare batch data
        batch_data = StudentAttendanceBatch(
            date=date,
            section_id=section_id,
            period_id=period_id,
            records=records_data,
        )
        
        # Save attendance
        service = AttendanceService(db)
        result = await service.batch_record(
            school_id=current_user.school_id,
            user_id=current_user.id,
            req=batch_data,
        )
        
        return RedirectResponse(
            f"/attendance/students?date={date}&section_id={section_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except Exception as e:
        # Get data for re-rendering
        section_service = SectionService(db)
        sections = await section_service.get_all(current_user.school_id)
        periods = await db.query(Period).filter(Period.is_active == True).all()
        
        return templates.TemplateResponse(
            "attendance/students/form.html",
            {
                "request": request,
                "error": str(e),
                "sections": sections,
                "periods": periods,
                "selected_date": date,
                "selected_section": section_id,
                "selected_period": period_id,
                "today": datetime.now().strftime("%Y-%m-%d"),
                "can": lambda p: current_user.has_permission(p),
            },
            status_code=400,
        )


@router.post("/students/quick")
async def student_attendance_quick(
    student_id: str = Form(...),
    date: str = Form(...),
    status: StudentAttendanceStatus = Form(...),
    note: Optional[str] = Form(None),
    section_id: Optional[str] = Form(None),
    period_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """تسجيل حضور طالب سريع (AJAX)."""
    try:
        attendance_data = StudentAttendanceCreate(
            student_id=student_id,
            section_id=section_id,
            period_id=period_id,
            date=date,
            status=status,
            note=note,
        )
        
        service = AttendanceService(db)
        result = await service.record_student(
            school_id=current_user.school_id,
            user_id=current_user.id,
            req=attendance_data,
        )
        
        return {
            "success": True,
            "message": "تم تسجيل الحضور بنجاح",
            "data": result,
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.get("/students/check")
async def check_student_attendance(
    student_id: str = Query(...),
    date: str = Query(...),
    period_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """التحقق من وجود سجل حضور لطالب في تاريخ معين."""
    service = AttendanceService(db)
    record = await service.student_att.get_by_student_date(
        student_id=student_id,
        date=date,
        period_id=period_id,
    )
    
    return {
        "exists": record is not None,
        "status": record.status if record else None,
        "record_id": record.id if record else None,
    }


# ==================== Teacher Attendance ====================

@router.get("/teachers")
async def teacher_attendance_list(
    request: Request,
    date: Optional[str] = Query(None),
    status: Optional[TeacherAttendanceStatus] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """عرض قائمة حضور المعلمين."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    school_id = current_user.school_id
    
    service = AttendanceService(db)
    
    # Get absent teachers
    absent_teachers = await service.absent_teachers(school_id, selected_date)
    
    # Get all teachers for reference
    teacher_service = TeacherService(db)
    teachers = await teacher_service.get_all(school_id, is_active=True)
    
    context = {
        "request": request,
        "absent_teachers": absent_teachers,
        "total": len(teachers),
        "absent_count": len(absent_teachers),
        "selected_date": selected_date,
        "selected_status": status,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/teachers/list.html", context)


@router.get("/teachers/new")
async def teacher_attendance_create_form(
    request: Request,
    date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """عرض نموذج إضافة حضور معلمين."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    school_id = current_user.school_id
    
    # Get all active teachers
    teacher_service = TeacherService(db)
    teachers = await teacher_service.get_all(school_id, is_active=True)
    
    context = {
        "request": request,
        "teachers": teachers,
        "selected_date": selected_date,
        "statuses": TeacherAttendanceStatus,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/teachers/form.html", context)


@router.post("/teachers")
async def teacher_attendance_create(
    request: Request,
    teacher_id: str = Form(...),
    date: str = Form(...),
    status: TeacherAttendanceStatus = Form(...),
    note: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.create")),
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
            school_id=current_user.school_id,
            user_id=current_user.id,
            req=attendance_data,
        )
        
        return RedirectResponse(
            f"/attendance/teachers?date={date}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except Exception as e:
        teacher_service = TeacherService(db)
        teachers = await teacher_service.get_all(current_user.school_id, is_active=True)
        
        return templates.TemplateResponse(
            "attendance/teachers/form.html",
            {
                "request": request,
                "teachers": teachers,
                "error": str(e),
                "teacher_id": teacher_id,
                "selected_date": date,
                "status": status,
                "note": note,
                "statuses": TeacherAttendanceStatus,
                "today": datetime.now().strftime("%Y-%m-%d"),
                "can": lambda p: current_user.has_permission(p),
            },
            status_code=400,
        )


# ==================== Reports ====================

@router.get("/reports/daily")
async def attendance_daily_report(
    request: Request,
    date: Optional[str] = Query(None),
    section_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.view_reports")),
):
    """تقرير الحضور اليومي."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    school_id = current_user.school_id
    
    service = AttendanceService(db)
    
    # Get student attendance summary
    student_summary = await service.student_summary(school_id, selected_date)
    
    # Get teacher attendance summary
    teacher_summary = await service.absent_teachers(school_id, selected_date)
    
    # Get sections for filter
    section_service = SectionService(db)
    sections = await section_service.get_all(school_id)
    
    context = {
        "request": request,
        "date": selected_date,
        "student_summary": student_summary,
        "teacher_summary": teacher_summary,
        "sections": sections,
        "selected_section": section_id,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/reports/daily.html", context)


# ==================== API Endpoints ====================

@router.get("/api/sections/{section_id}/students")
async def get_section_students(
    section_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """الحصول على طلاب مجموعة معينة (AJAX)."""
    student_service = StudentService(db)
    students = await student_service.get_by_section(
        current_user.school_id,
        section_id,
        is_active=True
    )
    
    return {
        "students": [
            {
                "id": s.id,
                "full_name": s.full_name,
                "student_number": s.student_number,
            }
            for s in students
        ]
    }


@router.get("/api/sections")
async def get_sections(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """الحصول على جميع المجموعات (AJAX)."""
    section_service = SectionService(db)
    sections = await section_service.get_all(current_user.school_id)
    
    return {
        "sections": [
            {
                "id": s.id,
                "name": s.name,
            }
            for s in sections
        ]
    }
