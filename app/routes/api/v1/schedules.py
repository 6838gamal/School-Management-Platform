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

# ✅ إزالة الـ prefix من هنا - سيتم إضافته من main.py
router = APIRouter(tags=["schedules-api"])


@router.post("/schedules")  # ✅ المسار الكامل سيكون /api/v1/schedules
async def create_schedule(
    req: ScheduleCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء جدول جديد"""
    try:
        print("=" * 50)
        print("📝 API: إنشاء جدول جديد")
        print(f"   user_id: {user.id}")
        print(f"   school_id: {user.school_id}")
        print(f"   data: {req.model_dump()}")
        print("=" * 50)
        
        if not user.school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="المستخدم ليس لديه مدرسة مرتبطة"
            )
        
        service = ScheduleService(db)
        result = await service.create_schedule(user.school_id, req)
        
        return {
            "success": True,
            "id": result.id,
            "message": "تم إنشاء الجدول بنجاح"
        }
        
    except ValueError as e:
        print(f"❌ خطأ في البيانات: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"حدث خطأ: {str(e)}"
        )


@router.put("/schedules/{schedule_id}")
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


@router.delete("/schedules/{schedule_id}")
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


@router.post("/schedules/{schedule_id}/entries")
async def add_schedule_entry(
    schedule_id: str,
    req: ScheduleEntryCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إضافة مدخل (حصة) إلى الجدول"""
    try:
        print("=" * 50)
        print("📝 API: إضافة حصة جديدة")
        print(f"   schedule_id: {schedule_id}")
        print(f"   data: {req.model_dump()}")
        print("=" * 50)
        
        service = ScheduleService(db)
        result = await service.add_entry(schedule_id, req)
        
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة الحصة بنجاح"
        }
    except ValueError as e:
        print(f"❌ خطأ في البيانات: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/schedules/entries/{entry_id}")
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


@router.delete("/schedules/entries/{entry_id}")
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


@router.get("/schedules/data/{school_id}")
async def get_schedule_data(
    school_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب المواد والمعلمين والقاعات لاستخدامها في إضافة الحصص"""
    try:
        service = ScheduleService(db)
        
        subjects = await service.get_subjects(school_id)
        teachers = await service.get_teachers(school_id)
        rooms = await service.get_rooms(school_id)
        
        return {
            "success": True,
            "subjects": subjects,
            "teachers": teachers,
            "rooms": rooms
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/schedules/sections/{school_id}")
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
            "sections": sections
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/schedules/academic-years/{school_id}")
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


@router.get("/schedules/periods/{school_id}")
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
            "periods": periods
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/schedules/{schedule_id}/entries")
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
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "schedule_name": schedule["name"],
            "entries": schedule["entries"],
            "count": schedule["entries_count"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/schedules/check-data")
async def check_available_data(
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: التحقق من البيانات المتاحة للمستخدم الحالي"""
    try:
        service = ScheduleService(db)
        data = await service.check_available_data(user.school_id)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
