"""Students web routes — shared pages used by director, deputy, and teacher."""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.student_service import StudentService
from app.schemas.student import StudentCreate, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def students_list(
    request: Request,
    page: int = 1,
    search: str = "",
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = StudentService(db)
    result = await service.list_students(user.school_id, page, 20, search or None)
    return templates.TemplateResponse(
        "students/list.html",
        {**ctx, "title": "الطلاب", "students": result["items"], "total": result["total"],
         "page": page, "page_size": 20, "search": search},
    )


@router.get("/{student_id}")
async def student_detail(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = StudentService(db)
    detail = await service.get_student_detail(student_id)
    return templates.TemplateResponse(
        "students/detail.html",
        {**ctx, "title": detail["full_name"], "student": detail},
    )


@router.get("/new")
async def student_new(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    from app.services.academic_service import AcademicService
    academic = AcademicService(db)
    data = await academic.get_onboarding_data(user.school_id)
    return templates.TemplateResponse(
        "students/form.html",
        {**ctx, "title": "إضافة طالب", "mode": "create", 
         "sections": data["sections"], "years": data["years"]},
    )


@router.post("")
async def student_create(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    student_number: str = Form(...),
    national_id: Optional[str] = Form(None),
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_phone: Optional[str] = Form(None),
    guardian_email: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    section_id: Optional[str] = Form(None),
    year_id: Optional[str] = Form(None),
):
    service = StudentService(db)
    
    student_data = StudentCreate(
        student_number=student_number,
        national_id=national_id,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        birth_date=birth_date,
        guardian_name=guardian_name,
        guardian_phone=guardian_phone,
        guardian_email=guardian_email,
        address=address,
        section_id=section_id,
        year_id=year_id,
    )
    
    try:
        student = await service.create_student(student_data, user.id, user.school_id)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except ValueError as e:
        ctx = await template_context(request, user)
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", 
             "sections": data["sections"], "years": data["years"], "error": str(e)},
            status_code=400
        )


@router.get("/{student_id}/edit")
async def student_edit(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = StudentService(db)
    detail = await service.get_student_detail(student_id)
    
    from app.services.academic_service import AcademicService
    academic = AcademicService(db)
    data = await academic.get_onboarding_data(user.school_id)
    
    return templates.TemplateResponse(
        "students/form.html",
        {**ctx, "title": "تعديل طالب", "mode": "edit", "student": detail, 
         "sections": data["sections"], "years": data["years"]},
    )


@router.post("/{student_id}/edit")
async def student_update(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    national_id: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_phone: Optional[str] = Form(None),
    guardian_email: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
):
    service = StudentService(db)
    
    student_update = StudentUpdate(
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        gender=gender,
        birth_date=birth_date,
        guardian_name=guardian_name,
        guardian_phone=guardian_phone,
        guardian_email=guardian_email,
        address=address,
        is_active=is_active,
    )
    
    try:
        student = await service.update_student(student_id, student_update)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except ValueError as e:
        ctx = await template_context(request, user)
        detail = await service.get_student_detail(student_id)
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "تعديل طالب", "mode": "edit", "student": detail,
             "sections": data["sections"], "years": data["years"], "error": str(e)},
            status_code=400
        )


@router.post("/{student_id}")
async def student_delete(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    await service.delete_student(student_id)
    return RedirectResponse(url="/students", status_code=303)
