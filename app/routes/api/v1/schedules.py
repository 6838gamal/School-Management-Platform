"""Schedules API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission
from app.services.schedule_service import ScheduleService
from app.schemas.schedules import (
    ScheduleCreate, ScheduleUpdate, 
    ScheduleEntryCreate, ScheduleEntryUpdate
)

router = APIRouter(prefix="/schedules", tags=["schedules-api"])


@router.post("")
async def create_schedule(
    req: ScheduleCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    result = await service.create_schedule(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إنشاء الجدول بنجاح"}


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    req: ScheduleUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    result = await service.update_schedule(schedule_id, req)
    return {"success": True, "message": "تم تحديث الجدول بنجاح"}


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    await service.delete_schedule(schedule_id)
    return {"success": True, "message": "تم حذف الجدول بنجاح"}


@router.post("/{schedule_id}/entries")
async def add_schedule_entry(
    schedule_id: str,
    req: ScheduleEntryCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    result = await service.add_entry(schedule_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة المدخل بنجاح"}


@router.put("/entries/{entry_id}")
async def update_schedule_entry(
    entry_id: str,
    req: ScheduleEntryUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    result = await service.update_entry(entry_id, req)
    return {"success": True, "message": "تم تحديث المدخل بنجاح"}


@router.delete("/entries/{entry_id}")
async def delete_schedule_entry(
    entry_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    await service.delete_entry(entry_id)
    return {"success": True, "message": "تم حذف المدخل بنجاح"}








@router.get("/data/{school_id}")
async def get_schedule_data(
    school_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب المواد والمعلمين والقاعات لاستخدامها في إضافة الحصص"""
    service = ScheduleService(db)
    
    subjects = await service.get_subjects(school_id)
    teachers = await service.get_teachers(school_id)
    rooms = await service.get_rooms(school_id)
    
    return {
        "success": True,
        "subjects": [{"id": s.id, "name": s.name} for s in subjects],
        "teachers": [{"id": t.id, "full_name": t.full_name} for t in teachers],
        "rooms": [{"id": r.id, "name": r.name} for r in rooms]
    }
