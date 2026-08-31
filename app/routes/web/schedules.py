"""Schedules web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Dict, Any
import uuid
import traceback
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.schedule_service import ScheduleService
from app.core.exceptions import NotFoundException, AppException

# إضافة النماذج المفقودة
from app.models.schedules import Schedule, ScheduleEntry
from app.models.academics import Section, Subject, Grade, Stage
from app.models.teachers import Teacher

router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# دوال مساعدة
# ============================================================

async def get_sections_with_details(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب الفصول مع تفاصيلها
    """
    try:
        result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.stage),
                selectinload(Section.grade)
            )
            .where(Section.school_id == school_id)
            .order_by(Section.stage_id, Section.grade_id, Section.name)
        )
        sections = result.scalars().all()
        
        return [
            {
                "id": str(section.id),
                "name": section.name,
                "stage_name": section.stage.name if section.stage else "غير محدد",
                "grade_name": section.grade.name if section.grade else "غير محدد",
                "full_name": f"{section.stage.name if section.stage else ''} - {section.grade.name if section.grade else ''} - {section.name}"
            }
            for section in sections
        ]
    except Exception as e:
        print(f"⚠️ Error in get_sections_with_details: {str(e)}")
        return []


async def get_academic_years(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب السنوات الدراسية
    """
    try:
        # محاولة جلب السنوات الدراسية من قاعدة البيانات
        from app.models.academics import AcademicYear
        result = await db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .order_by(AcademicYear.start_date.desc())
        )
        years = result.scalars().all()
        
        return [
            {
                "id": str(year.id),
                "name": year.name,
                "start_date": year.start_date,
                "end_date": year.end_date,
                "is_active": year.is_active if hasattr(year, 'is_active') else False
            }
            for year in years
        ]
    except ImportError:
        # إذا لم يكن هناك نموذج AcademicYear
        print("⚠️ AcademicYear model not found, returning empty list")
        return []
    except Exception as e:
        print(f"⚠️ Error in get_academic_years: {str(e)}")
        return []


async def get_subjects(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب المواد الدراسية
    """
    try:
        result = await db.execute(
            select(Subject)
            .where(Subject.school_id == school_id)
            .order_by(Subject.name)
        )
        subjects = result.scalars().all()
        
        return [
            {
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code if hasattr(subject, 'code') else None
            }
            for subject in subjects
        ]
    except Exception as e:
        print(f"⚠️ Error in get_subjects: {str(e)}")
        return []


async def get_teachers(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب المعلمين
    """
    try:
        result = await db.execute(
            select(Teacher)
            .where(Teacher.school_id == school_id)
            .order_by(Teacher.full_name)
        )
        teachers = result.scalars().all()
        
        return [
            {
                "id": str(teacher.id),
                "name": teacher.full_name or teacher.name,
                "email": teacher.email if hasattr(teacher, 'email') else None
            }
            for teacher in teachers
        ]
    except Exception as e:
        print(f"⚠️ Error in get_teachers: {str(e)}")
        return []


# ============================================================
# المسارات الرئيسية
# ============================================================

@router.get("")
async def schedules_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة الجداول الدراسية الرئيسية"""
    try:
        service = ScheduleService(db)
        schedules = await service.list_schedules(user.school_id)
        
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": schedules or [], 
                "type": "schedules",
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in schedules_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": [], 
                "type": "schedules",
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


@router.get("/list")
async def list_schedules(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة قائمة الجداول الدراسية"""
    try:
        service = ScheduleService(db)
        schedules = await service.list_schedules(user.school_id)
        
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": schedules or [], 
                "type": "schedules",
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in list_schedules: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": [], 
                "type": "schedules",
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


@router.get("/create")
async def create_schedule_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة إنشاء جدول جديد"""
    try:
        print("=" * 50)
        print("📄 صفحة إنشاء جدول جديد")
        print(f"   user_id: {user.id}")
        print(f"   school_id: {user.school_id}")
        print("=" * 50)
        
        # جلب البيانات المطلوبة
        sections = await get_sections_with_details(db, user.school_id)
        academic_years = await get_academic_years(db, user.school_id)
        subjects = await get_subjects(db, user.school_id)
        teachers = await get_teachers(db, user.school_id)
        
        print(f"✅ تم جلب {len(sections)} شعبة")
        print(f"✅ تم جلب {len(academic_years)} عام دراسي")
        print(f"✅ تم جلب {len(subjects)} مادة")
        print(f"✅ تم جلب {len(teachers)} معلم")
        
        # إذا لم توجد بيانات، عرض رسالة للمستخدم
        if not sections:
            print("⚠️ لا توجد شعب دراسية")
        
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "sections": sections,
                "academic_years": academic_years,
                "subjects": subjects,
                "teachers": teachers,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ خطأ في صفحة إنشاء الجدول: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "sections": [],
                "academic_years": [],
                "subjects": [],
                "teachers": [],
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


@router.get("/{schedule_id}/update")
async def update_schedule_page(
    request: Request,
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل جدول"""
    try:
        service = ScheduleService(db)
        schedule = await service.get_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="الجدول غير موجود")
        
        sections = await get_sections_with_details(db, user.school_id)
        academic_years = await get_academic_years(db, user.school_id)
        subjects = await get_subjects(db, user.school_id)
        teachers = await get_teachers(db, user.school_id)
        
        return templates.TemplateResponse(
            "schedules/update.html",
            {
                **ctx,
                "title": "تعديل جدول دراسي",
                "item": schedule,
                "sections": sections,
                "academic_years": academic_years,
                "subjects": subjects,
                "teachers": teachers,
                "error": None
            }
        )
    except HTTPException:
        raise
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Error in update_schedule_page: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"حدث خطأ: {str(e)}")


@router.get("/{schedule_id}/view")
async def view_schedule_page(
    request: Request,
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة عرض الجدول"""
    try:
        service = ScheduleService(db)
        schedule = await service.get_schedule_with_entries(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="الجدول غير موجود")
        
        # جلب الحصص (periods)
        periods = await get_periods(db, user.school_id)
        
        return templates.TemplateResponse(
            "schedules/view.html",
            {
                **ctx,
                "title": "عرض الجدول الدراسي",
                "schedule": schedule,
                "periods": periods,
                "days": ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"],
                "error": None
            }
        )
    except HTTPException:
        raise
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Error in view_schedule_page: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"حدث خطأ: {str(e)}")


# ============================================================
# دوال مساعدة إضافية لـ ScheduleService
# ============================================================

async def get_periods(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب الحصص الدراسية (الفترات)
    """
    try:
        # إذا كان هناك نموذج Period، استخدمه
        try:
            from app.models.academics import Period
            result = await db.execute(
                select(Period)
                .where(Period.school_id == school_id)
                .order_by(Period.number)
            )
            periods = result.scalars().all()
            
            return [
                {
                    "id": str(period.id),
                    "number": period.number,
                    "name": period.name,
                    "start_time": period.start_time if hasattr(period, 'start_time') else None,
                    "end_time": period.end_time if hasattr(period, 'end_time') else None
                }
                for period in periods
            ]
        except ImportError:
            # إذا لم يكن هناك نموذج Period
            print("⚠️ Period model not found, returning default periods")
            return [
                {"id": "1", "number": 1, "name": "الحصة الأولى"},
                {"id": "2", "number": 2, "name": "الحصة الثانية"},
                {"id": "3", "number": 3, "name": "الحصة الثالثة"},
                {"id": "4", "number": 4, "name": "الحصة الرابعة"},
                {"id": "5", "number": 5, "name": "الحصة الخامسة"},
                {"id": "6", "number": 6, "name": "الحصة السادسة"},
            ]
    except Exception as e:
        print(f"⚠️ Error in get_periods: {str(e)}")
        # إرجاع حصص افتراضية
        return [
            {"id": "1", "number": 1, "name": "الحصة الأولى"},
            {"id": "2", "number": 2, "name": "الحصة الثانية"},
            {"id": "3", "number": 3, "name": "الحصة الثالثة"},
            {"id": "4", "number": 4, "name": "الحصة الرابعة"},
            {"id": "5", "number": 5, "name": "الحصة الخامسة"},
            {"id": "6", "number": 6, "name": "الحصة السادسة"},
        ]


# ============================================================
# مسارات API للتصحيح
# ============================================================

@router.get("/debug/data")
async def debug_schedule_data(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    عرض بيانات الجداول للتصحيح
    """
    try:
        result = {
            "sections": await get_sections_with_details(db, user.school_id),
            "academic_years": await get_academic_years(db, user.school_id),
            "subjects": await get_subjects(db, user.school_id),
            "teachers": await get_teachers(db, user.school_id),
            "periods": await get_periods(db, user.school_id),
            "schedules": []
        }
        
        # جلب الجداول الموجودة
        try:
            service = ScheduleService(db)
            schedules = await service.list_schedules(user.school_id)
            result["schedules"] = schedules or []
        except Exception as e:
            result["schedules_error"] = str(e)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"❌ Error in debug_schedule_data: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {
                "error": str(e),
                "traceback": traceback.format_exc()
            },
            status_code=500
        )


@router.get("/debug/create-default")
async def create_default_schedule(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء جدول افتراضي للاختبار
    """
    try:
        print("=" * 50)
        print("📅 إنشاء جدول افتراضي")
        print(f"   user_id: {user.id}")
        print(f"   school_id: {user.school_id}")
        print("=" * 50)
        
        # 1. جلب الفصل الأول
        section_result = await db.execute(
            select(Section).where(Section.school_id == user.school_id).limit(1)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            return JSONResponse({
                "status": "error",
                "message": "لا توجد فصول في هذه المدرسة"
            })
        
        # 2. جلب المواد
        subjects_result = await db.execute(
            select(Subject).where(Subject.school_id == user.school_id)
        )
        subjects = subjects_result.scalars().all()
        
        if not subjects:
            # إنشاء مواد افتراضية
            default_subjects = ["اللغة العربية", "الرياضيات", "العلوم", "اللغة الإنجليزية"]
            for name in default_subjects:
                subject = Subject(
                    id=str(uuid.uuid4()),
                    name=name,
                    school_id=user.school_id,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(subject)
            await db.flush()
            
            # جلب المواد مرة أخرى
            subjects_result = await db.execute(
                select(Subject).where(Subject.school_id == user.school_id)
            )
            subjects = subjects_result.scalars().all()
        
        # 3. جلب المعلمين
        teachers_result = await db.execute(
            select(Teacher).where(Teacher.school_id == user.school_id)
        )
        teachers = teachers_result.scalars().all()
        
        if not teachers:
            # إنشاء معلمين افتراضيين
            default_teachers = ["أحمد محمد", "سارة خالد"]
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
            await db.flush()
            
            # جلب المعلمين مرة أخرى
            teachers_result = await db.execute(
                select(Teacher).where(Teacher.school_id == user.school_id)
            )
            teachers = teachers_result.scalars().all()
        
        # 4. إنشاء جدول
        schedule = Schedule(
            id=str(uuid.uuid4()),
            name="الجدول الرئيسي",
            section_id=section.id,
            school_id=user.school_id,
            created_by=user.id,
            updated_by=user.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(schedule)
        await db.flush()
        
        # 5. إنشاء entries
        days = [0, 1, 2, 3, 4]  # الأحد إلى الخميس
        periods = range(1, 5)  # 4 حصص
        
        entries_count = 0
        for day in days:
            for period in periods:
                subject = subjects[period % len(subjects)]
                teacher = teachers[period % len(teachers)]
                
                entry = ScheduleEntry(
                    id=str(uuid.uuid4()),
                    schedule_id=schedule.id,
                    section_id=section.id,
                    subject_id=subject.id,
                    teacher_id=teacher.id,
                    day=day,
                    period=period,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(entry)
                entries_count += 1
        
        await db.commit()
        
        print(f"✅ تم إنشاء الجدول: {schedule.name}")
        print(f"✅ تم إنشاء {entries_count} حصة")
        
        return JSONResponse({
            "status": "success",
            "message": "تم إنشاء جدول افتراضي بنجاح",
            "schedule_id": str(schedule.id),
            "schedule_name": schedule.name,
            "entries_count": entries_count
        })
        
    except Exception as e:
        print(f"❌ Error in create_default_schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {
                "error": str(e),
                "traceback": traceback.format_exc()
            },
            status_code=500
        )
