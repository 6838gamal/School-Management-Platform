"""Schedules web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")


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
        "schedules/list.html",
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
    try:
        print("=" * 50)
        print("📄 صفحة إنشاء جدول جديد")
        print(f"   user_id: {user.id}")
        print(f"   school_id: {user.school_id}")
        print("=" * 50)
        
        service = ScheduleService(db)
        
        sections = await service.get_sections_objects(user.school_id)
        academic_years = await service.get_academic_years_objects(user.school_id)
        
        print(f"✅ تم جلب {len(sections)} شعبة")
        print(f"✅ تم جلب {len(academic_years)} عام دراسي")
        
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "sections": sections,
                "academic_years": academic_years,
            }
        )
    except Exception as e:
        print(f"❌ خطأ في صفحة إنشاء الجدول: {str(e)}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "sections": [],
                "academic_years": [],
                "error": str(e)
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
    
    sections = await service.get_sections_objects(user.school_id)
    academic_years = await service.get_academic_years_objects(user.school_id)
    
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
