"""Attendance web routes with full academic hierarchy support - Manual queries only."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List, Dict, Any
import uuid
import traceback
import json
import re
from datetime import datetime, date

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.attendance_service import AttendanceService
from app.core.exceptions import NotFoundException, AppException, ValidationException

# ============================================================
# استيراد الـ Schemas
# ============================================================
from app.schemas.attendance import (
    StudentAttendanceCreate,
    StudentAttendanceBatch,
    StudentAttendanceStatus,
    TeacherAttendanceCreate,
    TeacherAttendanceStatus,
    AttendanceFilter,
    AttendanceSummary,
)

# النماذج
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.models.academics import Section, Subject, Grade, Stage, AcademicYear
from app.models.students import Student
from app.models.teachers import Teacher
from app.models.users import User

router = APIRouter(prefix="/attendance", tags=["attendance"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# دوال مساعدة للبحث اليدوي (بدون علاقات)
# ============================================================

async def get_grade_by_id(db: AsyncSession, grade_id: str) -> Optional[Grade]:
    """جلب الصف بالمعرف - بحث يدوي"""
    try:
        if not grade_id:
            return None
        result = await db.execute(
            select(Grade).where(Grade.id == grade_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        print(f"⚠️ Error in get_grade_by_id: {str(e)}")
        return None


async def get_stage_by_id(db: AsyncSession, stage_id: str) -> Optional[Stage]:
    """جلب المرحلة بالمعرف - بحث يدوي"""
    try:
        if not stage_id:
            return None
        result = await db.execute(
            select(Stage).where(Stage.id == stage_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        print(f"⚠️ Error in get_stage_by_id: {str(e)}")
        return None


async def get_academic_year_by_id(db: AsyncSession, year_id: str) -> Optional[AcademicYear]:
    """جلب السنة الدراسية بالمعرف - بحث يدوي"""
    try:
        if not year_id:
            return None
        result = await db.execute(
            select(AcademicYear).where(AcademicYear.id == year_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        print(f"⚠️ Error in get_academic_year_by_id: {str(e)}")
        return None


async def get_sections_with_details(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب الشعب مع تفاصيلها (الصف والمرحلة والسنة) - بحث يدوي"""
    try:
        # 1. جلب جميع الشعب
        result = await db.execute(
            select(Section)
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.grade_id, Section.name)
        )
        sections = result.scalars().all()
        
        sections_data = []
        for section in sections:
            # 2. جلب الصف يدوياً
            grade = None
            grade_name = "غير محدد"
            stage_name = "غير محدد"
            year_name = "غير محدد"
            year_id = None
            
            if section.grade_id:
                grade = await get_grade_by_id(db, section.grade_id)
                if grade:
                    grade_name = grade.name
                    year_id = grade.year_id
                    
                    # 3. جلب المرحلة يدوياً
                    if grade.stage_id:
                        stage = await get_stage_by_id(db, grade.stage_id)
                        if stage:
                            stage_name = stage.name
                    
                    # 4. جلب السنة يدوياً
                    if grade.year_id:
                        year = await get_academic_year_by_id(db, grade.year_id)
                        if year:
                            year_name = year.name
            
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "grade_name": grade_name,
                "stage_name": stage_name,
                "year_id": str(year_id) if year_id else None,
                "year_name": year_name,
                "display_name": f"{stage_name} - {grade_name} - {section.name}",
                "capacity": section.capacity,
                "is_active": section.is_active
            })
        
        return sections_data
    except Exception as e:
        print(f"⚠️ Error in get_sections_with_details: {str(e)}")
        traceback.print_exc()
        return []


