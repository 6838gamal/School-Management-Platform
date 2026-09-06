"""Web routes for attendance module with full integration with students and academics."""
from datetime import datetime
from typing import Optional
import json
import logging

from fastapi import APIRouter, Request, Form, Query, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_async_db
from app.core.auth import get_current_user, require_permission
from app.models.users import User
from app.models.students import Student
from app.models.teachers import Teacher
from app.models.academics import Section, Period, Grade, Stage, AcademicYear
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
from app.services.academic_service import AcademicService
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["Attendance"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# 1️⃣ الصفحة الرئيسية لإدارة الحضور
# ============================================================

@router.get("")
async def attendance_page(
    request: Request,
    date: Optional[str] = Query(None, description="التاريخ (YYYY-MM-DD)"),
    section_id: Optional[str] = Query(None, description="معرف المجموعة"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """الصفحة الرئيسية لإدارة الحضور."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    
    school_id = current_user.school_id
    
    # --- جلب ملخص الحضور من Attendance Service ---
    service = AttendanceService(db)
    summary = await service.student_summary(school_id, selected_date)
    
    # --- جلب الشعب من Academics Routes ---
    academic_service = AcademicService(db)
    sections = await academic_service.sections.list_by_school(school_id)
    
    # --- جلب سجلات الحضور للتاريخ المحدد ---
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


# ============================================================
# 2️⃣ قائمة حضور الطلاب (مع دعم التصفية المتدرجة)
# ============================================================

@router.get("/students")
async def student_attendance_list(
    request: Request,
    date: Optional[str] = Query(None, description="التاريخ (YYYY-MM-DD)"),
    year_id: Optional[str] = Query(None, description="معرف السنة الدراسية"),
    stage_id: Optional[str] = Query(None, description="معرف المرحلة"),
    grade_id: Optional[str] = Query(None, description="معرف الصف"),
    section_id: Optional[str] = Query(None, description="معرف الشعبة"),
    period_id: Optional[str] = Query(None, description="معرف الحصة"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """عرض قائمة حضور الطلاب مع دعم التصفية المتدرجة."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    school_id = current_user.school_id
    
    # --- جلب الخدمات ---
    service = AttendanceService(db)
    academic_service = AcademicService(db)
    
    # --- جلب جميع البيانات للقوائم المنسدلة ---
    # 1. السنوات الدراسية
    years = await academic_service.years.list_by_school(school_id)
    
    # 2. جميع المراحل (للحالة عندما لا يكون هناك سنة محددة)
    all_stages = await academic_service.stages.list_by_school(school_id)
    
    # 3. جميع الصفوف
    all_grades = await academic_service.grades.list_by_school(school_id)
    
    # 4. جميع الشعب
    all_sections = await academic_service.sections.list_by_school(school_id)
    
    # --- التصفية المتدرجة ---
    # تحديد المراحل حسب السنة المحددة
    stages = []
    if year_id:
        stages = await academic_service.stages.list_by_school_and_year(school_id, year_id)
    else:
        stages = all_stages
    
    # تحديد الصفوف حسب السنة والمرحلة
    grades = []
    if year_id and stage_id:
        grades = await academic_service.grades.list_by_school_and_stage(school_id, stage_id, year_id)
    elif year_id:
        grades = await academic_service.grades.list_by_school_and_year(school_id, year_id)
    elif stage_id:
        grades = await academic_service.grades.list_by_school_and_stage(school_id, stage_id)
    else:
        grades = all_grades
    
    # تحديد الشعب حسب الصف
    sections = []
    if grade_id:
        sections = await academic_service.sections.list_by_grade(grade_id)
    elif year_id and stage_id:
        # جلب الشعب حسب السنة والمرحلة
        sections = await academic_service.sections.list_by_school_year_stage(school_id, year_id, stage_id)
    elif year_id:
        sections = await academic_service.sections.list_by_school_and_year(school_id, year_id)
    else:
        sections = all_sections
    
    # --- جلب سجلات الحضور ---
    records = []
    section_name = None
    
    if section_id:
        # جلب سجلات الشعبة المحددة
        records = await service.section_attendance(section_id, selected_date)
        
        # جلب اسم الشعبة
        section = await academic_service.sections.get_by_id(section_id)
        if section:
            section_name = section.name
    elif grade_id:
        # جلب جميع الشعب في الصف المحدد
        grade_sections = await academic_service.sections.list_by_grade(grade_id)
        for sec in grade_sections:
            sec_records = await service.section_attendance(sec.id, selected_date)
            records.extend(sec_records)
    elif stage_id:
        # جلب جميع الصفوف في المرحلة ثم شعبها
        stage_grades = await academic_service.grades.list_by_school_and_stage(school_id, stage_id)
        for grade in stage_grades:
            grade_sections = await academic_service.sections.list_by_grade(grade.id)
            for sec in grade_sections:
                sec_records = await service.section_attendance(sec.id, selected_date)
                records.extend(sec_records)
    elif year_id:
        # جلب كل شيء حسب السنة
        year_stages = await academic_service.stages.list_by_school_and_year(school_id, year_id)
        for stage in year_stages:
            stage_grades = await academic_service.grades.list_by_school_and_stage(school_id, stage.id)
            for grade in stage_grades:
                grade_sections = await academic_service.sections.list_by_grade(grade.id)
                for sec in grade_sections:
                    sec_records = await service.section_attendance(sec.id, selected_date)
                    records.extend(sec_records)
    
    # --- جلب ملخص الحضور ---
    summary = await service.student_summary(school_id, selected_date)
    
    # --- تجهيز السياق للقالب ---
    context = {
        "request": request,
        "records": records,
        "summary": summary,
        "years": years,
        "stages": stages,
        "grades": grades,
        "sections": sections,
        "all_stages": all_stages,
        "all_grades": all_grades,
        "all_sections": all_sections,
        "selected_date": selected_date,
        "selected_year": year_id,
        "selected_stage": stage_id,
        "selected_grade": grade_id,
        "selected_section": section_id,
        "section_name": section_name,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/students/list.html", context)


# ============================================================
# 3️⃣ نموذج إضافة حضور طلاب (مع دعم التصفية المتدرجة)
# ============================================================

@router.get("/students/new")
async def student_attendance_create_form(
    request: Request,
    section_id: Optional[str] = Query(None, description="معرف الشعبة"),
    year_id: Optional[str] = Query(None, description="معرف السنة الدراسية"),
    stage_id: Optional[str] = Query(None, description="معرف المرحلة"),
    grade_id: Optional[str] = Query(None, description="معرف الصف"),
    period_id: Optional[str] = Query(None, description="معرف الحصة"),
    date: Optional[str] = Query(None, description="التاريخ"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """عرض نموذج إضافة حضور طلاب مع دعم التصفية المتدرجة."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    school_id = current_user.school_id
    
    # --- جلب الخدمات ---
    academic_service = AcademicService(db)
    
    # --- جلب جميع البيانات للقوائم المنسدلة ---
    years = await academic_service.years.list_by_school(school_id)
    
    # جميع المراحل (للحالة عندما لا يكون هناك سنة محددة)
    all_stages = await academic_service.stages.list_by_school(school_id)
    
    # جميع الصفوف
    all_grades = await academic_service.grades.list_by_school(school_id)
    
    # جميع الشعب
    all_sections = await academic_service.sections.list_by_school(school_id)
    
    # --- التصفية المتدرجة ---
    # تحديد المراحل حسب السنة المحددة
    stages = []
    if year_id:
        stages = await academic_service.stages.list_by_school_and_year(school_id, year_id)
    else:
        stages = all_stages
    
    # تحديد الصفوف حسب السنة والمرحلة
    grades = []
    if year_id and stage_id:
        grades = await academic_service.grades.list_by_school_and_stage(school_id, stage_id, year_id)
    elif year_id:
        grades = await academic_service.grades.list_by_school_and_year(school_id, year_id)
    elif stage_id:
        grades = await academic_service.grades.list_by_school_and_stage(school_id, stage_id)
    else:
        grades = all_grades
    
    # تحديد الشعب حسب الصف
    sections = []
    if grade_id:
        sections = await academic_service.sections.list_by_grade(grade_id)
    elif year_id and stage_id:
        sections = await academic_service.sections.list_by_school_year_stage(school_id, year_id, stage_id)
    elif year_id:
        sections = await academic_service.sections.list_by_school_and_year(school_id, year_id)
    else:
        sections = all_sections
    
    # --- جلب الطلاب ---
    students = []
    section_name = None
    grade_name = None
    stage_name = None
    year_name = None
    
    if section_id:
        # جلب تفاصيل الشعبة
        section = await academic_service.sections.get_by_id(section_id)
        if section:
            section_name = section.name
            if section.grade:
                grade_name = section.grade.name
                if section.grade.stage:
                    stage_name = section.grade.stage.name
                if section.grade.year:
                    year_name = section.grade.year.name
        
        # جلب الطلاب مع حالة الحضور
        student_service = StudentService(db)
        students = await student_service.get_students_with_details(
            school_id=school_id,
            section_id=section_id,
            is_active=True,
            include_attendance=True,
            date=selected_date,
            period_id=period_id,
        )
    
    context = {
        "request": request,
        "years": years,
        "stages": stages,
        "grades": grades,
        "sections": sections,
        "all_stages": all_stages,
        "all_grades": all_grades,
        "all_sections": all_sections,
        "students": students,
        "selected_year": year_id,
        "selected_stage": stage_id,
        "selected_grade": grade_id,
        "selected_section": section_id,
        "selected_period": period_id,
        "selected_date": selected_date,
        "section_name": section_name,
        "grade_name": grade_name,
        "stage_name": stage_name,
        "year_name": year_name,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/students/form.html", context)


# ============================================================
# 4️⃣ تسجيل حضور الطلاب (دفعة واحدة مع التحقق الكامل)
# ============================================================

@router.post("/students")
async def student_attendance_create(
    request: Request,
    date: str = Form(...),
    section_id: str = Form(...),
    period_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    """إنشاء حضور طلاب (دفعة واحدة) مع التحقق من البيانات من Students و Academics."""
    
    try:
        # 1. جلب جميع الحقول المرسلة من النموذج
        form_data = await request.form()
        
        # 2. تجميع بيانات الحضور لكل طالب
        records = []
        for key, value in form_data.items():
            if key.startswith("status_"):
                student_id = key.replace("status_", "")
                status = value
                
                # جلب الملاحظة إذا وجدت
                note_key = f"note_{student_id}"
                note = form_data.get(note_key)
                
                records.append({
                    "student_id": student_id,
                    "status": status,
                    "note": note,
                })
        
        # 3. التحقق من وجود طلاب
        if not records:
            raise ValueError("لم يتم تحديد أي طالب لتسجيل الحضور")
        
        # 4. التحقق من صحة البيانات قبل الحفظ باستخدام Students Routes
        student_service = StudentService(db)
        for record in records:
            # التحقق من وجود الطالب
            student = await student_service.get_student(record["student_id"])
            if not student:
                raise ValidationException(f"الطالب غير موجود")
            
            # التحقق من أن الطالب ينتمي إلى نفس المدرسة
            if student.school_id != current_user.school_id:
                raise ValidationException(f"الطالب {student.full_name} لا ينتمي إلى مدرستك")
            
            # التحقق من أن الطالب نشط
            if not student.is_active:
                raise ValidationException(f"الطالب {student.full_name} غير نشط")
            
            # التحقق من أن الطالب في الشعبة المحددة
            if student.section_id != section_id:
                raise ValidationException(f"الطالب {student.full_name} ليس في هذه الشعبة")
        
        # 5. التحقق من وجود الشعبة في Academics Routes
        academic_service = AcademicService(db)
        section = await academic_service.sections.get_by_id(section_id)
        if not section:
            raise ValidationException("الشعبة غير موجودة")
        
        if section.school_id != current_user.school_id:
            raise ValidationException("الشعبة لا تنتمي إلى مدرستك")
        
        # 6. التحقق من وجود الحصة إذا تم تحديدها
        if period_id:
            period = await db.get(Period, period_id)
            if not period:
                raise ValidationException("الحصة غير موجودة")
            if period.school_id != current_user.school_id:
                raise ValidationException("الحصة لا تنتمي إلى مدرستك")
        
        # 7. حفظ الحضور
        service = AttendanceService(db)
        batch_data = StudentAttendanceBatch(
            date=date,
            section_id=section_id,
            period_id=period_id,
            records=records,
        )
        
        result = await service.batch_record(
            school_id=current_user.school_id,
            user_id=current_user.id,
            req=batch_data,
        )
        
        # 8. إعادة التوجيه مع رسالة نجاح
        return RedirectResponse(
            f"/attendance/students?date={date}&section_id={section_id}&success=true",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        return await _render_attendance_form_with_error(
            request, db, current_user, date, section_id, period_id, str(e)
        )
    except Exception as e:
        logger.error(f"Error creating student attendance: {e}", exc_info=True)
        return await _render_attendance_form_with_error(
            request, db, current_user, date, section_id, period_id, f"حدث خطأ: {str(e)}"
        )


async def _render_attendance_form_with_error(
    request: Request,
    db: AsyncSession,
    current_user: User,
    date: str,
    section_id: str,
    period_id: Optional[str],
    error_message: str,
):
    """دالة مساعدة لعرض نموذج الحضور مع رسالة خطأ."""
    today = datetime.now().strftime("%Y-%m-%d")
    school_id = current_user.school_id
    
    # جلب البيانات لعرض النموذج مرة أخرى
    academic_service = AcademicService(db)
    
    years = await academic_service.years.list_by_school(school_id)
    all_stages = await academic_service.stages.list_by_school(school_id)
    all_grades = await academic_service.grades.list_by_school(school_id)
    all_sections = await academic_service.sections.list_by_school(school_id)
    
    # جلب تفاصيل الشعبة
    section = await academic_service.sections.get_by_id(section_id)
    section_name = section.name if section else None
    
    # جلب الطلاب
    student_service = StudentService(db)
    students = await student_service.get_students_with_details(
        school_id=school_id,
        section_id=section_id,
        is_active=True,
        include_attendance=True,
        date=date,
        period_id=period_id,
    )
    
    return templates.TemplateResponse(
        "attendance/students/form.html",
        {
            "request": request,
            "error": error_message,
            "years": years,
            "stages": all_stages,
            "grades": all_grades,
            "sections": all_sections,
            "all_stages": all_stages,
            "all_grades": all_grades,
            "all_sections": all_sections,
            "students": students,
            "selected_date": date,
            "selected_section": section_id,
            "selected_period": period_id,
            "section_name": section_name,
            "today": today,
            "can": lambda p: current_user.has_permission(p),
        },
        status_code=400,
    )


# ============================================================
# 5️⃣ تسجيل حضور طالب سريع (AJAX)
# ============================================================

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
    """تسجيل حضور طالب سريع (AJAX) مع التحقق من البيانات."""
    try:
        # --- التحقق من وجود الطالب من Students Routes ---
        student_service = StudentService(db)
        student = await student_service.get_student(student_id)
        if not student:
            return {"success": False, "message": "الطالب غير موجود"}
        
        if student.school_id != current_user.school_id:
            return {"success": False, "message": "الطالب لا ينتمي إلى مدرستك"}
        
        if not student.is_active:
            return {"success": False, "message": "الطالب غير نشط"}
        
        # --- التحقق من وجود الشعبة من Academics Routes ---
        if section_id:
            academic_service = AcademicService(db)
            section = await academic_service.sections.get_by_id(section_id)
            if not section:
                return {"success": False, "message": "الشعبة غير موجودة"}
        
        # --- تسجيل الحضور ---
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
            "student": {
                "id": student.id,
                "full_name": student.full_name,
                "student_number": student.student_number,
            }
        }
        
    except Exception as e:
        logger.error(f"Error in quick attendance: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================
# 6️⃣ التحقق من حضور طالب
# ============================================================

@router.get("/students/check")
async def check_student_attendance(
    student_id: str = Query(...),
    date: str = Query(...),
    period_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """التحقق من وجود سجل حضور لطالب في تاريخ معين."""
    # --- التحقق من وجود الطالب من Students Routes ---
    student_service = StudentService(db)
    student = await student_service.get_student(student_id)
    if not student:
        return {"exists": False, "message": "الطالب غير موجود"}
    
    if student.school_id != current_user.school_id:
        return {"exists": False, "message": "الطالب لا ينتمي إلى مدرستك"}
    
    # --- التحقق من الحضور ---
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
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "student_number": student.student_number,
        }
    }


# ============================================================
# 7️⃣ قائمة حضور المعلمين
# ============================================================

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
    
    # جلب المعلمين الغائبين
    absent_teachers = await service.absent_teachers(school_id, selected_date)
    
    # جلب جميع المعلمين
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


# ============================================================
# 8️⃣ نموذج إضافة حضور معلمين
# ============================================================

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
    
    # جلب جميع المعلمين النشطين
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


# ============================================================
# 9️⃣ تسجيل حضور معلم
# ============================================================

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
    """إنشاء حضور معلم مع التحقق من البيانات."""
    try:
        # --- التحقق من وجود المعلم ---
        teacher_service = TeacherService(db)
        teacher = await teacher_service.get_teacher(teacher_id)
        if not teacher:
            raise ValidationException("المعلم غير موجود")
        
        if teacher.school_id != current_user.school_id:
            raise ValidationException("المعلم لا ينتمي إلى مدرستك")
        
        if not teacher.is_active:
            raise ValidationException("المعلم غير نشط")
        
        # --- تسجيل الحضور ---
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
            f"/attendance/teachers?date={date}&success=true",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
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
    except Exception as e:
        logger.error(f"Error creating teacher attendance: {e}", exc_info=True)
        teacher_service = TeacherService(db)
        teachers = await teacher_service.get_all(current_user.school_id, is_active=True)
        
        return templates.TemplateResponse(
            "attendance/teachers/form.html",
            {
                "request": request,
                "teachers": teachers,
                "error": f"حدث خطأ: {str(e)}",
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


# ============================================================
# 🔟 تقرير الحضور اليومي (مدمج مع Students و Academics)
# ============================================================

@router.get("/reports/daily")
async def attendance_daily_report(
    request: Request,
    date: Optional[str] = Query(None),
    year_id: Optional[str] = Query(None, description="معرف السنة الدراسية"),
    stage_id: Optional[str] = Query(None, description="معرف المرحلة"),
    grade_id: Optional[str] = Query(None, description="معرف الصف"),
    section_id: Optional[str] = Query(None, description="معرف الشعبة"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.view_reports")),
):
    """تقرير الحضور اليومي مع تفاصيل من Students و Academics."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    school_id = current_user.school_id
    
    service = AttendanceService(db)
    academic_service = AcademicService(db)
    
    # --- جلب جميع البيانات للقوائم المنسدلة ---
    years = await academic_service.years.list_by_school(school_id)
    all_stages = await academic_service.stages.list_by_school(school_id)
    all_grades = await academic_service.grades.list_by_school(school_id)
    all_sections = await academic_service.sections.list_by_school(school_id)
    
    # --- التصفية المتدرجة ---
    stages = []
    if year_id:
        stages = await academic_service.stages.list_by_school_and_year(school_id, year_id)
    else:
        stages = all_stages
    
    grades = []
    if year_id and stage_id:
        grades = await academic_service.grades.list_by_school_and_stage(school_id, stage_id, year_id)
    elif year_id:
        grades = await academic_service.grades.list_by_school_and_year(school_id, year_id)
    elif stage_id:
        grades = await academic_service.grades.list_by_school_and_stage(school_id, stage_id)
    else:
        grades = all_grades
    
    sections = []
    if grade_id:
        sections = await academic_service.sections.list_by_grade(grade_id)
    elif year_id and stage_id:
        sections = await academic_service.sections.list_by_school_year_stage(school_id, year_id, stage_id)
    elif year_id:
        sections = await academic_service.sections.list_by_school_and_year(school_id, year_id)
    else:
        sections = all_sections
    
    # --- جلب ملخص حضور الطلاب ---
    student_summary = await service.student_summary(school_id, selected_date)
    
    # --- جلب المعلمين الغائبين ---
    teacher_summary = await service.absent_teachers(school_id, selected_date)
    
    # --- جلب تفاصيل الطلاب مع الحضور ---
    students_with_attendance = []
    if section_id:
        student_service = StudentService(db)
        students_with_attendance = await student_service.get_students_with_details(
            school_id=school_id,
            section_id=section_id,
            is_active=True,
            include_attendance=True,
            date=selected_date,
        )
    elif grade_id:
        student_service = StudentService(db)
        grade_sections = await academic_service.sections.list_by_grade(grade_id)
        for sec in grade_sections:
            sec_students = await student_service.get_students_with_details(
                school_id=school_id,
                section_id=sec.id,
                is_active=True,
                include_attendance=True,
                date=selected_date,
            )
            students_with_attendance.extend(sec_students)
    
    context = {
        "request": request,
        "date": selected_date,
        "student_summary": student_summary,
        "teacher_summary": teacher_summary,
        "years": years,
        "stages": stages,
        "grades": grades,
        "sections": sections,
        "all_stages": all_stages,
        "all_grades": all_grades,
        "all_sections": all_sections,
        "selected_year": year_id,
        "selected_stage": stage_id,
        "selected_grade": grade_id,
        "selected_section": section_id,
        "students": students_with_attendance,
        "today": today,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/reports/daily.html", context)


# ============================================================
# 1️⃣1️⃣ تقرير مفصل لطالب معين (مدمج مع Students)
# ============================================================

@router.get("/reports/student-detail")
async def student_attendance_detail_report(
    request: Request,
    student_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.view_reports")),
):
    """تقرير مفصل لحضور طالب معين مع بياناته من Students Routes."""
    
    # --- جلب بيانات الطالب من Students Routes ---
    student_service = StudentService(db)
    try:
        student_detail = await student_service.get_student_detail(student_id)
    except NotFoundException:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "message": "الطالب غير موجود"},
            status_code=404
        )
    
    # التحقق من أن الطالب ينتمي لنفس المدرسة
    if student_detail.get("school_id") != current_user.school_id:
        return templates.TemplateResponse(
            "errors/403.html",
            {"request": request, "message": "ليس لديك صلاحية لعرض بيانات هذا الطالب"},
            status_code=403
        )
    
    # --- جلب سجلات الحضور من Attendance Routes ---
    attendance_service = AttendanceService(db)
    records = await attendance_service.get_student_attendance_history(
        student_id=student_id,
        date_from=date_from,
        date_to=date_to,
    )
    
    # --- حساب الإحصائيات ---
    total_days = len(records)
    present = sum(1 for r in records if r.status == "present")
    absent = sum(1 for r in records if r.status == "absent")
    late = sum(1 for r in records if r.status == "late")
    excused = sum(1 for r in records if r.status == "excused")
    
    attendance_percentage = round((present / total_days) * 100, 2) if total_days > 0 else 0
    
    context = {
        "request": request,
        "student": student_detail,
        "records": records,
        "total_days": total_days,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "attendance_percentage": attendance_percentage,
        "date_from": date_from,
        "date_to": date_to,
        "can": lambda p: current_user.has_permission(p),
    }
    
    return templates.TemplateResponse("attendance/reports/student_detail.html", context)


# ============================================================
# 1️⃣2️⃣ API: جلب طلاب شعبة مع تفاصيلهم (AJAX)
# ============================================================

@router.get("/api/sections/{section_id}/students")
async def get_section_students_with_details(
    section_id: str,
    date: Optional[str] = Query(None),
    period_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """الحصول على طلاب مجموعة معينة مع تفاصيلهم من Students و Academics (AJAX)."""
    
    # --- التحقق من وجود الشعبة من Academics Routes ---
    academic_service = AcademicService(db)
    section = await academic_service.sections.get_by_id(section_id)
    if not section:
        return {"success": False, "message": "الشعبة غير موجودة"}
    
    if section.school_id != current_user.school_id:
        return {"success": False, "message": "الشعبة لا تنتمي إلى مدرستك"}
    
    # --- جلب الطلاب مع تفاصيلهم من Students Routes ---
    student_service = StudentService(db)
    students = await student_service.get_students_with_details(
        school_id=current_user.school_id,
        section_id=section_id,
        is_active=True,
        include_attendance=True,
        date=date or datetime.now().strftime("%Y-%m-%d"),
        period_id=period_id,
    )
    
    return {
        "success": True,
        "section": {
            "id": section.id,
            "name": section.name,
            "grade_name": section.grade.name if section.grade else None,
            "stage_name": section.grade.stage.name if section.grade and section.grade.stage else None,
        },
        "students": students,
        "count": len(students),
    }


# ============================================================
# 1️⃣3️⃣ API: جلب جميع الشعب مع تفاصيلها (AJAX)
# ============================================================

@router.get("/api/sections")
async def get_sections_with_details(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """الحصول على جميع الشعب مع تفاصيلها من Academics Routes (AJAX)."""
    
    # --- جلب الشعب من Academics Routes ---
    academic_service = AcademicService(db)
    sections = await academic_service.sections.list_by_school(current_user.school_id)
    
    # --- جلب تفاصيل إضافية لكل شعبة ---
    result = []
    for section in sections:
        # حساب عدد الطلاب في الشعبة
        student_count = await db.query(Student).filter(
            Student.section_id == section.id,
            Student.is_active == True,
            Student.school_id == current_user.school_id
        ).count()
        
        result.append({
            "id": section.id,
            "name": section.name,
            "grade_name": section.grade.name if section.grade else None,
            "stage_name": section.grade.stage.name if section.grade and section.grade.stage else None,
            "academic_year": section.academic_year.name if section.academic_year else None,
            "student_count": student_count,
            "is_active": section.is_active,
        })
    
    return {
        "success": True,
        "sections": result,
        "count": len(result),
    }


# ============================================================
# 1️⃣4️⃣ API: إحصائيات الحضور (مدمجة)
# ============================================================

@router.get("/api/stats")
async def attendance_stats(
    date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("attendance.view_reports")),
):
    """الحصول على إحصائيات الحضور مدمجة مع بيانات Students و Academics."""
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = date or today
    school_id = current_user.school_id
    
    service = AttendanceService(db)
    academic_service = AcademicService(db)
    
    # --- إحصائيات الطلاب ---
    student_summary = await service.student_summary(school_id, selected_date)
    
    # --- جلب عدد الطلاب الكلي من Students Routes ---
    student_service = StudentService(db)
    total_students = await student_service.count_students(school_id, is_active=True)
    
    # --- إحصائيات المعلمين ---
    teacher_summary = await service.absent_teachers(school_id, selected_date)
    
    # --- جلب عدد المعلمين الكلي ---
    teacher_service = TeacherService(db)
    total_teachers = await teacher_service.count_teachers(school_id, is_active=True)
    
    # --- جلب الشعب من Academics Routes ---
    sections = await academic_service.sections.list_by_school(school_id)
    
    # --- حساب نسبة الحضور لكل شعبة ---
    section_attendance = []
    for section in sections:
        section_students = await student_service.count_students(
            school_id, 
            section_id=section.id,
            is_active=True
        )
        
        if section_students > 0:
            # جلب حضور هذه الشعبة
            section_records = await service.section_attendance(section.id, selected_date)
            present_count = sum(1 for r in section_records if r.status == "present")
            percentage = round((present_count / section_students) * 100, 2)
        else:
            percentage = 0
        
        section_attendance.append({
            "section_id": section.id,
            "section_name": section.name,
            "grade_name": section.grade.name if section.grade else None,
            "total_students": section_students,
            "attendance_percentage": percentage,
        })
    
    return {
        "success": True,
        "date": selected_date,
        "students": {
            "total": total_students,
            "present": student_summary.get("present", 0) if student_summary else 0,
            "absent": student_summary.get("absent", 0) if student_summary else 0,
            "late": student_summary.get("late", 0) if student_summary else 0,
            "excused": student_summary.get("excused", 0) if student_summary else 0,
            "percentage": student_summary.get("percentage", 0) if student_summary else 0,
        },
        "teachers": {
            "total": total_teachers,
            "absent": len(teacher_summary) if teacher_summary else 0,
        },
        "sections": section_attendance,
    }
