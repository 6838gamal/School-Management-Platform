"""Deputy dashboard web route — الفصول مرتبة من اليمين لليسار + إحصائيات الحضور + الأضواء 🟢/🟠/🔴."""
from datetime import date as _date
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.services.deputy_dashboard_service import DeputyDashboardService


router = APIRouter(prefix="/deputy", tags=["deputy-dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard")
async def deputy_dashboard(
    request: Request,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    target_date: str | None = None,
):
    service = DeputyDashboardService(db)
    data = await service.dashboard(
        school_id=user.school_id,
        target_date=target_date or _date.today().isoformat(),
    )
    return templates.TemplateResponse(
        "deputy/dashboard_v2.html",
        {
            **ctx,
            "title": "لوحة تحكم الوكيل",
            "dashboard": data,
            "selected_date": data["date"],
        },
    )
