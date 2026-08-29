"""Grades web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.core.exceptions import NotFoundException
from app.services.grade_service import GradeService
from app.services.academic_service import AcademicService
from app.models.students import Student
from app.models.academics import Assessment
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


async def get_assessment_with_details(db: AsyncSession, assessment_id: str):
    """جلب تفاصيل التقييم مع معلومات إضافية"""
    service = GradeService(db)
    assessment = await service.assessments.get(assessment_id)
    if not assessment:
        return None
    
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
        "year_id": getattr(assessment, 'year_id', None),
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


# ============= الصفحة الرئيسية =============
@router.get("", name="grades.index")
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
    
    # ✅ بناء الاستعلام لجلب التقييمات
    query = select(Assessment).where(Assessment.school_id == user.school_id)
    
    if section_id:
        query = query.where(Assessment.section_id == section_id)
    
    if search:
        query = query.where(
            or_(
                Assessment.title.ilike(f"%{search}%"),
                Assessment.description.ilike(f"%{search}%")
            )
        )
    
    # ترتيب حسب التاريخ (الأحدث أولاً)
    query = query.order_by(Assessment.date.desc().nullslast(), Assessment.created_at.desc())
    
    # حساب العدد الإجمالي
    count_query = select(func.count()).select_from(Assessment).where(Assessment.school_id == user.school_id)
    if section_id:
        count_query = count_query.where(Assessment.section_id == section_id)
    if search:
        count_query = count_query.where(
            or_(
                Assessment.title.ilike(f"%{search}%"),
                Assessment.description.ilike(f"%{search}%")
            )
        )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # تطبيق الترحيل
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    assessments = result.scalars().all()
    
    # جلب الشعب والمواد
    sections = await get_sections(db, user.school_id)
    subjects = await get_subjects(db, user.school_id)
    
    # تنسيق البيانات للعرض في القالب
    formatted_assessments = []
    for a in assessments:
        # جلب اسم الشعبة والمادة
        section_name = None
        subject_name = None
        
        # محاولة جلب الأسماء من العلاقات
        if hasattr(a, 'section') and a.section:
            section_name = a.section.name
        elif hasattr(a, 'section_id'):
            # البحث عن الشعبة في قائمة sections
            for sec in sections:
                if sec.id == a.section_id:
                    section_name = sec.name
                    break
        
        if hasattr(a, 'subject') and a.subject:
            subject_name = a.subject.name
        elif hasattr(a, 'subject_id'):
            for sub in subjects:
                if sub.id == a.subject_id:
                    subject_name = sub.name
                    break
        
        formatted_assessments.append({
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "section_name": section_name or a.section_id,
            "subject_name": subject_name or a.subject_id,
            "assessment_type": a.assessment_type,
            "assessment_type_label": get_assessment_type_label(a.assessment_type),
            "max_score": float(a.max_score),
            "date": a.date,
            "created_at": a.created_at,
            "section_id": a.section_id,
            "subject_id": a.subject_id,
        })
    
    return templates.TemplateResponse(
        "grades/index.html",
        {
            **ctx,
            "title": "الدرجات",
            "assessments": formatted_assessments,
            "total": total,
            "page": page,
            "page_size": page_size,
            "search": search or "",
            "sections": sections,
            "subjects": subjects,
            "selected_section": section_id,
            "now": datetime.now(),
        },
    )


def get_assessment_type_label(assessment_type: str) -> str:
    """الحصول على التسمية العربية لنوع التقييم"""
    labels = {
        "exam": "اختبار",
        "quiz": "قصير",
        "assignment": "واجب",
        "homework": "تكليف",
        "activity": "نشاط",
        "participation": "مشاركة",
    }
    return labels.get(assessment_type, assessment_type)


@router.get("/list", name="grades.list")
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

@router.get("/create", name="grades.create")
async def create_assessment_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """عرض صفحة إنشاء تقييم جديد"""
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


@router.post("/create", name="grades.store")
async def store_assessment(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """معالجة إنشاء تقييم جديد (POST)"""
    service = GradeService(db)
    academic_service = AcademicService(db)
    
    form_data = await request.form()
    
    # جلب العام الدراسي الحالي
    try:
        current_year = await academic_service.get_current_year(user.school_id)
        year_id = current_year.id
    except NotFoundException:
        years = await academic_service.years.list_by_school(user.school_id)
        if years:
            year_id = years[0].id
        else:
            return RedirectResponse(
                url="/grades/create?error=يجب إنشاء عام دراسي أولاً",
                status_code=303
            )
    
    # تجميع بيانات التقييم
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
        "teacher_id": form_data.get("teacher_id") or None,
        "school_id": user.school_id,
        "year_id": year_id,
    }
    
    try:
        assessment = await service.assessments.create(**data)
        return RedirectResponse(
            url=f"/grades/{assessment.id}?success=created",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url="/grades/create?error=" + str(e),
            status_code=303
        )


@router.get("/{assessment_id}/update", name="grades.edit")
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


@router.post("/{assessment_id}/update", name="grades.update")
async def update_assessment(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    """معالجة تحديث التقييم (POST)"""
    service = GradeService(db)
    form_data = await request.form()
    
    existing = await service.assessments.get(assessment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
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


@router.get("/{assessment_id}", name="grades.show")
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
    
    service = GradeService(db)
    grades = await service.grades.list_by_assessment(assessment_id)
    
    # جلب أسماء الطلاب
    student_names = {}
    for g in grades:
        student = await service.students.get(g.student_id)
        if student:
            student_names[g.student_id] = student.name
    
    formatted_grades = []
    for g in grades:
        formatted_grades.append({
            "id": g.id,
            "student_id": g.student_id,
            "student_name": student_names.get(g.student_id, g.student_id),
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


@router.get("/{assessment_id}/grades", name="grades.entry")
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
    
    # ✅ استعلام مباشر باستخدام SQLAlchemy
    stmt = select(Student).where(
        Student.section_id == assessment.section_id,
        Student.school_id == user.school_id
    )
    result = await db.execute(stmt)
    students = result.scalars().all()
    
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
    
    # رسائل النجاح والخطأ
    success_message = None
    error_message = None
    warning_message = None
    
    if request.query_params.get('success') == 'grades_saved':
        count = request.query_params.get('count', '0')
        success_message = f"✅ تم حفظ {count} درجة بنجاح"
    elif request.query_params.get('error'):
        error_message = f"❌ حدث خطأ: {request.query_params.get('error')}"
    elif request.query_params.get('warning') == 'no_grades':
        warning_message = "⚠️ لم يتم إدخال أي درجات للحفظ"
    
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
            "success_message": success_message,
            "error_message": error_message,
            "warning_message": warning_message,
            "now": datetime.now(),
        }
    )


@router.post("/{assessment_id}/grades/save", name="grades.save_grades")
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
            score = float(value) if value and value.strip() else None
            
            if score is not None:
                note_key = f"note_{student_id}"
                note = form_data.get(note_key)
                records.append({
                    "student_id": student_id,
                    "score": score,
                    "note": note or "",
                })
    
    # حفظ الدرجات
    if records:
        try:
            batch_data = GradeRecordBatch(
                assessment_id=assessment_id,
                records=records
            )
            result = await service.batch_record(user.id, batch_data)
            
            # إعادة التوجيه مع رسالة نجاح
            return RedirectResponse(
                url=f"/grades/{assessment_id}/grades?success=grades_saved&count={result.get('recorded', 0)}",
                status_code=303
            )
        except Exception as e:
            # في حالة الخطأ، إعادة التوجيه مع رسالة خطأ
            return RedirectResponse(
                url=f"/grades/{assessment_id}/grades?error={str(e)}",
                status_code=303
            )
    
    # إذا لم توجد درجات للحفظ
    return RedirectResponse(
        url=f"/grades/{assessment_id}/grades?warning=no_grades",
        status_code=303
    )


@router.post("/{assessment_id}/delete", name="grades.delete")
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

@router.get("/students/{student_id}", name="grades.student")
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

@router.post("/api/assessments/create", name="grades.api.create")
async def create_assessment_api(
    req: AssessmentCreate,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: إنشاء تقييم جديد"""
    service = GradeService(db)
    academic_service = AcademicService(db)
    
    # جلب العام الدراسي الحالي
    try:
        current_year = await academic_service.get_current_year(user.school_id)
        year_id = current_year.id
    except NotFoundException:
        years = await academic_service.years.list_by_school(user.school_id)
        if not years:
            raise HTTPException(status_code=400, detail="لا يوجد عام دراسي")
        year_id = years[0].id
    
    # إضافة year_id و school_id إلى الطلب
    req_data = req.model_dump()
    req_data["year_id"] = year_id
    req_data["school_id"] = user.school_id
    
    assessment = await service.assessments.create(**req_data)
    return {
        "success": True,
        "id": assessment.id,
        "message": "تم إنشاء التقييم بنجاح"
    }


