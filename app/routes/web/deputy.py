"""
Deputy dashboard web route — الفصول مرتبة من اليمين لليسار + إحصائيات الحضور + الأضواء 🟢/🟠/🔴.
مع تحسينات التصحيح والتسجيل التفصيلي ومسارات الاختبار
"""
from datetime import date as _date, datetime, timedelta
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
import logging
import sys
from typing import Optional, Dict, Any, List
import uuid
import traceback

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.models.attendance import StudentAttendance
from app.models.schools import School
from app.models.academics import Section, Subject, Grade, Stage, AcademicYear
from app.models.users import User 
from app.models.students import Student 
from app.models.teachers import Teacher
from app.models.schedules import Schedule, ScheduleEntry

# ============================================================================
# تكوين التسجيل (Logging Configuration)
# ============================================================================

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

for name in ['app', 'app.routes', 'app.routes.deputy_dashboard']:
    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(logging.DEBUG)

router = APIRouter(prefix="/deputy", tags=["deputy-dashboard"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# ============================================================================
# مسارات التصحيح
# ============================================================================

@router.get("/ping")
async def ping():
    return {"status": "ok", "message": "Deputy dashboard router is working!", "timestamp": datetime.now().isoformat()}


@router.get("/debug/simple")
async def debug_simple(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    """مسرح تصحيح بسيط لعرض البيانات الخام"""
    result = {
        "user_id": str(user.id),
        "school_id": str(user.school_id) if user.school_id else None,
        "sections": [],
        "students": [],
        "attendance": [],
        "schedule": [],
        "errors": []
    }
    
    try:
        # جلب المدرسة
        school = await db.execute(
            select(School).where(School.id == user.school_id)
        )
        school = school.scalar_one_or_none()
        
        if school:
            result["school"] = {"id": str(school.id), "name": school.name}
        else:
            result["errors"].append("School not found")
        
        # جلب الفصول مع العلاقات
        sections = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == user.school_id)
        )
        sections = sections.scalars().all()
        
        for section in sections:
            student_count = await db.scalar(
                select(func.count(Student.id))
                .where(Student.section_id == section.id)
            ) or 0
            
            result["sections"].append({
                "id": str(section.id),
                "name": section.name,
                "grade": section.grade.name if section.grade else None,
                "stage": section.grade.stage.name if section.grade and section.grade.stage else None,
                "student_count": student_count
            })
        
        # جلب سجلات الحضور
        attendance_records = await db.execute(
            select(StudentAttendance).limit(10)
        )
        attendance = attendance_records.scalars().all()
        
        for record in attendance:
            result["attendance"].append({
                "id": str(record.id),
                "student_id": str(record.student_id) if hasattr(record, 'student_id') else None,
                "status": getattr(record, 'status', None),
                "date": str(getattr(record, 'date', None))
            })
        
        # اختبار قاعدة البيانات
        db_result = await db.execute(text("SELECT 1"))
        result["database"] = {
            "connected": True,
            "test_result": db_result.scalar() == 1
        }
        
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": traceback.format_exc()}
        )


# ============================================================================
# الصفحات الرئيسية
# ============================================================================

@router.get("/dashboard")
async def deputy_dashboard(
    request: Request,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    target_date: str | None = None,
):
    """لوحة تحكم الوكيل - تعرض الفصول مرتبة مع الحصص والإحصائيات"""
    try:
        selected_date = target_date or _date.today().isoformat()
        selected_month = selected_date[:7]
        
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        
        # إعداد بيانات الرسم البياني
        analytics = dashboard_data.get("analytics", {})
        chart_data = {
            "status": {
                "present": analytics.get("present", 0),
                "absent": analytics.get("absent", 0),
                "late": analytics.get("late", 0),
                "excused": analytics.get("excused", 0),
                "sick": analytics.get("sick", 0),
                "late_arrival": analytics.get("late_arrival", 0)
            },
            "attendance": {
                "present": analytics.get("present", 0),
                "absent": analytics.get("absent", 0),
                "late": analytics.get("late", 0),
                "excused": analytics.get("excused", 0),
                "sick": analytics.get("sick", 0),
                "late_arrival": analytics.get("late_arrival", 0)
            }
        }
        dashboard_data["chart_data"] = chart_data
        
        # أيام الأسبوع
        week_days = get_week_days(selected_date)
        
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
                "debug_mode": True,
            },
        )
    
    except Exception as e:
        print(f"❌ Error in deputy_dashboard: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/dashboard/date/{date}")
