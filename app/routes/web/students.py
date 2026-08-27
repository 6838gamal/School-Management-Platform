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
        {**ctx, "title": "إضافة طالب", "mode": "create", "sections": data["sections"], "years": data["years"]},
    )


@router.post("")
async def student_create(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    # استقبال البيانات من النموذج
    full_name: str = Form(...),
    student_number: str = Form(...),
    gender: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    section: Optional[str] = Form(None),
    enrollment_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    is_active: bool = Form(True),
):
    service = StudentService(db)
    
    # تحويل التاريخ إلى التنسيق المناسب
    from datetime import datetime
    birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date() if birth_date else None
    enrollment_date_obj = datetime.strptime(enrollment_date, "%Y-%m-%d").date() if enrollment_date else None
    
    student_data = StudentCreate(
        school_id=user.school_id,
        full_name=full_name,
        student_number=student_number,
        gender=gender,
        birth_date=birth_date_obj,
        email=email,
        phone=phone,
        guardian_name=guardian_name,
        guardian_phone=guardian_phone,
        address=address,
        grade=grade,
        section=section,
        enrollment_date=enrollment_date_obj,
        notes=notes,
        is_active=is_active
    )
    
    try:
        student = await service.create_student(student_data, user.id)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except ValueError as e:
        # خطأ في التحقق من البيانات
        ctx = await template_context(request)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", "error": str(e)},
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
    
    # جلب بيانات الأكاديمية للقوائم المنسدلة
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
    # استقبال البيانات من النموذج
    full_name: str = Form(...),
    student_number: str = Form(...),
    gender: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    section: Optional[str] = Form(None),
    enrollment_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    is_active: bool = Form(True),
):
    service = StudentService(db)
    
    from datetime import datetime
    birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date() if birth_date else None
    enrollment_date_obj = datetime.strptime(enrollment_date, "%Y-%m-%d").date() if enrollment_date else None
    
    student_update = StudentUpdate(
        full_name=full_name,
        student_number=student_number,
        gender=gender,
        birth_date=birth_date_obj,
        email=email,
        phone=phone,
        guardian_name=guardian_name,
        guardian_phone=guardian_phone,
        address=address,
        grade=grade,
        section=section,
        enrollment_date=enrollment_date_obj,
        notes=notes,
        is_active=is_active
    )
    
    try:
        student = await service.update_student(student_id, student_update)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except ValueError as e:
        ctx = await template_context(request)
        # جلب بيانات الأكاديمية للقوائم المنسدلة
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "تعديل طالب", "mode": "edit", "student": await service.get_student_detail(student_id),
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
