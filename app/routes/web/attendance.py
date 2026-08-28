"""Web routes for modules."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, Query, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette import status

from app.core.database import get_db
from app.core.auth import get_current_user, require_permission
from app.models.user import User
from app.models.students import Student
from app.models.teachers import Teacher
from app.models.section import Section
from app.models.period import Period
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.schemas.attendance import (
    StudentAttendanceCreate,
    StudentAttendanceBatch,
    StudentAttendanceOut,
    StudentAttendanceStatus,
    TeacherAttendanceCreate,
    TeacherAttendanceStatus,
    AttendanceQueryParams,
    AttendanceSummary,
)
from app.services.attendance_service import AttendanceService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.services.section_service import SectionService

router = APIRouter(prefix="/attendance", tags=["Attendance"])
templates = Jinja2Templates(directory="app/templates")


# ==================== Main Attendance Page ====================

@router.get("")
async def attendance_page(
    request: Request,
    date: Optional[str] = Query(None, description="التاريخ (YYYY-MM-DD)"),
    section_id: Optional[str] = Query(None, description="معرف المجموعة"),
    status: Optional[StudentAttendanceStatus] = Query(None, description="حالة الحضور"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """الصفحة الرئيسية لإدارة الحضور."""
    # Get current date for default value
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    # Build query params
    params = AttendanceQueryParams(
        date_from=selected_date,
        date_to=selected_date,
        section_id=section_id,
        status=status,
    )
    
    # Get attendance records
    service = AttendanceService(db)
    records, total = service.get_student_attendance(
        params=params,
        page=page,
        page_size=page_size,
    )
    
    # Get sections for filter
    sections = SectionService(db).get_all()
    
    # Calculate pagination
    start_index = (page - 1) * page_size
    end_index = min(start_index + page_size, total)
    
    context = {
        "request": request,
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "start_index": start_index,
        "end_index": end_index,
        "sections": sections,
        "selected_date": selected_date,
        "selected_section": section_id,
        "selected_status": status,
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
    status: Optional[StudentAttendanceStatus] = Query(None, description="حالة الحضور"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """عرض قائمة حضور الطلاب."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    # Build query params
    params = AttendanceQueryParams(
        date_from=selected_date,
        date_to=selected_date,
        section_id=section_id,
        status=status,
    )
    
    # Get attendance records
    service = AttendanceService(db)
    records, total = service.get_student_attendance(
        params=params,
        page=page,
        page_size=page_size,
    )
    
    # Get sections and periods for filters
    sections = SectionService(db).get_all()
    periods = db.query(Period).filter(Period.is_active == True).all()
    
    # Calculate pagination
    start_index = (page - 1) * page_size
    end_index = min(start_index + page_size, total)
    
    context = {
        "request": request,
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "start_index": start_index,
        "end_index": end_index,
        "sections": sections,
        "periods": periods,
        "selected_date": selected_date,
        "selected_section": section_id,
        "selected_period": period_id,
        "selected_status": status,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """عرض نموذج إضافة حضور طلاب."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    # Get sections and periods for dropdowns
    sections = SectionService(db).get_all()
    periods = db.query(Period).filter(Period.is_active == True).all()
    
    # If section_id provided, get students
    students = []
    if section_id:
        students = StudentService(db).get_by_section(section_id, is_active=True)
    
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
    db: Session = Depends(get_db),
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
        result = service.create_student_attendance_batch(
            batch=batch_data,
            recorded_by=current_user.id,
        )
        
        return RedirectResponse(
            f"/attendance/students?date={date}&section_id={section_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except Exception as e:
        # Get data for re-rendering
        sections = SectionService(db).get_all()
        periods = db.query(Period).filter(Period.is_active == True).all()
        
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


@router.get("/students/{attendance_id}")
async def student_attendance_detail(
    request: Request,
    attendance_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """عرض تفاصيل حضور طالب."""
    service = AttendanceService(db)
    record = service.get_student_attendance_by_id(attendance_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="سجل الحضور غير موجود")
    
    context = {
        "request": request,
        "record": record,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/students/detail.html", context)


@router.get("/students/{attendance_id}/edit")
async def student_attendance_edit_form(
    request: Request,
    attendance_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.update")),
):
    """عرض نموذج تعديل حضور طالب."""
    service = AttendanceService(db)
    record = service.get_student_attendance_by_id(attendance_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="سجل الحضور غير موجود")
    
    context = {
        "request": request,
        "record": record,
        "statuses": StudentAttendanceStatus,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/students/edit.html", context)


@router.post("/students/{attendance_id}")
async def student_attendance_update(
    attendance_id: str,
    status: StudentAttendanceStatus = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.update")),
):
    """تحديث حضور طالب."""
    service = AttendanceService(db)
    success = service.update_student_attendance(
        attendance_id=attendance_id,
        status=status,
        note=note,
        updated_by=current_user.id,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="سجل الحضور غير موجود")
    
    return RedirectResponse(
        f"/attendance/students/{attendance_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/students/{attendance_id}/delete")
async def student_attendance_delete(
    attendance_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.delete")),
):
    """حذف حضور طالب."""
    service = AttendanceService(db)
    success = service.delete_student_attendance(attendance_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="سجل الحضور غير موجود")
    
    return RedirectResponse(
        "/attendance/students",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/students/summary")
async def student_attendance_summary(
    request: Request,
    date: Optional[str] = Query(None),
    section_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """عرض ملخص حضور الطلاب."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    service = AttendanceService(db)
    summary = service.get_student_attendance_summary(
        date=selected_date,
        section_id=section_id,
    )
    
    # Get sections for filter
    sections = SectionService(db).get_all()
    
    context = {
        "request": request,
        "summary": summary,
        "sections": sections,
        "selected_date": selected_date,
        "selected_section": section_id,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/students/summary.html", context)


# ==================== Teacher Attendance ====================

@router.get("/teachers")
async def teacher_attendance_list(
    request: Request,
    date: Optional[str] = Query(None),
    status: Optional[TeacherAttendanceStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """عرض قائمة حضور المعلمين."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    service = AttendanceService(db)
    records, total = service.get_teacher_attendance(
        date=selected_date,
        status=status,
        page=page,
        page_size=page_size,
    )
    
    # Calculate pagination
    start_index = (page - 1) * page_size
    end_index = min(start_index + page_size, total)
    
    context = {
        "request": request,
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "start_index": start_index,
        "end_index": end_index,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """عرض نموذج إضافة حضور معلمين."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    # Get all active teachers
    teachers = TeacherService(db).get_all(is_active=True)
    
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
    db: Session = Depends(get_db),
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
        result = service.create_teacher_attendance(
            attendance=attendance_data,
            recorded_by=current_user.id,
        )
        
        return RedirectResponse(
            f"/attendance/teachers?date={date}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except Exception as e:
        teachers = TeacherService(db).get_all(is_active=True)
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


@router.get("/teachers/{attendance_id}/edit")
async def teacher_attendance_edit_form(
    request: Request,
    attendance_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.update")),
):
    """عرض نموذج تعديل حضور معلم."""
    service = AttendanceService(db)
    record = service.get_teacher_attendance_by_id(attendance_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="سجل الحضور غير موجود")
    
    context = {
        "request": request,
        "record": record,
        "statuses": TeacherAttendanceStatus,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/teachers/edit.html", context)


@router.post("/teachers/{attendance_id}")
async def teacher_attendance_update(
    attendance_id: str,
    status: TeacherAttendanceStatus = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.update")),
):
    """تحديث حضور معلم."""
    service = AttendanceService(db)
    success = service.update_teacher_attendance(
        attendance_id=attendance_id,
        status=status,
        note=note,
        updated_by=current_user.id,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="سجل الحضور غير موجود")
    
    return RedirectResponse(
        f"/attendance/teachers?date={datetime.now().strftime('%Y-%m-%d')}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/teachers/{attendance_id}/delete")
async def teacher_attendance_delete(
    attendance_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.delete")),
):
    """حذف حضور معلم."""
    service = AttendanceService(db)
    success = service.delete_teacher_attendance(attendance_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="سجل الحضور غير موجود")
    
    return RedirectResponse(
        "/attendance/teachers",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ==================== Quick Actions (AJAX) ====================

@router.post("/students/quick")
async def student_attendance_quick(
    student_id: str = Form(...),
    date: str = Form(...),
    status: StudentAttendanceStatus = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """تسجيل حضور طالب سريع (AJAX)."""
    try:
        attendance_data = StudentAttendanceCreate(
            student_id=student_id,
            date=date,
            status=status,
            note=note,
        )
        
        service = AttendanceService(db)
        result = service.create_student_attendance(
            attendance=attendance_data,
            recorded_by=current_user.id,
        )
        
        return {
            "success": True,
            "message": "تم تسجيل الحضور بنجاح",
            "data": result.dict(),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """التحقق من وجود سجل حضور لطالب في تاريخ معين."""
    service = AttendanceService(db)
    record = service.get_student_attendance_by_student_date(
        student_id=student_id,
        date=date,
    )
    
    return {
        "exists": record is not None,
        "status": record.status if record else None,
        "record_id": record.id if record else None,
    }


# ==================== Reports ====================

@router.get("/reports/daily")
async def attendance_daily_report(
    request: Request,
    date: Optional[str] = Query(None),
    section_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.view_reports")),
):
    """تقرير الحضور اليومي."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    service = AttendanceService(db)
    
    # Get student attendance summary
    student_summary = service.get_student_attendance_summary(
        date=selected_date,
        section_id=section_id,
    )
    
    # Get teacher attendance summary
    teacher_summary = service.get_teacher_attendance_summary(date=selected_date)
    
    # Get sections for filter
    sections = SectionService(db).get_all()
    
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


@router.get("/reports/monthly")
async def attendance_monthly_report(
    request: Request,
    month: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    section_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.view_reports")),
):
    """تقرير الحضور الشهري."""
    import calendar
    
    now = datetime.now()
    if not month:
        month = now.strftime("%m")
    if not year:
        year = now.strftime("%Y")
    
    service = AttendanceService(db)
    
    # Get monthly attendance statistics
    stats = service.get_monthly_attendance_stats(
        year=int(year),
        month=int(month),
        section_id=section_id,
    )
    
    # Get daily breakdown
    daily_breakdown = service.get_daily_attendance_breakdown(
        year=int(year),
        month=int(month),
        section_id=section_id,
    )
    
    # Get sections for filter
    sections = SectionService(db).get_all()
    
    # Month name in Arabic
    month_names = {
        "01": "يناير", "02": "فبراير", "03": "مارس", "04": "أبريل",
        "05": "مايو", "06": "يونيو", "07": "يوليو", "08": "أغسطس",
        "09": "سبتمبر", "10": "أكتوبر", "11": "نوفمبر", "12": "ديسمبر"
    }
    
    context = {
        "request": request,
        "month": month,
        "year": year,
        "month_name": month_names.get(month, month),
        "stats": stats,
        "daily_breakdown": daily_breakdown,
        "days_in_month": calendar.monthrange(int(year), int(month))[1],
        "sections": sections,
        "selected_section": section_id,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/reports/monthly.html", context)


# ==================== API Endpoints (JSON) ====================

@router.get("/api/sections/{section_id}/students")
async def get_section_students(
    section_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """الحصول على طلاب مجموعة معينة (AJAX)."""
    students = StudentService(db).get_by_section(section_id, is_active=True)
    
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


@router.get("/api/attendance/student/{student_id}")
async def get_student_attendance_api(
    student_id: str,
    date_from: str = Query(..., description="تاريخ البداية"),
    date_to: str = Query(..., description="تاريخ النهاية"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """الحصول على سجلات حضور طالب (API)."""
    service = AttendanceService(db)
    
    params = AttendanceQueryParams(
        student_id=student_id,
        date_from=date_from,
        date_to=date_to,
    )
    
    records, total = service.get_student_attendance(params=params)
    
    return {
        "total": total,
        "records": [
            {
                "id": r.id,
                "date": r.date,
                "status": r.status,
                "note": r.note,
            }
            for r in records
        ]
    }
