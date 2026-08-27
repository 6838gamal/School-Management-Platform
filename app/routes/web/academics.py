"""Academic structure web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.academic_service import AcademicService
from app.schemas.academics import (
    AcademicYearCreate, StageCreate, GradeCreate, SectionCreate,
    SubjectCreate, RoomCreate, PeriodCreate,
    AcademicYearUpdate, StageUpdate, GradeUpdate, 
    SectionUpdate, SubjectUpdate, RoomUpdate, PeriodUpdate
)

router = APIRouter(prefix="/academics", tags=["academics"])
templates = Jinja2Templates(directory="app/templates")


# ============= الصفحة الرئيسية =============
@router.get("")
async def academics_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    data = await service.get_onboarding_data(user.school_id)
    return templates.TemplateResponse(
        "academics/index.html",
        {**ctx, "title": "الهيكل الأكاديمي", "data": data},
    )


# ============= الأعوام الدراسية =============

@router.get("/years/list")
async def list_years(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
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
    return templates.TemplateResponse(
        "academics/years/create.html",
        {**ctx, "title": "إضافة عام دراسي"}
    )


@router.get("/years/{year_id}/edit")
async def edit_year_page(
    request: Request,
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    year = await service.years.get_by_id(year_id)
    if not year:
        raise HTTPException(status_code=404, detail="العام الدراسي غير موجود")
    return templates.TemplateResponse(
        "academics/years/edit.html",
        {**ctx, "title": "تعديل عام دراسي", "item": year}
    )


@router.post("/api/years/create")
async def create_year_api(
    req: AcademicYearCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.create_year(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة العام الدراسي بنجاح"}


@router.put("/api/years/{year_id}")
async def update_year_api(
    year_id: str,
    req: AcademicYearUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.update_year(year_id, req)
    return {"success": True, "message": "تم تحديث العام الدراسي بنجاح"}


@router.delete("/api/years/{year_id}")
async def delete_year_api(
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    await service.delete_year(year_id)
    return {"success": True, "message": "تم حذف العام الدراسي بنجاح"}


# ============= المراحل =============

@router.get("/stages/list")
async def list_stages(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
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
    service = AcademicService(db)
    years = await service.years.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/stages/create.html",
        {**ctx, "title": "إضافة مرحلة", "years": years}
    )


@router.get("/stages/{stage_id}/edit")
async def edit_stage_page(
    request: Request,
    stage_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    stage = await service.stages.get_by_id(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="المرحلة غير موجودة")
    years = await service.years.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/stages/edit.html",
        {**ctx, "title": "تعديل مرحلة", "item": stage, "years": years}
    )


@router.post("/api/stages/create")
async def create_stage_api(
    req: StageCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.create_stage(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة المرحلة بنجاح"}


@router.put("/api/stages/{stage_id}")
async def update_stage_api(
    stage_id: str,
    req: StageUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.update_stage(stage_id, req)
    return {"success": True, "message": "تم تحديث المرحلة بنجاح"}


@router.delete("/api/stages/{stage_id}")
async def delete_stage_api(
    stage_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    await service.delete_stage(stage_id)
    return {"success": True, "message": "تم حذف المرحلة بنجاح"}


# ============= الصفوف =============

@router.get("/grades/list")
async def list_grades(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    grades = await service.grades.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/grades/list.html",
        {**ctx, "title": "الصفوف", "items": grades, "type": "grades"}
    )


@router.get("/grades/create")
async def create_grade_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    stages = await service.stages.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/grades/create.html",
        {**ctx, "title": "إضافة صف", "stages": stages}
    )


@router.get("/grades/{grade_id}/edit")
async def edit_grade_page(
    request: Request,
    grade_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    grade = await service.grades.get_by_id(grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="الصف غير موجود")
    stages = await service.stages.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/grades/edit.html",
        {**ctx, "title": "تعديل صف", "item": grade, "stages": stages}
    )


@router.post("/api/grades/create")
async def create_grade_api(
    req: GradeCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.create_grade(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة الصف بنجاح"}


@router.put("/api/grades/{grade_id}")
async def update_grade_api(
    grade_id: str,
    req: GradeUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.update_grade(grade_id, req)
    return {"success": True, "message": "تم تحديث الصف بنجاح"}


@router.delete("/api/grades/{grade_id}")
async def delete_grade_api(
    grade_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    await service.delete_grade(grade_id)
    return {"success": True, "message": "تم حذف الصف بنجاح"}


# ============= الشعب =============

@router.get("/sections/list")
async def list_sections(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    sections = await service.sections.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/sections/list.html",
        {**ctx, "title": "الشعب", "items": sections, "type": "sections"}
    )


@router.get("/sections/create")
async def create_section_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    grades = await service.grades.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/sections/create.html",
        {**ctx, "title": "إضافة شعبة", "grades": grades}
    )


@router.get("/sections/{section_id}/edit")
async def edit_section_page(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    section = await service.sections.get_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="الشعبة غير موجودة")
    grades = await service.grades.list_by_school(user.school_id)
    return templates.TemplateResponse(
        "academics/sections/edit.html",
        {**ctx, "title": "تعديل شعبة", "item": section, "grades": grades}
    )


@router.post("/api/sections/create")
async def create_section_api(
    req: SectionCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.create_section(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة الشعبة بنجاح"}


@router.put("/api/sections/{section_id}")
async def update_section_api(
    section_id: str,
    req: SectionUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.update_section(section_id, req)
    return {"success": True, "message": "تم تحديث الشعبة بنجاح"}


@router.delete("/api/sections/{section_id}")
async def delete_section_api(
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    await service.delete_section(section_id)
    return {"success": True, "message": "تم حذف الشعبة بنجاح"}


# ============= المواد =============

@router.get("/subjects/list")
async def list_subjects(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
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
    return templates.TemplateResponse(
        "academics/subjects/create.html",
        {**ctx, "title": "إضافة مادة"}
    )


@router.get("/subjects/{subject_id}/edit")
async def edit_subject_page(
    request: Request,
    subject_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    subject = await service.subjects.get_by_id(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="المادة غير موجودة")
    return templates.TemplateResponse(
        "academics/subjects/edit.html",
        {**ctx, "title": "تعديل مادة", "item": subject}
    )


@router.post("/api/subjects/create")
async def create_subject_api(
    req: SubjectCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.create_subject(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة المادة بنجاح"}


@router.put("/api/subjects/{subject_id}")
async def update_subject_api(
    subject_id: str,
    req: SubjectUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.update_subject(subject_id, req)
    return {"success": True, "message": "تم تحديث المادة بنجاح"}


@router.delete("/api/subjects/{subject_id}")
async def delete_subject_api(
    subject_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    await service.delete_subject(subject_id)
    return {"success": True, "message": "تم حذف المادة بنجاح"}


# ============= القاعات =============

@router.get("/rooms/list")
async def list_rooms(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
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
    return templates.TemplateResponse(
        "academics/rooms/create.html",
        {**ctx, "title": "إضافة قاعة"}
    )


@router.get("/rooms/{room_id}/edit")
async def edit_room_page(
    request: Request,
    room_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    room = await service.rooms.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="القاعة غير موجودة")
    return templates.TemplateResponse(
        "academics/rooms/edit.html",
        {**ctx, "title": "تعديل قاعة", "item": room}
    )


@router.post("/api/rooms/create")
async def create_room_api(
    req: RoomCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.create_room(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة القاعة بنجاح"}


@router.put("/api/rooms/{room_id}")
async def update_room_api(
    room_id: str,
    req: RoomUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.update_room(room_id, req)
    return {"success": True, "message": "تم تحديث القاعة بنجاح"}


@router.delete("/api/rooms/{room_id}")
async def delete_room_api(
    room_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    await service.delete_room(room_id)
    return {"success": True, "message": "تم حذف القاعة بنجاح"}


# ============= الفصول (الحصص) =============

@router.get("/periods/list")
async def list_periods(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
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
    return templates.TemplateResponse(
        "academics/periods/create.html",
        {**ctx, "title": "إضافة فصل (حصة)"}
    )


@router.get("/periods/{period_id}/edit")
async def edit_period_page(
    request: Request,
    period_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    period = await service.periods.get_by_id(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    return templates.TemplateResponse(
        "academics/periods/edit.html",
        {**ctx, "title": "تعديل فصل (حصة)", "item": period}
    )


@router.post("/api/periods/create")
async def create_period_api(
    req: PeriodCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.create_period(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة الفصل بنجاح"}


@router.put("/api/periods/{period_id}")
async def update_period_api(
    period_id: str,
    req: PeriodUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    result = await service.update_period(period_id, req)
    return {"success": True, "message": "تم تحديث الفصل بنجاح"}


@router.delete("/api/periods/{period_id}")
async def delete_period_api(
    period_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    await service.delete_period(period_id)
    return {"success": True, "message": "تم حذف الفصل بنجاح"}


# ============= الشجرة الأكاديمية =============

@router.get("/tree")
async def academic_tree(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    tree = await service.get_full_tree(user.school_id)
    return templates.TemplateResponse(
        "academics/tree.html",
        {**ctx, "title": "الشجرة الأكاديمية", "tree": tree},
    )


# ============= الشجرة الأكاديمية =============
@router.get("/tree")
async def academic_tree(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = AcademicService(db)
    try:
        tree = await service.get_full_tree(user.school_id)
    except NotFoundException:
        tree = []
    return templates.TemplateResponse(
        "academics/tree.html",
        {**ctx, "title": "الشجرة الأكاديمية", "tree": tree}
                               )


# ============================================================
#  مسارات API المباشرة (للتوافق مع القوالب الحالية)
# ============================================================

@router.post("/api/years/create")
async def api_create_year(
    req: AcademicYearCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء عام دراسي جديد"""
    service = AcademicService(db)
    result = await service.create_year(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة العام الدراسي بنجاح"}


@router.post("/api/stages/create")
async def api_create_stage(
    req: StageCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء مرحلة جديدة"""
    service = AcademicService(db)
    result = await service.create_stage(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة المرحلة بنجاح"}


@router.post("/api/grades/create")
async def api_create_grade(
    req: GradeCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء صف جديد"""
    service = AcademicService(db)
    result = await service.create_grade(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة الصف بنجاح"}


@router.post("/api/sections/create")
async def api_create_section(
    req: SectionCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء شعبة جديدة"""
    service = AcademicService(db)
    result = await service.create_section(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة الشعبة بنجاح"}


@router.post("/api/subjects/create")
async def api_create_subject(
    req: SubjectCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء مادة جديدة"""
    service = AcademicService(db)
    result = await service.create_subject(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة المادة بنجاح"}


@router.post("/api/rooms/create")
async def api_create_room(
    req: RoomCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء قاعة جديدة"""
    service = AcademicService(db)
    result = await service.create_room(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة القاعة بنجاح"}


@router.post("/api/periods/create")
async def api_create_period(
    req: PeriodCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء فصل جديد"""
    service = AcademicService(db)
    result = await service.create_period(user.school_id, req)
    return {"success": True, "id": result.id, "message": "تم إضافة الفصل بنجاح"}


# ============================================================
#  مسارات API للحذف (DELETE)
# ============================================================

@router.delete("/api/years/{year_id}")
async def api_delete_year(
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف عام دراسي"""
    service = AcademicService(db)
    await service.delete_year(year_id)
    return {"success": True, "message": "تم حذف العام الدراسي بنجاح"}


@router.delete("/api/stages/{stage_id}")
async def api_delete_stage(
    stage_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف مرحلة"""
    service = AcademicService(db)
    await service.delete_stage(stage_id)
    return {"success": True, "message": "تم حذف المرحلة بنجاح"}


@router.delete("/api/grades/{grade_id}")
async def api_delete_grade(
    grade_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف صف"""
    service = AcademicService(db)
    await service.delete_grade(grade_id)
    return {"success": True, "message": "تم حذف الصف بنجاح"}


@router.delete("/api/sections/{section_id}")
async def api_delete_section(
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف شعبة"""
    service = AcademicService(db)
    await service.delete_section(section_id)
    return {"success": True, "message": "تم حذف الشعبة بنجاح"}


@router.delete("/api/subjects/{subject_id}")
async def api_delete_subject(
    subject_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف مادة"""
    service = AcademicService(db)
    await service.delete_subject(subject_id)
    return {"success": True, "message": "تم حذف المادة بنجاح"}


@router.delete("/api/rooms/{room_id}")
async def api_delete_room(
    room_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف قاعة"""
    service = AcademicService(db)
    await service.delete_room(room_id)
    return {"success": True, "message": "تم حذف القاعة بنجاح"}


@router.delete("/api/periods/{period_id}")
async def api_delete_period(
    period_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: حذف فصل"""
    service = AcademicService(db)
    await service.delete_period(period_id)
    return {"success": True, "message": "تم حذف الفصل بنجاح"}
