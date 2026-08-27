"""Schedules API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
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
    """API: إنشاء جدول جديد"""
    try:
        service = ScheduleService(db)
        result = await service.create_schedule(user.school_id, req)
        return {
            "success": True, 
            "id": result.id, 
            "message": "تم إنشاء الجدول بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    req: ScheduleUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث جدول"""
    try:
        service = ScheduleService(db)
        result = await service.update_schedule(schedule_id, req)
        return {
            "success": True, 
            "message": "تم تحديث الجدول بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف جدول"""
    try:
        service = ScheduleService(db)
        await service.delete_schedule(schedule_id)
        return {"success": True, "message": "تم حذف الجدول بنجاح"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{schedule_id}/entries")
async def add_schedule_entry(
    schedule_id: str,
    req: ScheduleEntryCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إضافة مدخل (حصة) إلى الجدول"""
    try:
        service = ScheduleService(db)
        result = await service.add_entry(schedule_id, req)
        return {
            "success": True, 
            "id": result.id, 
            "message": "تم إضافة الحصة بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/entries/{entry_id}")
async def update_schedule_entry(
    entry_id: str,
    req: ScheduleEntryUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث مدخل (حصة) في الجدول"""
    try:
        service = ScheduleService(db)
        result = await service.update_entry(entry_id, req)
        return {
            "success": True, 
            "message": "تم تحديث الحصة بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/entries/{entry_id}")
async def delete_schedule_entry(
    entry_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف مدخل (حصة) من الجدول"""
    try:
        service = ScheduleService(db)
        await service.delete_entry(entry_id)
        return {"success": True, "message": "تم حذف الحصة بنجاح"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/data/{school_id}")
async def get_schedule_data(
    school_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب المواد والمعلمين والقاعات لاستخدامها في إضافة الحصص"""
    try:
        service = ScheduleService(db)
        
        # الدوال تعيد قوائم من Dictionaries
        subjects = await service.get_subjects(school_id)
        teachers = await service.get_teachers(school_id)
        rooms = await service.get_rooms(school_id)
        
        return {
            "success": True,
            "subjects": subjects,  # بالفعل قائمة من {"id": ..., "name": ...}
            "teachers": teachers,  # بالفعل قائمة من {"id": ..., "full_name": ...}
            "rooms": rooms         # بالفعل قائمة من {"id": ..., "name": ...}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/sections/{school_id}")
async def get_school_sections(
    school_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب جميع الشعب لمدرسة معينة"""
    try:
        service = ScheduleService(db)
        sections = await service.get_all_sections(school_id)
        return {
            "success": True,
            "sections": [
                {
                    "id": s.id,
                    "name": s.name,
                    "grade_id": s.grade_id,
                    "grade_name": s.grade.name if s.grade else None,
                    "capacity": s.capacity,
                    "is_active": s.is_active
                }
                for s in sections
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/academic-years/{school_id}")
async def get_school_academic_years(
    school_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب جميع الأعوام الدراسية لمدرسة معينة"""
    try:
        service = ScheduleService(db)
        years = await service.get_academic_years_objects(school_id)
        return {
            "success": True,
            "academic_years": [
                {
                    "id": y.id,
                    "name": y.name,
                    "start_date": y.start_date,
                    "end_date": y.end_date,
                    "is_current": y.is_current,
                    "is_active": y.is_active
                }
                for y in years
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/periods/{school_id}")
async def get_school_periods(
    school_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب جميع الفترات لمدرسة معينة"""
    try:
        service = ScheduleService(db)
        periods = await service.get_periods(school_id)
        return {
            "success": True,
            "periods": periods  # بالفعل قائمة من Dictionaries
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{schedule_id}/entries")
async def get_schedule_entries(
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب جميع مدخلات (حصص) جدول معين"""
    try:
        service = ScheduleService(db)
        schedule = await service.get_schedule_with_entries(schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="الجدول غير موجود")
        
        entries = []
        for entry in schedule.entries:
            entries.append({
                "id": entry.id,
                "day_of_week": entry.day_of_week,
                "period_id": entry.period_id,
                "period_name": entry.period.name if entry.period else None,
                "subject_id": entry.subject_id,
                "subject_name": entry.subject.name if entry.subject else None,
                "teacher_id": entry.teacher_id,
                "teacher_name": entry.teacher.full_name if entry.teacher else None,
                "room_id": entry.room_id,
                "room_name": entry.room.name if entry.room else None,
                "note": entry.note
            })
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "schedule_name": schedule.name,
            "entries": entries,
            "count": len(entries)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