async def deputy_dashboard_by_date(
    request: Request,
    date: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """لوحة تحكم الوكيل بتاريخ محدد"""
    try:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="تنسيق تاريخ غير صحيح")
        
        dashboard_data = await get_dashboard_data(db, user.school_id, date)
        selected_month = date[:7]
        
        analytics = dashboard_data.get("analytics", {})
        chart_data = {
            "status": {
                "present": analytics.get("present", 0),
                "absent": analytics.get("absent", 0),
                "late": analytics.get("late", 0),
                "excused": analytics.get("excused", 0),
                "sick": analytics.get("sick", 0),
                "late_arrival": analytics.get("late_arrival", 0)
            },
            "attendance": {
                "present": analytics.get("present", 0),
                "absent": analytics.get("absent", 0),
                "late": analytics.get("late", 0),
                "excused": analytics.get("excused", 0),
                "sick": analytics.get("sick", 0),
                "late_arrival": analytics.get("late_arrival", 0)
            }
        }
        dashboard_data["chart_data"] = chart_data
        
        week_days = get_week_days(date)
        
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
                "debug_mode": True,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in deputy_dashboard_by_date: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


# ============================================================================
# عرض تفاصيل الفصل
# ============================================================================

@router.get("/section/{section_id}/students")
async def section_students(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة الطلاب في فصل معين مع تفاصيل الحضور"""
    try:
        section_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.id == section_id)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
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
        print(f"❌ Error in section_students: {str(e)}")
        traceback.print_exc()
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
    """تسجيل الحضور والغياب للفصل"""
    try:
        selected_date = target_date or _date.today().isoformat()
        
        section_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.id == section_id)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .order_by(Student.full_name)
        )
        students = students_result.scalars().all()
        
        students_data = []
        for student in students:
            attendance_result = await db.execute(
                select(StudentAttendance)
                .where(
                    StudentAttendance.student_id == student.id,
                    StudentAttendance.date == selected_date
                )
            )
            attendance = attendance_result.scalars().first()
            students_data.append({
                "id": student.id,
                "name": student.full_name,
                "current_status": attendance.status if attendance else "unknown",
                "attendance_id": attendance.id if attendance else None
            })
        
        status_options = [
            {"value": "present", "label": "✅ حضور"},
            {"value": "absent", "label": "❌ غياب"},
            {"value": "late", "label": "🟠 تأخير"},
            {"value": "excused", "label": "📋 استئذان"},
            {"value": "sick", "label": "🏥 حالة صحية"},
            {"value": "late_arrival", "label": "⏰ تأخير صباحي"},
        ]
        
        return templates.TemplateResponse(
            "deputy/attendance_form.html",
            {
                **ctx,
                "request": request,
                "section": section,
                "students": students_data,
                "selected_date": selected_date,
                "user": user,
                "status_options": status_options
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in section_attendance: {str(e)}")
        traceback.print_exc()
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
    """عرض تقرير مفصل للفصل"""
    try:
        selected_date = target_date or _date.today().isoformat()
        
        section_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.id == section_id)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
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
                "attendance": stats
            })
        
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
        print(f"❌ Error in section_report: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


# ============================================================================
# وظائف مساعدة (Helper Functions)
# ============================================================================

def get_status_config(status: str) -> Dict[str, str]:
    """إرجاع إعدادات الحالة بناءً على نوعها"""
    status_config = {
        "present": {"indicator": "🟢", "label": "✅ حضور", "status": "present", "color": "green"},
        "absent": {"indicator": "🔴", "label": "❌ غياب", "status": "absent", "color": "red"},
        "late": {"indicator": "🟠", "label": "⏰ تأخير", "status": "late", "color": "orange"},
        "excused": {"indicator": "📋", "label": "📋 استئذان", "status": "excused", "color": "blue"},
        "sick": {"indicator": "🟣", "label": "🏥 حالة صحية", "status": "sick", "color": "purple"},
        "late_arrival": {"indicator": "🟡", "label": "⏰ تأخير صباحي", "status": "late_arrival", "color": "yellow"},
        "unknown": {"indicator": "⚪", "label": "⏳ لم يسجل", "status": "unknown", "color": "gray"},
    }
    return status_config.get(status, status_config["unknown"])


async def get_section_attendance_stats(db: AsyncSession, section_id: str, target_date: str) -> Dict[str, int]:
    """جلب إحصائيات الحضور لفصل معين في تاريخ محدد"""
    try:
        students_result = await db.execute(
            select(Student.id).where(Student.section_id == section_id)
        )
        student_ids = [row[0] for row in students_result.all()]
        
        if not student_ids:
            return {
                "present": 0, "absent": 0, "late": 0, "excused": 0,
                "sick": 0, "late_arrival": 0, "total": 0
            }
        
        result = await db.execute(
            select(StudentAttendance.status, func.count(StudentAttendance.id))
            .where(
                StudentAttendance.student_id.in_(student_ids),
                StudentAttendance.date == target_date
            )
            .group_by(StudentAttendance.status)
        )
        
        stats = result.all()
        
        attendance_stats = {
            "present": 0, "absent": 0, "late": 0, "excused": 0,
            "sick": 0, "late_arrival": 0, "total": 0
        }
        
        for status, count in stats:
            if status in attendance_stats:
                attendance_stats[status] = count
            attendance_stats["total"] += count
        
        return attendance_stats
    
    except Exception as e:
        print(f"❌ Error getting section attendance stats: {str(e)}")
        return {
            "present": 0, "absent": 0, "late": 0, "excused": 0,
            "sick": 0, "late_arrival": 0, "total": 0
        }


async def get_student_attendance_stats(db: AsyncSession, student_id: str) -> Dict[str, int]:
    """جلب إحصائيات الحضور لطالب معين"""
    try:
        result = await db.execute(
            select(StudentAttendance.status, func.count(StudentAttendance.id))
            .where(StudentAttendance.student_id == student_id)
            .group_by(StudentAttendance.status)
        )
        
        stats = result.all()
        
        attendance_stats = {
            "present": 0, "absent": 0, "late": 0,
            "excused": 0, "sick": 0, "late_arrival": 0,
            "total": 0
        }
        
        for status, count in stats:
            if status in attendance_stats:
                attendance_stats[status] = count
            attendance_stats["total"] += count
        
        return attendance_stats
    
    except Exception as e:
        print(f"❌ Error getting student stats: {str(e)}")
        return {
            "present": 0, "absent": 0, "late": 0,
            "excused": 0, "sick": 0, "late_arrival": 0,
            "total": 0
        }


async def get_section_periods_for_date(
    db: AsyncSession, 
    section_id: str, 
    school_id: str, 
    target_date: str
) -> List[Dict]:
    """جلب الحصص لفصل في تاريخ محدد"""
    try:
        # جلب الجدول النشط لهذا الفصل
        schedule_result = await db.execute(
            select(Schedule)
            .where(
                Schedule.section_id == section_id,
                Schedule.school_id == school_id,
                Schedule.is_active == True
            )
            .limit(1)
        )
        schedule = schedule_result.scalar_one_or_none()
        
        if not schedule:
            return []
        
        # تحويل التاريخ إلى يوم الأسبوع
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        # Python: 0=إثنين, 6=أحد
        # نظامنا: 0=أحد, 1=إثنين, 2=ثلاثاء, 3=أربعاء, 4=خميس
        day_map = {6: 0, 0: 1, 1: 2, 2: 3, 3: 4}
        day_of_week = day_map.get(date_obj.weekday(), -1)
        
        if day_of_week < 0:
            return []
        
        # جلب الحصص لهذا اليوم
        entries_result = await db.execute(
            select(ScheduleEntry)
            .where(
                ScheduleEntry.schedule_id == schedule.id,
                ScheduleEntry.day_of_week == day_of_week
            )
            .order_by(ScheduleEntry.period_id)
        )
        entries = entries_result.scalars().all()
        
        periods = []
        for entry in entries:
            subject_name = "غير محدد"
            if entry.subject_id:
                subject = await db.get(Subject, entry.subject_id)
                if subject:
                    subject_name = subject.name[:15]
            
            teacher_name = "غير محدد"
            if entry.teacher_id:
                teacher = await db.get(Teacher, entry.teacher_id)
                if teacher:
                    teacher_name = teacher.full_name or teacher.name or "معلم"
            
            period_number = entry.period_id
            
            periods.append({
                "id": entry.id,
                "schedule_entry_id": entry.id,
                "subject_id": entry.subject_id,
                "subject_name": subject_name,
                "teacher_id": entry.teacher_id,
                "teacher_name": teacher_name,
                "period_number": period_number,
                "day_of_week": entry.day_of_week,
                "status": "unknown",
                "status_label": "⏳ لم يسجل",
                "indicator": "⚪",
                "is_attendance_recorded": False
            })
        
        return periods
        
    except Exception as e:
        print(f"❌ Error in get_section_periods_for_date: {str(e)}")
        return []


async def get_dashboard_data(db: AsyncSession, school_id: str, target_date: str) -> Dict[str, Any]:
    """جلب جميع بيانات الداشبورد من قاعدة البيانات"""
    result = {
        "date": target_date,
        "sections": [],
        "all_students": [],
        "analytics": {
            "present": 0, "absent": 0, "late": 0, "late_arrival": 0,
            "excused": 0, "sick": 0, "total_records": 0
        },
        "error": None
    }
    
    try:
        # جلب المدرسة
        school = await db.execute(
            select(School).where(School.id == school_id)
        )
        school = school.scalar_one_or_none()
        
        if not school:
            result["error"] = f"المدرسة غير موجودة: {school_id}"
            return result
        
        # جلب الفصول مع العلاقات
        sections = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == school_id)
            .order_by(Section.grade_id, Section.name)
        )
        sections = sections.scalars().all()
        
        if not sections:
            result["error"] = "لا توجد فصول مسجلة في هذه المدرسة"
            return result
        
        # معالجة كل فصل
        for section in sections:
            try:
                # جلب الطلاب في الفصل
                students = await db.execute(
                    select(Student)
                    .where(Student.section_id == section.id)
                    .order_by(Student.full_name)
                )
                students = students.scalars().all()
                
                # جلب الحصص لهذا اليوم
                periods = await get_section_periods_for_date(
                    db, section.id, school_id, target_date
                )
                
                # معالجة بيانات الطلاب
                students_data = []
                for student in students:
                    stats = await get_student_attendance_stats(db, student.id)
                    
                    status = "unknown"
                    if stats.get("total", 0) > 0:
                        if stats.get("present", 0) > 0:
                            status = "present"
                        elif stats.get("absent", 0) > 0:
                            status = "absent"
                        elif stats.get("late", 0) > 0:
                            status = "late"
                    
                    for key in ["present", "absent", "late", "excused", "sick", "late_arrival"]:
                        if key in stats:
                            result["analytics"][key] = result["analytics"].get(key, 0) + stats.get(key, 0)
                            result["analytics"]["total_records"] = result["analytics"].get("total_records", 0) + stats.get(key, 0)
                    
                    students_data.append({
                        "id": student.id,
                        "name": student.full_name,
                        "status": status,
                        "status_label": get_status_config(status)["label"],
                        "attendance": stats,
                        "section": section.name,
                        "grade": section.grade.name if section.grade else "غير محدد",
                    })
                
                # جلب إحصائيات الفصل
                attendance_stats = await get_section_attendance_stats(db, section.id, target_date)
                
                # بناء بيانات الفصل
                section_data = {
                    "section_id": section.id,
                    "stage_name": section.grade.stage.name if section.grade and section.grade.stage else "غير محدد",
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                    "section_name": section.name or "فصل",
                    "enrolled_count": len(students),
                    "periods_today": periods,
                    "attendance_stats": attendance_stats,
                    "students": students_data
                }
                
                result["sections"].append(section_data)
                result["all_students"].extend(students_data)
                
            except Exception as e:
                print(f"Error processing section {section.name}: {str(e)}")
                continue
        
        return result
        
    except Exception as e:
        print(f"FATAL ERROR in get_dashboard_data: {str(e)}")
        result["error"] = str(e)
        return result


def get_week_days(target_date: str) -> List[Dict]:
    """إنشاء بيانات أيام الأسبوع"""
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
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "sick": 0,
            "late_arrival": 0
        })
    
    return week_days


# ============================================================================
# واجهات API
# ============================================================================

@router.get("/api/dashboard/data")
async def api_dashboard_data(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    target_date: str | None = None,
):
    """واجهة API للحصول على بيانات الداشبورد"""
    try:
        selected_date = target_date or _date.today().isoformat()
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        return {
            "success": True,
            "data": dashboard_data,
            "date": selected_date
        }
    
    except Exception as e:
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
    """تحديث حالة الحضور لحصة معينة (API)"""
    try:
        valid_statuses = ["present", "absent", "late", "excused", "sick", "late_arrival"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail="حالة غير صحيحة")
        
        attendance = await db.execute(
            select(StudentAttendance).where(StudentAttendance.schedule_entry_id == schedule_entry_id)
        )
        attendance = attendance.scalar_one_or_none()
        
        if attendance:
            attendance.status = status
            attendance.updated_by = user.id
            attendance.updated_at = datetime.now()
        else:
            attendance = StudentAttendance(
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
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")


@router.get("/api/section/{section_id}/students")
async def api_section_students(
    section_id: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    """API لجلب قائمة الطلاب في فصل معين"""
    try:
        students = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .order_by(Student.full_name)
        )
        students = students.scalars().all()
        
        return {
            "success": True,
            "students": [
                {
                    "id": student.id,
                    "name": student.full_name,
                }
                for student in students
            ]
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
