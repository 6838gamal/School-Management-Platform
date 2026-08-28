"""Students web routes — shared pages used by director, deputy, and teacher."""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.student_service import StudentService
from app.schemas.students import StudentCreate, StudentUpdate
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ValidationException,
    AppException
)

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# 🔴 IMPORTANT: الترتيب مهم جداً!
#    المسارات الثابتة (مثل /new) يجب أن تأتي قبل المسارات الديناميكية (مثل /{student_id})
# ============================================================

# 1️⃣ GET /students/new - صفحة إضافة طالب جديد (يجب أن يكون أولاً!)
@router.get("/new")
async def student_new(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    try:
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", 
             "sections": data.get("sections", []), "years": data.get("years", [])},
        )
    except AppException as e:
        return templates.TemplateResponse(
            "errors/error.html",
            {**ctx, "message": str(e)},
            status_code=400
        )


# 2️⃣ POST /students - إنشاء طالب جديد
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
    ctx = await template_context(request, user)
    
    # التحقق من صحة البيانات الأساسية
    if not student_number or len(student_number) < 3:
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", 
             "sections": data.get("sections", []), "years": data.get("years", []),
             "error": "رقم الطالب يجب أن يكون 3 أحرف على الأقل"},
            status_code=400
        )
    
    if not first_name or len(first_name) < 2:
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", 
             "sections": data.get("sections", []), "years": data.get("years", []),
             "error": "الاسم الأول يجب أن يكون حرفين على الأقل"},
            status_code=400
        )
    
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
        # ✅ تمرير user.id و user.school_id
        student = await service.create_student(student_data, user.id, user.school_id)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except ConflictException as e:
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", 
             "sections": data.get("sections", []), "years": data.get("years", []), 
             "error": str(e)},
            status_code=409
        )
    except ValidationException as e:
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", 
             "sections": data.get("sections", []), "years": data.get("years", []), 
             "error": str(e)},
            status_code=422
        )
    except AppException as e:
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "إضافة طالب", "mode": "create", 
             "sections": data.get("sections", []), "years": data.get("years", []), 
             "error": str(e)},
            status_code=400
        )


# 3️⃣ GET /students - قائمة الطلاب
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


# 4️⃣ GET /students/{student_id}/edit - صفحة تعديل الطالب (يجب أن يأتي قبل /{student_id})
@router.get("/{student_id}/edit")
async def student_edit(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = StudentService(db)
    try:
        detail = await service.get_student_detail(student_id)
        
        from app.services.academic_service import AcademicService
        academic = AcademicService(db)
        data = await academic.get_onboarding_data(user.school_id)
        
        return templates.TemplateResponse(
            "students/form.html",
            {**ctx, "title": "تعديل طالب", "mode": "edit", "student": detail, 
             "sections": data.get("sections", []), "years": data.get("years", [])},
        )
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except AppException as e:
        return templates.TemplateResponse(
            "errors/error.html",
            {**ctx, "message": str(e)},
            status_code=400
        )


# 5️⃣ POST /students/{student_id}/edit - تحديث بيانات الطالب
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
    ctx = await template_context(request, user)
    
    # التحقق من صحة البيانات
    if first_name is not None and len(first_name) < 2:
        try:
            detail = await service.get_student_detail(student_id)
            from app.services.academic_service import AcademicService
            academic = AcademicService(db)
            data = await academic.get_onboarding_data(user.school_id)
            return templates.TemplateResponse(
                "students/form.html",
                {**ctx, "title": "تعديل طالب", "mode": "edit", "student": detail,
                 "sections": data.get("sections", []), "years": data.get("years", []), 
                 "error": "الاسم الأول يجب أن يكون حرفين على الأقل"},
                status_code=400
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    
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
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except ConflictException as e:
        try:
            detail = await service.get_student_detail(student_id)
            from app.services.academic_service import AcademicService
            academic = AcademicService(db)
            data = await academic.get_onboarding_data(user.school_id)
            return templates.TemplateResponse(
                "students/form.html",
                {**ctx, "title": "تعديل طالب", "mode": "edit", "student": detail,
                 "sections": data.get("sections", []), "years": data.get("years", []), 
                 "error": str(e)},
                status_code=409
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    except ValidationException as e:
        try:
            detail = await service.get_student_detail(student_id)
            from app.services.academic_service import AcademicService
            academic = AcademicService(db)
            data = await academic.get_onboarding_data(user.school_id)
            return templates.TemplateResponse(
                "students/form.html",
                {**ctx, "title": "تعديل طالب", "mode": "edit", "student": detail,
                 "sections": data.get("sections", []), "years": data.get("years", []), 
                 "error": str(e)},
                status_code=422
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    except AppException as e:
        try:
            detail = await service.get_student_detail(student_id)
            from app.services.academic_service import AcademicService
            academic = AcademicService(db)
            data = await academic.get_onboarding_data(user.school_id)
            return templates.TemplateResponse(
                "students/form.html",
                {**ctx, "title": "تعديل طالب", "mode": "edit", "student": detail,
                 "sections": data.get("sections", []), "years": data.get("years", []), 
                 "error": str(e)},
                status_code=400
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )


# 6️⃣ POST /students/{student_id} - حذف الطالب
@router.post("/{student_id}")
async def student_delete(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    try:
        await service.delete_student(student_id)
        return RedirectResponse(url="/students", status_code=303)
    except (NotFoundException, AppException):
        return RedirectResponse(url="/students", status_code=303)


# 7️⃣ GET /students/{student_id} - تفاصيل الطالب (يجب أن يكون في النهاية!)
@router.get("/{student_id}")
async def student_detail(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = StudentService(db)
    try:
        detail = await service.get_student_detail(student_id)
        return templates.TemplateResponse(
            "students/detail.html",
            {**ctx, "title": detail["full_name"], "student": detail},
        )
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except AppException as e:
        return templates.TemplateResponse(
            "errors/error.html",
            {**ctx, "message": str(e)},
            status_code=e.status_code if hasattr(e, 'status_code') else 400
        )
