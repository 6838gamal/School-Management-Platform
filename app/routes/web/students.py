"""Students web routes — shared pages used by director, deputy, and teacher."""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid
import traceback
from datetime import datetime

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
# النماذج
from app.models.students import Student
from app.models.academics import Section, Grade, Stage, AcademicYear, Period

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# 🔴 IMPORTANT: الترتيب مهم جداً!
#    المسارات الثابتة (مثل /new) يجب أن تأتي قبل المسارات الديناميكية (مثل /{student_id})
# ============================================================

# ============================================================
# دالة مساعدة لجلب بيانات الفصول والسنوات والصفوف والفترات
# ============================================================
async def get_onboarding_data(db: AsyncSession, school_id: str):
    """
    جلب بيانات الفصول والسنوات والصفوف والفترات للمدرسة
    """
    try:
        # 1. جلب السنوات الدراسية
        years_result = await db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .order_by(AcademicYear.start_date.desc())
        )
        years = years_result.scalars().all()
        
        # 2. جلب الصفوف
        grades_result = await db.execute(
            select(Grade)
            .where(Grade.school_id == school_id)
            .order_by(Grade.order)
        )
        grades = grades_result.scalars().all()
        
        # 3. جلب الشعب مع العلاقات
        sections_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade)
            )
            .where(Section.school_id == school_id)
            .order_by(Section.name)
        )
        sections = sections_result.scalars().all()
        
        
        
        return {
            "years": years,
            "grades": grades,
            "sections": sections,
            
        }
    except Exception as e:
        print(f"⚠️ Error in get_onboarding_data: {str(e)}")
        return {"years": [], "grades": [], "sections": [], "periods": []}


# 1️⃣ GET /students/new - صفحة إضافة طالب جديد
@router.get("/new")
async def student_new(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    try:
        data = await get_onboarding_data(db, user.school_id)
        
        # تحويل البيانات إلى صيغة مناسبة للقالب
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": sections_data, 
                "years": data.get("years", []),
                "grades": data.get("grades", []),
        
                "student": None,
                "error": None
            },
        )
    except Exception as e:
        print(f"❌ Error in student_new: {str(e)}")
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": [], 
                "years": [],
                "grades": [],
                
                "student": None,
                "error": f"حدث خطأ: {str(e)}"
            },
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
    year_id: Optional[str] = Form(None),
    grade_id: Optional[str] = Form(None),
    section_id: Optional[str] = Form(None),
    
):
    service = StudentService(db)
    ctx = await template_context(request)
    
    # ✅ جمع الأخطاء لعرضها للمستخدم
    errors = {}
    
    # التحقق من صحة البيانات الأساسية
    if not student_number or len(student_number.strip()) < 3:
        errors["student_number"] = "رقم الطالب يجب أن يكون 3 أحرف على الأقل"
    
    if not first_name or len(first_name.strip()) < 2:
        errors["first_name"] = "الاسم الأول يجب أن يكون حرفين على الأقل"
    
    if not last_name or len(last_name.strip()) < 2:
        errors["last_name"] = "اسم العائلة يجب أن يكون حرفين على الأقل"
    
    # إذا كان هناك أخطاء، ارجع الصفحة مع رسائل الخطأ
    if errors:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": sections_data, 
                "years": data.get("years", []),
                "grades": data.get("grades", []),
                
                "student": None,
                "error": "الرجاء تصحيح الأخطاء التالية:<br>• " + "<br>• ".join(errors.values())
            },
            status_code=422
        )
    
    student_data = StudentCreate(
        student_number=student_number.strip(),
        national_id=national_id.strip() if national_id else None,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        gender=gender,
        birth_date=birth_date,
        guardian_name=guardian_name.strip() if guardian_name else None,
        guardian_phone=guardian_phone.strip() if guardian_phone else None,
        guardian_email=guardian_email.strip().lower() if guardian_email else None,
        address=address.strip() if address else None,
        year_id=year_id,
        grade_id=grade_id,
        section_id=section_id,
    
    )
    
    try:
        student = await service.create_student(student_data, user.id, user.school_id)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except ConflictException as e:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": sections_data, 
                "years": data.get("years", []),
                "grades": data.get("grades", []),
                
                "student": None,
                "error": str(e)
            },
            status_code=409
        )
    except ValidationException as e:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": sections_data, 
                "years": data.get("years", []),
                "grades": data.get("grades", []),
                
                "student": None,
                "error": str(e)
            },
            status_code=422
        )
    except AppException as e:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": sections_data, 
                "years": data.get("years", []),
                "grades": data.get("grades", []),
                
                "student": None,
                "error": str(e)
            },
            status_code=400
        )
    except Exception as e:
        print(f"❌ Error in student_create: {str(e)}")
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": sections_data, 
                "years": data.get("years", []),
                "grades": data.get("grades", []),
            
                "student": None,
                "error": f"حدث خطأ غير متوقع: {str(e)}"
            },
            status_code=500
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
    try:
        service = StudentService(db)
        result = await service.list_students(user.school_id, page, 20, search or None)
        return templates.TemplateResponse(
            "students/list.html",
            {
                **ctx, 
                "title": "الطلاب", 
                "students": result.get("items", []), 
                "total": result.get("total", 0),
                "page": page, 
                "page_size": 20, 
                "search": search
            },
        )
    except Exception as e:
        print(f"❌ Error in students_list: {str(e)}")
        return templates.TemplateResponse(
            "students/list.html",
            {
                **ctx, 
                "title": "الطلاب", 
                "students": [], 
                "total": 0,
                "page": page, 
                "page_size": 20, 
                "search": search,
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# 4️⃣ GET /students/{student_id}/edit - صفحة تعديل الطالب
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
        data = await get_onboarding_data(db, user.school_id)
        
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "تعديل طالب", 
                "mode": "edit", 
                "student": detail, 
                "sections": sections_data, 
                "years": data.get("years", []),
                "grades": data.get("grades", []),
                
                "error": None
            },
        )
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error in student_edit: {str(e)}")
        return templates.TemplateResponse(
            "errors/error.html",
            {**ctx, "message": f"حدث خطأ: {str(e)}"},
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
    year_id: Optional[str] = Form(None),
    grade_id: Optional[str] = Form(None),
    section_id: Optional[str] = Form(None),
    
    is_active: Optional[bool] = Form(None),
):
    service = StudentService(db)
    ctx = await template_context(request)
    
    # ✅ جمع الأخطاء لعرضها للمستخدم
    errors = {}
    
    if first_name is not None and first_name.strip() and len(first_name.strip()) < 2:
        errors["first_name"] = "الاسم الأول يجب أن يكون حرفين على الأقل"
    
    if last_name is not None and last_name.strip() and len(last_name.strip()) < 2:
        errors["last_name"] = "اسم العائلة يجب أن يكون حرفين على الأقل"
    
    if errors:
        try:
            detail = await service.get_student_detail(student_id)
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": detail,
                    "sections": sections_data, 
                    "years": data.get("years", []),
                    "grades": data.get("grades", []),
                    
                    "error": "الرجاء تصحيح الأخطاء التالية:<br>• " + "<br>• ".join(errors.values())
                },
                status_code=422
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    
    student_update = StudentUpdate(
        first_name=first_name.strip() if first_name else None,
        last_name=last_name.strip() if last_name else None,
        national_id=national_id.strip() if national_id else None,
        gender=gender,
        birth_date=birth_date,
        guardian_name=guardian_name.strip() if guardian_name else None,
        guardian_phone=guardian_phone.strip() if guardian_phone else None,
        guardian_email=guardian_email.strip().lower() if guardian_email else None,
        address=address.strip() if address else None,
        year_id=year_id,
        grade_id=grade_id,
        section_id=section_id,
    
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
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": detail,
                    "sections": sections_data, 
                    "years": data.get("years", []),
                    "grades": data.get("grades", []),
                    
                    "error": str(e)
                },
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
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": detail,
                    "sections": sections_data, 
                    "years": data.get("years", []),
                    "grades": data.get("grades", []),
                
                    "error": str(e)
                },
                status_code=422
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    except Exception as e:
        print(f"❌ Error in student_update: {str(e)}")
        try:
            detail = await service.get_student_detail(student_id)
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": detail,
                    "sections": sections_data, 
                    "years": data.get("years", []),
                    "grades": data.get("grades", []),
                    
                    "error": f"حدث خطأ غير متوقع: {str(e)}"
                },
                status_code=500
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
    except Exception as e:
        print(f"❌ Error in student_delete: {str(e)}")
        return RedirectResponse(url="/students", status_code=303)


