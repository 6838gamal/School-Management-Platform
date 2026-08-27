"""Schedules web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.schedule_service import ScheduleService
from app.schemas.schedules import (
    ScheduleCreate, ScheduleUpdate, 
    ScheduleEntryCreate, ScheduleEntryUpdate
)

router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")


# ============= صفحات الويب =============

@router.get("")
async def schedules_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة الجداول الدراسية الرئيسية"""
    service = ScheduleService(db)
    schedules = await service.list_schedules(user.school_id)
    return templates.TemplateResponse(
        "schedules/index.html",
        {**ctx, "title": "الجداول الدراسية", "items": schedules, "type": "schedules"}
    )


@router.get("/list")
async def list_schedules(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة قائمة الجداول الدراسية"""
    service = ScheduleService(db)
    schedules = await service.list_schedules(user.school_id)
    return templates.TemplateResponse(
        "schedules/list.html",
        {**ctx, "title": "الجداول الدراسية", "items": schedules, "type": "schedules"}
    )


@router.get("/create")
async def create_schedule_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة إنشاء جدول جديد"""
    service = ScheduleService(db)
    sections = await service.get_sections(user.school_id)
    academic_years = await service.get_academic_years(user.school_id)
    
    return templates.TemplateResponse(
        "schedules/create.html",
        {
            **ctx,
            "title": "إنشاء جدول دراسي",
            "sections": sections,
            "academic_years": academic_years,
        }
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
    service = ScheduleService(db)
    schedule = await service.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="الجدول غير موجود")
    
    sections = await service.get_sections(user.school_id)
    academic_years = await service.get_academic_years(user.school_id)
    
    return templates.TemplateResponse(
        "schedules/update.html",
        {
            **ctx,
            "title": "تعديل جدول دراسي",
            "item": schedule,
            "sections": sections,
            "academic_years": academic_years,
        }
    )


@router.get("/{schedule_id}/view")
async def view_schedule_page(
    request: Request,
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة عرض الجدول"""
    service = ScheduleService(db)
    schedule = await service.get_schedule_with_entries(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="الجدول غير موجود")
    
    periods = await service.get_periods(user.school_id)
    
    return templates.TemplateResponse(
        "schedules/view.html",
        {
            **ctx,
            "title": "عرض الجدول الدراسي",
            "schedule": schedule,
            "periods": periods,
            "days": ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
        }
    )


# ============= مسارات API =============

@router.post("/api/v1/schedules")
async def create_schedule(
    req: ScheduleCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء جدول جديد"""
    service = ScheduleService(db)
    result = await service.create_schedule(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إنشاء الجدول بنجاح"}


@router.put("/api/v1/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    req: ScheduleUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث جدول"""
    service = ScheduleService(db)
    result = await service.update_schedule(schedule_id, req)
    return {"success": True, "message": "تم تحديث الجدول بنجاح"}


@router.delete("/api/v1/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف جدول"""
    service = ScheduleService(db)
    await service.delete_schedule(schedule_id)
    return {"success": True, "message": "تم حذف الجدول بنجاح"}


@router.post("/api/v1/schedules/{schedule_id}/entries")
async def add_schedule_entry(
    schedule_id: str,
    req: ScheduleEntryCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إضافة مدخل إلى الجدول"""
    service = ScheduleService(db)
    result = await service.add_entry(schedule_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة المدخل بنجاح"}


@router.put("/api/v1/schedules/entries/{entry_id}")
async def update_schedule_entry(
    entry_id: str,
    req: ScheduleEntryUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث مدخل في الجدول"""
    service = ScheduleService(db)
    result = await service.update_entry(entry_id, req)
    return {"success": True, "message": "تم تحديث المدخل بنجاح"}


@router.delete("/api/v1/schedules/entries/{entry_id}")
async def delete_schedule_entry(
    entry_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف مدخل من الجدول"""
    service = ScheduleService(db)
    await service.delete_entry(entry_id)
    return {"success": True, "message": "تم حذف المدخل بنجاح"}
