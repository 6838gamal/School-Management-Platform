"""Deputy dashboard web route — الفصول مرتبة من اليمين لليسار + إحصائيات الحضور + الأضواء 🟢/🟠/🔴."""
from datetime import date as _date, datetime, timedelta
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import logging
from typing import Optional, Dict, Any, List
import uuid
import random

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.models.schools import School
from app.models.academics import Section, Subject, Grade, Stage
from app.models.users import User 
from app.models.students import Student 
from app.models.teachers import Teacher
from app.models.schedules import Schedule, ScheduleEntry

router = APIRouter(prefix="/deputy", tags=["deputy-dashboard"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


# ============================================================================
# بيانات افتراضية (للاختبار)
# ============================================================================

MOCK_STAGES = ["المرحلة الابتدائية", "المرحلة المتوسطة", "المرحلة الثانوية"]
MOCK_GRADES = ["الصف الأول", "الصف الثاني", "الصف الثالث"]
MOCK_SECTIONS = ["أ", "ب", "ج"]
MOCK_SUBJECTS = [
    "اللغة العربية", "الرياضيات", "العلوم", "اللغة الإنجليزية",
    "التربية الإسلامية", "الدراسات الاجتماعية", "الحاسب الآلي",
    "التربية الفنية", "التربية البدنية"
]
MOCK_TEACHERS = [
    "أحمد محمد", "سارة خالد", "محمد علي", "نورة أحمد",
    "خالد سعد", "منى إبراهيم", "عبدالله عمر", "فاطمة حسن"
]
MOCK_STUDENTS = [
    "أحمد علي", "محمد خالد", "عبدالله سعد", "نورة أحمد",
    "سارة محمد", "فاطمة حسن", "خالد عمر", "منى إبراهيم",
    "علي عبدالله", "ريم خالد", "حسن محمد", "لينا أحمد",
    "سعود سعد", "مها عمر", "ناصر حسن", "هند علي"
]
MOCK_STATUSES = ["present", "absent", "late", "excused", "sick", "late_arrival"]
MOCK_STATUS_LABELS = {
    "present": "✅ حضور",
    "absent": "❌ غياب",
    "late": "🟠 تأخير",
    "excused": "📋 استئذان",
    "sick": "🏥 حالة صحية",
    "late_arrival": "⏰ تأخير صباحي",
    "unknown": "⚪ لم يسجل"
}


# ============================================================================
# القسم 1: الصفحات الرئيسية
# ============================================================================

@router.get("/dashboard")
async def deputy_dashboard(
    request: Request,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    target_date: str | None = None,
):
    """
    لوحة تحكم الوكيل - تعرض الفصول مرتبة من اليمين لليسار مع الحصص والإحصائيات
    """
    try:
        # تحديد التاريخ المستهدف
        selected_date = target_date or _date.today().isoformat()
        selected_month = selected_date[:7]
        
        # جلب بيانات الداشبورد
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        
        # جلب أيام الأسبوع
        week_days = get_mock_week_days(selected_date)
        
        # إعداد بيانات الرسم البياني
        chart_data = {
            "status": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            },
            "attendance": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            }
        }
        
        # إضافة chart_data إلى dashboard
        dashboard_data["chart_data"] = chart_data
        
        return templates.TemplateResponse(
            "deputy/dashboard.html",
            {
                **ctx,
                "request": request,
                "title": "لوحة تحكم الوكيل",
                "dashboard": dashboard_data,
                "selected_date": selected_date,
                "selected_month": selected_month,
                "week_days": week_days,
                "user": user,
            },
        )
    
    except Exception as e:
        logger.error(f"❌ Error in deputy_dashboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/dashboard/date/{date}")
async def deputy_dashboard_by_date(
    request: Request,
    date: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """
    لوحة تحكم الوكيل بتاريخ محدد
    """
    try:
        # التحقق من صحة التاريخ
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="تنسيق تاريخ غير صحيح. استخدم YYYY-MM-DD")
        
        dashboard_data = await get_dashboard_data(db, user.school_id, date)
        selected_month = date[:7]
        week_days = get_mock_week_days(date)
        
        # إعداد بيانات الرسم البياني
        chart_data = {
            "status": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            },
            "attendance": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            }
        }
        dashboard_data["chart_data"] = chart_data
        
        return templates.TemplateResponse(
            "deputy/dashboard.html",
            {
                **ctx,
                "request": request,
                "title": f"لوحة تحكم الوكيل - {date}",
                "dashboard": dashboard_data,
                "selected_date": date,
                "selected_month": selected_month,
                "week_days": week_days,
                "user": user,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in deputy_dashboard_by_date: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


# ============================================================================
# القسم 2: عرض تفاصيل الفصل
# ============================================================================

@router.get("/section/{section_id}/students")
async def section_students(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """
    عرض قائمة الطلاب في فصل معين مع تفاصيل الحضور والغياب
    """
    try:
        # جلب الفصل
        section_result = await db.execute(
            select(Section)
            .options(selectinload(Section.stage), selectinload(Section.grade))
            .where(Section.id == section_id)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
        # جلب الطلاب
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .order_by(Student.full_name)
        )
        students = students_result.scalars().all()
        
        students_data = []
        for student in students:
            stats = await get_student_attendance_stats(db, student.id)
            students_data.append({
                "id": student.id,
                "name": student.full_name,
                "code": student.code,
                "gender": student.gender,
                "attendance": stats
            })
        
        return templates.TemplateResponse(
            "deputy/students.html",
            {
                **ctx,
                "request": request,
                "section": section,
                "students": students_data,
                "user": user,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in section_students: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/section/{section_id}/attendance")
async def section_attendance(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    target_date: str | None = None,
):
    """
    تسجيل الحضور والغياب للفصل - يتحكم فيها الوكيل فقط
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        
        # جلب الفصل
        section_result = await db.execute(
            select(Section)
            .options(selectinload(Section.stage), selectinload(Section.grade))
            .where(Section.id == section_id)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
        # جلب الطلاب
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .order_by(Student.full_name)
        )
        students = students_result.scalars().all()
        
        # جلب سجلات الحضور الحالية
        from app.models.attendance import Attendance
        
        students_data = []
        for student in students:
            attendance_result = await db.execute(
                select(Attendance)
                .where(
                    Attendance.student_id == student.id,
                    Attendance.date == selected_date
                )
            )
            attendance = attendance_result.scalars().first()
            students_data.append({
                "id": student.id,
                "name": student.full_name,
                "current_status": attendance.status if attendance else "unknown",
                "attendance_id": attendance.id if attendance else None
            })
        
        return templates.TemplateResponse(
            "deputy/attendance_form.html",
            {
                **ctx,
                "request": request,
                "section": section,
                "students": students_data,
                "selected_date": selected_date,
                "user": user,
                "status_options": [
                    {"value": "present", "label": "✅ حضور"},
                    {"value": "absent", "label": "❌ غياب"},
                    {"value": "late", "label": "🟠 تأخير"},
                    {"value": "excused", "label": "📋 استئذان"},
                    {"value": "sick", "label": "🏥 حالة صحية"},
                    {"value": "late_arrival", "label": "⏰ تأخير صباحي"},
                ]
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in section_attendance: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/section/{section_id}/transfer")
async def transfer_students(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """
    نقل الطلاب بين الصفوف أو المراحل أو المدارس
    """
    try:
        # جلب الفصل الحالي
        section_result = await db.execute(
            select(Section)
            .options(selectinload(Section.stage), selectinload(Section.grade))
            .where(Section.id == section_id)
        )
        current_section = section_result.scalar_one_or_none()
        
        if not current_section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
        # جلب جميع الفصول الأخرى في المدرسة
        other_sections_result = await db.execute(
            select(Section)
            .options(selectinload(Section.stage), selectinload(Section.grade))
            .where(
                Section.school_id == current_section.school_id,
                Section.id != section_id
            )
            .order_by(Section.stage_id, Section.grade_id, Section.name)
        )
        other_sections = other_sections_result.scalars().all()
        
        # جلب الطلاب في الفصل الحالي
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .order_by(Student.full_name)
        )
        students = students_result.scalars().all()
        
        # جلب جميع المدارس للنقل بين المدارس
        schools_result = await db.execute(
            select(School).order_by(School.name)
        )
        schools = schools_result.scalars().all()
        
        return templates.TemplateResponse(
            "deputy/transfer.html",
            {
                **ctx,
                "request": request,
                "current_section": current_section,
                "students": students,
                "other_sections": other_sections,
                "schools": schools,
                "user": user,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in transfer_students: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/section/{section_id}/report")
async def section_report(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    target_date: str | None = None,
):
    """
    عرض تقرير مفصل للفصل
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        
        # جلب الفصل
        section_result = await db.execute(
            select(Section)
            .options(selectinload(Section.stage), selectinload(Section.grade))
            .where(Section.id == section_id)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
        # جلب الطلاب مع إحصائياتهم
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .order_by(Student.full_name)
        )
        students = students_result.scalars().all()
        
        students_data = []
        for student in students:
            stats = await get_student_attendance_stats(db, student.id)
            students_data.append({
                "id": student.id,
                "name": student.full_name,
                "code": student.code,
                "attendance": stats
            })
        
        # جلب إحصائيات الفصل
        attendance_stats = await get_section_attendance_stats(db, section_id, selected_date)
        
        return templates.TemplateResponse(
            "deputy/section_report.html",
            {
                **ctx,
                "request": request,
                "section": section,
                "students": students_data,
                "attendance_stats": attendance_stats,
                "selected_date": selected_date,
                "user": user,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in section_report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


# ============================================================================
# القسم 3: وظائف تصدير البيانات
# ============================================================================

@router.get("/dashboard/export/pdf")
async def export_dashboard_pdf(
    request: Request,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    target_date: str | None = None,
):
    """
    تصدير لوحة التحكم كملف PDF
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        
        # إعداد بيانات الرسم البياني
        chart_data = {
            "status": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            },
            "attendance": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            }
        }
        dashboard_data["chart_data"] = chart_data
        
        return templates.TemplateResponse(
            "deputy/dashboard_print.html",
            {
                **ctx,
                "request": request,
                "dashboard": dashboard_data,
                "selected_date": selected_date,
                "user": user,
            },
        )
    
    except Exception as e:
        logger.error(f"❌ Error in export_dashboard_pdf: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/dashboard/export/report")
async def export_report(
    request: Request,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    target_date: str | None = None,
):
    """
    تصدير تقرير مفصل
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        
        # إعداد بيانات الرسم البياني
        chart_data = {
            "status": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            },
            "attendance": {
                "present": dashboard_data.get("analytics", {}).get("present", 0),
                "absent": dashboard_data.get("analytics", {}).get("absent", 0),
                "late": dashboard_data.get("analytics", {}).get("late", 0),
                "excused": dashboard_data.get("analytics", {}).get("excused", 0),
                "sick": dashboard_data.get("analytics", {}).get("sick", 0),
                "late_arrival": dashboard_data.get("analytics", {}).get("late_arrival", 0)
            }
        }
        dashboard_data["chart_data"] = chart_data
        
        return templates.TemplateResponse(
            "deputy/report_export.html",
            {
                **ctx,
                "request": request,
                "dashboard": dashboard_data,
                "selected_date": selected_date,
                "user": user,
            },
        )
    
    except Exception as e:
        logger.error(f"❌ Error in export_report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


# ============================================================================
# القسم 4: وظائف مساعدة (Helper Functions)
# ============================================================================

def get_status_config(status: str) -> Dict[str, str]:
    """
    إرجاع إعدادات الحالة بناءً على نوعها
    """
    status_config = {
        "present": {"indicator": "🟢", "label": "✅ حضور", "status": "present", "color": "green"},
        "absent": {"indicator": "🔴", "label": "❌ غياب", "status": "absent", "color": "red"},
        "late": {"indicator": "🟠", "label": "⏰ تأخير", "status": "late", "color": "orange"},
        "excused": {"indicator": "📋", "label": "📋 استئذان", "status": "excused", "color": "blue"},
        "sick": {"indicator": "🟣", "label": "🏥 حالة صحية", "status": "sick", "color": "purple"},
        "late_arrival": {"indicator": "🟡", "label": "⏰ تأخير صباحي", "status": "late_arrival", "color": "yellow"},
        "teacher_absent": {"indicator": "🔴", "label": "👨‍🏫 غياب معلم", "status": "teacher_absent", "color": "red"},
        "substitute_required": {"indicator": "🔴", "label": "🔄 مطلوب بديل", "status": "substitute_required", "color": "red"},
        "unknown": {"indicator": "⚪", "label": "⏳ لم يسجل", "status": "unknown", "color": "gray"},
    }
    return status_config.get(status, status_config["unknown"])


async def get_section_attendance_stats(db: AsyncSession, section_id: str, target_date: str) -> Dict[str, int]:
    """
    جلب إحصائيات الحضور لفصل معين في تاريخ محدد
    """
    try:
        from app.models.attendance import Attendance
        
        # جلب جميع سجلات الحضور للفصل في التاريخ المحدد
        result = await db.execute(
            select(Attendance.status, func.count(Attendance.id))
            .join(ScheduleEntry, ScheduleEntry.id == Attendance.schedule_entry_id)
            .where(
                ScheduleEntry.section_id == section_id,
                ScheduleEntry.schedule_date == target_date
            )
            .group_by(Attendance.status)
        )
        
        stats = result.all()
        
        # تجهيز الإحصائيات
        attendance_stats = {
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "sick": 0,
            "late_arrival": 0,
            "teacher_absent": 0,
            "substitute_required": 0,
            "other": 0,
            "total": 0
        }
        
        for status, count in stats:
            if status in attendance_stats:
                attendance_stats[status] = count
            else:
                attendance_stats["other"] += count
            attendance_stats["total"] += count
        
        return attendance_stats
    
    except Exception as e:
        logger.error(f"❌ Error getting section attendance stats: {str(e)}")
        return {
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "sick": 0,
            "late_arrival": 0,
            "teacher_absent": 0,
            "substitute_required": 0,
            "other": 0,
            "total": 0
        }


async def get_student_attendance_stats(db: AsyncSession, student_id: str) -> Dict[str, int]:
    """
    جلب إحصائيات الحضور لطالب معين
    """
    try:
        from app.models.attendance import Attendance
        
        result = await db.execute(
            select(Attendance.status, func.count(Attendance.id))
            .where(Attendance.student_id == student_id)
            .group_by(Attendance.status)
        )
        
        stats = result.all()
        
        attendance_stats = {
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "sick": 0,
            "late_arrival": 0,
            "total": 0
        }
        
        for status, count in stats:
            if status in attendance_stats:
                attendance_stats[status] = count
            attendance_stats["total"] += count
        
        return attendance_stats
    
    except Exception as e:
        logger.error(f"❌ Error getting student stats: {str(e)}")
        return {
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "sick": 0,
            "late_arrival": 0,
            "total": 0
        }


async def get_dashboard_data(db: AsyncSession, school_id: str, target_date: str) -> Dict[str, Any]:
    """
    جلب جميع بيانات الداشبورد من قاعدة البيانات
    """
    try:
        # 1. جلب المدرسة
        school_result = await db.execute(
            select(School).where(School.id == school_id)
        )
        school = school_result.scalar_one_or_none()
        
        if not school:
            logger.warning(f"⚠️ School not found with ID: {school_id}")
            return get_empty_dashboard_data(target_date)
        
        # 2. جلب جميع الفصول في المدرسة مع تحميل العلاقات
        sections_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.stage),
                selectinload(Section.grade)
            )
            .where(Section.school_id == school_id)
            .order_by(
                Section.stage_id,
                Section.grade_id,
                Section.name
            )
        )
        sections = sections_result.scalars().all()
        
        logger.info(f"✅ Found {len(sections)} sections for school: {school.name}")
        
        if not sections:
            logger.info(f"ℹ️ No sections found for school: {school.name}")
            return get_empty_dashboard_data(target_date)
        
        dashboard_sections = []
        all_students = []
        analytics = {
            "present": 0,
            "absent": 0,
            "late": 0,
            "late_arrival": 0,
            "excused": 0,
            "sick": 0,
            "teacher_absent": 0,
            "substitute_required": 0,
            "other": 0,
            "total_records": 0
        }
        
        # 3. معالجة كل فصل
        for section in sections:
            logger.info(f"📚 Processing section: {section.name} (ID: {section.id})")
            section_data = await process_section_data(db, section, target_date)
            dashboard_sections.append(section_data)
            
            # جمع الطلاب من هذا الفصل
            if section_data.get("students"):
                all_students.extend(section_data["students"])
            
            # تحديث الإحصائيات
            for period in section_data.get("periods_today", []):
                status = period.get("status", "unknown")
                if status in analytics:
                    analytics[status] += 1
                else:
                    analytics["other"] += 1
                analytics["total_records"] += 1
        
        return {
            "date": target_date,
            "sections": dashboard_sections,
            "all_students": all_students,
            "analytics": analytics
        }
    
    except Exception as e:
        logger.error(f"❌ Error in get_dashboard_data: {str(e)}", exc_info=True)
        return get_empty_dashboard_data(target_date)


async def process_section_data(db: AsyncSession, section: Section, target_date: str) -> Dict[str, Any]:
    """
    معالجة بيانات فصل واحد
    """
    try:
        # جلب عدد الطلاب في الفصل
        students_count = await db.scalar(
            select(func.count(Student.id))
            .where(Student.section_id == section.id)
        ) or 0
        
        logger.info(f"👥 Section {section.name} has {students_count} students")
        
        # جلب اسم المرحلة والصف
        stage_name = section.stage.name if section.stage else "المرحلة"
        grade_name = section.grade.name if section.grade else "الصف"
        
        logger.info(f"🏷️ Stage: {stage_name}, Grade: {grade_name}")
        
        # جلب الحصص لهذا اليوم
        periods = await get_section_periods(db, section.id, target_date)
        
        logger.info(f"📖 Found {len(periods)} periods for section {section.name}")
        
        periods_data = []
        for period in periods:
            period_info = await process_period_data(db, period)
            periods_data.append(period_info)
        
        # جلب إحصائيات الحضور للفصل
        attendance_stats = await get_section_attendance_stats(db, section.id, target_date)
        
        # جلب الطلاب في الفصل
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section.id)
            .order_by(Student.full_name)
        )
        students = students_result.scalars().all()
        
        students_data = []
        for student in students:
            stats = await get_student_attendance_stats(db, student.id)
            # تحديد الحالة الحالية للطالب
            status = "unknown"
            if stats["total"] > 0:
                if stats["present"] > stats["absent"] and stats["present"] > stats["late"]:
                    status = "present"
                elif stats["absent"] > stats["present"] and stats["absent"] > stats["late"]:
                    status = "absent"
                elif stats["late"] > 0:
                    status = "late"
                elif stats["excused"] > 0:
                    status = "excused"
                elif stats["sick"] > 0:
                    status = "sick"
            
            students_data.append({
                "id": student.id,
                "name": student.full_name,
                "code": student.code,
                "status": status,
                "status_label": MOCK_STATUS_LABELS.get(status, status),
                "attendance": stats
            })
        
        return {
            "section_id": section.id,
            "stage_name": stage_name,
            "grade_name": grade_name,
            "section_name": section.name or "فصل",
            "enrolled_count": students_count,
            "periods_today": periods_data,
            "attendance_stats": attendance_stats,
            "students": students_data
        }
    
    except Exception as e:
        logger.error(f"❌ Error processing section {section.id}: {str(e)}", exc_info=True)
        return {
            "section_id": section.id,
            "stage_name": "خطأ",
            "grade_name": "خطأ",
            "section_name": section.name or "فصل",
            "enrolled_count": 0,
            "periods_today": [],
            "attendance_stats": {},
            "students": []
        }


async def get_section_periods(db: AsyncSession, section_id: str, target_date: str) -> List[ScheduleEntry]:
    """
    جلب الحصص لفصل في تاريخ محدد مع محاولة حقول تاريخ مختلفة
    """
    date_fields = ['schedule_date', 'date', 'day', 'period_date']
    
    for field in date_fields:
        try:
            query = select(ScheduleEntry).where(
                ScheduleEntry.section_id == section_id,
                getattr(ScheduleEntry, field) == target_date
            ).order_by(ScheduleEntry.period_number)
            
            result = await db.execute(query)
            periods = result.scalars().all()
            
            if periods:
                logger.info(f"✅ Found {len(periods)} periods using field '{field}'")
                return periods
        except Exception as e:
            logger.debug(f"Field '{field}' not found or error: {e}")
            continue
    
    logger.warning(f"⚠️ No date field found, returning all periods for section {section_id}")
    try:
        result = await db.execute(
            select(ScheduleEntry)
            .where(ScheduleEntry.section_id == section_id)
            .order_by(ScheduleEntry.period_number)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"❌ Error getting periods: {e}")
        return []


async def process_period_data(db: AsyncSession, period: ScheduleEntry) -> Dict[str, Any]:
    """
    معالجة بيانات حصة واحدة
    """
    try:
        # جلب المادة
        subject_name = "غير محدد"
        if period.subject_id:
            subject_result = await db.execute(
                select(Subject).where(Subject.id == period.subject_id)
            )
            subject = subject_result.scalar_one_or_none()
            if subject:
                subject_name = subject.name[:8]
        
        # جلب المعلم
        teacher_name = "غير محدد"
        if period.teacher_id:
            teacher_result = await db.execute(
                select(Teacher).where(Teacher.id == period.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = teacher.full_name or teacher.name or "معلم"
        
        # جلب الحضور
        attendance = await get_period_attendance(db, period.id)
        
        # تحديد الحالة
        status = attendance.status if attendance else "unknown"
        status_config = get_status_config(status)
        
        # إحصائيات عشوائية للحصة (للعرض)
        stats = {
            "present": random.randint(5, 15),
            "absent": random.randint(0, 5),
            "late": random.randint(0, 3),
            "excused": random.randint(0, 2),
            "sick": random.randint(0, 2),
            "late_arrival": random.randint(0, 2)
        }
        
        return {
            "subject_id": str(period.subject_id or ""),
            "subject_name": subject_name,
            "teacher_name": teacher_name,
            "indicator": status_config["indicator"],
            "status_label": status_config["label"],
            "status": status_config["status"],
            "schedule_entry_id": period.id,
            "period_number": period.period_number,
            "attendance_id": attendance.id if attendance else None,
            "is_attendance_recorded": attendance is not None,
            "attendance_stats": stats
        }
    
    except Exception as e:
        logger.error(f"❌ Error processing period {period.id}: {str(e)}", exc_info=True)
        return {
            "subject_id": "",
            "subject_name": "خطأ",
            "teacher_name": "خطأ",
            "indicator": "⚪",
            "status_label": "خطأ",
            "status": "unknown",
            "schedule_entry_id": period.id,
            "period_number": 0,
            "attendance_id": None,
            "is_attendance_recorded": False,
            "attendance_stats": {}
        }


async def get_period_attendance(db: AsyncSession, schedule_entry_id: str):
    """
    جلب سجل الحضور لحصة معينة
    """
    try:
        from app.models.attendance import Attendance
        
        result = await db.execute(
            select(Attendance)
            .where(Attendance.schedule_entry_id == schedule_entry_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.warning(f"⚠️ Could not query attendance for period {schedule_entry_id}: {e}")
        return None


def get_mock_week_days(target_date: str) -> List[Dict]:
    """
    إنشاء بيانات أيام الأسبوع الافتراضية
    """
    day_names = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
    
    try:
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    except:
        date_obj = datetime.now()
    
    start_of_week = date_obj - timedelta(days=date_obj.weekday() + 1)
    
    week_days = []
    for i in range(7):
        current_date = start_of_week + timedelta(days=i)
        is_today = current_date.date() == date_obj.date()
        
        week_days.append({
            "name": day_names[i],
            "date": current_date.strftime("%Y-%m-%d"),
            "is_today": is_today,
            "present": random.randint(50, 100),
            "absent": random.randint(0, 15),
            "late": random.randint(0, 10),
            "excused": random.randint(0, 8),
            "sick": random.randint(0, 5),
            "late_arrival": random.randint(0, 5)
        })
    
    return week_days


def get_empty_dashboard_data(target_date: str) -> Dict[str, Any]:
    """
    إرجاع بيانات فارغة للداشبورد
    """
    return {
        "date": target_date,
        "sections": [],
        "all_students": [],
        "analytics": {
            "present": 0,
            "absent": 0,
            "late": 0,
            "late_arrival": 0,
            "excused": 0,
            "sick": 0,
            "teacher_absent": 0,
            "substitute_required": 0,
            "other": 0,
            "total_records": 0
        }
    }


# ============================================================================
# القسم 5: واجهات API (للميزات الإضافية)
# ============================================================================

@router.get("/api/dashboard/data")
async def api_dashboard_data(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    target_date: str | None = None,
):
    """
    واجهة API للحصول على بيانات الداشبورد بصيغة JSON
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        return {
            "success": True,
            "data": dashboard_data,
            "date": selected_date
        }
    
    except Exception as e:
        logger.error(f"❌ Error in API: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/api/attendance/update")
async def api_update_attendance(
    schedule_entry_id: str,
    status: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث حالة الحضور لحصة معينة (API)
    """
    try:
        valid_statuses = ["present", "absent", "late", "excused", "late_arrival"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail="حالة غير صحيحة")
        
        from app.models.attendance import Attendance
        
        attendance_result = await db.execute(
            select(Attendance).where(Attendance.schedule_entry_id == schedule_entry_id)
        )
        attendance = attendance_result.scalar_one_or_none()
        
        if attendance:
            attendance.status = status
            attendance.updated_by = user.id
            attendance.updated_at = datetime.now()
        else:
            attendance = Attendance(
                id=str(uuid.uuid4()),
                schedule_entry_id=schedule_entry_id,
                status=status,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(attendance)
        
        await db.commit()
        await db.refresh(attendance)
        
        return {
            "success": True,
            "message": "تم تحديث الحضور بنجاح",
            "status": status,
            "attendance_id": attendance.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating attendance: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/api/section/{section_id}/students")
async def api_section_students(
    section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    API لجلب قائمة الطلاب في فصل معين
    """
    try:
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .order_by(Student.full_name)
        )
        students = students_result.scalars().all()
        
        return {
            "success": True,
            "students": [
                {
                    "id": student.id,
                    "name": student.full_name,
                    "code": student.code,
                    "gender": student.gender
                }
                for student in students
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting students: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/api/student/transfer")
async def api_transfer_student(
    student_id: str,
    target_section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    API لنقل طالب إلى فصل آخر
    """
    try:
        # جلب الطالب
        student_result = await db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(status_code=404, detail="الطالب غير موجود")
        
        # جلب الفصل المستهدف
        section_result = await db.execute(
            select(Section).where(Section.id == target_section_id)
        )
        target_section = section_result.scalar_one_or_none()
        
        if not target_section:
            raise HTTPException(status_code=404, detail="الفصل المستهدف غير موجود")
        
        # تسجيل عملية النقل
        from app.models.transfers import TransferLog
        
        transfer_log = TransferLog(
            id=str(uuid.uuid4()),
            student_id=student_id,
            from_section_id=student.section_id,
            to_section_id=target_section_id,
            transfer_type="section",
            transferred_by=user.id,
            transferred_at=datetime.now(),
            notes="نقل بواسطة الوكيل"
        )
        db.add(transfer_log)
        
        # تحديث فصل الطالب
        student.section_id = target_section_id
        
        await db.commit()
        
        return {
            "success": True,
            "message": "تم نقل الطالب بنجاح",
            "student_id": student_id,
            "new_section": target_section.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error transferring student: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")