@router.put("/api/assessments/{assessment_id}", name="grades.api.update")
async def update_assessment_api(
    assessment_id: str,
    req: AssessmentUpdate,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: تحديث التقييم"""
    service = GradeService(db)
    assessment = await service.assessments.get(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    update_data = req.model_dump(exclude_unset=True)
    await service.assessments.update(assessment, **update_data)
    return {
        "success": True,
        "message": "تم تحديث التقييم بنجاح"
    }


@router.delete("/api/assessments/{assessment_id}", name="grades.api.delete")
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


@router.post("/api/grades/batch", name="grades.api.batch")
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


@router.post("/api/grades/single", name="grades.api.single")
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


@router.get("/api/assessments", name="grades.api.list")
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


@router.get("/api/assessments/{assessment_id}", name="grades.api.show")
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


@router.get("/api/assessments/{assessment_id}/grades", name="grades.api.grades")
async def get_assessment_grades_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب درجات التقييم"""
    service = GradeService(db)
    grades = await service.grades.list_by_assessment(assessment_id)
    return {"success": True, "items": grades}


@router.get("/api/students/{student_id}/grades", name="grades.api.student")
async def get_student_grades_api(
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: جلب درجات طالب"""
    service = GradeService(db)
    grades = await service.student_grades(student_id)
    return {"success": True, "items": grades}
