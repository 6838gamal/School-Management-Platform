"""Timetable-linked alerts settings — مرتبطة بالـSchool Timetable."""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.models.timetable_alerts import TimetableAlertSetting
from sqlalchemy import select


router = APIRouter(prefix="/settings/alerts", tags=["timetable-alerts"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def show(
    request: Request,
    user: CurrentUser = Depends(require_permission("timetable_alerts.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    row = (
        await db.execute(
            select(TimetableAlertSetting).where(TimetableAlertSetting.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if not row:
        # seed defaults from spec
        row = TimetableAlertSetting(
            school_id=user.school_id,
            assembly_lead_minutes=10,
            period_start_lead_minutes=5,
            period_end_lead_minutes=5,
            preparation_lead_minutes=3,
            late_threshold_minutes=10,
            alert_on_late_preparation=True,
        )
        db.add(row)
        await db.commit()
    return templates.TemplateResponse(
        "settings/alerts.html",
        {**ctx, "title": "إعدادات التنبيهات", "settings": row},
    )


@router.post("/update")
async def update(
    request: Request,
    user: CurrentUser = Depends(require_permission("timetable_alerts.update")),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    row = (
        await db.execute(
            select(TimetableAlertSetting).where(TimetableAlertSetting.school_id == user.school_id)
        )
    ).scalar_one_or_none()
    if not row:
        row = TimetableAlertSetting(school_id=user.school_id)
        db.add(row)
    row.assembly_lead_minutes = int(form.get("assembly_lead_minutes", 10))
    row.period_start_lead_minutes = int(form.get("period_start_lead_minutes", 5))
    row.period_end_lead_minutes = int(form.get("period_end_lead_minutes", 5))
    row.preparation_lead_minutes = int(form.get("preparation_lead_minutes", 3))
    row.late_threshold_minutes = int(form.get("late_threshold_minutes", 10))
    row.alert_on_late_preparation = form.get("alert_on_late_preparation") == "on"
    await db.commit()
    return RedirectResponse(url="/settings/alerts?saved=1", status_code=303)
