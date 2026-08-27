"""Teachers web routes."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.teacher_service import TeacherService

router = APIRouter(prefix="/teachers", tags=["teachers"])
templates = Jinja2Templates(directory="app/templates")

# ⚠️ IMPORTANT: Put specific routes BEFORE dynamic routes

@router.get("/new")  # ✅ هذا يجب أن يأتي أولاً
async def teacher_new(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("teachers.create")),
    ctx: dict = Depends(template_context),
):
    return templates.TemplateResponse(
        "teachers/form.html",
        {**ctx, "title": "إضافة معلم", "mode": "create"},
    )

@router.get("")  # ✅ القائمة
async def teachers_list(
    request: Request,
    page: int = 1,
    search: str = "",
    user: CurrentUser = Depends(require_any_permission("teachers.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = TeacherService(db)
    result = await service.list_teachers(user.school_id, page, 20, search or None)
    return templates.TemplateResponse(
        "teachers/list.html",
        {**ctx, "title": "المعلمون", "teachers": result["items"], "total": result["total"],
         "page": page, "page_size": 20, "search": search},
    )

@router.get("/{teacher_id}/update")  # ✅ التعديل
async def teacher_edit(
    request: Request,
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = TeacherService(db)
    teacher = await service.get_teacher_detail(teacher_id)
    return templates.TemplateResponse(
        "teachers/form.html",
        {**ctx, "title": "تعديل معلم", "mode": "edit", "teacher": teacher},
    )

@router.get("/{teacher_id}")  # ✅ التفاصيل - يجب أن يكون آخراً
async def teacher_detail(
    request: Request,
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = TeacherService(db)
    detail = await service.get_teacher_detail(teacher_id)
    return templates.TemplateResponse(
        "teachers/detail.html",
        {**ctx, "title": detail["full_name"], "teacher": detail},
    )

@router.post("/{teacher_id}/delete")  # ✅ الحذف
async def teacher_delete(
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = TeacherService(db)
    await service.delete_teacher(teacher_id)
    return RedirectResponse(url="/teachers", status_code=303)
