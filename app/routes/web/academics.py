"""Academic structure web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.core.exceptions import NotFoundException, ConflictException, ValidationException  # ✅ تصحيح الاستيراد
from app.services.academic_service import AcademicService
from app.schemas.academics import (
    AcademicYearCreate, StageCreate, GradeCreate, SectionCreate,
    SubjectCreate, RoomCreate, PeriodCreate,
    AcademicYearUpdate, StageUpdate, GradeUpdate, 
    SectionUpdate, SubjectUpdate, RoomUpdate, PeriodUpdate
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/academics", tags=["academics"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
#  الصفحة الرئيسية
# ============================================================

@router.get("")
async def academics_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """الصفحة الرئيسية للهيكل الأكاديمي"""
    service = AcademicService(db)
    data = await service.get_onboarding_data(user.school_id)
    return templates.TemplateResponse(
        "academics/index.html",
        {**ctx, "title": "الهيكل الأكاديمي", "data": data},
    )


# ============================================================
#  الأعوام الدراسية - Years
# ============================================================

@router.get("/years/list")
async def list_years(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة الأعوام الدراسية"""
    service = AcademicService(db)
    years = await service.years.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/years/list.html",
        {**ctx, "title": "الأعوام الدراسية", "items": years, "type": "years"}
    )


@router.get("/years/create")
async def create_year_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    ctx: dict = Depends(template_context),
):
    """صفحة إضافة عام دراسي"""
    return templates.TemplateResponse(
        "academics/years/create.html",
        {**ctx, "title": "إضافة عام دراسي"}
    )


@router.get("/years/{year_id}/update")
async def edit_year_page(
    request: Request,
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل عام دراسي"""
    service = AcademicService(db)
    year = await service.years.get_by_id(year_id)
    if not year:
        raise HTTPException(status_code=404, detail="العام الدراسي غير موجود")
    return templates.TemplateResponse(
        "academics/years/update.html",
        {**ctx, "title": "تعديل عام دراسي", "item": year}
    )


@router.post("/api/years/create")
async def create_year_api(
    req: AcademicYearCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء عام دراسي جديد"""
    service = AcademicService(db)
    try:
        result = await service.create_year(user.school_id, req)
        return {"success": True, "id": result.id, "message": "تم إضافة العام الدراسي بنجاح"}
    except ConflictException as e:  # ✅ استخدام ConflictException
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating year: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة العام الدراسي"
        )


