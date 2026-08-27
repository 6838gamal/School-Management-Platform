"""Academic structure API routes - Version 1."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission
from app.services.academic_service import AcademicService
from app.schemas.academics import (
    # Create Schemas
    AcademicYearCreate,
    StageCreate,
    GradeCreate,
    SectionCreate,
    SubjectCreate,
    RoomCreate,
    PeriodCreate,
    # Update Schemas
    AcademicYearUpdate,
    StageUpdate,
    GradeUpdate,
    SectionUpdate,
    SubjectUpdate,
    RoomUpdate,
    PeriodUpdate,
    # Out Schemas
    AcademicYearOut,
    StageOut,
    GradeOut,
    SectionOut,
    SubjectOut,
    RoomOut,
    PeriodOut,
)

router = APIRouter(prefix="/academics", tags=["academics"])


# ============================================================
#  الأعوام الدراسية (Academic Years)
# ============================================================

@router.post(
    "/years/create",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء عام دراسي جديد",
    description="إضافة عام دراسي جديد للمدرسة مع تحديد تاريخ البداية والنهاية"
)
async def create_year(
    req: AcademicYearCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء عام دراسي جديد.
    
    - **name**: اسم العام الدراسي (مثال: 2026-2027)
    - **start_date**: تاريخ البداية (مثال: 2026-09-01)
    - **end_date**: تاريخ النهاية (مثال: 2027-06-30)
    - **is_current**: تعيين كعام حالي (اختياري، افتراضي: True)
    """
    service = AcademicService(db)
    try:
        result = await service.create_year(user.school_id, req)
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة العام الدراسي بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "is_current": result.is_current
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/years/{year_id}",
    response_model=dict,
    summary="تحديث عام دراسي",
    description="تحديث بيانات عام دراسي موجود"
)
async def update_year(
    year_id: str,
    req: AcademicYearUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث عام دراسي موجود.
    
    - **year_id**: معرف العام الدراسي
    - **name**: اسم العام الدراسي (اختياري)
    - **start_date**: تاريخ البداية (اختياري)
    - **end_date**: تاريخ النهاية (اختياري)
    - **is_current**: تعيين كعام حالي (اختياري)
    - **is_active**: تفعيل/إلغاء تفعيل (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.update_year(year_id, req)
        return {
            "success": True,
            "message": "تم تحديث العام الدراسي بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "is_current": result.is_current,
                "is_active": result.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/years/{year_id}",
    response_model=dict,
    summary="حذف عام دراسي",
    description="حذف عام دراسي موجود مع جميع المراحل والصفوف المرتبطة به"
)
async def delete_year(
    year_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    حذف عام دراسي.
    
    - **year_id**: معرف العام الدراسي
    """
    service = AcademicService(db)
    try:
        await service.delete_year(year_id)
        return {
            "success": True,
            "message": "تم حذف العام الدراسي بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/years/list",
    response_model=dict,
    summary="قائمة الأعوام الدراسية",
    description="الحصول على قائمة جميع الأعوام الدراسية للمدرسة"
)
async def list_years(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على قائمة الأعوام الدراسية للمدرسة."""
    service = AcademicService(db)
    years = await service.years.list_by_school(user.school_id)
    return {
        "success": True,
        "data": [
            {
                "id": y.id,
                "name": y.name,
                "start_date": y.start_date,
                "end_date": y.end_date,
                "is_current": y.is_current,
                "is_active": y.is_active,
                "created_at": y.created_at.isoformat() if y.created_at else None
            }
            for y in years
        ],
        "count": len(years)
    }


@router.get(
    "/years/current",
    response_model=dict,
    summary="العام الدراسي الحالي",
    description="الحصول على العام الدراسي الحالي للمدرسة"
)
async def get_current_year(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على العام الدراسي الحالي."""
    service = AcademicService(db)
    year = await service.years.get_current(user.school_id)
    if not year:
        return {
            "success": False,
            "message": "لا يوجد عام دراسي حالي",
            "data": None
        }
    return {
        "success": True,
        "data": {
            "id": year.id,
            "name": year.name,
            "start_date": year.start_date,
            "end_date": year.end_date,
            "is_current": year.is_current,
            "is_active": year.is_active
        }
    }


# ============================================================
#  المراحل (Stages)
# ============================================================

@router.post(
    "/stages/create",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مرحلة جديدة",
    description="إضافة مرحلة جديدة للمدرسة"
)
async def create_stage(
    req: StageCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء مرحلة جديدة.
    
    - **year_id**: معرف العام الدراسي
    - **name**: اسم المرحلة (مثال: ابتدائي)
    - **name_en**: اسم المرحلة بالإنجليزية (اختياري)
    - **order**: ترتيب المرحلة (اختياري، افتراضي: 0)
    """
    service = AcademicService(db)
    try:
        result = await service.create_stage(user.school_id, req)
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة المرحلة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "order": result.order
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/stages/{stage_id}",
    response_model=dict,
    summary="تحديث مرحلة",
    description="تحديث بيانات مرحلة موجودة"
)
async def update_stage(
    stage_id: str,
    req: StageUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث مرحلة موجودة.
    
    - **stage_id**: معرف المرحلة
    - **year_id**: معرف العام الدراسي (اختياري)
    - **name**: اسم المرحلة (اختياري)
    - **name_en**: اسم المرحلة بالإنجليزية (اختياري)
    - **order**: ترتيب المرحلة (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.update_stage(stage_id, req)
        return {
            "success": True,
            "message": "تم تحديث المرحلة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "order": result.order
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/stages/{stage_id}",
    response_model=dict,
    summary="حذف مرحلة",
    description="حذف مرحلة موجودة مع جميع الصفوف المرتبطة بها"
)
async def delete_stage(
    stage_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف مرحلة."""
    service = AcademicService(db)
    try:
        await service.delete_stage(stage_id)
        return {
            "success": True,
            "message": "تم حذف المرحلة بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/stages/list",
    response_model=dict,
    summary="قائمة المراحل",
    description="الحصول على قائمة جميع المراحل للمدرسة"
)
async def list_stages(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على قائمة المراحل للمدرسة."""
    service = AcademicService(db)
    stages = await service.stages.list_by_school(user.school_id)
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "name_en": s.name_en,
                "order": s.order,
                "year_id": s.year_id
            }
            for s in stages
        ],
        "count": len(stages)
    }


# ============================================================
#  الصفوف (Grades)
# ============================================================

@router.post(
    "/grades/create",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء صف جديد",
    description="إضافة صف جديد للمدرسة"
)
async def create_grade(
    req: GradeCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء صف جديد.
    
    - **stage_id**: معرف المرحلة
    - **name**: اسم الصف (مثال: الصف الأول)
    - **name_en**: اسم الصف بالإنجليزية (اختياري)
    - **order**: ترتيب الصف (اختياري، افتراضي: 0)
    """
    service = AcademicService(db)
    try:
        result = await service.create_grade(user.school_id, req)
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة الصف بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "order": result.order
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/grades/{grade_id}",
    response_model=dict,
    summary="تحديث صف",
    description="تحديث بيانات صف موجود"
)
async def update_grade(
    grade_id: str,
    req: GradeUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث صف موجود.
    
    - **grade_id**: معرف الصف
    - **stage_id**: معرف المرحلة (اختياري)
    - **name**: اسم الصف (اختياري)
    - **name_en**: اسم الصف بالإنجليزية (اختياري)
    - **order**: ترتيب الصف (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.update_grade(grade_id, req)
        return {
            "success": True,
            "message": "تم تحديث الصف بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "order": result.order
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/grades/{grade_id}",
    response_model=dict,
    summary="حذف صف",
    description="حذف صف موجود مع جميع الشعب المرتبطة به"
)
async def delete_grade(
    grade_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف صف."""
    service = AcademicService(db)
    try:
        await service.delete_grade(grade_id)
        return {
            "success": True,
            "message": "تم حذف الصف بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/grades/list",
    response_model=dict,
    summary="قائمة الصفوف",
    description="الحصول على قائمة جميع الصفوف للمدرسة"
)
async def list_grades(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على قائمة الصفوف للمدرسة."""
    service = AcademicService(db)
    grades = await service.grades.list_by_school(user.school_id)
    return {
        "success": True,
        "data": [
            {
                "id": g.id,
                "name": g.name,
                "name_en": g.name_en,
                "order": g.order,
                "stage_id": g.stage_id
            }
            for g in grades
        ],
        "count": len(grades)
    }


# ============================================================
#  الشعب (Sections)
# ============================================================

@router.post(
    "/sections/create",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء شعبة جديدة",
    description="إضافة شعبة جديدة للمدرسة"
)
async def create_section(
    req: SectionCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء شعبة جديدة.
    
    - **grade_id**: معرف الصف
    - **name**: اسم الشعبة (مثال: 1-أ)
    - **capacity**: سعة الشعبة (اختياري، افتراضي: 30)
    """
    service = AcademicService(db)
    try:
        result = await service.create_section(user.school_id, req)
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة الشعبة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "capacity": result.capacity,
                "is_active": result.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/sections/{section_id}",
    response_model=dict,
    summary="تحديث شعبة",
    description="تحديث بيانات شعبة موجودة"
)
async def update_section(
    section_id: str,
    req: SectionUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث شعبة موجودة.
    
    - **section_id**: معرف الشعبة
    - **grade_id**: معرف الصف (اختياري)
    - **name**: اسم الشعبة (اختياري)
    - **capacity**: سعة الشعبة (اختياري)
    - **is_active**: تفعيل/إلغاء تفعيل (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.update_section(section_id, req)
        return {
            "success": True,
            "message": "تم تحديث الشعبة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "capacity": result.capacity,
                "is_active": result.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/sections/{section_id}",
    response_model=dict,
    summary="حذف شعبة",
    description="حذف شعبة موجودة"
)
async def delete_section(
    section_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف شعبة."""
    service = AcademicService(db)
    try:
        await service.delete_section(section_id)
        return {
            "success": True,
            "message": "تم حذف الشعبة بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/sections/list",
    response_model=dict,
    summary="قائمة الشعب",
    description="الحصول على قائمة جميع الشعب للمدرسة"
)
async def list_sections(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على قائمة الشعب للمدرسة."""
    service = AcademicService(db)
    sections = await service.sections.list_by_school(user.school_id)
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "capacity": s.capacity,
                "is_active": s.is_active,
                "grade_id": s.grade_id
            }
            for s in sections
        ],
        "count": len(sections)
    }


# ============================================================
#  المواد (Subjects)
# ============================================================

@router.post(
    "/subjects/create",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مادة جديدة",
    description="إضافة مادة جديدة للمدرسة"
)
async def create_subject(
    req: SubjectCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء مادة جديدة.
    
    - **name**: اسم المادة (مثال: رياضيات)
    - **name_en**: اسم المادة بالإنجليزية (اختياري)
    - **code**: كود المادة (اختياري)
    - **color**: لون المادة (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.create_subject(user.school_id, req)
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة المادة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "code": result.code,
                "color": result.color
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/subjects/{subject_id}",
    response_model=dict,
    summary="تحديث مادة",
    description="تحديث بيانات مادة موجودة"
)
async def update_subject(
    subject_id: str,
    req: SubjectUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث مادة موجودة.
    
    - **subject_id**: معرف المادة
    - **name**: اسم المادة (اختياري)
    - **name_en**: اسم المادة بالإنجليزية (اختياري)
    - **code**: كود المادة (اختياري)
    - **color**: لون المادة (اختياري)
    - **is_active**: تفعيل/إلغاء تفعيل (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.update_subject(subject_id, req)
        return {
            "success": True,
            "message": "تم تحديث المادة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "code": result.code,
                "color": result.color,
                "is_active": result.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/subjects/{subject_id}",
    response_model=dict,
    summary="حذف مادة",
    description="حذف مادة موجودة"
)
async def delete_subject(
    subject_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف مادة."""
    service = AcademicService(db)
    try:
        await service.delete_subject(subject_id)
        return {
            "success": True,
            "message": "تم حذف المادة بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/subjects/list",
    response_model=dict,
    summary="قائمة المواد",
    description="الحصول على قائمة جميع المواد للمدرسة"
)
async def list_subjects(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على قائمة المواد للمدرسة."""
    service = AcademicService(db)
    subjects = await service.subjects.list_by_school(user.school_id)
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "name_en": s.name_en,
                "code": s.code,
                "color": s.color,
                "is_active": s.is_active
            }
            for s in subjects
        ],
        "count": len(subjects)
    }


# ============================================================
#  القاعات (Rooms)
# ============================================================

@router.post(
    "/rooms/create",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء قاعة جديدة",
    description="إضافة قاعة جديدة للمدرسة"
)
async def create_room(
    req: RoomCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء قاعة جديدة.
    
    - **name**: اسم القاعة (مثال: قاعة 101)
    - **building**: المبنى (اختياري)
    - **floor**: الطابق (اختياري)
    - **capacity**: سعة القاعة (اختياري، افتراضي: 30)
    """
    service = AcademicService(db)
    try:
        result = await service.create_room(user.school_id, req)
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة القاعة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "building": result.building,
                "floor": result.floor,
                "capacity": result.capacity
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/rooms/{room_id}",
    response_model=dict,
    summary="تحديث قاعة",
    description="تحديث بيانات قاعة موجودة"
)
async def update_room(
    room_id: str,
    req: RoomUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث قاعة موجودة.
    
    - **room_id**: معرف القاعة
    - **name**: اسم القاعة (اختياري)
    - **building**: المبنى (اختياري)
    - **floor**: الطابق (اختياري)
    - **capacity**: سعة القاعة (اختياري)
    - **is_active**: تفعيل/إلغاء تفعيل (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.update_room(room_id, req)
        return {
            "success": True,
            "message": "تم تحديث القاعة بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "building": result.building,
                "floor": result.floor,
                "capacity": result.capacity,
                "is_active": result.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/rooms/{room_id}",
    response_model=dict,
    summary="حذف قاعة",
    description="حذف قاعة موجودة"
)
async def delete_room(
    room_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف قاعة."""
    service = AcademicService(db)
    try:
        await service.delete_room(room_id)
        return {
            "success": True,
            "message": "تم حذف القاعة بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/rooms/list",
    response_model=dict,
    summary="قائمة القاعات",
    description="الحصول على قائمة جميع القاعات للمدرسة"
)
async def list_rooms(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على قائمة القاعات للمدرسة."""
    service = AcademicService(db)
    rooms = await service.rooms.list_by_school(user.school_id)
    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "building": r.building,
                "floor": r.floor,
                "capacity": r.capacity,
                "is_active": r.is_active
            }
            for r in rooms
        ],
        "count": len(rooms)
    }


# ============================================================
#  الفصول (Periods)
# ============================================================

@router.post(
    "/periods/create",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء فصل جديد",
    description="إضافة فصل جديد للمدرسة"
)
async def create_period(
    req: PeriodCreate,
    user: CurrentUser = Depends(require_any_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء فصل جديد.
    
    - **name**: اسم الفصل (مثال: الفترة الأولى)
    - **order**: ترتيب الفصل
    - **start_time**: وقت البداية (مثال: 07:00)
    - **end_time**: وقت النهاية (مثال: 07:45)
    - **is_break**: فترة استراحة (اختياري، افتراضي: False)
    """
    service = AcademicService(db)
    try:
        result = await service.create_period(user.school_id, req)
        return {
            "success": True,
            "id": result.id,
            "message": "تم إضافة الفصل بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "order": result.order,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "is_break": result.is_break
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/periods/{period_id}",
    response_model=dict,
    summary="تحديث فصل",
    description="تحديث بيانات فصل موجود"
)
async def update_period(
    period_id: str,
    req: PeriodUpdate,
    user: CurrentUser = Depends(require_any_permission("academics.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث فصل موجود.
    
    - **period_id**: معرف الفصل
    - **name**: اسم الفصل (اختياري)
    - **order**: ترتيب الفصل (اختياري)
    - **start_time**: وقت البداية (اختياري)
    - **end_time**: وقت النهاية (اختياري)
    - **is_break**: فترة استراحة (اختياري)
    """
    service = AcademicService(db)
    try:
        result = await service.update_period(period_id, req)
        return {
            "success": True,
            "message": "تم تحديث الفصل بنجاح",
            "data": {
                "id": result.id,
                "name": result.name,
                "order": result.order,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "is_break": result.is_break
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/periods/{period_id}",
    response_model=dict,
    summary="حذف فصل",
    description="حذف فصل موجود"
)
async def delete_period(
    period_id: str,
    user: CurrentUser = Depends(require_any_permission("academics.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف فصل."""
    service = AcademicService(db)
    try:
        await service.delete_period(period_id)
        return {
            "success": True,
            "message": "تم حذف الفصل بنجاح"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/periods/list",
    response_model=dict,
    summary="قائمة الفصول",
    description="الحصول على قائمة جميع الفصول للمدرسة"
)
async def list_periods(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على قائمة الفصول للمدرسة."""
    service = AcademicService(db)
    periods = await service.periods.list_by_school(user.school_id)
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "order": p.order,
                "start_time": p.start_time,
                "end_time": p.end_time,
                "is_break": p.is_break
            }
            for p in periods
        ],
        "count": len(periods)
    }


# ============================================================
#  إحصائيات سريعة
# ============================================================

@router.get(
    "/stats",
    response_model=dict,
    summary="إحصائيات الهيكل الأكاديمي",
    description="الحصول على إحصائيات سريعة للهيكل الأكاديمي للمدرسة"
)
async def get_academics_stats(
    user: CurrentUser = Depends(require_any_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    """الحصول على إحصائيات سريعة للهيكل الأكاديمي."""
    service = AcademicService(db)
    
    years = await service.years.list_by_school(user.school_id)
    stages = await service.stages.list_by_school(user.school_id)
    grades = await service.grades.list_by_school(user.school_id)
    sections = await service.sections.list_by_school(user.school_id)
    subjects = await service.subjects.list_by_school(user.school_id)
    rooms = await service.rooms.list_by_school(user.school_id)
    periods = await service.periods.list_by_school(user.school_id)
    
    # عدد العناصر النشطة
    active_years = len([y for y in years if y.is_active])
    active_sections = len([s for s in sections if s.is_active])
    active_subjects = len([s for s in subjects if s.is_active])
    active_rooms = len([r for r in rooms if r.is_active])
    
    return {
        "success": True,
        "data": {
            "years": {
                "total": len(years),
                "active": active_years,
                "current": len([y for y in years if y.is_current])
            },
            "stages": {
                "total": len(stages)
            },
            "grades": {
                "total": len(grades)
            },
            "sections": {
                "total": len(sections),
                "active": active_sections,
                "total_capacity": sum([s.capacity for s in sections])
            },
            "subjects": {
                "total": len(subjects),
                "active": active_subjects
            },
            "rooms": {
                "total": len(rooms),
                "active": active_rooms,
                "total_capacity": sum([r.capacity for r in rooms])
            },
            "periods": {
                "total": len(periods),
                "breaks": len([p for p in periods if p.is_break])
            },
            "total_elements": len(years) + len(stages) + len(grades) + len(sections) + len(subjects) + len(rooms) + len(periods)
        }
    }


# ============================================================
#  تصدير جميع المسارات
# ============================================================

__all__ = ["router"]
