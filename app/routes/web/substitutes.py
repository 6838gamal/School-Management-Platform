"""Substitute assignment (تكليف معلم بديل) — قبول/رفض + شاشة البدائل المتاحة."""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.services.substitute_service import SubstituteService


router = APIRouter(prefix="/substitutes", tags=["substitutes"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/alternatives")
async def list_alternatives(
    request: Request,
    schedule_entry_id: str,
    date: str,
    user: CurrentUser = Depends(require_permission("substitutes.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = SubstituteService(db)
    data = await service.list_alternatives(
        school_id=user.school_id,
        schedule_entry_id=schedule_entry_id,
        date=date,
    )
    return templates.TemplateResponse(
        "substitutes/alternatives.html",
        {**ctx, "title": "البدلاء المقترحون", "data": data, "date": date},
    )


@router.post("/request")
async def request_substitute(
    request: Request,
    user: CurrentUser = Depends(require_permission("substitutes.create")),
    db: AsyncSession = Depends(get_db),
):
    if "substitutes.create" not in user.permissions:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("لا تملك صلاحية تكليف معلم بديل")
    form = await request.form()
    service = SubstituteService(db)
    await service.request(
        school_id=user.school_id,
        actor_id=user.id,
        actor_role=user.primary_role,
        user_permissions=user.permissions,
        schedule_entry_id=form.get("schedule_entry_id"),
        absent_teacher_id=form.get("absent_teacher_id"),
        substitute_teacher_id=form.get("substitute_teacher_id"),
        date=form.get("date"),
        reason=form.get("reason"),
    )
    return RedirectResponse(url="/deputy/dashboard?substitute=sent", status_code=303)


@router.post("/{assignment_id}/respond")
async def respond_to_substitute(
    assignment_id: str,
    request: Request,
    user: CurrentUser = Depends(require_permission("substitutes.respond")),
    db: AsyncSession = Depends(get_db),
    accept: bool = Form(...),
    reason: str = Form(""),
):
    if "substitutes.respond" not in user.permissions:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("لا تملك صلاحية الرد على التكليف")
    service = SubstituteService(db)
    await service.respond(
        school_id=user.school_id,
        actor_id=user.id,
        actor_role=user.primary_role,
        user_permissions=user.permissions,
        assignment_id=assignment_id,
        accept=accept,
        reason=reason,
    )
    return RedirectResponse(url="/substitutes/inbox?responded=1", status_code=303)


@router.get("/inbox")
async def inbox(
    request: Request,
    user: CurrentUser = Depends(require_permission("substitutes.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = SubstituteService(db)
    items = await service.list_inbox(user.school_id, user.id)
    return templates.TemplateResponse(
        "substitutes/inbox.html",
        {**ctx, "title": "تكليفات بانتظار ردّك", "items": items},
    )
