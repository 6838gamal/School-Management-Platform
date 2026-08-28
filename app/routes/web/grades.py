"""Grades web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.grade_service import GradeService
from app.services.academic_service import AcademicService
from app.schemas.grades import (
    AssessmentCreate, AssessmentUpdate, GradeRecordCreate, GradeRecordBatch
)

router = APIRouter(prefix="/grades", tags=["grades"])
templates = Jinja2Templates(directory="app/templates")


# ============= دوال مساعدة مؤقتة =============
# TODO: استبدل هذه الدوال بالخدمات الحقيقية عند توفرها

async def get_sections(db: AsyncSession, school_id: str):
    """جلب الشعب من AcademicService"""
    service = AcademicService(db)
    return await service.sections.list_by_school(school_id)


async def get_subjects(db: AsyncSession, school_id: str):
    """جلب المواد من AcademicService"""
    service = AcademicService(db)
    return await service.subjects.list_by_school(school_id)


async def get_teachers(db: AsyncSession, school_id: str):
    """جلب المعلمين (مؤقت)"""
    # TODO: استبدل بخدمة المعلمين
    return []


async def get_students_by_section(db: AsyncSession, section_id: str, school_id: str):
    """جلب طلاب الشعبة (مؤقت)"""
    # TODO: استبدل بخدمة الطلاب
    return []


# ============= الصفحة الرئيسية =============
@router.get("")
async def grades_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    """عرض صفحة الدرجات الرئيسية"""
    service = GradeService(db)
    
    # جلب التقييمات
    assessments = await service.get_all_assessments(
        school_id=user.school_id,
        search=search,
        page=page,
        page_size=page_size
    )
    
    # جلب البيانات للفلاتر من AcademicService
    sections = await get_sections(db, user.school_id)
    subjects = await get_subjects(db, user.school_id)
    
    return templates.TemplateResponse(
        "grades/index.html",
        {
            **ctx,
            "title": "الدرجات",
            "assessments": assessments,
            "total": len(assessments),
            "page": page,
            "page_size": page_size,
            "search": search or "",
            "sections": sections,
            "subjects": subjects,
            "now": datetime.now(),
        },
    )


@router.get("/list")
async def list_assessments(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة التقييمات (للـ AJAX)"""
    service = GradeService(db)
    assessments = await service.get_all_assessments(user.school_id)
    return templates.TemplateResponse(
        "grades/list.html",
        {**ctx, "title": "قائمة التقييمات", "items": assessments}
    )


# ============= التقييمات =============

