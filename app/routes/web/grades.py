"""Grades web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.core.exceptions import NotFoundException
from app.services.grade_service import GradeService
from app.services.academic_service import AcademicService
from app.schemas.grades import (
    AssessmentCreate, AssessmentUpdate, GradeRecordCreate, GradeRecordBatch
)

router = APIRouter(prefix="/grades", tags=["grades"])
templates = Jinja2Templates(directory="app/templates")


# ============= دوال مساعدة =============

async def get_sections(db: AsyncSession, school_id: str):
    """جلب الشعب من AcademicService"""
    service = AcademicService(db)
    return await service.sections.list_by_school(school_id)


async def get_subjects(db: AsyncSession, school_id: str):
    """جلب المواد من AcademicService"""
    service = AcademicService(db)
    return await service.subjects.list_by_school(school_id)


async def get_teachers(db: AsyncSession, school_id: str):
    """جلب المعلمين (مؤقت - استبدل بخدمة المعلمين عند توفرها)"""
    # TODO: استبدل بخدمة المعلمين
    return []


async def get_students_by_section(db: AsyncSession, section_id: str):
    """جلب طلاب الشعبة"""
    service = GradeService(db)
    students = await service.students.list_by_section(section_id)
    return students


async def get_assessment_with_details(db: AsyncSession, assessment_id: str):
    """جلب تفاصيل التقييم مع معلومات إضافية"""
    service = GradeService(db)
    assessment = await service.assessments.get(assessment_id)
    if not assessment:
        return None
    
    # إضافة معلومات إضافية
    return {
        "id": assessment.id,
        "title": assessment.title,
        "description": getattr(assessment, 'description', None),
        "section_id": assessment.section_id,
        "subject_id": assessment.subject_id,
        "assessment_type": assessment.assessment_type,
        "max_score": float(assessment.max_score),
        "passing_score": float(assessment.passing_score) if hasattr(assessment, 'passing_score') else None,
        "weight": float(assessment.weight) if hasattr(assessment, 'weight') else 1.0,
        "date": assessment.date,
        "teacher_id": getattr(assessment, 'teacher_id', None),
        "school_id": assessment.school_id,
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


# ============= الصفحة الرئيسية =============
@router.get("")
async def grades_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    section_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    """عرض صفحة الدرجات الرئيسية"""
    service = GradeService(db)
    
    # جلب التقييمات (حسب الشعبة إذا تم تحديدها)
    if section_id:
        assessments = await service.list_assessments(section_id)
    else:
        # جلب جميع التقييمات للمدرسة
        # ملاحظة: الخدمة الحالية لا تدعم جلب كل التقييمات،
        # سنستخدم حل مؤقت أو نضيف دالة جديدة
        assessments = []
        # TODO: إضافة دالة list_all_assessments في الخدمة
    
    # جلب البيانات للفلاتر من AcademicService
    sections = await get_sections(db, user.school_id)
    subjects = await get_subjects(db, user.school_id)
    
    # تحويل البيانات للتنسيق المطلوب في القالب
    formatted_assessments = []
    for a in assessments:
        formatted_assessments.append({
            "id": a.get("id") if isinstance(a, dict) else getattr(a, 'id', None),
            "title": a.get("title") if isinstance(a, dict) else getattr(a, 'title', None),
            "section_name": a.get("section_name") if isinstance(a, dict) else None,
            "subject_name": a.get("subject_name") if isinstance(a, dict) else None,
            "assessment_type": a.get("type") if isinstance(a, dict) else getattr(a, 'assessment_type', None),
            "max_score": a.get("max_score") if isinstance(a, dict) else getattr(a, 'max_score', None),
            "date": a.get("date") if isinstance(a, dict) else getattr(a, 'date', None),
        })
    
    return templates.TemplateResponse(
        "grades/index.html",
        {
            **ctx,
            "title": "الدرجات",
            "assessments": formatted_assessments,
            "total": len(formatted_assessments),
            "page": page,
            "page_size": page_size,
            "search": search or "",
            "sections": sections,
            "subjects": subjects,
            "selected_section": section_id,
            "now": datetime.now(),
        },
    )


@router.get("/list")
async def list_assessments(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    section_id: Optional[str] = None,
):
    """عرض قائمة التقييمات (للـ AJAX)"""
    service = GradeService(db)
    
    if section_id:
        assessments = await service.list_assessments(section_id)
    else:
        assessments = []
    
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


@router.post("/create")
async def store_assessment(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """معالجة إنشاء تقييم جديد (POST)"""
    service = GradeService(db)
    form_data = await request.form()
    
    # تحويل البيانات من النموذج
    data = {
        "title": form_data.get("title"),
        "section_id": form_data.get("section_id"),
        "subject_id": form_data.get("subject_id"),
        "assessment_type": form_data.get("assessment_type"),
        "date": form_data.get("date"),
        "max_score": float(form_data.get("max_score", 100)),
        "passing_score": float(form_data.get("passing_score", 50)),
        "weight": float(form_data.get("weight", 1.0)),
        "description": form_data.get("description"),
        "teacher_id": form_data.get("teacher_id"),
        "school_id": user.school_id,
    }
    
    try:
        assessment = await service.assessments.create(**data)
        return RedirectResponse(
            url=f"/grades/{assessment.id}?success=created",
            status_code=303
        )
    except Exception as e:
        # عرض رسالة خطأ
        return RedirectResponse(
            url="/grades/create?error=" + str(e),
            status_code=303
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
    assessment = await get_assessment_with_details(db, assessment_id)
    
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


@router.post("/{assessment_id}/update")
async def update_assessment(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    """معالجة تحديث التقييم (POST)"""
    service = GradeService(db)
    form_data = await request.form()
    
    # التحقق من وجود التقييم
    existing = await service.assessments.get(assessment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # تحديث البيانات
    update_data = {}
    for key in ["title", "section_id", "subject_id", "assessment_type", "date", "description", "teacher_id"]:
        value = form_data.get(key)
        if value:
            update_data[key] = value
    
    if form_data.get("max_score"):
        update_data["max_score"] = float(form_data.get("max_score"))
    if form_data.get("passing_score"):
        update_data["passing_score"] = float(form_data.get("passing_score"))
    if form_data.get("weight"):
        update_data["weight"] = float(form_data.get("weight"))
    
    await service.assessments.update(existing, **update_data)
    
    return RedirectResponse(
        url=f"/grades/{assessment_id}?success=updated",
        status_code=303
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
    assessment = await get_assessment_with_details(db, assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # جلب درجات الطلاب لهذا التقييم
    service = GradeService(db)
    grades = await service.grades.list_by_assessment(assessment_id)
    
    # تنسيق الدرجات للعرض
    formatted_grades = []
    for g in grades:
        formatted_grades.append({
            "id": g.id,
            "student_id": g.student_id,
            "score": float(g.score) if g.score is not None else None,
            "note": g.note,
            "graded_by": g.graded_by,
            "created_at": g.created_at,
            "updated_at": g.updated_at,
        })
    
    return templates.TemplateResponse(
        "grades/show.html",
        {
            **ctx,
            "title": f"تفاصيل التقييم: {assessment['title']}",
            "item": assessment,
            "grades": formatted_grades,
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
    assessment = await service.assessments.get(assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # جلب الطلاب في الشعبة
    students = await service.students.list_by_section(assessment.section_id)
    
    # جلب الدرجات المسجلة
    grades = await service.grades.list_by_assessment(assessment_id)
    
    # إنشاء قاموس للدرجات المسجلة
    grades_map = {}
    for g in grades:
        grades_map[g.student_id] = {
            "score": float(g.score) if g.score is not None else None,
            "note": g.note,
            "grade_id": g.id,
        }
    
    # تجهيز بيانات الطلاب مع الدرجات
    students_with_grades = []
    for student in students:
        students_with_grades.append({
            "id": student.id,
            "name": student.name,
            "grade": grades_map.get(student.id, {}).get("score"),
            "note": grades_map.get(student.id, {}).get("note"),
            "grade_id": grades_map.get(student.id, {}).get("grade_id"),
        })
    
    return templates.TemplateResponse(
        "grades/entry.html",
        {
            **ctx,
            "title": f"إدخال درجات: {assessment.title}",
            "assessment": {
                "id": assessment.id,
                "title": assessment.title,
                "max_score": float(assessment.max_score),
                "passing_score": float(assessment.passing_score) if hasattr(assessment, 'passing_score') else None,
                "weight": float(assessment.weight) if hasattr(assessment, 'weight') else 1.0,
            },
            "students": students_with_grades,
            "now": datetime.now(),
        }
    )


@router.post("/{assessment_id}/grades/save")
async def save_grades(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """حفظ درجات التقييم (Batch)"""
    service = GradeService(db)
    form_data = await request.form()
    
    # تجميع الدرجات من النموذج
    records = []
    for key, value in form_data.items():
        if key.startswith("score_"):
            student_id = key.replace("score_", "")
            score = float(value) if value else None
            
            if score is not None:
                note_key = f"note_{student_id}"
                note = form_data.get(note_key)
                records.append({
                    "student_id": student_id,
                    "score": score,
                    "note": note,
                })
    
    if records:
        batch_data = GradeRecordBatch(
            assessment_id=assessment_id,
            records=records
        )
        result = await service.batch_record(user.id, batch_data)
    
    return RedirectResponse(
        url=f"/grades/{assessment_id}?success=grades_saved",
        status_code=303
    )


@router.post("/{assessment_id}/delete")
async def delete_assessment(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف التقييم (POST)"""
    service = GradeService(db)
    
    assessment = await service.assessments.get(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    await service.assessments.delete(assessment)
    
    return RedirectResponse(
        url="/grades?success=deleted",
        status_code=303
    )


# ============= الطلاب والدرجات =============

@router.get("/students/{student_id}")
async def student_grades(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض درجات طالب معين"""
    service = GradeService(db)
    grades = await service.student_grades(student_id)
    
    # جلب معلومات الطالب
    student = await service.students.get(student_id)
    
    # حساب الإحصائيات
    total_weighted = 0
    total_weight = 0
    for g in grades:
        if g["score"] is not None:
            total_weighted += g["score"] * g["weight"]
            total_weight += g["weight"]
    
    average = total_weighted / total_weight if total_weight > 0 else 0
    
    return templates.TemplateResponse(
        "grades/student_grades.html",
        {
            **ctx,
            "title": f"درجات الطالب: {student.name if student else student_id}",
            "student": student,
            "grades": grades,
            "average": round(average, 2),
            "total_weighted": round(total_weighted, 2),
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
    result = await service.create_assessment(user.school_id, req)
    return {
        "success": True,
        "id": result["id"],
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
    assessment = await service.assessments.get(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    await service.assessments.delete(assessment)
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
    result = await service.batch_record(user.id, req)
    return {
        "success": True,
        "count": result["recorded"],
        "message": f"تم إدخال {result['recorded']} درجة بنجاح"
    }


@router.post("/api/grades/single")
async def create_grade_api(
    req: GradeRecordCreate,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إدخال درجة واحدة"""
    service = GradeService(db)
    result = await service.record_grade(user.id, req)
    return {
        "success": True,
        "id": result["id"],
        "message": "تم إدخال الدرجة بنجاح"
    }


@router.get("/api/assessments")
async def get_assessments_api(
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    section_id: Optional[str] = None,
):
    """API: جلب قائمة التقييمات"""
    service = GradeService(db)
    if section_id:
        assessments = await service.list_assessments(section_id)
    else:
        assessments = []
    return {
        "success": True,
        "items": assessments,
        "total": len(assessments),
    }


@router.get("/api/assessments/{assessment_id}")
async def get_assessment_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب تفاصيل تقييم"""
    assessment = await get_assessment_with_details(db, assessment_id)
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
    grades = await service.grades.list_by_assessment(assessment_id)
    return {"success": True, "items": grades}


@router.get("/api/students/{student_id}/grades")
async def get_student_grades_api(
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب درجات طالب"""
    service = GradeService(db)
    grades = await service.student_grades(student_id)
    return {"success": True, "items": grades}
