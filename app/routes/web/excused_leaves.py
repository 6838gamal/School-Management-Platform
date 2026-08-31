"""Excused leaves (استئذان) — deputy-only web routes."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.core.exceptions import ForbiddenException
from app.services.excused_leave_service import ExcusedLeaveService
from app.services.student_service import StudentService


router = APIRouter(prefix="/excused-leaves", tags=["excused-leaves"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def excused_leaves_list(
    request: Request,
    user: CurrentUser = Depends(require_permission("excused_leaves.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    section_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    if "excused_leaves.view" not in user.permissions:
        raise ForbiddenException("لا تملك صلاحية عرض الاستئذانات")
    service = ExcusedLeaveService(db)
    items = []
    if section_id:
        items = await service.list_for_section(
            user.school_id, section_id=section_id,
            date_from=date_from, date_to=date_to,
        )
    return templates.TemplateResponse(
        "excused_leaves/list.html",
        {**ctx, "title": "الاستئذانات", "items": items,
         "section_id": section_id, "date_from": date_from, "date_to": date_to},
    )


@router.post("/create")
async def excused_leave_create(
    request: Request,
    user: CurrentUser = ...,  # filled below
    db: AsyncSession = Depends(get_db),
):
    # ضغط Backend RBAC — المعلّم لا يستطيع إنشاء استئذان أبدًا
    if "excused_leaves.create" not in user.permissions or user.primary_role == "teacher":
        raise ForbiddenException(
            "تسجيل الاستئذان صلاحية حصرية للوكيل"
        )
    form = await request.form()
    service = ExcusedLeaveService(db)
    try:
        await service.create(
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
            url=f"/students/{form.get('student_id')}?excused=created",
            status_code=303,
        )
    except Exception as e:
        raise ForbiddenException(str(e))