@router.get("/create")
async def create_assessment_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض صفحة إنشاء تقييم جديد"""
    # جلب البيانات من AcademicService
    sections = await get_sections(db, user.school_id)
    subjects = await get_subjects(db, user.school_id)
    teachers = await get_teachers(db, user.school_id)
    
    return templates.TemplateResponse(
        "grades/create.html",
        {
            **ctx,
            "title": "إنشاء تقييم جديد",
            "sections": sections,
            "subjects": subjects,
            "teachers": teachers,
        }
    )


@router.get("/{assessment_id}/update")
async def edit_assessment_page(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض صفحة تعديل التقييم"""
    service = GradeService(db)
    assessment = await service.get_assessment_by_id(assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # جلب البيانات للقوائم المنسدلة
    sections = await get_sections(db, user.school_id)
    subjects = await get_subjects(db, user.school_id)
    teachers = await get_teachers(db, user.school_id)
    
    return templates.TemplateResponse(
        "grades/update.html",
        {
            **ctx,
            "title": "تعديل التقييم",
            "item": assessment,
            "sections": sections,
            "subjects": subjects,
            "teachers": teachers,
            "now": datetime.now(),
        }
    )


@router.get("/{assessment_id}")
async def show_assessment(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض تفاصيل تقييم محدد"""
    service = GradeService(db)
    assessment = await service.get_assessment_by_id(assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # جلب درجات الطلاب لهذا التقييم
    grades = await service.get_grades_by_assessment(assessment_id)
    
    return templates.TemplateResponse(
        "grades/show.html",
        {
            **ctx,
            "title": "تفاصيل التقييم",
            "item": assessment,
            "grades": grades,
            "now": datetime.now(),
        }
    )


@router.get("/{assessment_id}/grades")
async def view_assessment_grades(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض صفحة إدخال درجات التقييم"""
    service = GradeService(db)
    assessment = await service.get_assessment_by_id(assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # جلب الطلاب في الشعبة
    students = await get_students_by_section(db, assessment.section_id, user.school_id)
    
    # جلب الدرجات المسجلة
    grades = await service.get_grades_by_assessment(assessment_id)
    
    return templates.TemplateResponse(
        "grades/entry.html",
        {
            **ctx,
            "title": "إدخال درجات التقييم",
            "assessment": assessment,
            "students": students,
            "grades": grades,
            "now": datetime.now(),
        }
    )


# ============= API Routes =============

@router.post("/api/assessments/create")
async def create_assessment_api(
    req: AssessmentCreate,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء تقييم جديد"""
    service = GradeService(db)
    result = await service.create_assessment(user.school_id, req, user.id)
    return {
        "success": True,
        "id": result.id,
        "message": "تم إنشاء التقييم بنجاح"
    }


@router.put("/api/assessments/{assessment_id}")
async def update_assessment_api(
    assessment_id: str,
    req: AssessmentUpdate,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث التقييم"""
    service = GradeService(db)
    result = await service.update_assessment(assessment_id, req)
    return {
        "success": True,
        "message": "تم تحديث التقييم بنجاح"
    }


@router.delete("/api/assessments/{assessment_id}")
async def delete_assessment_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف التقييم"""
    service = GradeService(db)
    await service.delete_assessment(assessment_id)
    return {
        "success": True,
        "message": "تم حذف التقييم بنجاح"
    }


@router.post("/api/grades/batch")
async def create_grades_batch_api(
    req: GradeRecordBatch,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إدخال درجات متعددة (Batch)"""
    service = GradeService(db)
    result = await service.create_grades_batch(req, user.id)
    return {
        "success": True,
        "count": len(result),
        "message": f"تم إدخال {len(result)} درجة بنجاح"
    }


@router.post("/api/grades/single")
async def create_grade_api(
    req: GradeRecordCreate,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إدخال درجة واحدة"""
    service = GradeService(db)
    result = await service.create_grade(req, user.id)
    return {
        "success": True,
        "id": result.id,
        "message": "تم إدخال الدرجة بنجاح"
    }


@router.put("/api/grades/{grade_id}")
async def update_grade_api(
    grade_id: str,
    req: dict,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث درجة"""
    service = GradeService(db)
    result = await service.update_grade(grade_id, req)
    return {
        "success": True,
        "message": "تم تحديث الدرجة بنجاح"
    }


@router.delete("/api/grades/{grade_id}")
async def delete_grade_api(
    grade_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف درجة"""
    service = GradeService(db)
    await service.delete_grade(grade_id)
    return {
        "success": True,
        "message": "تم حذف الدرجة بنجاح"
    }


@router.get("/api/assessments")
async def get_assessments_api(
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    """API: جلب قائمة التقييمات"""
    service = GradeService(db)
    assessments = await service.get_all_assessments(
        school_id=user.school_id,
        search=search,
        page=page,
        page_size=page_size
    )
    return {
        "success": True,
        "items": assessments,
        "total": len(assessments),
        "page": page,
        "page_size": page_size,
    }


@router.get("/api/assessments/{assessment_id}")
async def get_assessment_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب تفاصيل تقييم"""
    service = GradeService(db)
    assessment = await service.get_assessment_by_id(assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    return {"success": True, "item": assessment}


@router.get("/api/assessments/{assessment_id}/grades")
async def get_assessment_grades_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب درجات التقييم"""
    service = GradeService(db)
    grades = await service.get_grades_by_assessment(assessment_id)
    return {"success": True, "items": grades}


@router.get("/api/students/{section_id}")
async def get_students_by_section_api(
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب طلاب الشعبة لإدخال الدرجات"""
    students = await get_students_by_section(db, section_id, user.school_id)
    return {"success": True, "items": students}


# ============= إحصائيات =============

@router.get("/statistics")
async def get_statistics(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض صفحة إحصائيات الدرجات"""
    service = GradeService(db)
    stats = await service.get_statistics(user.school_id)
    
    return templates.TemplateResponse(
        "grades/statistics.html",
        {
            **ctx,
            "title": "إحصائيات الدرجات",
            "stats": stats,
            "now": datetime.now(),
        }
    )


@router.get("/api/statistics")
async def get_statistics_api(
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب إحصائيات الدرجات"""
    service = GradeService(db)
    stats = await service.get_statistics(user.school_id)
    return {"success": True, "data": stats}