@router.put("/api/years/{year_id}")
async def update_year_api(
    year_id: str,
    req: AcademicYearUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث عام دراسي"""
    service = AcademicService(db)
    try:
        await service.update_year(year_id, req)
        return {"success": True, "message": "تم تحديث العام الدراسي بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="العام الدراسي غير موجود")
    except Exception as e:
        logger.error(f"Error updating year: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث العام الدراسي"
        )


@router.delete("/api/years/{year_id}")
async def delete_year_api(
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف عام دراسي"""
    service = AcademicService(db)
    try:
        await service.delete_year(year_id)
        return {"success": True, "message": "تم حذف العام الدراسي بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="العام الدراسي غير موجود")
    except Exception as e:
        logger.error(f"Error deleting year: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف العام الدراسي"
        )


# ============================================================
#  المراحل - Stages
# ============================================================

@router.get("/stages/list")
async def list_stages(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة المراحل"""
    service = AcademicService(db)
    stages = await service.stages.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/stages/list.html",
        {**ctx, "title": "المراحل", "items": stages, "type": "stages"}
    )


@router.get("/stages/create")
async def create_stage_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة إضافة مرحلة"""
    service = AcademicService(db)
    years = await service.years.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/stages/create.html",
        {**ctx, "title": "إضافة مرحلة", "years": years}
    )


@router.get("/stages/{stage_id}/update")
async def edit_stage_page(
    request: Request,
    stage_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل مرحلة"""
    service = AcademicService(db)
    stage = await service.stages.get_by_id(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="المرحلة غير موجودة")
    years = await service.years.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/stages/update.html",
        {**ctx, "title": "تعديل مرحلة", "item": stage, "years": years}
    )


@router.post("/api/stages/create")
async def create_stage_api(
    req: StageCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء مرحلة جديدة"""
    service = AcademicService(db)
    try:
        result = await service.create_stage(user.school_id, req)
        return {"success": True, "id": result.id, "message": "تم إضافة المرحلة بنجاح"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictException as e:  # ✅ استخدام ConflictException
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating stage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة المرحلة"
        )


@router.put("/api/stages/{stage_id}")
async def update_stage_api(
    stage_id: str,
    req: StageUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث مرحلة"""
    service = AcademicService(db)
    try:
        await service.update_stage(stage_id, req)
        return {"success": True, "message": "تم تحديث المرحلة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="المرحلة غير موجودة")
    except Exception as e:
        logger.error(f"Error updating stage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المرحلة"
        )


@router.delete("/api/stages/{stage_id}")
async def delete_stage_api(
    stage_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف مرحلة"""
    service = AcademicService(db)
    try:
        await service.delete_stage(stage_id)
        return {"success": True, "message": "تم حذف المرحلة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="المرحلة غير موجودة")
    except Exception as e:
        logger.error(f"Error deleting stage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المرحلة"
        )


# ============================================================
#  الصفوف - Grades (مع دعم السنة الدراسية)
# ============================================================

@router.get("/grades/list")
async def list_grades(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    year_id: Optional[str] = None,
):
    """عرض قائمة الصفوف"""
    service = AcademicService(db)
    
    # جلب جميع الصفوف مع إمكانية التصفية
    if year_id:
        grades = await service.grades.list_by_school_and_year(user.school_id, year_id)
    else:
        grades = await service.grades.list_by_school(user.school_id)
    
    # جلب السنوات للفلترة
    years = await service.years.list_by_school(user.school_id)
    
    return templates.TemplateResponse(
        "academics/grades/list.html",
        {
            **ctx,
            "title": "الصفوف",
            "items": grades,
            "type": "grades",
            "years": years,
            "selected_year": year_id
        }
    )


@router.get("/grades/create")
async def create_grade_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة إضافة صف جديد - مع دعم السنة الدراسية"""
    service = AcademicService(db)
    
    # جلب السنوات الدراسية للمدرسة
    years = await service.years.list_by_school(user.school_id)
    
    # جلب المراحل (مرتبطة بالسنوات)
    stages = await service.stages.list_by_school(user.school_id)
    
    return templates.TemplateResponse(
        "academics/grades/create.html",
        {
            **ctx,
            "title": "إضافة صف",
            "years": years,
            "stages": stages,
        }
    )


@router.get("/grades/{grade_id}/update")
async def edit_grade_page(
    request: Request,
    grade_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل صف - مع دعم السنة الدراسية"""
    service = AcademicService(db)
    
    grade = await service.grades.get_by_id(grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="الصف غير موجود")
    
    years = await service.years.list_by_school(user.school_id)
    stages = await service.stages.list_by_school(user.school_id)
    
    return templates.TemplateResponse(
        "academics/grades/update.html",
        {
            **ctx,
            "title": "تعديل صف",
            "item": grade,
            "years": years,
            "stages": stages,
        }
    )


@router.post("/api/grades/create")
async def create_grade_api(
    req: GradeCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء صف جديد - مع دعم السنة الدراسية"""
    service = AcademicService(db)
    
    try:
        # التحقق من وجود السنة الدراسية
        year = await service.years.get_by_id(req.year_id)
        if not year:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="السنة الدراسية غير موجودة"
            )
        
        # التحقق من وجود المرحلة
        stage = await service.stages.get_by_id(req.stage_id)
        if not stage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المرحلة غير موجودة"
            )
        
        # التحقق من أن المرحلة تابعة للسنة المحددة
        if stage.year_id != req.year_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="المرحلة المحددة لا تنتمي إلى السنة الدراسية المختارة"
            )
        
        # إنشاء الصف
        result = await service.create_grade(user.school_id, req)
        
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة الصف بنجاح"
        }
        
    except HTTPException:
        raise
    except ConflictException as e:  # ✅ استخدام ConflictException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValidationException as e:  # ✅ استخدام ValidationException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating grade: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة الصف"
        )


@router.put("/api/grades/{grade_id}")
async def update_grade_api(
    grade_id: str,
    req: GradeUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث صف - مع دعم السنة الدراسية"""
    service = AcademicService(db)
    
    try:
        # إذا تم تغيير السنة، التحقق من وجودها
        if req.year_id:
            year = await service.years.get_by_id(req.year_id)
            if not year:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="السنة الدراسية غير موجودة"
                )
        
        # إذا تم تغيير المرحلة، التحقق من وجودها
        if req.stage_id:
            stage = await service.stages.get_by_id(req.stage_id)
            if not stage:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="المرحلة غير موجودة"
                )
            
            # التحقق من أن المرحلة تابعة للسنة المحددة
            if req.year_id and stage.year_id != req.year_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="المرحلة المحددة لا تنتمي إلى السنة الدراسية المختارة"
                )
        
        await service.update_grade(grade_id, req)
        return {"success": True, "message": "تم تحديث الصف بنجاح"}
        
    except NotFoundException:
        raise HTTPException(status_code=404, detail="الصف غير موجود")
    except ConflictException as e:  # ✅ استخدام ConflictException
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationException as e:  # ✅ استخدام ValidationException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating grade: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الصف"
        )


@router.delete("/api/grades/{grade_id}")
async def delete_grade_api(
    grade_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف صف"""
    service = AcademicService(db)
    try:
        await service.delete_grade(grade_id)
        return {"success": True, "message": "تم حذف الصف بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="الصف غير موجود")
    except Exception as e:
        logger.error(f"Error deleting grade: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الصف"
        )


# ============================================================
#  الشعب - Sections
# ============================================================

@router.get("/sections/list")
async def list_sections(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    grade_id: Optional[str] = None,
):
    """عرض قائمة الشعب"""
    service = AcademicService(db)
    
    if grade_id:
        sections = await service.sections.list_by_grade(grade_id)
    else:
        sections = await service.sections.list_by_school(user.school_id)
    
    grades = await service.grades.list_by_school(user.school_id)
    
    return templates.TemplateResponse(
        "academics/sections/list.html",
        {
            **ctx,
            "title": "الشعب",
            "items": sections,
            "type": "sections",
            "grades": grades,
            "selected_grade": grade_id
        }
    )


@router.get("/sections/create")
async def create_section_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة إضافة شعبة"""
    service = AcademicService(db)
    grades = await service.grades.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/sections/create.html",
        {**ctx, "title": "إضافة شعبة", "grades": grades}
    )


@router.get("/sections/{section_id}/update")
async def edit_section_page(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل شعبة"""
    service = AcademicService(db)
    section = await service.sections.get_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="الشعبة غير موجودة")
    grades = await service.grades.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/sections/update.html",
        {**ctx, "title": "تعديل شعبة", "item": section, "grades": grades}
    )


@router.post("/api/sections/create")
async def create_section_api(
    req: SectionCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء شعبة جديدة"""
    service = AcademicService(db)
    try:
        result = await service.create_section(user.school_id, req)
        return {"success": True, "id": result.id, "message": "تم إضافة الشعبة بنجاح"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating section: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة الشعبة"
        )


@router.put("/api/sections/{section_id}")
async def update_section_api(
    section_id: str,
    req: SectionUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث شعبة"""
    service = AcademicService(db)
    try:
        await service.update_section(section_id, req)
        return {"success": True, "message": "تم تحديث الشعبة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="الشعبة غير موجودة")
    except Exception as e:
        logger.error(f"Error updating section: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الشعبة"
        )


@router.delete("/api/sections/{section_id}")
async def delete_section_api(
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف شعبة"""
    service = AcademicService(db)
    try:
        await service.delete_section(section_id)
        return {"success": True, "message": "تم حذف الشعبة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="الشعبة غير موجودة")
    except Exception as e:
        logger.error(f"Error deleting section: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الشعبة"
        )


# ============================================================
#  المواد - Subjects
# ============================================================

@router.get("/subjects/list")
async def list_subjects(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة المواد"""
    service = AcademicService(db)
    subjects = await service.subjects.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/subjects/list.html",
        {**ctx, "title": "المواد", "items": subjects, "type": "subjects"}
    )


@router.get("/subjects/create")
async def create_subject_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    ctx: dict = Depends(template_context),
):
    """صفحة إضافة مادة"""
    return templates.TemplateResponse(
        "academics/subjects/create.html",
        {**ctx, "title": "إضافة مادة"}
    )


@router.get("/subjects/{subject_id}/update")
async def edit_subject_page(
    request: Request,
    subject_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل مادة"""
    service = AcademicService(db)
    subject = await service.subjects.get_by_id(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="المادة غير موجودة")
    return templates.TemplateResponse(
        "academics/subjects/update.html",
        {**ctx, "title": "تعديل مادة", "item": subject}
    )


@router.post("/api/subjects/create")
async def create_subject_api(
    req: SubjectCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء مادة جديدة"""
    service = AcademicService(db)
    try:
        result = await service.create_subject(user.school_id, req)
        return {"success": True, "id": result.id, "message": "تم إضافة المادة بنجاح"}
    except ConflictException as e:  # ✅ استخدام ConflictException
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating subject: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة المادة"
        )


@router.put("/api/subjects/{subject_id}")
async def update_subject_api(
    subject_id: str,
    req: SubjectUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث مادة"""
    service = AcademicService(db)
    try:
        await service.update_subject(subject_id, req)
        return {"success": True, "message": "تم تحديث المادة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="المادة غير موجودة")
    except Exception as e:
        logger.error(f"Error updating subject: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المادة"
        )


@router.delete("/api/subjects/{subject_id}")
async def delete_subject_api(
    subject_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف مادة"""
    service = AcademicService(db)
    try:
        await service.delete_subject(subject_id)
        return {"success": True, "message": "تم حذف المادة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="المادة غير موجودة")
    except Exception as e:
        logger.error(f"Error deleting subject: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المادة"
        )


# ============================================================
#  القاعات - Rooms
# ============================================================

@router.get("/rooms/list")
async def list_rooms(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة القاعات"""
    service = AcademicService(db)
    rooms = await service.rooms.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/rooms/list.html",
        {**ctx, "title": "القاعات", "items": rooms, "type": "rooms"}
    )


@router.get("/rooms/create")
async def create_room_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    ctx: dict = Depends(template_context),
):
    """صفحة إضافة قاعة"""
    return templates.TemplateResponse(
        "academics/rooms/create.html",
        {**ctx, "title": "إضافة قاعة"}
    )


@router.get("/rooms/{room_id}/update")
async def edit_room_page(
    request: Request,
    room_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل قاعة"""
    service = AcademicService(db)
    room = await service.rooms.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="القاعة غير موجودة")
    return templates.TemplateResponse(
        "academics/rooms/update.html",
        {**ctx, "title": "تعديل قاعة", "item": room}
    )


@router.post("/api/rooms/create")
async def create_room_api(
    req: RoomCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء قاعة جديدة"""
    service = AcademicService(db)
    try:
        result = await service.create_room(user.school_id, req)
        return {"success": True, "id": result.id, "message": "تم إضافة القاعة بنجاح"}
    except ConflictException as e:  # ✅ استخدام ConflictException
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating room: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة القاعة"
        )


@router.put("/api/rooms/{room_id}")
async def update_room_api(
    room_id: str,
    req: RoomUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث قاعة"""
    service = AcademicService(db)
    try:
        await service.update_room(room_id, req)
        return {"success": True, "message": "تم تحديث القاعة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="القاعة غير موجودة")
    except Exception as e:
        logger.error(f"Error updating room: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث القاعة"
        )


@router.delete("/api/rooms/{room_id}")
async def delete_room_api(
    room_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف قاعة"""
    service = AcademicService(db)
    try:
        await service.delete_room(room_id)
        return {"success": True, "message": "تم حذف القاعة بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="القاعة غير موجودة")
    except Exception as e:
        logger.error(f"Error deleting room: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف القاعة"
        )


# ============================================================
#  الفصول (الحصص) - Periods
# ============================================================

@router.get("/periods/list")
async def list_periods(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض قائمة الفصول"""
    service = AcademicService(db)
    periods = await service.periods.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/periods/list.html",
        {**ctx, "title": "الفصول (الحصص)", "items": periods, "type": "periods"}
    )


@router.get("/periods/create")
async def create_period_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    ctx: dict = Depends(template_context),
):
    """صفحة إضافة فصل"""
    return templates.TemplateResponse(
        "academics/periods/create.html",
        {**ctx, "title": "إضافة فصل (حصة)"}
    )


@router.get("/periods/{period_id}/update")
async def edit_period_page(
    request: Request,
    period_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل فصل"""
    service = AcademicService(db)
    period = await service.periods.get_by_id(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    return templates.TemplateResponse(
        "academics/periods/update.html",
        {**ctx, "title": "تعديل فصل (حصة)", "item": period}
    )


@router.post("/api/periods/create")
async def create_period_api(
    req: PeriodCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء فصل جديد"""
    service = AcademicService(db)
    try:
        result = await service.create_period(user.school_id, req)
        return {"success": True, "id": result.id, "message": "تم إضافة الفصل بنجاح"}
    except ConflictException as e:  # ✅ استخدام ConflictException
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating period: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة الفصل"
        )


@router.put("/api/periods/{period_id}")
async def update_period_api(
    period_id: str,
    req: PeriodUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث فصل"""
    service = AcademicService(db)
    try:
        await service.update_period(period_id, req)
        return {"success": True, "message": "تم تحديث الفصل بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    except Exception as e:
        logger.error(f"Error updating period: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث الفصل"
        )


@router.delete("/api/periods/{period_id}")
async def delete_period_api(
    period_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف فصل"""
    service = AcademicService(db)
    try:
        await service.delete_period(period_id)
        return {"success": True, "message": "تم حذف الفصل بنجاح"}
    except NotFoundException:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    except Exception as e:
        logger.error(f"Error deleting period: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف الفصل"
        )


# ============================================================
#  الشجرة الأكاديمية - Academic Tree
# ============================================================

@router.get("/tree")
async def academic_tree(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض الشجرة الأكاديمية مع دعم السنة الدراسية"""
    service = AcademicService(db)
    try:
        tree = await service.get_full_tree(user.school_id)
        
        # جلب السنوات للفلترة في الواجهة
        years = await service.years.list_by_school(user.school_id)
        
        return templates.TemplateResponse(
            "academics/tree.html",
            {
                **ctx,
                "title": "الشجرة الأكاديمية",
                "tree": tree,
                "years": years
            }
        )
    except Exception as e:
        logger.error(f"Error loading academic tree: {str(e)}")
        return templates.TemplateResponse(
            "academics/tree.html",
            {
                **ctx,
                "title": "الشجرة الأكاديمية",
                "tree": [],
                "years": [],
                "error": "حدث خطأ أثناء تحميل الشجرة الأكاديمية"
            }
        )


# ============================================================
#  API إضافية للتصفية حسب السنة
# ============================================================

@router.get("/api/grades/by-year/{year_id}")
async def get_grades_by_year(
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب الصفوف حسب السنة الدراسية"""
    service = AcademicService(db)
    
    try:
        # التحقق من وجود السنة
        year = await service.years.get_by_id(year_id)
        if not year:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="السنة الدراسية غير موجودة"
            )
        
        # جلب الصفوف
        grades = await service.grades.list_by_school_and_year(user.school_id, year_id)
        
        return {
            "success": True,
            "data": [
                {
                    "id": g.id,
                    "name": g.name,
                    "name_en": g.name_en,
                    "stage_id": g.stage_id,
                    "stage_name": g.stage.name if g.stage else None,
                    "order": g.order
                }
                for g in grades
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching grades by year: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب الصفوف"
        )


@router.get("/api/stages/by-year/{year_id}")
async def get_stages_by_year(
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب المراحل حسب السنة الدراسية"""
    service = AcademicService(db)
    
    try:
        # التحقق من وجود السنة
        year = await service.years.get_by_id(year_id)
        if not year:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="السنة الدراسية غير موجودة"
            )
        
        # جلب المراحل
        stages = await service.stages.list_by_school_and_year(user.school_id, year_id)
        
        return {
            "success": True,
            "data": [
                {
                    "id": s.id,
                    "name": s.name,
                    "name_en": s.name_en,
                    "order": s.order
                }
                for s in stages
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stages by year: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المراحل"
        )