# 7️⃣ GET /students/{student_id} - تفاصيل الطالب
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
            {**ctx, "title": detail.get("full_name", "تفاصيل الطالب"), "student": detail},
        )
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error in student_detail: {str(e)}")
        return templates.TemplateResponse(
            "errors/error.html",
            {**ctx, "message": f"حدث خطأ: {str(e)}"},
            status_code=400
        )


# ============================================================
# 🔧 مسار تصحيح إضافي - عرض جميع الطلاب مع فصولهم
# ============================================================
@router.get("/debug/all")
async def debug_all_students(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    عرض جميع الطلاب مع فصولهم (للتأكد من ارتباطهم)
    """
    try:
        students_result = await db.execute(
            select(Student, Section, Grade, AcademicYear)
            .outerjoin(Section, Student.section_id == Section.id)
            .outerjoin(Grade, Student.grade_id == Grade.id)
            .outerjoin(AcademicYear, Student.year_id == AcademicYear.id)
            .where(Student.school_id == user.school_id)
        )
        students = students_result.all()
        
        result = []
        for student, section, grade, year in students:
            result.append({
                "id": str(student.id),
                "name": student.full_name,
                "year_id": str(student.year_id) if student.year_id else None,
                "year_name": year.name if year else None,
                "grade_id": str(student.grade_id) if student.grade_id else None,
                "grade_name": grade.name if grade else None,
                "section_id": str(student.section_id) if student.section_id else None,
                "section_name": section.name if section else None,
                "school_id": str(student.school_id),
                "is_active": student.is_active if hasattr(student, 'is_active') else True
            })
        
        return JSONResponse({
            "total": len(result),
            "students": result
        })
        
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)