async def get_academic_years(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب السنوات الدراسية - بحث يدوي"""
    try:
        result = await db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .where(AcademicYear.is_active == True)
            .order_by(AcademicYear.start_date.desc())
        )
        years = result.scalars().all()
        
        return [
            {
                "id": str(year.id),
                "name": year.name,
                "start_date": year.start_date,
                "end_date": year.end_date,
                "is_current": year.is_current,
                "is_active": year.is_active
            }
            for year in years
        ]
    except Exception as e:
        print(f"⚠️ Error in get_academic_years: {str(e)}")
        return []


async def get_stages(db: AsyncSession, school_id: str, year_id: Optional[str] = None) -> List[Dict]:
    """جلب المراحل حسب السنة الدراسية - بحث يدوي"""
    try:
        stmt = select(Stage).where(Stage.school_id == school_id)
        if year_id:
            stmt = stmt.where(Stage.year_id == year_id)
        stmt = stmt.order_by(Stage.order)
        
        result = await db.execute(stmt)
        stages = result.scalars().all()
        
        return [
            {
                "id": str(stage.id),
                "name": stage.name,
                "name_en": stage.name_en,
                "year_id": str(stage.year_id) if stage.year_id else None,
                "order": stage.order,
                "is_active": getattr(stage, 'is_active', True)
            }
            for stage in stages
        ]
    except Exception as e:
        print(f"⚠️ Error in get_stages: {str(e)}")
        return []


async def get_grades(db: AsyncSession, school_id: str, stage_id: Optional[str] = None, year_id: Optional[str] = None) -> List[Dict]:
    """جلب الصفوف حسب المرحلة والسنة - بحث يدوي"""
    try:
        stmt = select(Grade).where(
            Grade.school_id == school_id,
            Grade.is_active == True
        )
        if stage_id:
            stmt = stmt.where(Grade.stage_id == stage_id)
        if year_id:
            stmt = stmt.where(Grade.year_id == year_id)
        stmt = stmt.order_by(Grade.order)
        
        result = await db.execute(stmt)
        grades = result.scalars().all()
        
        return [
            {
                "id": str(grade.id),
                "name": grade.name,
                "name_en": grade.name_en,
                "stage_id": str(grade.stage_id) if grade.stage_id else None,
                "year_id": str(grade.year_id) if grade.year_id else None,
                "order": grade.order,
                "is_active": grade.is_active
            }
            for grade in grades
        ]
    except Exception as e:
        print(f"⚠️ Error in get_grades: {str(e)}")
        return []


async def get_students_with_attendance(
    db: AsyncSession, 
    school_id: str, 
    section_id: Optional[str] = None,
    date: Optional[str] = None,
    period_id: Optional[str] = None
) -> List[Dict]:
    """جلب الطلاب مع حالة الحضور - بحث يدوي"""
    try:
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        )
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
        stmt = stmt.order_by(Student.first_name, Student.last_name)
        
        result = await db.execute(stmt)
        students = result.scalars().all()
        
        students_data = []
        for student in students:
            student_dict = {
                "id": str(student.id),
                "student_number": student.student_number,
                "full_name": student.full_name,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "section_id": str(student.section_id) if student.section_id else None,
                "grade_id": str(student.grade_id) if student.grade_id else None,
                "stage_id": str(student.stage_id) if student.stage_id else None,
                "year_id": str(student.year_id) if student.year_id else None,
                "attendance_status": None,
                "attendance_id": None,
                "attendance_note": None,
                "has_attendance": False,
            }
            
            # جلب حالة الحضور إذا كان التاريخ محدداً
            if date:
                att_stmt = select(StudentAttendance).where(
                    StudentAttendance.student_id == student.id,
                    StudentAttendance.date == date
                )
                if period_id:
                    att_stmt = att_stmt.where(StudentAttendance.period_id == period_id)
                
                att_result = await db.execute(att_stmt)
                attendance = att_result.scalar_one_or_none()
                
                if attendance:
                    student_dict["attendance_status"] = attendance.status
                    student_dict["attendance_id"] = str(attendance.id)
                    student_dict["attendance_note"] = attendance.note
                    student_dict["has_attendance"] = True
            
            students_data.append(student_dict)
        
        return students_data
    except Exception as e:
        print(f"⚠️ Error in get_students_with_attendance: {str(e)}")
        traceback.print_exc()
        return []


async def get_attendance_summary(
    db: AsyncSession, 
    school_id: str, 
    date: str,
    section_id: Optional[str] = None
) -> Dict:
    """جلب ملخص الحضور - بحث يدوي"""
    try:
        stmt = select(StudentAttendance).where(
            StudentAttendance.school_id == school_id,
            StudentAttendance.date == date
        )
        if section_id:
            stmt = stmt.where(StudentAttendance.section_id == section_id)
        
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        total = len(records)
        present = sum(1 for r in records if r.status == "present")
        absent = sum(1 for r in records if r.status == "absent")
        late = sum(1 for r in records if r.status == "late")
        excused = sum(1 for r in records if r.status == "excused")
        
        # جلب إجمالي الطلاب في الشعبة
        total_students = 0
        if section_id:
            student_stmt = select(func.count(Student.id)).where(
                Student.school_id == school_id,
                Student.section_id == section_id,
                Student.is_active == True
            )
            total_students = await db.scalar(student_stmt) or 0
        
        return {
            "total": total_students or total,
            "present": present,
            "absent": absent,
            "late": late,
            "excused": excused,
            "rate": round((present / total_students * 100) if total_students > 0 else 0, 1)
        }
    except Exception as e:
        print(f"⚠️ Error in get_attendance_summary: {str(e)}")
        return {"total": 0, "present": 0, "absent": 0, "late": 0, "excused": 0, "rate": 0}


async def get_attendance_records_with_details(
    db: AsyncSession,
    school_id: str,
    date: str,
    section_id: Optional[str] = None,
    period_id: Optional[str] = None
) -> List[Dict]:
    """جلب سجلات الحضور مع تفاصيل الطالب - بحث يدوي"""
    try:
        stmt = select(StudentAttendance).where(
            StudentAttendance.school_id == school_id,
            StudentAttendance.date == date
        )
        if section_id:
            stmt = stmt.where(StudentAttendance.section_id == section_id)
        if period_id:
            stmt = stmt.where(StudentAttendance.period_id == period_id)
        
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        records_data = []
        for record in records:
            # جلب الطالب يدوياً
            student = None
            student_name = "غير معروف"
            student_number = ""
            
            if record.student_id:
                student_result = await db.execute(
                    select(Student).where(Student.id == record.student_id)
                )
                student = student_result.scalar_one_or_none()
                if student:
                    student_name = student.full_name
                    student_number = student.student_number
            
            # جلب الشعبة يدوياً
            section_name = None
            if record.section_id:
                section_result = await db.execute(
                    select(Section).where(Section.id == record.section_id)
                )
                section = section_result.scalar_one_or_none()
                if section:
                    section_name = section.name
            
            # جلب الصف يدوياً
            grade_name = None
            if record.grade_id:
                grade = await get_grade_by_id(db, record.grade_id)
                if grade:
                    grade_name = grade.name
            
            # جلب المرحلة يدوياً
            stage_name = None
            if record.stage_id:
                stage = await get_stage_by_id(db, record.stage_id)
                if stage:
                    stage_name = stage.name
            
            # جلب السنة يدوياً
            year_name = None
            if record.year_id:
                year = await get_academic_year_by_id(db, record.year_id)
                if year:
                    year_name = year.name
            
            records_data.append({
                "id": str(record.id),
                "student_id": str(record.student_id),
                "student_name": student_name,
                "student_number": student_number,
                "section_id": str(record.section_id) if record.section_id else None,
                "section_name": section_name,
                "grade_id": str(record.grade_id) if record.grade_id else None,
                "grade_name": grade_name,
                "stage_id": str(record.stage_id) if record.stage_id else None,
                "stage_name": stage_name,
                "year_id": str(record.year_id) if record.year_id else None,
                "year_name": year_name,
                "date": record.date,
                "status": record.status,
                "status_arabic": StudentAttendanceStatus.get_arabic_name(record.status) if hasattr(StudentAttendanceStatus, 'get_arabic_name') else record.status,
                "note": record.note,
                "recorded_by": str(record.recorded_by) if record.recorded_by else None,
            })
        
        return records_data
    except Exception as e:
        print(f"⚠️ Error in get_attendance_records_with_details: {str(e)}")
        traceback.print_exc()
        return []


# ============================================================
# 1️⃣ الصفحة الرئيسية للحضور
# ============================================================

@router.get("")
async def attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """الصفحة الرئيسية للحضور"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # جلب البيانات - بحث يدوي
        years = await get_academic_years(db, user.school_id)
        sections = await get_sections_with_details(db, user.school_id)
        
        return templates.TemplateResponse(
            "attendance/index.html",
            {
                **ctx,
                "title": "الحضور والغياب",
                "years": years,
                "sections": sections,
                "today": today,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in attendance_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/index.html",
            {
                **ctx,
                "title": "الحضور والغياب",
                "years": [],
                "sections": [],
                "today": datetime.now().strftime("%Y-%m-%d"),
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 2️⃣ قائمة حضور الطلاب (مع التصفية المتدرجة)
# ============================================================

@router.get("/students")
async def student_attendance_list(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    date: Optional[str] = None,
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
    section_id: Optional[str] = None,
    period_id: Optional[str] = None,
):
    """عرض قائمة حضور الطلاب مع التصفية المتدرجة - بحث يدوي"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        print("=" * 50)
        print("📊 صفحة حضور الطلاب")
        print(f"   date: {selected_date}")
        print(f"   year_id: {year_id}")
        print(f"   stage_id: {stage_id}")
        print(f"   grade_id: {grade_id}")
        print(f"   section_id: {section_id}")
        print("=" * 50)
        
        # جلب جميع البيانات للقوائم - بحث يدوي
        years = await get_academic_years(db, user.school_id)
        stages = await get_stages(db, user.school_id, year_id)
        grades = await get_grades(db, user.school_id, stage_id, year_id)
        sections = await get_sections_with_details(db, user.school_id)
        
        # جلب سجلات الحضور
        records = []
        summary = {"total": 0, "present": 0, "absent": 0, "late": 0, "excused": 0, "rate": 0}
        
        if section_id:
            # جلب سجلات الحضور مع التفاصيل - بحث يدوي
            records = await get_attendance_records_with_details(
                db, user.school_id, selected_date, section_id, period_id
            )
            
            # جلب ملخص الحضور
            summary = await get_attendance_summary(db, user.school_id, selected_date, section_id)
        
        return templates.TemplateResponse(
            "attendance/students/list.html",
            {
                **ctx,
                "title": "حضور الطلاب",
                "records": records,
                "summary": summary,
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
                "selected_date": selected_date,
                "selected_year": year_id,
                "selected_stage": stage_id,
                "selected_grade": grade_id,
                "selected_section": section_id,
                "selected_period": period_id,
                "today": today,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in student_attendance_list: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/students/list.html",
            {
                **ctx,
                "title": "حضور الطلاب",
                "records": [],
                "summary": {"total": 0, "present": 0, "absent": 0, "late": 0, "excused": 0, "rate": 0},
                "years": [],
                "stages": [],
                "grades": [],
                "sections": [],
                "selected_date": datetime.now().strftime("%Y-%m-%d"),
                "selected_year": None,
                "selected_stage": None,
                "selected_grade": None,
                "selected_section": None,
                "selected_period": None,
                "today": datetime.now().strftime("%Y-%m-%d"),
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 3️⃣ نموذج تسجيل حضور الطلاب
# ============================================================

@router.get("/students/create")
async def create_student_attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    section_id: Optional[str] = None,
    date: Optional[str] = None,
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
    period_id: Optional[str] = None,
):
    """صفحة تسجيل حضور الطلاب - بحث يدوي"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        print("=" * 50)
        print("📝 صفحة تسجيل حضور الطلاب")
        print(f"   section_id: {section_id}")
        print(f"   date: {selected_date}")
        print("=" * 50)
        
        # جلب جميع البيانات - بحث يدوي
        years = await get_academic_years(db, user.school_id)
        stages = await get_stages(db, user.school_id, year_id)
        grades = await get_grades(db, user.school_id, stage_id, year_id)
        sections = await get_sections_with_details(db, user.school_id)
        
        # جلب الطلاب
        students = []
        section_name = None
        if section_id:
            students = await get_students_with_attendance(
                db, user.school_id, section_id, selected_date, period_id
            )
            
            # جلب اسم الشعبة
            for section in sections:
                if section["id"] == section_id:
                    section_name = section["display_name"]
                    break
        
        return templates.TemplateResponse(
            "attendance/students/create.html",
            {
                **ctx,
                "title": "تسجيل حضور الطلاب",
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
                "students": students,
                "section_name": section_name,
                "selected_date": selected_date,
                "selected_section": section_id,
                "selected_year": year_id,
                "selected_stage": stage_id,
                "selected_grade": grade_id,
                "selected_period": period_id,
                "today": today,
                "statuses": [
                    {"value": "present", "label": "✅ حاضر", "color": "green"},
                    {"value": "absent", "label": "❌ غائب", "color": "red"},
                    {"value": "late", "label": "⏰ متأخر", "color": "yellow"},
                    {"value": "excused", "label": "📝 معذور", "color": "blue"},
                ],
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in create_student_attendance_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/students/create.html",
            {
                **ctx,
                "title": "تسجيل حضور الطلاب",
                "years": [],
                "stages": [],
                "grades": [],
                "sections": [],
                "students": [],
                "section_name": None,
                "selected_date": datetime.now().strftime("%Y-%m-%d"),
                "selected_section": None,
                "selected_year": None,
                "selected_stage": None,
                "selected_grade": None,
                "selected_period": None,
                "today": datetime.now().strftime("%Y-%m-%d"),
                "statuses": [],
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 4️⃣ API: تسجيل حضور الطلاب (دفعة)
# ============================================================

@router.post("/api/v1/students")
async def create_student_attendance_api(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل حضور الطلاب عبر API - يدعم JSON و FormData"""
    try:
        content_type = request.headers.get("content-type", "")
        print(f"📥 Content-Type: {content_type}")
        
        body = await request.body()
        print(f"📦 Raw body length: {len(body)}")
        
        if "application/json" in content_type:
            data = await request.json()
            date_val = data.get("date")
            section_id = data.get("section_id")
            period_id = data.get("period_id")
            records = data.get("records", [])
        else:
            form_data = await request.form()
            date_val = form_data.get("date")
            section_id = form_data.get("section_id")
            period_id = form_data.get("period_id")
            
            records = []
            for key, value in form_data.items():
                if key.startswith("status_"):
                    student_id = key.replace("status_", "")
                    status = value
                    note = form_data.get(f"note_{student_id}", "")
                    records.append({
                        "student_id": student_id,
                        "status": status,
                        "note": note
                    })
        
        if not date_val:
            return JSONResponse({"detail": "التاريخ مطلوب"}, status_code=422)
        
        if not section_id:
            return JSONResponse({"detail": "الشعبة مطلوبة"}, status_code=422)
        
        if not records:
            return JSONResponse({"detail": "يجب تحديد طالب واحد على الأقل"}, status_code=422)
        
        service = AttendanceService(db)
        
        saved_count = 0
        for record in records:
            try:
                attendance_data = StudentAttendanceCreate(
                    student_id=record["student_id"],
                    section_id=section_id,
                    period_id=period_id,
                    date=date_val,
                    status=record["status"],
                    note=record.get("note", "")
                )
                await service.record_student(
                    school_id=user.school_id,
                    user_id=user.id,
                    req=attendance_data
                )
                saved_count += 1
            except Exception as e:
                print(f"⚠️ Error saving record for student {record.get('student_id')}: {str(e)}")
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"تم تسجيل حضور {saved_count} طالب بنجاح",
            "total": len(records),
            "saved": saved_count
        }
        
    except ValidationException as e:
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=422)
    except Exception as e:
        print(f"❌ Error creating attendance: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


# ============================================================
# 5️⃣ API: تحديث حضور طالب
# ============================================================

@router.put("/api/v1/students/{attendance_id}")
async def update_student_attendance_api(
    attendance_id: str,
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.update")),
    db: AsyncSession = Depends(get_db),
):
    """تحديث سجل حضور طالب"""
    try:
        data = await request.json()
        
        result = await db.execute(
            select(StudentAttendance).where(StudentAttendance.id == attendance_id)
        )
        attendance = result.scalar_one_or_none()
        
        if not attendance:
            return JSONResponse({"detail": "سجل الحضور غير موجود"}, status_code=404)
        
        if "status" in data:
            attendance.status = data["status"]
        if "note" in data:
            attendance.note = data["note"]
        
        await db.commit()
        
        return {
            "success": True,
            "message": "تم تحديث سجل الحضور بنجاح",
            "id": attendance_id
        }
        
    except Exception as e:
        print(f"❌ Error updating attendance: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


# ============================================================
# 6️⃣ API: حذف سجل حضور
# ============================================================

@router.delete("/api/v1/students/{attendance_id}")
async def delete_student_attendance_api(
    attendance_id: str,
    user: CurrentUser = Depends(require_any_permission("attendance.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف سجل حضور طالب"""
    try:
        result = await db.execute(
            select(StudentAttendance).where(StudentAttendance.id == attendance_id)
        )
        attendance = result.scalar_one_or_none()
        
        if not attendance:
            return JSONResponse({"detail": "سجل الحضور غير موجود"}, status_code=404)
        
        await db.delete(attendance)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم حذف سجل الحضور بنجاح"
        }
        
    except Exception as e:
        print(f"❌ Error deleting attendance: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


# ============================================================
# 7️⃣ API: جلب إحصائيات الحضور
# ============================================================

@router.get("/api/v1/stats")
async def get_attendance_stats(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    date: Optional[str] = None,
    section_id: Optional[str] = None,
):
    """جلب إحصائيات الحضور"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        summary = await get_attendance_summary(db, user.school_id, selected_date, section_id)
        
        return JSONResponse({
            "success": True,
            "date": selected_date,
            "summary": summary
        })
        
    except Exception as e:
        print(f"❌ Error getting attendance stats: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


# ============================================================
# 8️⃣ API: جلب الطلاب حسب الشعبة
# ============================================================

@router.get("/api/v1/sections/{section_id}/students")
async def get_section_students_api(
    section_id: str,
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    date: Optional[str] = None,
):
    """جلب طلاب الشعبة مع حالة الحضور"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        students = await get_students_with_attendance(
            db, user.school_id, section_id, selected_date
        )
        
        return JSONResponse({
            "success": True,
            "students": students,
            "count": len(students)
        })
        
    except Exception as e:
        print(f"❌ Error getting section students: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


# ============================================================
# 9️⃣ صفحة حضور المعلمين
# ============================================================

@router.get("/teachers")
async def teacher_attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    date: Optional[str] = None,
):
    """صفحة حضور المعلمين - بحث يدوي"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        # جلب جميع المعلمين
        teachers_result = await db.execute(
            select(Teacher).where(
                Teacher.school_id == user.school_id,
                Teacher.is_active == True
            ).order_by(Teacher.first_name, Teacher.last_name)
        )
        teachers = teachers_result.scalars().all()
        
        # جلب سجلات الحضور للمعلمين
        attendance_result = await db.execute(
            select(TeacherAttendance).where(
                TeacherAttendance.school_id == user.school_id,
                TeacherAttendance.date == selected_date
            )
        )
        attendance_records = attendance_result.scalars().all()
        
        # ربط المعلمين بسجلات الحضور
        attendance_map = {str(a.teacher_id): a for a in attendance_records}
        
        teachers_data = []
        for teacher in teachers:
            record = attendance_map.get(str(teacher.id))
            teachers_data.append({
                "id": str(teacher.id),
                "full_name": teacher.full_name,
                "employee_number": teacher.employee_number,
                "specialization": teacher.specialization,
                "attendance_id": str(record.id) if record else None,
                "status": record.status if record else None,
                "note": record.note if record else None,
                "has_attendance": record is not None
            })
        
        return templates.TemplateResponse(
            "attendance/teachers/list.html",
            {
                **ctx,
                "title": "حضور المعلمين",
                "teachers": teachers_data,
                "selected_date": selected_date,
                "today": today,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in teacher_attendance_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/teachers/list.html",
            {
                **ctx,
                "title": "حضور المعلمين",
                "teachers": [],
                "selected_date": datetime.now().strftime("%Y-%m-%d"),
                "today": datetime.now().strftime("%Y-%m-%d"),
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 🔟 مسارات التصحيح (Debug)
# ============================================================

@router.get("/debug/data")
async def debug_attendance_data(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
):
    """عرض بيانات الحضور للتصحيح - بحث يدوي"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        result = {
            "years": await get_academic_years(db, user.school_id),
            "stages": await get_stages(db, user.school_id),
            "grades": await get_grades(db, user.school_id),
            "sections": await get_sections_with_details(db, user.school_id),
        }
        
        # جلب عدد سجلات الحضور
        count_result = await db.execute(
            select(func.count(StudentAttendance.id)).where(
                StudentAttendance.school_id == user.school_id
            )
        )
        result["attendance_count"] = count_result.scalar() or 0
        
        # جلب سجلات اليوم
        today_result = await db.execute(
            select(func.count(StudentAttendance.id)).where(
                StudentAttendance.school_id == user.school_id,
                StudentAttendance.date == today
            )
        )
        result["today_attendance"] = today_result.scalar() or 0
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"❌ Error in debug_attendance_data: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@router.get("/debug/students")
async def debug_students(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    section_id: Optional[str] = None,
):
    """عرض بيانات الطلاب للتصحيح - بحث يدوي"""
    try:
        students = await get_students_with_attendance(
            db, user.school_id, section_id
        )
        
        return JSONResponse({
            "total": len(students),
            "students": students,
            "school_id": str(user.school_id),
            "section_id": section_id
        })
        
    except Exception as e:
        print(f"❌ Error in debug_students: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@router.get("/debug/hierarchy")
async def debug_hierarchy(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
):
    """عرض التسلسل الهرمي للتصحيح - بحث يدوي"""
    try:
        years = await get_academic_years(db, user.school_id)
        stages = await get_stages(db, user.school_id, year_id)
        grades = await get_grades(db, user.school_id, stage_id, year_id)
        sections = await get_sections_with_details(db, user.school_id)
        
        return JSONResponse({
            "success": True,
            "years": years,
            "stages": stages,
            "grades": grades,
            "sections": sections,
            "school_id": str(user.school_id),
            "selected_year": year_id,
            "selected_stage": stage_id,
            "selected_grade": grade_id,
        })
        
    except Exception as e:
        print(f"❌ Error in debug_hierarchy: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )
