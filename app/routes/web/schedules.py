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
from app.core.security import hash_password

# ============================================================
# استيراد الـ Schemas
# ============================================================
from app.schemas.schedules import (
    ScheduleCreate, ScheduleUpdate, 
    ScheduleEntryCreate, ScheduleEntryUpdate
)


# النماذج
from app.models.schedules import Schedule, ScheduleEntry
from app.models.academics import Section, Subject, Grade, Stage, AcademicYear
from app.models.teachers import Teacher
from app.models.users import User, UserRole, Role

router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# دوال مساعدة لجلب البيانات
# ============================================================

async def get_sections_with_details(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب الفصول مع تفاصيلها (الصف والمرحلة)"""
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
    """جلب السنوات الدراسية"""
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
    """جلب المراحل حسب السنة الدراسية"""
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
                "order": stage.order
            }
            for stage in stages
        ]
    except Exception as e:
        print(f"⚠️ Error in get_stages: {str(e)}")
        return []


async def get_grades(db: AsyncSession, school_id: str, stage_id: Optional[str] = None) -> List[Dict]:
    """جلب الصفوف حسب المرحلة"""
    try:
        stmt = select(Grade).where(
            Grade.school_id == school_id,
            Grade.is_active == True
        )
        if stage_id:
            stmt = stmt.where(Grade.stage_id == stage_id)
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


async def get_subjects(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب المواد الدراسية"""
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
    """جلب المعلمين"""
    try:
        result = await db.execute(
            select(Teacher)
            .where(Teacher.school_id == school_id)
            .where(Teacher.is_active == True)
            .order_by(Teacher.first_name, Teacher.last_name)
        )
        teachers = result.scalars().all()
        
        if not teachers:
            return []
        
        return [
            {
                "id": str(teacher.id),
                "name": f"{teacher.first_name} {teacher.last_name}".strip() or teacher.full_name,
                "employee_number": teacher.employee_number,
                "email": teacher.email,
                "specialization": teacher.specialization
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
        years = await get_academic_years(db, user.school_id)
        stages = await get_stages(db, user.school_id)
        grades = await get_grades(db, user.school_id)
        sections = await get_sections_with_details(db, user.school_id)
        subjects = await get_subjects(db, user.school_id)
        teachers = await get_teachers(db, user.school_id)
        
        print(f"✅ تم جلب {len(years)} عام دراسي")
        print(f"✅ تم جلب {len(stages)} مرحلة")
        print(f"✅ تم جلب {len(grades)} صف")
        print(f"✅ تم جلب {len(sections)} شعبة")
        print(f"✅ تم جلب {len(subjects)} مادة")
        print(f"✅ تم جلب {len(teachers)} معلم")
        
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
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
                "years": [],
                "stages": [],
                "grades": [],
                "sections": [],
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
        
        years = await get_academic_years(db, user.school_id)
        stages = await get_stages(db, user.school_id)
        grades = await get_grades(db, user.school_id)
        sections = await get_sections_with_details(db, user.school_id)
        subjects = await get_subjects(db, user.school_id)
        teachers = await get_teachers(db, user.school_id)
        
        return templates.TemplateResponse(
            "schedules/update.html",
            {
                **ctx,
                "title": "تعديل جدول دراسي",
                "item": schedule,
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
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
        
        return templates.TemplateResponse(
            "schedules/view.html",
            {
                **ctx,
                "title": "عرض الجدول الدراسي",
                "schedule": schedule,
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
# مسارات API للجداول
# ============================================================

@router.post("/api/v1/schedules")
async def create_schedule_api(
    req: ScheduleCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """إنشاء جدول جديد عبر API"""
    try:
        service = ScheduleService(db)
        schedule = await service.create_schedule(user.school_id, req)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم إنشاء الجدول بنجاح",
            "id": str(schedule.id),
            "name": schedule.name
        }
        
    except ValueError as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=422
        )
    except Exception as e:
        print(f"❌ Error creating schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )


@router.put("/api/v1/schedules/{schedule_id}")
async def update_schedule_api(
    schedule_id: str,
    req: ScheduleUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """تحديث جدول عبر API"""
    try:
        service = ScheduleService(db)
        schedule = await service.update_schedule(schedule_id, req)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم تحديث الجدول بنجاح",
            "id": str(schedule.id)
        }
        
    except NotFoundException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error updating schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )


@router.delete("/api/v1/schedules/{schedule_id}")
async def delete_schedule_api(
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف جدول عبر API"""
    try:
        service = ScheduleService(db)
        await service.delete_schedule(schedule_id)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم حذف الجدول بنجاح"
        }
        
    except NotFoundException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error deleting schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )
