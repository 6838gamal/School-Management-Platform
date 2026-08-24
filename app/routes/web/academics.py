"""Academic structure web routes."""
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.academic_service import AcademicService

router = APIRouter(prefix="/academics", tags=["academics"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def academics_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    data = await service.get_onboarding_data(user.school_id)
    return templates.TemplateResponse(
        "academics/index.html",
        {**ctx, "title": "الهيكل الأكاديمي", "data": data},
    )


@router.get("/tree")
async def academic_tree(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    tree = await service.get_full_tree(user.school_id)
    return templates.TemplateResponse(
        "academics/tree.html",
        {**ctx, "title": "الشجرة الأكاديمية", "tree": tree},
    )
