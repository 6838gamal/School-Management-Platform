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
import random
import traceback

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.models.schools import School
from app.models.academics import Section, Subject, Grade, Stage
from app.models.users import User 
from app.models.students import Student 
from app.models.teachers import Teacher
from app.models.schedules import Schedule, ScheduleEntry

# ============================================================================
# تكوين التسجيل (Logging Configuration)
# ============================================================================

# تكوين logging للطباعة على stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# تعيين مستوى السجلات لجميع الـ loggers
for name in ['app', 'app.routes', 'app.routes.deputy_dashboard']:
    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(logging.DEBUG)

router = APIRouter(prefix="/deputy", tags=["deputy-dashboard"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
# القسم 0: مسارات الاختبار والتصحيح (Test & Debug Routes)
# ============================================================================

@router.get("/ping")
async def ping():
    """
    مسار اختبار بسيط للتأكد من أن الـ router يعمل
    """
    logger.info("🏓 Ping test - Router is working!")
    return {"status": "ok", "message": "Deputy dashboard router is working!", "timestamp": datetime.now().isoformat()}


@router.get("/test-log")
async def test_log(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
):
    """
    مسار اختبار للتأكد من أن التسجيل يعمل
    """
    logger.info("=" * 80)
    logger.info("🧪 TEST LOG - This is a test log message")
    logger.info(f"👤 User ID: {user.id}")
    logger.info(f"🏫 School ID: {user.school_id}")
    logger.info(f"📧 Email: {getattr(user, 'email', 'N/A')}")
    logger.info(f"📛 Full Name: {getattr(user, 'full_name', 'N/A')}")
    logger.info("=" * 80)
    return {
        "status": "ok", 
        "message": "Log test successful",
        "user": {
            "id": str(user.id),
            "school_id": str(user.school_id) if user.school_id else None,
            "email": getattr(user, 'email', None),
            "full_name": getattr(user, 'full_name', None),
        }
    }


@router.get("/debug/raw")
async def debug_raw(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    عرض البيانات الخام من قاعدة البيانات
    """
    try:
        logger.info("=" * 80)
        logger.info("🔍 DEBUG RAW DATA - STARTING")
        logger.info(f"👤 User ID: {user.id}")
        logger.info(f"🏫 School ID: {user.school_id}")
        logger.info("=" * 80)
        
        result = {
            "school": None,
            "sections": [],
            "students": [],
            "attendance": [],
            "schedule": [],
            "errors": []
        }
        
        # 1. جلب المدرسة
        try:
            logger.info("📚 Fetching school...")
            school_result = await db.execute(
                select(School).where(School.id == user.school_id)
            )
            school = school_result.scalar_one_or_none()
            
            if school:
                result["school"] = {
                    "id": str(school.id),
                    "name": school.name,
                    "code": getattr(school, 'code', None),
                    "address": getattr(school, 'address', None),
                    "phone": getattr(school, 'phone', None),
                }
                logger.info(f"✅ School found: {school.name}")
            else:
                result["errors"].append(f"School not found with ID: {user.school_id}")
                logger.error(f"❌ School not found with ID: {user.school_id}")
        except Exception as e:
            error_msg = f"Error fetching school: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 2. جلب الفصول
        try:
            logger.info("📚 Fetching sections...")
            sections_result = await db.execute(
                select(Section)
                .options(selectinload(Section.stage), selectinload(Section.grade))
                .where(Section.school_id == user.school_id)
                .order_by(Section.stage_id, Section.grade_id, Section.name)
            )
            sections = sections_result.scalars().all()
            logger.info(f"✅ Found {len(sections)} sections")
            
            for section in sections:
                # جلب عدد الطلاب في الفصل
                student_count = await db.scalar(
                    select(func.count(Student.id))
                    .where(Student.section_id == section.id)
                ) or 0
                
                section_info = {
                    "id": str(section.id),
                    "name": section.name,
                    "stage_id": str(section.stage_id) if section.stage_id else None,
                    "stage_name": section.stage.name if section.stage else None,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "grade_name": section.grade.name if section.grade else None,
                    "student_count": student_count,
                    "school_id": str(section.school_id) if section.school_id else None,
                }
                result["sections"].append(section_info)
                
        except Exception as e:
            error_msg = f"Error fetching sections: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 3. جلب الطلاب
        try:
            logger.info("👥 Fetching students...")
            total_students = await db.scalar(
                select(func.count(Student.id))
                .where(Student.school_id == user.school_id)
            ) or 0
            
            # جلب أول 50 طالب
            students_result = await db.execute(
                select(Student)
                .where(Student.school_id == user.school_id)
                .limit(50)
            )
            students = students_result.scalars().all()
            
            result["students"] = {
                "total": total_students,
                "sample": [
                    {
                        "id": str(s.id),
                        "name": s.full_name,
                        "section_id": str(s.section_id) if s.section_id else None,
                        "code": getattr(s, 'code', None),
                        "gender": getattr(s, 'gender', None),
                    }
                    for s in students
                ]
            }
            logger.info(f"✅ Total students: {total_students}")
        except Exception as e:
            error_msg = f"Error fetching students: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 4. جلب بيانات الحضور
        try:
            logger.info("📊 Fetching attendance data...")
            total_attendance = await db.scalar(
                select(func.count(Attendance.id))
            ) or 0
            
            # جلب عينة من سجلات الحضور
            attendance_result = await db.execute(
                select(Attendance)
                .limit(20)
            )
            attendance_records = attendance_result.scalars().all()
            
            result["attendance"] = {
                "total": total_attendance,
                "sample": [
                    {
                        "id": str(a.id),
                        "student_id": str(a.student_id) if hasattr(a, 'student_id') and a.student_id else None,
                        "schedule_entry_id": str(a.schedule_entry_id) if hasattr(a, 'schedule_entry_id') and a.schedule_entry_id else None,
                        "status": getattr(a, 'status', None),
                        "date": str(getattr(a, 'date', None)),
                        "created_at": str(getattr(a, 'created_at', None)),
                    }
                    for a in attendance_records
                ]
            }
            logger.info(f"✅ Total attendance records: {total_attendance}")
        except Exception as e:
            error_msg = f"Error fetching attendance: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 5. جلب بيانات الجدول
        try:
            logger.info("📅 Fetching schedule data...")
            total_schedule = await db.scalar(
                select(func.count(ScheduleEntry.id))
            ) or 0
            
            # جلب عينة من الجدول
            schedule_result = await db.execute(
                select(ScheduleEntry)
                .limit(20)
            )
            schedule_records = schedule_result.scalars().all()
            
            result["schedule"] = {
                "total": total_schedule,
                "sample": [
                    {
                        "id": str(s.id),
                        "section_id": str(s.section_id) if hasattr(s, 'section_id') and s.section_id else None,
                        "subject_id": str(s.subject_id) if hasattr(s, 'subject_id') and s.subject_id else None,
                        "teacher_id": str(s.teacher_id) if hasattr(s, 'teacher_id') and s.teacher_id else None,
                        "period_number": getattr(s, 'period_number', None),
                        "schedule_date": str(getattr(s, 'schedule_date', None)),
                        "day": getattr(s, 'day', None),
                    }
                    for s in schedule_records
                ]
            }
            logger.info(f"✅ Total schedule records: {total_schedule}")
        except Exception as e:
            error_msg = f"Error fetching schedule: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 6. اختبار الاتصال بقاعدة البيانات
        try:
            logger.info("🔗 Testing database connection...")
            result_db = await db.execute(text("SELECT 1"))
            result["database"] = {
                "connected": True,
                "test_result": result_db.scalar() == 1
            }
            logger.info("✅ Database connection successful")
        except Exception as e:
            error_msg = f"Database connection error: {str(e)}"
            result["errors"].append(error_msg)
            result["database"] = {"connected": False, "error": str(e)}
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 7. معلومات النظام
        result["system"] = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "router_prefix": "/deputy",
        }
        
        logger.info("=" * 80)
        logger.info(f"🔍 DEBUG RAW COMPLETE - {len(result['errors'])} errors found")
        logger.info("=" * 80)
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"❌ Fatal error in debug_raw: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


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
        logger.info("=" * 80)
        logger.info("🚀 DEPUTY DASHBOARD - STARTING")
        logger.info(f"👤 User ID: {user.id}")
        logger.info(f"🏫 School ID: {user.school_id}")
        logger.info(f"📅 Target date: {target_date}")
        logger.info("=" * 80)
        
        # تحديد التاريخ المستهدف
        selected_date = target_date or _date.today().isoformat()
        selected_month = selected_date[:7]
        
        # جلب بيانات الداشبورد
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        
        # جلب أيام الأسبوع
        week_days = get_mock_week_days(selected_date)
        
        # ========== إعداد بيانات الرسم البياني ==========
        analytics = dashboard_data.get("analytics", {})
        
        # إنشاء chart_data بشكل منفصل
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
        
        # إضافة chart_data إلى dashboard_data
        dashboard_data["chart_data"] = chart_data
        
        logger.info(f"📊 Dashboard data prepared: {len(dashboard_data.get('sections', []))} sections")
        logger.info(f"📊 Total students: {len(dashboard_data.get('all_students', []))}")
        logger.info("=" * 80)
        
        # ========== عرض القالب ==========
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
        
        logger.info(f"📅 Deputy dashboard by date: {date}")
        
        dashboard_data = await get_dashboard_data(db, user.school_id, date)
        selected_month = date[:7]
        week_days = get_mock_week_days(date)
        
        # ========== إعداد بيانات الرسم البياني ==========
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
# القسم 1.5: صفحة تصحيح الأخطاء (DEBUG)
# ============================================================================

@router.get("/dashboard/debug")
async def debug_dashboard(
    request: Request,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """
    صفحة تصحيح الأخطاء لعرض البيانات الأولية
    """
    try:
        logger.info("=" * 80)
        logger.info("🐛 DEBUG DASHBOARD - STARTING")
        logger.info("=" * 80)
        
        debug_data = {
            "user": {
                "id": str(user.id),
                "school_id": str(user.school_id) if user.school_id else None,
                "email": getattr(user, 'email', None),
                "full_name": getattr(user, 'full_name', None),
            },
            "school": None,
            "sections": [],
            "students": [],
            "attendance": {},
            "schedule": {},
            "errors": []
        }
        
        # 1. جلب المدرسة
        try:
            logger.info("🔍 Step 1: Fetching school...")
            school_result = await db.execute(
                select(School).where(School.id == user.school_id)
            )
            school = school_result.scalar_one_or_none()
            
            if school:
                debug_data["school"] = {
                    "id": str(school.id),
                    "name": school.name,
                    "code": getattr(school, 'code', None),
                }
                logger.info(f"✅ School found: {school.name}")
            else:
                debug_data["errors"].append(f"School not found with ID: {user.school_id}")
                logger.error(f"❌ School not found with ID: {user.school_id}")
        except Exception as e:
            error_msg = f"Error fetching school: {str(e)}"
            debug_data["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 2. جلب الفصول
        try:
            logger.info("🔍 Step 2: Fetching sections...")
            sections_result = await db.execute(
                select(Section)
                .options(selectinload(Section.stage), selectinload(Section.grade))
                .where(Section.school_id == user.school_id)
                .order_by(Section.stage_id, Section.grade_id, Section.name)
            )
            sections = sections_result.scalars().all()
            logger.info(f"✅ Found {len(sections)} sections")
            
            for section in sections:
                # جلب عدد الطلاب في الفصل
                student_count = await db.scalar(
                    select(func.count(Student.id))
                    .where(Student.section_id == section.id)
                ) or 0
                
                # جلب الطلاب (أول 10 فقط)
                students_result = await db.execute(
                    select(Student)
                    .where(Student.section_id == section.id)
                    .limit(10)
                )
                students = students_result.scalars().all()
                
                section_info = {
                    "id": str(section.id),
                    "name": section.name,
                    "stage_id": str(section.stage_id) if section.stage_id else None,
                    "stage_name": section.stage.name if section.stage else None,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "grade_name": section.grade.name if section.grade else None,
                    "student_count": student_count,
                    "students": [
                        {
                            "id": str(s.id),
                            "name": s.full_name,
                            "code": getattr(s, 'code', None)
                        }
                        for s in students
                    ]
                }
                debug_data["sections"].append(section_info)
                
        except Exception as e:
            error_msg = f"Error fetching sections: {str(e)}"
            debug_data["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 3. جلب جميع الطلاب
        try:
            logger.info("🔍 Step 3: Fetching all students...")
            total_students = await db.scalar(
                select(func.count(Student.id))
                .where(Student.school_id == user.school_id)
            ) or 0
            
            # جلب أول 20 طالب
            students_result = await db.execute(
                select(Student)
                .where(Student.school_id == user.school_id)
                .limit(20)
            )
            students = students_result.scalars().all()
            
            debug_data["students"] = {
                "total": total_students,
                "sample": [
                    {
                        "id": str(s.id),
                        "name": s.full_name,
                        "section_id": str(s.section_id) if s.section_id else None,
                        "code": getattr(s, 'code', None)
                    }
                    for s in students
                ]
            }
            logger.info(f"✅ Total students: {total_students}")
        except Exception as e:
            error_msg = f"Error fetching students: {str(e)}"
            debug_data["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 4. جلب بيانات الحضور
        try:
            logger.info("🔍 Step 4: Fetching attendance data...")
            total_attendance = await db.scalar(
                select(func.count(Attendance.id))
            ) or 0
            
            # جلب عينة من سجلات الحضور
            attendance_sample = await db.execute(
                select(Attendance)
                .limit(10)
            )
            attendance_records = attendance_sample.scalars().all()
            
            debug_data["attendance"] = {
                "total": total_attendance,
                "sample": [
                    {
                        "id": str(a.id),
                        "student_id": str(a.student_id) if hasattr(a, 'student_id') else None,
                        "schedule_entry_id": str(a.schedule_entry_id) if hasattr(a, 'schedule_entry_id') else None,
                        "status": getattr(a, 'status', None),
                        "date": str(getattr(a, 'date', None))
                    }
                    for a in attendance_records
                ]
            }
            logger.info(f"✅ Total attendance records: {total_attendance}")
        except Exception as e:
            error_msg = f"Error fetching attendance: {str(e)}"
            debug_data["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 5. جلب بيانات الجدول
        try:
            logger.info("🔍 Step 5: Fetching schedule data...")
            total_schedule = await db.scalar(
                select(func.count(ScheduleEntry.id))
            ) or 0
            
            # جلب عينة من الجدول
            schedule_sample = await db.execute(
                select(ScheduleEntry)
                .limit(10)
            )
            schedule_records = schedule_sample.scalars().all()
            
            debug_data["schedule"] = {
                "total": total_schedule,
                "sample": [
                    {
                        "id": str(s.id),
                        "section_id": str(s.section_id) if hasattr(s, 'section_id') else None,
                        "subject_id": str(s.subject_id) if hasattr(s, 'subject_id') else None,
                        "teacher_id": str(s.teacher_id) if hasattr(s, 'teacher_id') else None,
                        "period_number": getattr(s, 'period_number', None),
                        "schedule_date": str(getattr(s, 'schedule_date', None))
                    }
                    for s in schedule_records
                ]
            }
            logger.info(f"✅ Total schedule records: {total_schedule}")
        except Exception as e:
            error_msg = f"Error fetching schedule: {str(e)}"
            debug_data["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 6. اختبار الاتصال بقاعدة البيانات
        try:
            logger.info("🔍 Step 6: Testing database connection...")
            result = await db.execute(text("SELECT 1"))
            debug_data["database"] = {
                "connected": True,
                "test_result": result.scalar() == 1
            }
            logger.info("✅ Database connection successful")
        except Exception as e:
            error_msg = f"Database connection error: {str(e)}"
            debug_data["errors"].append(error_msg)
            debug_data["database"] = {"connected": False, "error": str(e)}
            logger.error(f"❌ {error_msg}", exc_info=True)
        
        # 7. عرض النتائج
        logger.info("=" * 80)
        logger.info(f"🐛 DEBUG COMPLETE - {len(debug_data['errors'])} errors found")
        logger.info("=" * 80)
        
        return templates.TemplateResponse(
            "deputy/debug.html",
            {
                **ctx,
                "request": request,
                "user": user,
                "debug_data": debug_data,
                "has_errors": len(debug_data["errors"]) > 0
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Fatal error in debug: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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
        logger.info(f"👥 Fetching students for section: {section_id}")
        
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
    ctx: dict = Depends(template_context),
    target_date: str | None = None,
):
    """
    تصدير لوحة التحكم كملف PDF
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        
        # ========== إعداد بيانات الرسم البياني ==========
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
    ctx: dict = Depends(template_context),
    target_date: str | None = None,
):
    """
    تصدير تقرير مفصل
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        dashboard_data = await get_dashboard_data(db, user.school_id, selected_date)
        
        # ========== إعداد بيانات الرسم البياني ==========
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
    جلب إحصائيات الحضور لفصل معين في تاريخ محدد مع تسجيل تفصيلي
    """
    logger.info(f"            📊 Getting attendance stats for section {section_id}, date {target_date}")
    
    try:
        # التحقق من وجود Attendance في قاعدة البيانات
        try:
            total_attendance = await db.scalar(
                select(func.count(Attendance.id))
            )
            logger.info(f"            📊 Total attendance records in DB: {total_attendance}")
        except Exception as e:
            logger.error(f"            ❌ Error counting attendance: {str(e)}")
            total_attendance = 0
        
        if total_attendance == 0:
            logger.warning(f"            ⚠️ No attendance records found in database")
            return {
                "present": 0, "absent": 0, "late": 0, "excused": 0,
                "sick": 0, "late_arrival": 0, "teacher_absent": 0,
                "substitute_required": 0, "other": 0, "total": 0
            }
        
        # محاولة الاستعلام مع ScheduleEntry
        try:
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
            logger.info(f"            ✅ Found {len(stats)} status groups via join")
            
        except Exception as e:
            logger.error(f"            ❌ Error with join query: {str(e)}")
            # محاولة استعلام بديل باستخدام student_id
            try:
                # جلب الطلاب في الفصل
                students_result = await db.execute(
                    select(Student.id)
                    .where(Student.section_id == section_id)
                )
                student_ids = [row[0] for row in students_result.all()]
                
                if student_ids:
                    result = await db.execute(
                        select(Attendance.status, func.count(Attendance.id))
                        .where(
                            Attendance.student_id.in_(student_ids),
                            Attendance.date == target_date
                        )
                        .group_by(Attendance.status)
                    )
                    stats = result.all()
                    logger.info(f"            ✅ Found {len(stats)} status groups via student_ids")
                else:
                    stats = []
            except Exception as e2:
                logger.error(f"            ❌ Error with alternative query: {str(e2)}")
                stats = []
        
        # بناء النتيجة
        attendance_stats = {
            "present": 0, "absent": 0, "late": 0, "excused": 0,
            "sick": 0, "late_arrival": 0, "teacher_absent": 0,
            "substitute_required": 0, "other": 0, "total": 0
        }
        
        for status, count in stats:
            if status in attendance_stats:
                attendance_stats[status] = count
            else:
                attendance_stats["other"] += count
            attendance_stats["total"] += count
        
        logger.info(f"            ✅ Final stats: {attendance_stats}")
        return attendance_stats
    
    except Exception as e:
        logger.error(f"❌ Error getting section attendance stats: {str(e)}", exc_info=True)
        return {
            "present": 0, "absent": 0, "late": 0, "excused": 0,
            "sick": 0, "late_arrival": 0, "teacher_absent": 0,
            "substitute_required": 0, "other": 0, "total": 0
        }


async def get_student_attendance_stats(db: AsyncSession, student_id: str) -> Dict[str, int]:
    """
    جلب إحصائيات الحضور لطالب معين
    """
    try:
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
        logger.error(f"❌ Error getting student stats for {student_id}: {str(e)}")
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
    جلب جميع بيانات الداشبورد من قاعدة البيانات مع تسجيل تفصيلي
    """
    logger.info("=" * 60)
    logger.info(f"📊 STARTING get_dashboard_data()")
    logger.info(f"   school_id: {school_id}")
    logger.info(f"   target_date: {target_date}")
    logger.info("=" * 60)
    
    try:
        # 1. التحقق من وجود المدرسة
        logger.info("🔍 Step 1: Checking school...")
        try:
            school_result = await db.execute(
                select(School).where(School.id == school_id)
            )
            school = school_result.scalar_one_or_none()
            
            if not school:
                logger.error(f"❌ School not found with ID: {school_id}")
                logger.info("💡 Returning empty dashboard data")
                return get_empty_dashboard_data(target_date)
            
            logger.info(f"✅ School found: {school.name} (ID: {school.id})")
            
        except Exception as e:
            logger.error(f"❌ Error fetching school: {str(e)}", exc_info=True)
            return get_empty_dashboard_data(target_date)
        
        # 2. جلب الفصول
        logger.info("🔍 Step 2: Fetching sections...")
        try:
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
            
            logger.info(f"✅ Found {len(sections)} sections")
            
            # تسجيل تفاصيل الفصول
            for idx, section in enumerate(sections):
                stage_name = section.stage.name if section.stage else "None"
                grade_name = section.grade.name if section.grade else "None"
                logger.info(f"   Section {idx+1}: ID={section.id}, Name={section.name}, Stage={stage_name}, Grade={grade_name}")
            
        except Exception as e:
            logger.error(f"❌ Error fetching sections: {str(e)}", exc_info=True)
            return get_empty_dashboard_data(target_date)
        
        if not sections:
            logger.warning(f"⚠️ No sections found for school: {school.name}")
            return get_empty_dashboard_data(target_date)
        
        # 3. معالجة كل فصل
        logger.info("🔍 Step 3: Processing sections...")
        dashboard_sections = []
        all_students = []
        analytics = {
            "present": 0, "absent": 0, "late": 0, "late_arrival": 0,
            "excused": 0, "sick": 0, "teacher_absent": 0,
            "substitute_required": 0, "other": 0, "total_records": 0
        }
        
        for idx, section in enumerate(sections):
            logger.info(f"   📚 Processing section {idx+1}/{len(sections)}: {section.name}")
            
            try:
                section_data = await process_section_data(db, section, target_date)
                
                # التحقق من نجاح المعالجة
                if section_data:
                    dashboard_sections.append(section_data)
                    
                    if section_data.get("students"):
                        all_students.extend(section_data["students"])
                        logger.info(f"      ✅ Added {len(section_data['students'])} students")
                    
                    # تحديث الإحصائيات
                    if section_data.get("attendance_stats"):
                        for key in analytics:
                            if key in section_data["attendance_stats"]:
                                analytics[key] += section_data["attendance_stats"].get(key, 0)
                    
                    logger.info(f"      ✅ Section processed successfully")
                else:
                    logger.warning(f"      ⚠️ Section data is empty for {section.name}")
                    
            except Exception as e:
                logger.error(f"      ❌ Error processing section {section.name}: {str(e)}", exc_info=True)
                # الاستمرار مع الفصل التالي
        
        # 4. النتيجة النهائية
        logger.info("=" * 60)
        logger.info(f"📊 FINAL RESULTS:")
        logger.info(f"   Total sections: {len(dashboard_sections)}")
        logger.info(f"   Total students: {len(all_students)}")
        logger.info(f"   Analytics: {analytics}")
        logger.info("=" * 60)
        
        return {
            "date": target_date,
            "sections": dashboard_sections,
            "all_students": all_students,
            "analytics": analytics
        }
    
    except Exception as e:
        logger.error(f"❌ FATAL ERROR in get_dashboard_data: {str(e)}", exc_info=True)
        return get_empty_dashboard_data(target_date)


async def process_section_data(db: AsyncSession, section: Section, target_date: str) -> Dict[str, Any]:
    """
    معالجة بيانات فصل واحد مع تسجيل تفصيلي
    """
    logger.info(f"      🔍 Processing section: {section.name} (ID: {section.id})")
    
    try:
        # 1. جلب عدد الطلاب
        logger.info(f"         📊 Getting student count...")
        try:
            students_count = await db.scalar(
                select(func.count(Student.id))
                .where(Student.section_id == section.id)
            ) or 0
            logger.info(f"         ✅ Students count: {students_count}")
        except Exception as e:
            logger.error(f"         ❌ Error getting student count: {str(e)}")
            students_count = 0
        
        # 2. جلب أسماء المرحلة والصف
        try:
            stage_name = section.stage.name if section.stage else "غير محدد"
            grade_name = section.grade.name if section.grade else "غير محدد"
            logger.info(f"         ✅ Stage: {stage_name}, Grade: {grade_name}")
        except Exception as e:
            logger.error(f"         ❌ Error getting stage/grade names: {str(e)}")
            stage_name = "خطأ"
            grade_name = "خطأ"
        
        # 3. جلب الحصص
        logger.info(f"         📖 Getting periods for date: {target_date}")
        try:
            periods = await get_section_periods(db, section.id, target_date)
            logger.info(f"         ✅ Found {len(periods)} periods")
        except Exception as e:
            logger.error(f"         ❌ Error getting periods: {str(e)}", exc_info=True)
            periods = []
        
        # 4. معالجة الحصص
        periods_data = []
        for period in periods:
            try:
                period_info = await process_period_data(db, period)
                periods_data.append(period_info)
            except Exception as e:
                logger.error(f"         ❌ Error processing period {period.id}: {str(e)}")
                # إضافة بيانات فارغة للحصة
                periods_data.append({
                    "subject_id": "",
                    "subject_name": "خطأ",
                    "teacher_name": "خطأ",
                    "indicator": "⚪",
                    "status_label": "خطأ",
                    "status": "unknown",
                    "schedule_entry_id": period.id,
                    "period_number": getattr(period, 'period_number', 0),
                    "attendance_id": None,
                    "is_attendance_recorded": False,
                    "attendance_stats": {}
                })
        
        # 5. جلب إحصائيات الحضور
        logger.info(f"         📊 Getting attendance stats...")
        try:
            attendance_stats = await get_section_attendance_stats(db, section.id, target_date)
            logger.info(f"         ✅ Attendance stats: {attendance_stats}")
        except Exception as e:
            logger.error(f"         ❌ Error getting attendance stats: {str(e)}")
            attendance_stats = {}
        
        # 6. جلب الطلاب
        logger.info(f"         👥 Getting students...")
        try:
            students_result = await db.execute(
                select(Student)
                .where(Student.section_id == section.id)
                .order_by(Student.full_name)
            )
            students = students_result.scalars().all()
            logger.info(f"         ✅ Found {len(students)} students")
            
            # طباعة أسماء الطلاب للتأكد
            for student in students[:5]:  # أول 5 طلاب فقط
                logger.info(f"            - {student.full_name} (ID: {student.id})")
            if len(students) > 5:
                logger.info(f"            ... and {len(students) - 5} more")
                
        except Exception as e:
            logger.error(f"         ❌ Error getting students: {str(e)}", exc_info=True)
            students = []
        
        # 7. معالجة بيانات الطلاب
        students_data = []
        for student in students:
            try:
                stats = await get_student_attendance_stats(db, student.id)
                
                # تحديد الحالة الحالية
                status = "unknown"
                if stats.get("total", 0) > 0:
                    if stats.get("present", 0) > stats.get("absent", 0) and stats.get("present", 0) > stats.get("late", 0):
                        status = "present"
                    elif stats.get("absent", 0) > stats.get("present", 0) and stats.get("absent", 0) > stats.get("late", 0):
                        status = "absent"
                    elif stats.get("late", 0) > 0:
                        status = "late"
                    elif stats.get("excused", 0) > 0:
                        status = "excused"
                    elif stats.get("sick", 0) > 0:
                        status = "sick"
                
                students_data.append({
                    "id": student.id,
                    "name": student.full_name,
                    "code": getattr(student, 'code', ''),
                    "status": status,
                    "status_label": MOCK_STATUS_LABELS.get(status, status),
                    "attendance": stats
                })
            except Exception as e:
                logger.error(f"         ❌ Error processing student {student.id}: {str(e)}")
                students_data.append({
                    "id": student.id,
                    "name": getattr(student, 'full_name', 'غير معروف'),
                    "code": getattr(student, 'code', ''),
                    "status": "unknown",
                    "status_label": "خطأ",
                    "attendance": {}
                })
        
        # 8. النتيجة النهائية
        result = {
            "section_id": section.id,
            "stage_name": stage_name,
            "grade_name": grade_name,
            "section_name": section.name or "فصل",
            "enrolled_count": students_count,
            "periods_today": periods_data,
            "attendance_stats": attendance_stats,
            "students": students_data
        }
        
        logger.info(f"         ✅ Section processing complete: {len(students_data)} students, {len(periods_data)} periods")
        return result
    
    except Exception as e:
        logger.error(f"❌ FATAL ERROR processing section {section.id}: {str(e)}", exc_info=True)
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
    logger.info(f"            🔍 Fetching periods for section {section_id}, date {target_date}")
    
    # قائمة بجميع الحقول الممكنة للتاريخ
    date_fields = [
        'schedule_date', 
        'date', 
        'day', 
        'period_date',
        'session_date',
        'class_date',
        'entry_date'
    ]
    
    # أولاً: التحقق من وجود الجدول
    try:
        # التحقق من وجود أي بيانات في الجدول
        count_result = await db.execute(
            select(func.count(ScheduleEntry.id))
            .where(ScheduleEntry.section_id == section_id)
        )
        total_count = count_result.scalar() or 0
        logger.info(f"            📊 Total ScheduleEntry records for section: {total_count}")
        
        if total_count == 0:
            logger.warning(f"            ⚠️ No ScheduleEntry records found for section {section_id}")
            return []
            
    except Exception as e:
        logger.error(f"            ❌ Error checking ScheduleEntry table: {str(e)}")
        return []
    
    # محاولة كل حقل تاريخ
    for field in date_fields:
        try:
            logger.info(f"            🔍 Trying date field: '{field}'")
            
            # بناء الاستعلام
            query = select(ScheduleEntry).where(
                ScheduleEntry.section_id == section_id,
                getattr(ScheduleEntry, field) == target_date
            ).order_by(getattr(ScheduleEntry, 'period_number', ScheduleEntry.id))
            
            result = await db.execute(query)
            periods = result.scalars().all()
            
            if periods:
                logger.info(f"            ✅ Found {len(periods)} periods using field '{field}'")
                # طباعة تفاصيل الحصص
                for p in periods[:3]:
                    logger.info(f"               - Period: {getattr(p, 'period_number', '?')}, Subject: {p.subject_id}")
                return periods
            else:
                logger.info(f"            ℹ️ No periods found using field '{field}'")
                
        except AttributeError as e:
            logger.warning(f"            ⚠️ Field '{field}' not found in ScheduleEntry: {e}")
            continue
        except Exception as e:
            logger.error(f"            ❌ Error querying with field '{field}': {str(e)}")
            continue
    
    # محاولة الحصول على جميع الحصص بدون تصفية بالتاريخ
    logger.warning(f"            ⚠️ No date field matched, returning all periods for section {section_id}")
    try:
        result = await db.execute(
            select(ScheduleEntry)
            .where(ScheduleEntry.section_id == section_id)
            .order_by(getattr(ScheduleEntry, 'period_number', ScheduleEntry.id))
        )
        periods = result.scalars().all()
        logger.info(f"            ✅ Found {len(periods)} total periods (no date filter)")
        return periods
    except Exception as e:
        logger.error(f"            ❌ Error getting all periods: {str(e)}")
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
            "period_number": getattr(period, 'period_number', 0),
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


# ============================================================================
# القسم 6: صفحة Debug HTML (نموذج القالب)
# ============================================================================

# يمكن إضافة قالب debug.html في مجلد templates/deputy/
# انظر التعليقات في نهاية الملف للحصول على محتوى القالب
