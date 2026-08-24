"""Dashboard and onboarding web routes."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_user, template_context
from app.core.exceptions import ForbiddenException
from app.services.academic_service import AcademicService
from app.services.report_service import DashboardService

router = APIRouter(prefix="", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/onboarding")
async def onboarding_page(
    request: Request,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    if user.primary_role != "director":
        raise ForbiddenException("التهيئة متاحة للمدير فقط")
    service = AcademicService(db)
    data = await service.get_onboarding_data(user.school_id)
    return templates.TemplateResponse(
        "onboarding/onboarding.html",
        {**ctx, "title": "تهيئة المدرسة", "data": data},
    )


@router.get("/dashboard")
async def dashboard_router(
    request: Request,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = DashboardService(db)
    role = user.primary_role
    if role == "director":
        stats = await service.director_stats(user.school_id, user.id)
        return templates.TemplateResponse(
            "director/dashboard.html",
            {**ctx, "title": "لوحة تحكم المدير", "stats": stats},
        )
    elif role == "deputy":
        stats = await service.deputy_stats(user.school_id, user.id)
        return templates.TemplateResponse(
            "deputy/dashboard.html",
            {**ctx, "title": "لوحة تحكم الوكيل", "stats": stats},
        )
    elif role == "activities_manager":
        stats = await service.activities_manager_stats(user.school_id, user.id)
        return templates.TemplateResponse(
            "activities_manager/dashboard.html",
            {**ctx, "title": "لوحة تحكم مسؤول الأنشطة", "stats": stats},
        )
    elif role == "teacher":
        from app.repositories.teachers import TeacherRepository
        teacher_repo = TeacherRepository(db)
        teacher = await teacher_repo.get_by_user(user.id)
        teacher_id = teacher.id if teacher else ""
        stats = await service.teacher_stats(user.school_id, teacher_id, user.id)
        return templates.TemplateResponse(
            "teacher/dashboard.html",
            {**ctx, "title": "لوحة تحكم المعلم", "stats": stats},
        )
    raise ForbiddenException("دور غير معروف")
