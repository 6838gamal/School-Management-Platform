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
        
        # 2. جلب الفصول
        print("📚 Fetching sections...")
        sections = await db.execute(
            select(Section).where(Section.school_id == user.school_id)
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
                "student_count": student_count
            })
            print(f"   📚 Section: {section.name} - {student_count} students")
        
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
                "section_id": str(record.section_id) if hasattr(record, 'section_id') else None,
                "period_number": getattr(record, 'period_number', None),
                "schedule_date": str(getattr(record, 'schedule_date', None)) if hasattr(record, 'schedule_date') else None
            })
        
        # 6. اختبار قاعدة البيانات
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
                    .where(Section.school_id == user.school_id)
                    .limit(5)
                )
                for s in sections.scalars().all():
                    results["tables"]["sections"]["sample"].append({
                        "id": str(s.id),
                        "name": s.name,
                        "school_id": str(s.school_id) if s.school_id else None,
                        "grade_id": str(s.grade_id) if s.grade_id else None,
                        "stage_id": str(s.stage_id) if s.stage_id else None,
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
        
        # 5. التحقق من جدول ScheduleEntry
        try:
            schedule_count = await db.scalar(select(func.count(ScheduleEntry.id)))
            results["tables"]["schedule_entries"] = {
                "count": schedule_count or 0,
                "sample": [],
                "columns": []
            }
            
            if schedule_count and schedule_count > 0:
                records = await db.execute(select(ScheduleEntry).limit(5))
                for r in records.scalars().all():
                    results["tables"]["schedule_entries"]["sample"].append({
                        "id": str(r.id),
                        "section_id": str(r.section_id) if hasattr(r, 'section_id') and r.section_id else None,
                        "subject_id": str(r.subject_id) if hasattr(r, 'subject_id') and r.subject_id else None,
                        "teacher_id": str(r.teacher_id) if hasattr(r, 'teacher_id') and r.teacher_id else None,
                        "period_number": getattr(r, 'period_number', None),
                        "schedule_date": str(getattr(r, 'schedule_date', None)) if hasattr(r, 'schedule_date') else None,
                        "day": getattr(r, 'day', None),
                    })
                
                # عرض أعمدة الجدول
                sample_record = await db.execute(select(ScheduleEntry).limit(1))
                sample = sample_record.scalar_one_or_none()
                if sample:
                    results["tables"]["schedule_entries"]["columns"] = [
                        c for c in dir(sample) 
                        if not c.startswith('_') and not callable(getattr(sample, c))
                    ]
            print(f"✅ ScheduleEntry: {schedule_count or 0}")
        except Exception as e:
            results["errors"].append(f"ScheduleEntry error: {str(e)}")
            print(f"❌ ScheduleEntry error: {str(e)}")
        
        # 6. اختبار الاتصال بقاعدة البيانات
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
        
        # 2. جلب الفصول
        try:
            print("📚 Fetching sections...")
            sections_result = await db.execute(
                select(Section)
                .options(selectinload(Section.stage), selectinload(Section.grade))
                .where(Section.school_id == user.school_id)
                .order_by(Section.stage_id, Section.grade_id, Section.name)
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
                    "stage_id": str(section.stage_id) if section.stage_id else None,
                    "stage_name": section.stage.name if section.stage else None,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "grade_name": section.grade.name if section.grade else None,
                    "student_count": student_count,
                    "school_id": str(section.school_id) if section.school_id else None,
                }
                result["sections"].append(section_info)
                print(f"   📚 Section: {section.name} - Grade: {section.grade.name if section.grade else 'None'} - {student_count} students")
                
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
                        "schedule_entry_id": str(a.schedule_entry_id) if hasattr(a, 'schedule_entry_id') and a.schedule_entry_id else None,
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
        
        # 5. جلب بيانات الجدول
        try:
            print("📅 Fetching schedule data...")
            total_schedule = await db.scalar(
                select(func.count(ScheduleEntry.id))
            ) or 0
            
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
                        "schedule_date": str(getattr(s, 'schedule_date', None)) if hasattr(s, 'schedule_date') else None,
                        "day": getattr(s, 'day', None),
                    }
                    for s in schedule_records
                ]
            }
            print(f"✅ Total schedule records: {total_schedule}")
        except Exception as e:
            error_msg = f"Error fetching schedule: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()
        
        # 6. اختبار الاتصال بقاعدة البيانات
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
        
        # 1. إنشاء مراحل
        stages = []
        for stage_name in MOCK_STAGES:
            stage = Stage(
                id=str(uuid.uuid4()),
                name=stage_name,
                school_id=user.school_id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            stages.append(stage)
            db.add(stage)
        
        await db.flush()
        print(f"✅ Created {len(stages)} stages")
        
        # 2. إنشاء صفوف
        grades = []
        for i, grade_name in enumerate(MOCK_GRADES, 1):
            grade = Grade(
                id=str(uuid.uuid4()),
                name=grade_name,
                level=i,
                school_id=user.school_id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            grades.append(grade)
            db.add(grade)
        
        await db.flush()
        print(f"✅ Created {len(grades)} grades")
        
        # 3. إنشاء فصول
        sections = []
        for stage in stages[:2]:
            for grade in grades[:2]:
                for section_name in MOCK_SECTIONS[:2]:
                    section = Section(
                        id=str(uuid.uuid4()),
                        name=section_name,
                        stage_id=stage.id,
                        grade_id=grade.id,
                        school_id=user.school_id,
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    sections.append(section)
                    db.add(section)
        
        await db.flush()
        print(f"✅ Created {len(sections)} sections")
        
        # 4. إنشاء معلمين
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
        
        # 5. إنشاء مواد
        subjects = []
        for subject_name in MOCK_SUBJECTS[:5]:
            subject = Subject(
                id=str(uuid.uuid4()),
                name=subject_name,
                school_id=user.school_id,
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            subjects.append(subject)
            db.add(subject)
        
        await db.flush()
        print(f"✅ Created {len(subjects)} subjects")
        
        # 6. إنشاء طلاب
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
        
        # 7. إنشاء جدول دراسي
        schedule_entries = []
        today = _date.today()
        
        for section in sections:
            for period in range(1, 4):
                subject = random.choice(subjects)
                teacher = random.choice(teachers)
                
                # إنشاء حصص للأيام القادمة
                for day_offset in range(5):
                    schedule_date = today + timedelta(days=day_offset)
                    # تخطي الجمعة والسبت
                    if schedule_date.weekday() >= 4:
                        continue
                    
                    entry = ScheduleEntry(
                        id=str(uuid.uuid4()),
                        section_id=section.id,
                        subject_id=subject.id,
                        teacher_id=teacher.id,
                        period_number=period,
                        schedule_date=schedule_date,
                        day=schedule_date.weekday(),
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    schedule_entries.append(entry)
                    db.add(entry)
        
        await db.flush()
        print(f"✅ Created {len(schedule_entries)} schedule entries")
        
        # 8. إنشاء سجلات حضور
        attendance_records = []
        today = _date.today()
        
        for student in students[:30]:
            for day_offset in range(3):
                record_date = today - timedelta(days=day_offset)
                # تخطي الجمعة والسبت
                if record_date.weekday() >= 4:
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
        print(f"   Stages: {len(stages)}")
        print(f"   Grades: {len(grades)}")
        print(f"   Sections: {len(sections)}")
        print(f"   Teachers: {len(teachers)}")
        print(f"   Subjects: {len(subjects)}")
        print(f"   Students: {len(students)}")
        print(f"   Schedule entries: {len(schedule_entries)}")
        print(f"   Attendance records: {len(attendance_records)}")
        print("=" * 80)
        
        return JSONResponse({
            "status": "success",
            "message": "تم إنشاء بيانات وهمية بنجاح",
            "counts": {
                "stages": len(stages),
                "grades": len(grades),
                "sections": len(sections),
                "teachers": len(teachers),
                "subjects": len(subjects),
                "students": len(students),
                "schedule_entries": len(schedule_entries),
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
    جلب إحصائيات الحضور لفصل معين في تاريخ محدد مع تسجيل تفصيلي
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


async def get_dashboard_data(db: AsyncSession, school_id: str, target_date: str) -> Dict[str, Any]:
    """
    جلب جميع بيانات الداشبورد من قاعدة البيانات مع تسجيل تفصيلي
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
        
        # 2. جلب الفصول
        print("🔍 Step 2: Fetching sections...")
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
        print(f"✅ Found {len(sections)} sections")
        
        if not sections:
            print("⚠️ No sections found")
            result["error"] = "لا توجد فصول مسجلة في هذه المدرسة"
            return result
        
        # 3. معالجة كل فصل
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
                periods = await get_section_periods(db, section.id, target_date)
                
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
                
                # معالجة الحصص
                periods_data = []
                for period in periods:
                    subject_name = "غير محدد"
                    if hasattr(period, 'subject_id') and period.subject_id:
                        subject_result = await db.execute(
                            select(Subject).where(Subject.id == period.subject_id)
                        )
                        subject = subject_result.scalar_one_or_none()
                        if subject:
                            subject_name = subject.name[:15]
                    
                    teacher_name = "غير محدد"
                    if hasattr(period, 'teacher_id') and period.teacher_id:
                        teacher_result = await db.execute(
                            select(Teacher).where(Teacher.id == period.teacher_id)
                        )
                        teacher = teacher_result.scalar_one_or_none()
                        if teacher:
                            teacher_name = teacher.full_name or teacher.name or "معلم"
                    
                    attendance = await get_period_attendance(db, period.id)
                    status = attendance.status if attendance else "unknown"
                    status_config = get_status_config(status)
                    
                    periods_data.append({
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
                        "attendance_stats": {
                            "present": 0, "absent": 0, "late": 0,
                            "excused": 0, "sick": 0, "late_arrival": 0
                        }
                    })
                
                # جلب إحصائيات الفصل
                attendance_stats = await get_section_attendance_stats(db, section.id, target_date)
                
                # بناء بيانات الفصل
                section_data = {
                    "section_id": section.id,
                    "stage_name": section.stage.name if section.stage else "غير محدد",
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                    "section_name": section.name or "فصل",
                    "enrolled_count": len(students),
                    "periods_today": periods_data,
                    "attendance_stats": attendance_stats,
                    "students": students_data
                }
                
                result["sections"].append(section_data)
                result["all_students"].extend(students_data)
                
                print(f"      ✅ Added {len(students_data)} students, {len(periods_data)} periods")
                
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


async def get_section_periods(db: AsyncSession, section_id: str, target_date: str) -> List[ScheduleEntry]:
    """
    جلب الحصص لفصل في تاريخ محدد مع محاولة حقول تاريخ مختلفة
    """
    print(f"            🔍 Fetching periods for section {section_id}, date {target_date}")
    
    try:
        # التحقق من وجود ScheduleEntry في قاعدة البيانات
        count_result = await db.execute(
            select(func.count(ScheduleEntry.id))
        )
        total_count = count_result.scalar() or 0
        print(f"            📊 Total ScheduleEntry records in DB: {total_count}")
        
        if total_count == 0:
            print(f"            ⚠️ No ScheduleEntry records found")
            return []
            
    except Exception as e:
        print(f"            ❌ Error checking ScheduleEntry table: {str(e)}")
        return []
    
    # محاولة حقول تاريخ مختلفة
    date_fields = ['schedule_date', 'date', 'day', 'period_date', 'session_date', 'class_date', 'entry_date']
    
    for field in date_fields:
        try:
            # التحقق من وجود الحقل في النموذج
            if not hasattr(ScheduleEntry, field):
                continue
                
            print(f"            🔍 Trying date field: '{field}'")
            
            query = select(ScheduleEntry).where(
                ScheduleEntry.section_id == section_id,
                getattr(ScheduleEntry, field) == target_date
            ).order_by(getattr(ScheduleEntry, 'period_number', ScheduleEntry.id))
            
            result = await db.execute(query)
            periods = result.scalars().all()
            
            if periods:
                print(f"            ✅ Found {len(periods)} periods using field '{field}'")
                for p in periods[:3]:
                    print(f"               - Period: {getattr(p, 'period_number', '?')}, Subject: {p.subject_id}")
                return periods
            else:
                print(f"            ℹ️ No periods found using field '{field}'")
                
        except Exception as e:
            print(f"            ❌ Error querying with field '{field}': {str(e)}")
            continue
    
    # إذا لم يتم العثور على حصص بالتاريخ، نحاول جلب جميع الحصص لهذا الفصل
    print(f"            ⚠️ No periods found with date filter, returning all periods for section")
    try:
        result = await db.execute(
            select(ScheduleEntry)
            .where(ScheduleEntry.section_id == section_id)
            .order_by(getattr(ScheduleEntry, 'period_number', ScheduleEntry.id))
        )
        periods = result.scalars().all()
        print(f"            ✅ Found {len(periods)} total periods (no date filter)")
        return periods
    except Exception as e:
        print(f"            ❌ Error getting all periods: {str(e)}")
        return []


async def process_period_data(db: AsyncSession, period: ScheduleEntry) -> Dict[str, Any]:
    """
    معالجة بيانات حصة واحدة
    """
    try:
        subject_name = "غير محدد"
        if period.subject_id:
            subject_result = await db.execute(
                select(Subject).where(Subject.id == period.subject_id)
            )
            subject = subject_result.scalar_one_or_none()
            if subject:
                subject_name = subject.name[:8]
        
        teacher_name = "غير محدد"
        if period.teacher_id:
            teacher_result = await db.execute(
                select(Teacher).where(Teacher.id == period.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = teacher.full_name or teacher.name or "معلم"
        
        attendance = await get_period_attendance(db, period.id)
        status = attendance.status if attendance else "unknown"
        status_config = get_status_config(status)
        
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
            "attendance_stats": {
                "present": 0, "absent": 0, "late": 0,
                "excused": 0, "sick": 0, "late_arrival": 0
            }
        }
    
    except Exception as e:
        print(f"❌ Error processing period {period.id}: {str(e)}")
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
        # جلب الحضور المرتبط بالجدول الدراسي
        # افترض أن StudentAttendance لديه schedule_entry_id
        if hasattr(StudentAttendance, 'schedule_entry_id'):
            result = await db.execute(
                select(StudentAttendance)
                .where(StudentAttendance.schedule_entry_id == schedule_entry_id)
            )
            return result.scalars().first()
        else:
            # إذا لم يكن هناك حقل schedule_entry_id، نحاول جلب الحضور المرتبط بالجدول
            print(f"            ⚠️ StudentAttendance has no schedule_entry_id field")
            return None
    except Exception as e:
        print(f"⚠️ Could not query attendance for period {schedule_entry_id}: {e}")
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
