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
from app.models.academics import Section, Subject, Grade, Stage, Period, AcademicYear
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
    print("=" * 80)
    print("🏓 Ping test - Router is working!")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    return {"status": "ok", "message": "Deputy dashboard router is working!", "timestamp": datetime.now().isoformat()}


@router.get("/test-log")
async def test_log(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
):
    """
    مسار اختبار للتأكد من أن التسجيل يعمل
    """
    print("=" * 80)
    print("🧪 TEST LOG - This is a test log message")
    print(f"👤 User ID: {user.id}")
    print(f"🏫 School ID: {user.school_id}")
    print(f"📧 Email: {getattr(user, 'email', 'N/A')}")
    print(f"📛 Full Name: {getattr(user, 'full_name', 'N/A')}")
    print("=" * 80)
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


@router.get("/debug/simple")
async def debug_simple(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    مسار تصحيح بسيط لعرض البيانات الخام
    """
    print("=" * 80)
    print("🐛 DEBUG SIMPLE - STARTING")
    print(f"👤 User ID: {user.id}")
    print(f"🏫 School ID: {user.school_id}")
    print("=" * 80)
    
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
        # 1. جلب المدرسة
        print("📚 Fetching school...")
        school = await db.execute(
            select(School).where(School.id == user.school_id)
        )
        school = school.scalar_one_or_none()
        
        if school:
            result["school"] = {
                "id": str(school.id),
                "name": school.name
            }
            print(f"✅ School found: {school.name}")
        else:
            result["errors"].append("School not found")
            print("❌ School not found")
        
        # 2. جلب الفصول مع العلاقات
        print("📚 Fetching sections with relations...")
        sections = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == user.school_id)
        )
        sections = sections.scalars().all()
        print(f"✅ Found {len(sections)} sections")
        
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
            print(f"   📚 Section: {section.name} - Grade: {section.grade.name if section.grade else 'None'} - {student_count} students")
        
        # 3. جلب الطلاب
        print("👥 Fetching students...")
        students = await db.execute(
            select(Student).where(Student.school_id == user.school_id).limit(20)
        )
        students = students.scalars().all()
        print(f"✅ Found {len(students)} students (sample)")
        
        for student in students:
            result["students"].append({
                "id": str(student.id),
                "name": student.full_name,
                "section_id": str(student.section_id) if student.section_id else None
            })
            print(f"   👤 Student: {student.full_name} - Section: {student.section_id}")
        
        # 4. جلب سجلات الحضور (StudentAttendance)
        print("📊 Fetching attendance records...")
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
        
        # 5. جلب سجلات الجدول
        print("📅 Fetching schedule records...")
        schedule_records = await db.execute(
            select(ScheduleEntry).limit(10)
        )
        schedule = schedule_records.scalars().all()
        
        for record in schedule:
            result["schedule"].append({
                "id": str(record.id),
                "schedule_id": str(record.schedule_id) if hasattr(record, 'schedule_id') else None,
                "day_of_week": getattr(record, 'day_of_week', None),
                "period_id": getattr(record, 'period_id', None),
                "subject_id": getattr(record, 'subject_id', None),
                "teacher_id": getattr(record, 'teacher_id', None),
            })
        
        # 6. جلب سجلات Schedule
        print("📅 Fetching schedules...")
        schedules_result = await db.execute(
            select(Schedule).where(Schedule.school_id == user.school_id)
        )
        schedules = schedules_result.scalars().all()
        result["schedules"] = [
            {
                "id": str(s.id),
                "name": s.name,
                "section_id": str(s.section_id),
                "year_id": str(s.year_id),
                "is_active": s.is_active
            }
            for s in schedules
        ]
        print(f"✅ Found {len(schedules)} schedules")
        
        # 7. اختبار قاعدة البيانات
        print("🔗 Testing database connection...")
        db_result = await db.execute(text("SELECT 1"))
        result["database"] = {
            "connected": True,
            "test_result": db_result.scalar() == 1
        }
        print("✅ Database connection successful")
        
        print("=" * 80)
        print(f"✅ DEBUG COMPLETE - {len(result['errors'])} errors")
        print("=" * 80)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/debug/db-test")
async def debug_db_test(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    اختبار قاعدة البيانات وعرض معلومات مفصلة عن الجداول
    """
    print("=" * 80)
    print("🔍 DEBUG DB TEST - STARTING")
    print(f"👤 User ID: {user.id}")
    print(f"🏫 School ID: {user.school_id}")
    print("=" * 80)
    
    results = {
        "user": {
            "id": str(user.id),
            "school_id": str(user.school_id) if user.school_id else None,
            "email": getattr(user, 'email', None),
            "full_name": getattr(user, 'full_name', None),
        },
        "tables": {},
        "errors": []
    }
    
    try:
        # 1. التحقق من جدول School
        try:
            school_count = await db.scalar(select(func.count(School.id)))
            results["tables"]["schools"] = {
                "count": school_count or 0,
                "sample": []
            }
            
            if school_count and school_count > 0:
                schools = await db.execute(select(School).limit(5))
                for s in schools.scalars().all():
                    results["tables"]["schools"]["sample"].append({
                        "id": str(s.id),
                        "name": s.name,
                        "code": getattr(s, 'code', None)
                    })
            print(f"✅ Schools: {school_count or 0}")
        except Exception as e:
            results["errors"].append(f"Schools error: {str(e)}")
            print(f"❌ Schools error: {str(e)}")
        
        # 2. التحقق من جدول Section
        try:
            section_count = await db.scalar(select(func.count(Section.id)))
            results["tables"]["sections"] = {
                "count": section_count or 0,
                "sample": []
            }
            
            if section_count and section_count > 0:
                sections = await db.execute(
                    select(Section)
                    .options(
                        selectinload(Section.grade).selectinload(Grade.stage)
                    )
                    .where(Section.school_id == user.school_id)
                    .limit(5)
                )
                for s in sections.scalars().all():
                    results["tables"]["sections"]["sample"].append({
                        "id": str(s.id),
                        "name": s.name,
                        "school_id": str(s.school_id) if s.school_id else None,
                        "grade_id": str(s.grade_id) if s.grade_id else None,
                        "grade_name": s.grade.name if s.grade else None,
                        "stage_name": s.grade.stage.name if s.grade and s.grade.stage else None,
                    })
            print(f"✅ Sections: {section_count or 0}")
        except Exception as e:
            results["errors"].append(f"Sections error: {str(e)}")
            print(f"❌ Sections error: {str(e)}")
        
        # 3. التحقق من جدول Student
        try:
            student_count = await db.scalar(select(func.count(Student.id)))
            results["tables"]["students"] = {
                "count": student_count or 0,
                "sample": []
            }
            
            if student_count and student_count > 0:
                students = await db.execute(
                    select(Student)
                    .where(Student.school_id == user.school_id)
                    .limit(5)
                )
                for s in students.scalars().all():
                    results["tables"]["students"]["sample"].append({
                        "id": str(s.id),
                        "name": s.full_name,
                        "section_id": str(s.section_id) if s.section_id else None,
                        "school_id": str(s.school_id) if s.school_id else None,
                    })
            print(f"✅ Students: {student_count or 0}")
        except Exception as e:
            results["errors"].append(f"Students error: {str(e)}")
            print(f"❌ Students error: {str(e)}")
        
        # 4. التحقق من جدول StudentAttendance
        try:
            attendance_count = await db.scalar(select(func.count(StudentAttendance.id)))
            results["tables"]["student_attendance"] = {
                "count": attendance_count or 0,
                "sample": []
            }
            
            if attendance_count and attendance_count > 0:
                records = await db.execute(select(StudentAttendance).limit(5))
                for r in records.scalars().all():
                    results["tables"]["student_attendance"]["sample"].append({
                        "id": str(r.id),
                        "student_id": str(r.student_id) if hasattr(r, 'student_id') else None,
                        "status": getattr(r, 'status', None),
                        "date": str(getattr(r, 'date', None)) if hasattr(r, 'date') else None,
                    })
            print(f"✅ StudentAttendance: {attendance_count or 0}")
        except Exception as e:
            results["errors"].append(f"StudentAttendance error: {str(e)}")
            print(f"❌ StudentAttendance error: {str(e)}")
        
        # 5. التحقق من جدول Schedule
        try:
            schedule_count = await db.scalar(select(func.count(Schedule.id)))
            results["tables"]["schedules"] = {
                "count": schedule_count or 0,
                "sample": []
            }
            
            if schedule_count and schedule_count > 0:
                records = await db.execute(
                    select(Schedule)
                    .where(Schedule.school_id == user.school_id)
                    .limit(5)
                )
                for r in records.scalars().all():
                    results["tables"]["schedules"]["sample"].append({
                        "id": str(r.id),
                        "name": r.name,
                        "section_id": str(r.section_id),
                        "year_id": str(r.year_id),
                        "is_active": r.is_active
                    })
            print(f"✅ Schedules: {schedule_count or 0}")
        except Exception as e:
            results["errors"].append(f"Schedules error: {str(e)}")
            print(f"❌ Schedules error: {str(e)}")
        
        # 6. التحقق من جدول ScheduleEntry
        try:
            entries_count = await db.scalar(select(func.count(ScheduleEntry.id)))
            results["tables"]["schedule_entries"] = {
                "count": entries_count or 0,
                "sample": []
            }
            
            if entries_count and entries_count > 0:
                records = await db.execute(select(ScheduleEntry).limit(5))
                for r in records.scalars().all():
                    results["tables"]["schedule_entries"]["sample"].append({
                        "id": str(r.id),
                        "schedule_id": str(r.schedule_id),
                        "day_of_week": r.day_of_week,
                        "period_id": str(r.period_id),
                        "subject_id": str(r.subject_id),
                        "teacher_id": str(r.teacher_id),
                        "room_id": str(r.room_id),
                    })
            print(f"✅ ScheduleEntry: {entries_count or 0}")
        except Exception as e:
            results["errors"].append(f"ScheduleEntry error: {str(e)}")
            print(f"❌ ScheduleEntry error: {str(e)}")
        
        # 7. اختبار الاتصال بقاعدة البيانات
        try:
            db_result = await db.execute(text("SELECT 1"))
            results["database"] = {
                "connected": True,
                "test_result": db_result.scalar() == 1
            }
            print("✅ Database connection successful")
        except Exception as e:
            results["errors"].append(f"Database connection error: {str(e)}")
            results["database"] = {"connected": False, "error": str(e)}
            print(f"❌ Database connection error: {str(e)}")
        
        print("=" * 80)
        print(f"🔍 DEBUG DB TEST COMPLETE - {len(results['errors'])} errors")
        print("=" * 80)
        
        return JSONResponse(results)
        
    except Exception as e:
        print(f"❌ Fatal error in debug_db_test: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/debug/raw")
async def debug_raw(
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    عرض البيانات الخام من قاعدة البيانات بشكل مفصل
    """
    try:
        print("=" * 80)
        print("🔍 DEBUG RAW DATA - STARTING")
        print(f"👤 User ID: {user.id}")
        print(f"🏫 School ID: {user.school_id}")
        print("=" * 80)
        
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
            print("📚 Fetching school...")
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
                print(f"✅ School found: {school.name}")
            else:
                result["errors"].append(f"School not found with ID: {user.school_id}")
                print(f"❌ School not found with ID: {user.school_id}")
        except Exception as e:
            error_msg = f"Error fetching school: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        # 2. جلب الفصول مع العلاقات
        try:
            print("📚 Fetching sections with relations...")
            sections_result = await db.execute(
                select(Section)
                .options(
                    selectinload(Section.grade).selectinload(Grade.stage)
                )
                .where(Section.school_id == user.school_id)
                .order_by(Section.grade_id, Section.name)
            )
            sections = sections_result.scalars().all()
            print(f"✅ Found {len(sections)} sections")
            
            for section in sections:
                student_count = await db.scalar(
                    select(func.count(Student.id))
                    .where(Student.section_id == section.id)
                ) or 0
                
                section_info = {
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "grade_name": section.grade.name if section.grade else None,
                    "stage_name": section.grade.stage.name if section.grade and section.grade.stage else None,
                    "student_count": student_count,
                    "school_id": str(section.school_id) if section.school_id else None,
                }
                result["sections"].append(section_info)
                print(f"   📚 Section: {section.name} - Grade: {section.grade.name if section.grade else 'None'} - Stage: {section.grade.stage.name if section.grade and section.grade.stage else 'None'} - {student_count} students")
                
        except Exception as e:
            error_msg = f"Error fetching sections: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        # 3. جلب الطلاب
        try:
            print("👥 Fetching students...")
            total_students = await db.scalar(
                select(func.count(Student.id))
                .where(Student.school_id == user.school_id)
            ) or 0
            
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
            print(f"✅ Total students: {total_students}")
        except Exception as e:
            error_msg = f"Error fetching students: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        # 4. جلب بيانات الحضور (StudentAttendance)
        try:
            print("📊 Fetching attendance data...")
            total_attendance = await db.scalar(
                select(func.count(StudentAttendance.id))
            ) or 0
            
            attendance_result = await db.execute(
                select(StudentAttendance)
                .limit(20)
            )
            attendance_records = attendance_result.scalars().all()
            
            result["attendance"] = {
                "total": total_attendance,
                "sample": [
                    {
                        "id": str(a.id),
                        "student_id": str(a.student_id) if hasattr(a, 'student_id') and a.student_id else None,
                        "status": getattr(a, 'status', None),
                        "date": str(getattr(a, 'date', None)) if hasattr(a, 'date') else None,
                        "created_at": str(getattr(a, 'created_at', None)) if hasattr(a, 'created_at') else None,
                    }
                    for a in attendance_records
                ]
            }
            print(f"✅ Total attendance records: {total_attendance}")
        except Exception as e:
            error_msg = f"Error fetching attendance: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        # 5. جلب بيانات Schedule
        try:
            print("📅 Fetching schedules...")
            total_schedules = await db.scalar(
                select(func.count(Schedule.id))
                .where(Schedule.school_id == user.school_id)
            ) or 0
            
            schedules_result = await db.execute(
                select(Schedule)
                .where(Schedule.school_id == user.school_id)
                .limit(20)
            )
            schedules = schedules_result.scalars().all()
            
            result["schedules"] = {
                "total": total_schedules,
                "sample": [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "section_id": str(s.section_id),
                        "year_id": str(s.year_id),
                        "is_active": s.is_active,
                    }
                    for s in schedules
                ]
            }
            print(f"✅ Total schedules: {total_schedules}")
        except Exception as e:
            error_msg = f"Error fetching schedules: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        # 6. جلب بيانات ScheduleEntry
        try:
            print("📅 Fetching schedule entries...")
            total_entries = await db.scalar(
                select(func.count(ScheduleEntry.id))
            ) or 0
            
            entries_result = await db.execute(
                select(ScheduleEntry)
                .limit(20)
            )
            entries = entries_result.scalars().all()
            
            result["schedule_entries"] = {
                "total": total_entries,
                "sample": [
                    {
                        "id": str(e.id),
                        "schedule_id": str(e.schedule_id),
                        "day_of_week": e.day_of_week,
                        "period_id": str(e.period_id),
                        "subject_id": str(e.subject_id),
                        "teacher_id": str(e.teacher_id),
                        "room_id": str(e.room_id),
                    }
                    for e in entries
                ]
            }
            print(f"✅ Total schedule entries: {total_entries}")
        except Exception as e:
            error_msg = f"Error fetching schedule entries: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        # 7. اختبار الاتصال بقاعدة البيانات
        try:
            print("🔗 Testing database connection...")
            db_result = await db.execute(text("SELECT 1"))
            result["database"] = {
                "connected": True,
                "test_result": db_result.scalar() == 1
            }
            print("✅ Database connection successful")
        except Exception as e:
            error_msg = f"Database connection error: {str(e)}"
            result["errors"].append(error_msg)
            result["database"] = {"connected": False, "error": str(e)}
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        print("=" * 80)
        print(f"🔍 DEBUG RAW COMPLETE - {len(result['errors'])} errors found")
        print("=" * 80)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"❌ Fatal error in debug_raw: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/debug/generate-mock-data")
async def generate_mock_data(
    user: CurrentUser = Depends(require_permission("session_lifecycle.edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    توليد بيانات وهمية للاختبار
    """
    try:
        print("=" * 80)
        print("🔄 GENERATING MOCK DATA")
        print(f"👤 User ID: {user.id}")
        print(f"🏫 School ID: {user.school_id}")
        print("=" * 80)
        
        # التحقق من وجود بيانات
        section_count = await db.scalar(select(func.count(Section.id)).where(Section.school_id == user.school_id))
        if section_count and section_count > 0:
            return JSONResponse({
                "status": "warning",
                "message": f"هناك {section_count} فصول موجودة بالفعل. لن يتم إنشاء بيانات وهمية لتجنب التكرار.",
                "existing_sections": section_count
            })
        
        # 1. إنشاء سنة دراسية
        year = AcademicYear(
            id=str(uuid.uuid4()),
            name="العام الدراسي 2024-2025",
            school_id=user.school_id,
            start_date="2024-09-01",
            end_date="2025-06-30",
            is_current=True,
            is_active=True,
            created_by=user.id,
            updated_by=user.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(year)
        await db.flush()
        print(f"✅ Created academic year: {year.name}")
        
        # 2. إنشاء مراحل
        stages = []
        for stage_name in MOCK_STAGES:
            stage = Stage(
                id=str(uuid.uuid4()),
                name=stage_name,
                school_id=user.school_id,
                year_id=year.id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            stages.append(stage)
            db.add(stage)
        
        await db.flush()
        print(f"✅ Created {len(stages)} stages")
        
        # 3. إنشاء صفوف
        grades = []
        for i, grade_name in enumerate(MOCK_GRADES, 1):
            grade = Grade(
                id=str(uuid.uuid4()),
                name=grade_name,
                order=i,
                school_id=user.school_id,
                stage_id=stages[i % len(stages)].id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            grades.append(grade)
            db.add(grade)
        
        await db.flush()
        print(f"✅ Created {len(grades)} grades")
        
        # 4. إنشاء فصول
        sections = []
        for grade in grades[:2]:
            for section_name in MOCK_SECTIONS[:2]:
                section = Section(
                    id=str(uuid.uuid4()),
                    name=section_name,
                    grade_id=grade.id,
                    school_id=user.school_id,
                    capacity=30,
                    is_active=True,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                sections.append(section)
                db.add(section)
        
        await db.flush()
        print(f"✅ Created {len(sections)} sections")
        
        # 5. إنشاء معلمين
        teachers = []
        for teacher_name in MOCK_TEACHERS[:5]:
            teacher = Teacher(
                id=str(uuid.uuid4()),
                name=teacher_name,
                full_name=teacher_name,
                school_id=user.school_id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            teachers.append(teacher)
            db.add(teacher)
        
        await db.flush()
        print(f"✅ Created {len(teachers)} teachers")
        
        # 6. إنشاء مواد
        subjects = []
        for subject_name in MOCK_SUBJECTS[:5]:
            subject = Subject(
                id=str(uuid.uuid4()),
                name=subject_name,
                school_id=user.school_id,
                is_active=True,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            subjects.append(subject)
            db.add(subject)
        
        await db.flush()
        print(f"✅ Created {len(subjects)} subjects")
        
        # 7. إنشاء حصص (Periods)
        periods = []
        for i in range(1, 7):
            period = Period(
                id=str(uuid.uuid4()),
                name=f"الحصة {i}",
                order=i,
                start_time=f"{7 + i}:00",
                end_time=f"{7 + i + 1}:00",
                school_id=user.school_id,
                is_break=False,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            periods.append(period)
            db.add(period)
        
        await db.flush()
        print(f"✅ Created {len(periods)} periods")
        
        # 8. إنشاء طلاب
        students = []
        for section in sections:
            for student_name in MOCK_STUDENTS[:3]:
                student = Student(
                    id=str(uuid.uuid4()),
                    full_name=student_name,
                    section_id=section.id,
                    school_id=user.school_id,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                students.append(student)
                db.add(student)
        
        await db.flush()
        print(f"✅ Created {len(students)} students")
        
        # 9. إنشاء جدول دراسي (Schedule)
        schedules = []
        for section in sections:
            schedule = Schedule(
                id=str(uuid.uuid4()),
                name=f"جدول {section.name}",
                section_id=section.id,
                year_id=year.id,
                school_id=user.school_id,
                is_active=True,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            schedules.append(schedule)
            db.add(schedule)
        
        await db.flush()
        print(f"✅ Created {len(schedules)} schedules")
        
        # 10. إنشاء مدخلات الجدول (ScheduleEntry)
        entries_count = 0
        for schedule in schedules:
            for day in range(5):  # الأحد إلى الخميس
                for period in periods[:4]:  # 4 حصص في اليوم
                    subject = random.choice(subjects)
                    teacher = random.choice(teachers)
                    
                    entry = ScheduleEntry(
                        id=str(uuid.uuid4()),
                        schedule_id=schedule.id,
                        day_of_week=day,
                        period_id=period.id,
                        subject_id=subject.id,
                        teacher_id=teacher.id,
                        room_id="default_room",
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(entry)
                    entries_count += 1
        
        await db.flush()
        print(f"✅ Created {entries_count} schedule entries")
        
        # 11. إنشاء سجلات حضور
        attendance_records = []
        today = _date.today()
        
        for student in students[:30]:
            for day_offset in range(3):
                record_date = today - timedelta(days=day_offset)
                if record_date.weekday() >= 5:  # تخطي الجمعة والسبت
                    continue
                
                status = random.choices(
                    MOCK_STATUSES,
                    weights=[50, 20, 10, 10, 5, 5],
                    k=1
                )[0]
                
                attendance = StudentAttendance(
                    id=str(uuid.uuid4()),
                    student_id=student.id,
                    status=status,
                    date=record_date,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                attendance_records.append(attendance)
                db.add(attendance)
        
        await db.commit()
        print(f"✅ Created {len(attendance_records)} attendance records")
        
        print("=" * 80)
        print("✅ MOCK DATA GENERATION COMPLETE")
        print(f"   Academic Year: {year.name}")
        print(f"   Stages: {len(stages)}")
        print(f"   Grades: {len(grades)}")
        print(f"   Sections: {len(sections)}")
        print(f"   Teachers: {len(teachers)}")
        print(f"   Subjects: {len(subjects)}")
        print(f"   Periods: {len(periods)}")
        print(f"   Students: {len(students)}")
        print(f"   Schedules: {len(schedules)}")
        print(f"   Schedule entries: {entries_count}")
        print(f"   Attendance records: {len(attendance_records)}")
        print("=" * 80)
        
        return JSONResponse({
            "status": "success",
            "message": "تم إنشاء بيانات وهمية بنجاح",
            "counts": {
                "academic_year": year.name,
                "stages": len(stages),
                "grades": len(grades),
                "sections": len(sections),
                "teachers": len(teachers),
                "subjects": len(subjects),
                "periods": len(periods),
                "students": len(students),
                "schedules": len(schedules),
                "schedule_entries": entries_count,
                "attendance_records": len(attendance_records)
            }
        })
        
    except Exception as e:
        print(f"❌ Error generating mock data: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/debug/fix-all")
async def fix_all_data(
    request: Request,
    user: CurrentUser = Depends(require_permission("session_lifecycle.edit")),
    db: AsyncSession = Depends(get_db),
):
    """
    إصلاح جميع البيانات: ربط الطلاب، إنشاء معلمين، مواد، جدول، حضور
    """
    try:
        print("=" * 80)
        print("🔧 FIX ALL DATA - STARTING")
        print(f"👤 User ID: {user.id}")
        print(f"🏫 School ID: {user.school_id}")
        print("=" * 80)
        
        result = {
            "status": "success",
            "messages": [],
            "students_fixed": 0,
            "teachers_created": 0,
            "subjects_created": 0,
            "periods_created": 0,
            "schedules_created": 0,
            "schedule_entries_created": 0,
            "attendance_created": 0,
            "academic_year_created": False
        }
        
        # ============================================================
        # 1. التأكد من وجود سنة دراسية
        # ============================================================
        print("\n📅 Step 1: Checking academic year...")
        year_result = await db.execute(
            select(AcademicYear)
            .where(
                AcademicYear.school_id == user.school_id,
                AcademicYear.is_current == True
            )
            .limit(1)
        )
        year = year_result.scalar_one_or_none()
        
        if not year:
            year = AcademicYear(
                id=str(uuid.uuid4()),
                name="العام الدراسي 2024-2025",
                school_id=user.school_id,
                start_date="2024-09-01",
                end_date="2025-06-30",
                is_current=True,
                is_active=True,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(year)
            await db.flush()
            result["academic_year_created"] = True
            result["messages"].append("تم إنشاء سنة دراسية جديدة")
            print(f"   ✅ Created academic year: {year.name}")
        else:
            print(f"   ✅ Using existing academic year: {year.name}")
        
        # ============================================================
        # 2. التأكد من وجود فصل
        # ============================================================
        print("\n📚 Step 2: Checking sections...")
        sections_result = await db.execute(
            select(Section).where(Section.school_id == user.school_id)
        )
        sections = sections_result.scalars().all()
        
        if not sections:
            # إنشاء مرحلة
            stage = Stage(
                id=str(uuid.uuid4()),
                name="المرحلة الابتدائية",
                school_id=user.school_id,
                year_id=year.id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(stage)
            await db.flush()
            
            # إنشاء صف
            grade = Grade(
                id=str(uuid.uuid4()),
                name="الصف الأول",
                order=1,
                school_id=user.school_id,
                stage_id=stage.id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(grade)
            await db.flush()
            
            # إنشاء فصل
            section = Section(
                id=str(uuid.uuid4()),
                name="أ",
                grade_id=grade.id,
                school_id=user.school_id,
                capacity=30,
                is_active=True,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(section)
            await db.flush()
            sections = [section]
            result["messages"].append("تم إنشاء فصل جديد")
            print(f"   ✅ Created section: {section.name}")
        else:
            section = sections[0]
            print(f"   ✅ Using existing section: {section.name}")
        
        # ============================================================
        # 3. ربط الطلاب بالفصل
        # ============================================================
        print("\n👥 Step 3: Fixing students...")
        students_result = await db.execute(
            select(Student)
            .where(
                Student.school_id == user.school_id,
                Student.section_id.is_(None)
            )
        )
        students = students_result.scalars().all()
        
        for student in students:
            student.section_id = section.id
            result["students_fixed"] += 1
            print(f"   ✅ {student.full_name} -> {section.name}")
        
        await db.flush()
        if result["students_fixed"] > 0:
            result["messages"].append(f"تم ربط {result['students_fixed']} طالب بالفصل {section.name}")
        else:
            result["messages"].append("جميع الطلاب مرتبطون بالفعل بفصول")
        
        # ============================================================
        # 4. إنشاء معلمين إذا لم يوجد
        # ============================================================
        print("\n👨‍🏫 Step 4: Creating teachers...")
        teachers_result = await db.execute(
            select(Teacher).where(Teacher.school_id == user.school_id)
        )
        teachers = teachers_result.scalars().all()
        
        if not teachers:
            default_teachers = [
                "أحمد محمد",
                "سارة خالد", 
                "محمد علي",
                "نورة أحمد"
            ]
            for name in default_teachers:
                teacher = Teacher(
                    id=str(uuid.uuid4()),
                    name=name,
                    full_name=name,
                    school_id=user.school_id,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(teacher)
                result["teachers_created"] += 1
            await db.flush()
            result["messages"].append(f"تم إنشاء {result['teachers_created']} معلم")
            print(f"   ✅ Created {result['teachers_created']} teachers")
        else:
            print(f"   ✅ Using {len(teachers)} existing teachers")
        
        # جلب المعلمين مرة أخرى
        teachers_result = await db.execute(
            select(Teacher).where(Teacher.school_id == user.school_id)
        )
        teachers = teachers_result.scalars().all()
        
        # ============================================================
        # 5. إنشاء مواد إذا لم توجد
        # ============================================================
        print("\n📚 Step 5: Creating subjects...")
        subjects_result = await db.execute(
            select(Subject).where(Subject.school_id == user.school_id)
        )
        subjects = subjects_result.scalars().all()
        
        if not subjects:
            default_subjects = [
                "اللغة العربية",
                "الرياضيات",
                "العلوم",
                "اللغة الإنجليزية",
                "التربية الإسلامية"
            ]
            for name in default_subjects:
                subject = Subject(
                    id=str(uuid.uuid4()),
                    name=name,
                    school_id=user.school_id,
                    is_active=True,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(subject)
                result["subjects_created"] += 1
            await db.flush()
            result["messages"].append(f"تم إنشاء {result['subjects_created']} مادة")
            print(f"   ✅ Created {result['subjects_created']} subjects")
        else:
            print(f"   ✅ Using {len(subjects)} existing subjects")
        
        # جلب المواد مرة أخرى
        subjects_result = await db.execute(
            select(Subject).where(Subject.school_id == user.school_id)
        )
        subjects = subjects_result.scalars().all()
        
        # ============================================================
        # 6. إنشاء حصص (Periods)
        # ============================================================
        print("\n⏰ Step 6: Creating periods...")
        periods_result = await db.execute(
            select(Period).where(Period.school_id == user.school_id)
        )
        periods = periods_result.scalars().all()
        
        if not periods:
            for i in range(1, 7):
                period = Period(
                    id=str(uuid.uuid4()),
                    name=f"الحصة {i}",
                    order=i,
                    start_time=f"{7 + i}:00",
                    end_time=f"{7 + i + 1}:00",
                    school_id=user.school_id,
                    is_break=False,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(period)
                result["periods_created"] += 1
            await db.flush()
            result["messages"].append(f"تم إنشاء {result['periods_created']} حصة دراسية")
            print(f"   ✅ Created {result['periods_created']} periods")
        else:
            print(f"   ✅ Using {len(periods)} existing periods")
        
        # جلب الحصص مرة أخرى
        periods_result = await db.execute(
            select(Period).where(Period.school_id == user.school_id)
        )
        periods = periods_result.scalars().all()
        
        # ============================================================
        # 7. إنشاء جدول دراسي (Schedule)
        # ============================================================
        print("\n📅 Step 7: Creating schedules...")
        
        # حذف الجداول القديمة
        await db.execute(
            text("DELETE FROM schedules WHERE school_id = :school_id"),
            {"school_id": user.school_id}
        )
        await db.flush()
        
        # إنشاء جدول لكل فصل
        for sec in sections:
            schedule = Schedule(
                id=str(uuid.uuid4()),
                name=f"جدول {sec.name}",
                section_id=sec.id,
                year_id=year.id,
                school_id=user.school_id,
                is_active=True,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(schedule)
            result["schedules_created"] += 1
        
        await db.flush()
        result["messages"].append(f"تم إنشاء {result['schedules_created']} جدول دراسي")
        print(f"   ✅ Created {result['schedules_created']} schedules")
        
        # جلب الجداول مرة أخرى
        schedules_result = await db.execute(
            select(Schedule).where(Schedule.school_id == user.school_id)
        )
        schedules = schedules_result.scalars().all()
        
        # ============================================================
        # 8. إنشاء مدخلات الجدول (ScheduleEntry)
        # ============================================================
        print("\n📝 Step 8: Creating schedule entries...")
        
        entries_count = 0
        for schedule in schedules:
            for day in range(5):  # الأحد (0) إلى الخميس (4)
                for period in periods[:4]:  # 4 حصص في اليوم
                    subject = random.choice(subjects) if subjects else None
                    teacher = random.choice(teachers) if teachers else None
                    
                    if not subject or not teacher:
                        continue
                    
                    entry = ScheduleEntry(
                        id=str(uuid.uuid4()),
                        schedule_id=schedule.id,
                        day_of_week=day,
                        period_id=period.id,
                        subject_id=subject.id,
                        teacher_id=teacher.id,
                        room_id="default_room",
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(entry)
                    entries_count += 1
        
        await db.flush()
        result["schedule_entries_created"] = entries_count
        if entries_count > 0:
            result["messages"].append(f"تم إنشاء {entries_count} حصة دراسية في الجداول")
        print(f"   ✅ Created {entries_count} schedule entries")
        
        # ============================================================
        # 9. إنشاء سجلات حضور
        # ============================================================
        print("\n📊 Step 9: Creating attendance records...")
        
        # جلب جميع الطلاب في الفصول
        students_result = await db.execute(
            select(Student).where(Student.section_id.in_([s.id for s in sections]))
        )
        all_students = students_result.scalars().all()
        
        attendance_count = 0
        statuses = ["present", "present", "present", "absent", "late", "excused"]
        
        for student in all_students:
            for day_offset in range(5):  # آخر 5 أيام
                record_date = _date.today() - timedelta(days=day_offset)
                if record_date.weekday() >= 5:  # تخطي الجمعة والسبت
                    continue
                
                # التحقق من عدم وجود تكرار
                existing = await db.execute(
                    select(StudentAttendance)
                    .where(
                        StudentAttendance.student_id == student.id,
                        StudentAttendance.date == record_date
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                status = random.choice(statuses)
                attendance = StudentAttendance(
                    id=str(uuid.uuid4()),
                    student_id=student.id,
                    status=status,
                    date=record_date,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(attendance)
                attendance_count += 1
        
        await db.commit()
        result["attendance_created"] = attendance_count
        if attendance_count > 0:
            result["messages"].append(f"تم إنشاء {attendance_count} سجل حضور")
        print(f"   ✅ Created {attendance_count} attendance records")
        
        # ============================================================
        # 10. عرض النتائج النهائية
        # ============================================================
        print("\n" + "=" * 80)
        print("✅ FIX ALL DATA - COMPLETE")
        print(f"   Academic year created: {result['academic_year_created']}")
        print(f"   Students fixed: {result['students_fixed']}")
        print(f"   Teachers created: {result['teachers_created']}")
        print(f"   Subjects created: {result['subjects_created']}")
        print(f"   Periods created: {result['periods_created']}")
        print(f"   Schedules created: {result['schedules_created']}")
        print(f"   Schedule entries: {result['schedule_entries_created']}")
        print(f"   Attendance records: {result['attendance_created']}")
        print("=" * 80)
        
        return templates.TemplateResponse(
            "deputy/fix_result.html",
            {
                "request": request,
                "title": "نتيجة إصلاح البيانات",
                "result": result,
                "user": user,
            },
        )
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return templates.TemplateResponse(
            "errors/error.html",
            {
                "request": request,
                "title": "خطأ",
                "message": f"حدث خطأ: {str(e)}",
                "user": user,
            },
            status_code=500
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
        print("=" * 80)
        print("🚀 DEPUTY DASHBOARD - STARTING")
        print(f"👤 User ID: {user.id}")
        print(f"🏫 School ID: {user.school_id}")
        print(f"📅 Target date: {target_date}")
        print("=" * 80)
        
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
        
        print(f"📊 Dashboard data prepared: {len(dashboard_data.get('sections', []))} sections")
        print(f"📊 Total students: {len(dashboard_data.get('all_students', []))}")
        if dashboard_data.get("error"):
            print(f"⚠️ Error: {dashboard_data['error']}")
        print("=" * 80)
        
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
    """
    لوحة تحكم الوكيل بتاريخ محدد
    """
    try:
        # التحقق من صحة التاريخ
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="تنسيق تاريخ غير صحيح. استخدم YYYY-MM-DD")
        
        print(f"📅 Deputy dashboard by date: {date}")
        
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
        print(f"👥 Fetching students for section: {section_id}")
        
        # جلب الفصل مع العلاقات
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
    """
    تسجيل الحضور والغياب للفصل - يتحكم فيها الوكيل فقط
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        print(f"📝 Attendance form for section: {section_id}, date: {selected_date}")
        
        # جلب الفصل مع العلاقات
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
        print(f"❌ Error in section_attendance: {str(e)}")
        traceback.print_exc()
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
        print(f"🔄 Transfer students from section: {section_id}")
        
        # جلب الفصل الحالي مع العلاقات
        section_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.id == section_id)
        )
        current_section = section_result.scalar_one_or_none()
        
        if not current_section:
            raise HTTPException(status_code=404, detail="الفصل غير موجود")
        
        # جلب جميع الفصول الأخرى في المدرسة
        other_sections_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(
                Section.school_id == current_section.school_id,
                Section.id != section_id
            )
            .order_by(Section.grade_id, Section.name)
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
        print(f"❌ Error in transfer_students: {str(e)}")
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
    """
    عرض تقرير مفصل للفصل
    """
    try:
        selected_date = target_date or _date.today().isoformat()
        print(f"📊 Report for section: {section_id}, date: {selected_date}")
        
        # جلب الفصل مع العلاقات
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
        print(f"❌ Error in section_report: {str(e)}")
        traceback.print_exc()
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
        print(f"❌ Error in export_dashboard_pdf: {str(e)}")
        traceback.print_exc()
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
        print(f"❌ Error in export_report: {str(e)}")
        traceback.print_exc()
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
    print(f"            📊 Getting attendance stats for section {section_id}, date {target_date}")
    
    try:
        # جلب الطلاب في الفصل
        students_result = await db.execute(
            select(Student.id).where(Student.section_id == section_id)
        )
        student_ids = [row[0] for row in students_result.all()]
        
        if not student_ids:
            print(f"            ⚠️ No students found in section {section_id}")
            return {
                "present": 0, "absent": 0, "late": 0, "excused": 0,
                "sick": 0, "late_arrival": 0, "teacher_absent": 0,
                "substitute_required": 0, "other": 0, "total": 0
            }
        
        # جلب سجلات الحضور
        result = await db.execute(
            select(StudentAttendance.status, func.count(StudentAttendance.id))
            .where(
                StudentAttendance.student_id.in_(student_ids),
                StudentAttendance.date == target_date
            )
            .group_by(StudentAttendance.status)
        )
        
        stats = result.all()
        print(f"            ✅ Found {len(stats)} status groups")
        
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
        
        print(f"            ✅ Final stats: {attendance_stats}")
        return attendance_stats
    
    except Exception as e:
        print(f"❌ Error getting section attendance stats: {str(e)}")
        traceback.print_exc()
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
            select(StudentAttendance.status, func.count(StudentAttendance.id))
            .where(StudentAttendance.student_id == student_id)
            .group_by(StudentAttendance.status)
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
        print(f"❌ Error getting student stats for {student_id}: {str(e)}")
        return {
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "sick": 0,
            "late_arrival": 0,
            "total": 0
        }


async def get_section_periods_for_date(
    db: AsyncSession, 
    section_id: str, 
    school_id: str, 
    target_date: str
) -> List[Dict]:
    """
    جلب الحصص لفصل في تاريخ محدد باستخدام نموذج Schedule الصحيح
    """
    try:
        # 1. جلب الجدول النشط لهذا الفصل
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
        
        # 2. تحويل التاريخ إلى يوم الأسبوع
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        # Python: 0=إثنين, 6=أحد
        # نظامنا: 0=أحد, 1=إثنين, 2=ثلاثاء, 3=أربعاء, 4=خميس
        day_map = {6: 0, 0: 1, 1: 2, 2: 3, 3: 4}
        day_of_week = day_map.get(date_obj.weekday(), -1)
        
        if day_of_week < 0:
            return []  # يوم عطلة
        
        # 3. جلب الحصص لهذا اليوم
        entries_result = await db.execute(
            select(ScheduleEntry)
            .where(
                ScheduleEntry.schedule_id == schedule.id,
                ScheduleEntry.day_of_week == day_of_week
            )
            .order_by(ScheduleEntry.period_id)
        )
        entries = entries_result.scalars().all()
        
        # 4. تحويل البيانات
        periods = []
        for entry in entries:
            # جلب المادة
            subject_name = "غير محدد"
            if entry.subject_id:
                subject = await db.get(Subject, entry.subject_id)
                if subject:
                    subject_name = subject.name[:15]
            
            # جلب المعلم
            teacher_name = "غير محدد"
            if entry.teacher_id:
                teacher = await db.get(Teacher, entry.teacher_id)
                if teacher:
                    teacher_name = teacher.full_name or teacher.name or "معلم"
            
            # جلب رقم الحصة
            period_number = entry.period_id
            try:
                period = await db.get(Period, entry.period_id)
                if period:
                    period_number = period.order if hasattr(period, 'order') else period.name
            except:
                pass
            
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
        traceback.print_exc()
        return []


async def get_dashboard_data(db: AsyncSession, school_id: str, target_date: str) -> Dict[str, Any]:
    """
    جلب جميع بيانات الداشبورد من قاعدة البيانات
    """
    print("=" * 60)
    print(f"📊 STARTING get_dashboard_data()")
    print(f"   school_id: {school_id}")
    print(f"   target_date: {target_date}")
    print("=" * 60)
    
    result = {
        "date": target_date,
        "sections": [],
        "all_students": [],
        "analytics": {
            "present": 0, "absent": 0, "late": 0, "late_arrival": 0,
            "excused": 0, "sick": 0, "teacher_absent": 0,
            "substitute_required": 0, "other": 0, "total_records": 0
        },
        "error": None
    }
    
    try:
        # 1. جلب المدرسة
        print("🔍 Step 1: Fetching school...")
        school_result = await db.execute(
            select(School).where(School.id == school_id)
        )
        school = school_result.scalar_one_or_none()
        
        if not school:
            print(f"❌ School not found with ID: {school_id}")
            result["error"] = f"المدرسة غير موجودة: {school_id}"
            return result
        
        print(f"✅ School found: {school.name}")
        
        # 2. جلب الفصول مع العلاقات
        print("🔍 Step 2: Fetching sections with relations...")
        sections_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == school_id)
            .order_by(
                Section.grade_id,
                Section.name
            )
        )
        sections = sections_result.scalars().all()
        print(f"✅ Found {len(sections)} sections")
        
        if not sections:
            print("⚠️ No sections found")
            result["error"] = "لا توجد فصول مسجلة في هذه المدرسة"
            return result
        
        # 3. جلب الطلاب لكل فصل
        print("🔍 Step 3: Processing sections...")
        
        for idx, section in enumerate(sections):
            print(f"   📚 Processing section {idx+1}/{len(sections)}: {section.name}")
            
            try:
                # جلب الطلاب في الفصل
                students_result = await db.execute(
                    select(Student)
                    .where(Student.section_id == section.id)
                    .order_by(Student.full_name)
                )
                students = students_result.scalars().all()
                
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
                    
                    # تحديث الإحصائيات الكلية
                    for key in ["present", "absent", "late", "excused", "sick", "late_arrival"]:
                        if key in stats:
                            result["analytics"][key] = result["analytics"].get(key, 0) + stats.get(key, 0)
                            result["analytics"]["total_records"] = result["analytics"].get("total_records", 0) + stats.get(key, 0)
                    
                    students_data.append({
                        "id": student.id,
                        "name": student.full_name,
                        "code": getattr(student, 'code', ''),
                        "status": status,
                        "status_label": MOCK_STATUS_LABELS.get(status, status),
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
                
                print(f"      ✅ Added {len(students_data)} students, {len(periods)} periods")
                
            except Exception as e:
                print(f"      ❌ Error processing section {section.name}: {str(e)}")
                traceback.print_exc()
        
        print("=" * 60)
        print(f"📊 FINAL RESULTS:")
        print(f"   Total sections: {len(result['sections'])}")
        print(f"   Total students: {len(result['all_students'])}")
        print(f"   Analytics: {result['analytics']}")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {str(e)}")
        traceback.print_exc()
        result["error"] = str(e)
        return result


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
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "sick": 0,
            "late_arrival": 0
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
        },
        "error": None
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
        print(f"❌ Error in API: {str(e)}")
        traceback.print_exc()
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
        valid_statuses = ["present", "absent", "late", "excused", "sick", "late_arrival"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail="حالة غير صحيحة")
        
        # البحث عن سجل الحضور
        attendance_result = await db.execute(
            select(StudentAttendance).where(StudentAttendance.schedule_entry_id == schedule_entry_id)
        )
        attendance = attendance_result.scalar_one_or_none()
        
        if attendance:
            attendance.status = status
            attendance.updated_by = user.id
            attendance.updated_at = datetime.now()
        else:
            # إنشاء سجل جديد
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
        print(f"❌ Error updating attendance: {str(e)}")
        traceback.print_exc()
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
        print(f"❌ Error getting students: {str(e)}")
        traceback.print_exc()
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
        student_result = await db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(status_code=404, detail="الطالب غير موجود")
        
        section_result = await db.execute(
            select(Section).where(Section.id == target_section_id)
        )
        target_section = section_result.scalar_one_or_none()
        
        if not target_section:
            raise HTTPException(status_code=404, detail="الفصل المستهدف غير موجود")
        
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
        print(f"❌ Error transferring student: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ: {str(e)}")
