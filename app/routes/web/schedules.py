"""Schedules web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import uuid
import traceback
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.schedule_service import ScheduleService
from app.core.exceptions import NotFoundException, AppException

# النماذج
from app.models.schedules import Schedule, ScheduleEntry
from app.models.academics import Section, Subject, Grade, Stage, AcademicYear, Period
from app.models.teachers import Teacher
from app.models.users import User, UserRole, Role

router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# دوال مساعدة لجلب البيانات
# ============================================================

async def get_sections_with_details(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب الفصول مع تفاصيلها (الصف والمرحلة)
    """
    try:
        result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.grade_id, Section.name)
        )
        sections = result.scalars().all()
        
        return [
            {
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
                "stage_name": section.grade.stage.name if section.grade and section.grade.stage else "غير محدد",
                "display_name": f"{section.grade.stage.name if section.grade and section.grade.stage else ''} - {section.grade.name if section.grade else ''} - {section.name}",
                "capacity": section.capacity,
                "is_active": section.is_active
            }
            for section in sections
        ]
    except Exception as e:
        print(f"⚠️ Error in get_sections_with_details: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


async def get_academic_years(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب السنوات الدراسية
    """
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


async def get_subjects(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب المواد الدراسية
    """
    try:
        result = await db.execute(
            select(Subject)
            .where(Subject.school_id == school_id)
            .where(Subject.is_active == True)
            .order_by(Subject.name)
        )
        subjects = result.scalars().all()
        
        return [
            {
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code if hasattr(subject, 'code') else None,
                "color": subject.color if hasattr(subject, 'color') else None
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
        # جلب دور المعلم
        role_result = await db.execute(
            select(Role).where(Role.key == "teacher", Role.school_id == school_id)
        )
        teacher_role = role_result.scalar_one_or_none()
        
        if not teacher_role:
            print("⚠️ لا يوجد دور معلم في المدرسة")
            return []
        
        result = await db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == teacher_role.id)
            .where(User.school_id == school_id)
            .where(User.is_active == True)
            .order_by(User.full_name)
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


async def get_periods(db: AsyncSession, school_id: str) -> List[Dict]:
    """
    جلب الحصص الدراسية (الفترات)
    """
    try:
        result = await db.execute(
            select(Period)
            .where(Period.school_id == school_id)
            .order_by(Period.order)
        )
        periods = result.scalars().all()
        
        return [
            {
                "id": str(period.id),
                "order": period.order,
                "name": period.name,
                "start_time": period.start_time if hasattr(period, 'start_time') else None,
                "end_time": period.end_time if hasattr(period, 'end_time') else None
            }
            for period in periods
        ]
    except Exception as e:
        print(f"⚠️ Error in get_periods: {str(e)}")
        # إرجاع حصص افتراضية
        return [
            {"id": "1", "order": 1, "name": "الحصة الأولى"},
            {"id": "2", "order": 2, "name": "الحصة الثانية"},
            {"id": "3", "order": 3, "name": "الحصة الثالثة"},
            {"id": "4", "order": 4, "name": "الحصة الرابعة"},
            {"id": "5", "order": 5, "name": "الحصة الخامسة"},
            {"id": "6", "order": 6, "name": "الحصة السادسة"},
        ]


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
        
        # جلب البيانات المطلوبة باستخدام الدوال المحسنة
        sections = await get_sections_with_details(db, user.school_id)
        academic_years = await get_academic_years(db, user.school_id)
        subjects = await get_subjects(db, user.school_id)
        teachers = await get_teachers(db, user.school_id)
        periods = await get_periods(db, user.school_id)
        
        print(f"✅ تم جلب {len(sections)} شعبة")
        print(f"✅ تم جلب {len(academic_years)} عام دراسي")
        print(f"✅ تم جلب {len(subjects)} مادة")
        print(f"✅ تم جلب {len(teachers)} معلم")
        print(f"✅ تم جلب {len(periods)} حصة")
        
        # عرض تفاصيل الشعب للتأكد
        for section in sections[:5]:
            print(f"   📚 {section.get('display_name', section.get('name'))}")
        
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "sections": sections,
                "academic_years": academic_years,
                "subjects": subjects,
                "teachers": teachers,
                "periods": periods,
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
                "periods": [],
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
        periods = await get_periods(db, user.school_id)
        
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
                "periods": periods,
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


@router.get("/debug/sections")
async def debug_sections(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    عرض بيانات الشعب للتصحيح
    """
    try:
        sections = await get_sections_with_details(db, user.school_id)
        
        return JSONResponse({
            "total": len(sections),
            "sections": sections,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_sections: {str(e)}")
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
            select(Section)
            .options(selectinload(Section.grade).selectinload(Grade.stage))
            .where(Section.school_id == user.school_id)
            .limit(1)
        )
        section = section_result.scalar_one_or_none()
        
        if not section:
            return JSONResponse({
                "status": "error",
                "message": "لا توجد فصول في هذه المدرسة"
            })
        
        print(f"✅ تم العثور على الفصل: {section.name}")
        
        # 2. جلب السنة الدراسية النشطة
        year_result = await db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == user.school_id)
            .where(AcademicYear.is_current == True)
            .limit(1)
        )
        year = year_result.scalar_one_or_none()
        
        if not year:
            return JSONResponse({
                "status": "error",
                "message": "لا توجد سنة دراسية نشطة"
            })
        
        print(f"✅ تم العثور على السنة الدراسية: {year.name}")
        
        # 3. جلب المواد
        subjects_result = await db.execute(
            select(Subject)
            .where(Subject.school_id == user.school_id)
            .where(Subject.is_active == True)
        )
        subjects = list(subjects_result.scalars().all())
        
        if not subjects:
            # إنشاء مواد افتراضية
            default_subjects = ["اللغة العربية", "الرياضيات", "العلوم", "اللغة الإنجليزية"]
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
            await db.flush()
            
            subjects_result = await db.execute(
                select(Subject)
                .where(Subject.school_id == user.school_id)
                .where(Subject.is_active == True)
            )
            subjects = list(subjects_result.scalars().all())
        
        print(f"✅ تم جلب {len(subjects)} مادة")
        
        # 4. جلب المعلمين
        teachers_result = await db.execute(
            select(Teacher)
            .where(Teacher.school_id == user.school_id)
            .where(Teacher.is_active == True)
        )
        teachers = list(teachers_result.scalars().all())
        
        if not teachers:
            # إنشاء معلمين افتراضيين
            default_teachers = ["أحمد محمد", "سارة خالد", "محمد علي", "نورة أحمد"]
            for name in default_teachers:
                teacher = Teacher(
                    id=str(uuid.uuid4()),
                    name=name,
                    full_name=name,
                    school_id=user.school_id,
                    is_active=True,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(teacher)
            await db.flush()
            
            teachers_result = await db.execute(
                select(Teacher)
                .where(Teacher.school_id == user.school_id)
                .where(Teacher.is_active == True)
            )
            teachers = list(teachers_result.scalars().all())
        
        print(f"✅ تم جلب {len(teachers)} معلم")
        
        # 5. جلب الحصص (الفترات)
        periods_result = await db.execute(
            select(Period)
            .where(Period.school_id == user.school_id)
            .order_by(Period.order)
        )
        periods = list(periods_result.scalars().all())
        
        if not periods:
            # إنشاء حصص افتراضية
            for i in range(1, 7):
                period = Period(
                    id=str(uuid.uuid4()),
                    name=f"الحصة {i}",
                    order=i,
                    start_time=f"0{i+6}:00",
                    end_time=f"0{i+7}:00",
                    school_id=user.school_id,
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(period)
            await db.flush()
            
            periods_result = await db.execute(
                select(Period)
                .where(Period.school_id == user.school_id)
                .order_by(Period.order)
            )
            periods = list(periods_result.scalars().all())
        
        print(f"✅ تم جلب {len(periods)} حصة")
        
        # 6. إنشاء الجدول
        schedule = Schedule(
            id=str(uuid.uuid4()),
            name=f"الجدول الرئيسي - {section.name}",
            section_id=section.id,
            year_id=year.id,
            school_id=user.school_id,
            is_active=True,
            created_by=user.id,
            updated_by=user.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(schedule)
        await db.flush()
        
        print(f"✅ تم إنشاء الجدول: {schedule.name}")
        
        # 7. إنشاء entries
        days = [0, 1, 2, 3, 4]  # الأحد إلى الخميس
        entries_count = 0
        
        for day in days:
            for period in periods[:4]:  # 4 حصص في اليوم
                subject = subjects[entries_count % len(subjects)]
                teacher = teachers[entries_count % len(teachers)]
                
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
        
        await db.commit()
        
        print(f"✅ تم إنشاء {entries_count} حصة")
        
        return JSONResponse({
            "status": "success",
            "message": "تم إنشاء جدول افتراضي بنجاح",
            "schedule_id": str(schedule.id),
            "schedule_name": schedule.name,
            "section_name": section.name,
            "year_name": year.name,
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
