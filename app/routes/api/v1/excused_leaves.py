"""Excused leaves (استئذان) — web routes (deputy-only at the backend)."""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.services.excused_leave_service import ExcusedLeaveService
from app.services.student_service import StudentService


router = APIRouter(prefix="/excused-leaves", tags=["excused-leaves"])


@router.get("")
async def excused_leaves_index(
    request: Request,
    user: CurrentUser = Depends(require_permission("excused_leaves.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    # render index only for deputy/director; backend denies if teacher lacks view perm
    if "excused_leaves.view" not in user.permissions:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("لا تملك صلاحية عرض الاستئذانات")
    service = ExcusedLeaveService(db)
    items = await service.list_for_section(
        user.school_id, section_id=request.query_params.get("section_id", ""),
        date_from=request.query_params.get("date_from"),
        date_to=request.query_params.get("date_to"),
    )
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse(
        "excused_leaves/list.html",
        {**ctx, "title": "الاستئذانات", "items": items},
    )


@router.post("/create")
async def excused_leave_create(
    request: Request,
    user: CurrentUser = Depends(require_permission("excused_leaves.create")),
    db: AsyncSession = Depends(get_db),
):
    # Form-based: requires deputy in backend regardless of role.
    form = await request.form()
    service = ExcusedLeaveService(db)
    try:
        leave = await service.create(
            school_id=user.school_id,
            actor_id=user.id,
            actor_role=user.primary_role,
            user_permissions=user.permissions,
            student_id=form.get("student_id"),
            date=form.get("date"),
            requested_at=form.get("requested_at"),
            exit_time=form.get("exit_time"),
            reason=form.get("reason"),
            guardian_name=form.get("guardian_name"),
            guardian_relation=form.get("guardian_relation"),
            guardian_phone=form.get("guardian_phone"),
            notes=form.get("notes"),
        )
        return RedirectResponse(
            url=f"/students/{form.get('student_id')}?excused=created", status_code=303,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
