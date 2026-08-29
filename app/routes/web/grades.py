"""Grades web routes - Refactored with 3 templates only."""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.core.exceptions import NotFoundException
from app.services.grade_service import GradeService
from app.services.academic_service import AcademicService
from app.models.students import Student
from app.models.grades import Assessment
from app.schemas.grades import (
    AssessmentCreate, AssessmentUpdate, GradeRecordCreate, GradeRecordBatch
)

router = APIRouter(prefix="/grades", tags=["grades"])
templates = Jinja2Templates(directory="app/templates")


# ============= Helper Functions =============

def get_assessment_type_label(assessment_type: str) -> str:
    """Get Arabic label for assessment type."""
    labels = {
        "exam": "اختبار",
        "quiz": "قصير",
        "assignment": "واجب",
        "homework": "تكليف",
        "activity": "نشاط",
        "participation": "مشاركة",
    }
    return labels.get(assessment_type, assessment_type)


def get_message(request: Request) -> Dict[str, Optional[str]]:
    """Extract messages from query params."""
    messages = {}
    
    success = request.query_params.get('success')
    if success:
        success_messages = {
            'created': 'تم إنشاء التقييم بنجاح',
            'updated': 'تم تحديث التقييم بنجاح',
            'deleted': 'تم حذف التقييم بنجاح',
            'grades_saved': 'تم حفظ الدرجات بنجاح',
        }
        messages['success'] = success_messages.get(success)
    
    error = request.query_params.get('error')
    if error:
        messages['error'] = error
    
    warning = request.query_params.get('warning')
    if warning == 'no_grades':
        messages['warning'] = '⚠️ لم يتم إدخال أي درجات للحفظ'
    
    return messages


# ============= Data Fetching Helpers =============

class GradeDataHelper:
    """Helper class to fetch common data with caching."""
    
    def __init__(self, db: AsyncSession, school_id: str):
        self.db = db
        self.school_id = school_id
        self._sections = None
        self._subjects = None
        self._teachers = None
        self._current_year = None
        self._academic_service = None
    
    @property
    def academic_service(self):
        if not self._academic_service:
            self._academic_service = AcademicService(self.db)
        return self._academic_service
    
    async def get_sections(self):
        if self._sections is None:
            self._sections = await self.academic_service.sections.list_by_school(self.school_id)
        return self._sections
    
    async def get_subjects(self):
        if self._subjects is None:
            self._subjects = await self.academic_service.subjects.list_by_school(self.school_id)
        return self._subjects
    
    async def get_teachers(self):
        if self._teachers is None:
            self._teachers = []  # TODO: Replace with actual teacher service
        return self._teachers
    
    async def get_current_year(self):
        if self._current_year is None:
            try:
                self._current_year = await self.academic_service.get_current_year(self.school_id)
            except NotFoundException:
                years = await self.academic_service.years.list_by_school(self.school_id)
                self._current_year = years[0] if years else None
        return self._current_year


async def fetch_assessments(
    db: AsyncSession, 
    school_id: str, 
    section_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> tuple[List[Dict], int]:
    """Fetch assessments with filtering and pagination."""
    
    print("=" * 60, flush=True)
    print("🔍 fetch_assessments called", flush=True)
    print(f"   School ID: {school_id}", flush=True)
    print(f"   Section ID: {section_id}", flush=True)
    print(f"   Search: {search}", flush=True)
    print(f"   Page: {page}, Page Size: {page_size}", flush=True)
    print("=" * 60, flush=True)
    
    # استعلام مباشر للتحقق من وجود البيانات
    try:
        check_query = "SELECT COUNT(*) FROM assessments WHERE school_id = :school_id"
        check_result = await db.execute(text(check_query), {"school_id": school_id})
        total_count = check_result.scalar()
        print(f"📊 Total assessments in DB: {total_count}", flush=True)
        
        # جلب جميع التقييمات للتحقق
        all_query = "SELECT id, title, school_id FROM assessments WHERE school_id = :school_id LIMIT 10"
        all_result = await db.execute(text(all_query), {"school_id": school_id})
        all_rows = all_result.fetchall()
        for row in all_rows:
            print(f"   - ID: {row.id}, Title: {row.title}, School: {row.school_id}", flush=True)
    except Exception as e:
        print(f"❌ Error checking DB: {str(e)}", flush=True)
    
    # استعلام مبسط بدون JOIN
    query = """
        SELECT 
            a.id, 
            a.title, 
            a.description, 
            a.assessment_type, 
            a.max_score, 
            a.passing_score, 
            a.weight, 
            a.date,
            a.section_id, 
            a.subject_id, 
            a.teacher_id,
            a.school_id, 
            a.year_id, 
            a.created_at, 
            a.updated_at
        FROM assessments a
        WHERE a.school_id = :school_id
    """
    params = {"school_id": school_id}
    
    if section_id:
        query += " AND a.section_id = :section_id"
        params["section_id"] = section_id
    
    if search:
        query += " AND (a.title ILIKE :search OR a.description ILIKE :search)"
        params["search"] = f"%{search}%"
    
    print(f"📝 Query: {query}", flush=True)
    print(f"📝 Params: {params}", flush=True)
    
    try:
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) as subquery"
        count_result = await db.execute(text(count_query), params)
        total = count_result.scalar()
        print(f"📊 Total after filters: {total}", flush=True)
        
        # Get paginated results
        query += " ORDER BY a.created_at DESC"
        query += f" LIMIT {page_size} OFFSET {(page - 1) * page_size}"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        print(f"📊 Rows fetched: {len(rows)}", flush=True)
        
        assessments = []
        for row in rows:
            print(f"   Processing: {row.id} - {row.title}", flush=True)
            
            # جلب اسم الشعبة والمادة
            section_name = None
            subject_name = None
            
            if row.section_id:
                try:
                    sec_result = await db.execute(
                        text("SELECT name FROM sections WHERE id = :id"),
                        {"id": row.section_id}
                    )
                    sec_row = sec_result.fetchone()
                    if sec_row:
                        section_name = sec_row[0]
                        print(f"      Section: {section_name}", flush=True)
                except Exception as e:
                    print(f"      Error fetching section: {str(e)}", flush=True)
            
            if row.subject_id:
                try:
                    sub_result = await db.execute(
                        text("SELECT name FROM subjects WHERE id = :id"),
                        {"id": row.subject_id}
                    )
                    sub_row = sub_result.fetchone()
                    if sub_row:
                        subject_name = sub_row[0]
                        print(f"      Subject: {subject_name}", flush=True)
                except Exception as e:
                    print(f"      Error fetching subject: {str(e)}", flush=True)
            
            assessments.append({
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "assessment_type": row.assessment_type,
                "assessment_type_label": get_assessment_type_label(row.assessment_type),
                "max_score": float(row.max_score) if row.max_score else 0,
                "passing_score": float(row.passing_score) if row.passing_score else None,
                "weight": float(row.weight) if row.weight else 1.0,
                "date": row.date,
                "section_id": row.section_id,
                "section_name": section_name or '—',
                "subject_id": row.subject_id,
                "subject_name": subject_name or '—',
                "teacher_id": row.teacher_id,
                "school_id": row.school_id,
                "year_id": row.year_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        
        print(f"✅ Returning {len(assessments)} assessments", flush=True)
        print("=" * 60, flush=True)
        return assessments, total
        
    except Exception as e:
        print(f"❌ Error in fetch_assessments: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return [], 0


async def fetch_students_with_grades(
    db: AsyncSession, 
    assessment_id: str, 
    school_id: str
) -> List[Dict]:
    """Fetch students and their grades for an assessment."""
    service = GradeService(db)
    
    assessment = await service.assessments.get(assessment_id)
    if not assessment:
        return []
    
    # Fetch students
    stmt = select(Student).where(
        Student.section_id == assessment.section_id,
        Student.school_id == school_id
    )
    result = await db.execute(stmt)
    students = result.scalars().all()
    
    # Fetch grades
    grades = await service.grades.list_by_assessment(assessment_id)
    
    # Build grades map
    grades_map = {}
    for g in grades:
        grades_map[g.student_id] = {
            "score": float(g.score) if g.score is not None else None,
            "note": g.note,
            "grade_id": g.id,
        }
    
    return [
        {
            "id": student.id,
            "name": student.name,
            "grade": grades_map.get(student.id, {}).get("score"),
            "note": grades_map.get(student.id, {}).get("note"),
            "grade_id": grades_map.get(student.id, {}).get("grade_id"),
        }
        for student in students
    ]


async def get_assessment_with_details(db: AsyncSession, assessment_id: str) -> Optional[Dict]:
    """Fetch assessment with details."""
    service = GradeService(db)
    assessment = await service.assessments.get(assessment_id)
    
    if not assessment:
        return None
    
    # Fetch section and subject names
    section_name = None
    subject_name = None
    
    if assessment.section_id:
        result = await db.execute(
            text("SELECT name FROM sections WHERE id = :id"),
            {"id": assessment.section_id}
        )
        row = result.fetchone()
        if row:
            section_name = row[0]
    
    if assessment.subject_id:
        result = await db.execute(
            text("SELECT name FROM subjects WHERE id = :id"),
            {"id": assessment.subject_id}
        )
        row = result.fetchone()
        if row:
            subject_name = row[0]
    
    return {
        "id": assessment.id,
        "title": assessment.title,
        "description": getattr(assessment, 'description', None),
        "assessment_type": assessment.assessment_type,
        "assessment_type_label": get_assessment_type_label(assessment.assessment_type),
        "max_score": float(assessment.max_score),
        "passing_score": float(assessment.passing_score) if hasattr(assessment, 'passing_score') and assessment.passing_score else None,
        "weight": float(assessment.weight) if hasattr(assessment, 'weight') else 1.0,
        "date": assessment.date,
        "section_id": getattr(assessment, 'section_id', None),
        "section_name": section_name or '—',
        "subject_id": getattr(assessment, 'subject_id', None),
        "subject_name": subject_name or '—',
        "teacher_id": getattr(assessment, 'teacher_id', None),
        "school_id": assessment.school_id,
        "year_id": getattr(assessment, 'year_id', None),
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


# ============= Routes =============

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
    """Display main grades page (index)."""
    
    print("=" * 60, flush=True)
    print("🏠 grades_page called", flush=True)
    print(f"👤 User: {user.email}", flush=True)
    print(f"🏫 School ID: {user.school_id}", flush=True)
    print("=" * 60, flush=True)
    
    # التحقق المباشر من وجود تقييمات
    try:
        check_query = "SELECT COUNT(*) FROM assessments WHERE school_id = :school_id"
        check_result = await db.execute(text(check_query), {"school_id": user.school_id})
        count = check_result.scalar()
        print(f"📊 عدد التقييمات في قاعدة البيانات: {count}", flush=True)
        
        # جلب عينة من التقييمات
        sample_query = "SELECT id, title FROM assessments WHERE school_id = :school_id LIMIT 5"
        sample_result = await db.execute(text(sample_query), {"school_id": user.school_id})
        sample_rows = sample_result.fetchall()
        for row in sample_rows:
            print(f"   - {row.id}: {row.title}", flush=True)
    except Exception as e:
        print(f"❌ خطأ في التحقق: {str(e)}", flush=True)
    
    # جلب التقييمات
    assessments, total = await fetch_assessments(
        db, user.school_id, section_id, search, page, page_size
    )
    
    print(f"📊 عدد التقييمات المعروضة: {len(assessments)}", flush=True)
    print("=" * 60, flush=True)
    
    helper = GradeDataHelper(db, user.school_id)
    sections = await helper.get_sections()
    subjects = await helper.get_subjects()
    
    context = {
        **ctx,
        "title": "الدرجات",
        "assessments": assessments,
        "total": total,
        "page": page,
        "page_size": page_size,
        "search": search or "",
        "sections": sections,
        "subjects": subjects,
        "selected_section": section_id,
        "now": datetime.now(),
        **get_message(request),
    }
    
    return templates.TemplateResponse("grades/index.html", context)


@router.get("/create", name="grades.create")
async def create_assessment_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """Display create assessment page."""
    helper = GradeDataHelper(db, user.school_id)
    sections = await helper.get_sections()
    subjects = await helper.get_subjects()
    teachers = await helper.get_teachers()
    
    context = {
        **ctx,
        "title": "إنشاء تقييم جديد",
        "item": None,
        "sections": sections,
        "subjects": subjects,
        "teachers": teachers,
        "now": datetime.now(),
        **get_message(request),
    }
    
    return templates.TemplateResponse("grades/create.html", context)


@router.post("/create", name="grades.store")
async def store_assessment(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """Handle assessment creation (POST)."""
    service = GradeService(db)
    form_data = await request.form()
    
    helper = GradeDataHelper(db, user.school_id)
    current_year = await helper.get_current_year()
    
    if not current_year:
        return RedirectResponse(
            url="/grades/create?error=يجب إنشاء عام دراسي أولاً",
            status_code=303
        )
    
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
        "year_id": current_year.id,
    }
    
    print("=" * 60, flush=True)
    print("📝 إنشاء تقييم جديد:", flush=True)
    print(f"   Title: {data['title']}", flush=True)
    print(f"   School ID: {data['school_id']}", flush=True)
    print(f"   Year ID: {data['year_id']}", flush=True)
    print(f"   Section ID: {data['section_id']}", flush=True)
    print(f"   Subject ID: {data['subject_id']}", flush=True)
    print("=" * 60, flush=True)
    
    try:
        assessment = await service.assessments.create(**data)
        print(f"✅ تم إنشاء التقييم: {assessment.id}", flush=True)
        
        # التحقق من وجود التقييم في قاعدة البيانات
        verify_query = "SELECT id, title, school_id FROM assessments WHERE id = :id"
        verify_result = await db.execute(text(verify_query), {"id": assessment.id})
        verify_row = verify_result.fetchone()
        if verify_row:
            print(f"✅ التقييم موجود في قاعدة البيانات: {verify_row.id} - {verify_row.title} - School: {verify_row.school_id}", flush=True)
        else:
            print(f"❌ التقييم غير موجود في قاعدة البيانات!", flush=True)
        
        return RedirectResponse(
            url="/grades?success=created",
            status_code=303
        )
    except Exception as e:
        print(f"❌ خطأ في الإنشاء: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url=f"/grades/create?error={str(e)}",
            status_code=303
        )


@router.get("/{assessment_id}/update", name="grades.update_page")
async def update_assessment_page(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """Display update assessment page (includes details, update form, and grade entry)."""
    assessment = await get_assessment_with_details(db, assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    helper = GradeDataHelper(db, user.school_id)
    sections = await helper.get_sections()
    subjects = await helper.get_subjects()
    teachers = await helper.get_teachers()
    
    # Fetch students with grades for grade entry
    students_with_grades = await fetch_students_with_grades(db, assessment_id, user.school_id)
    
    context = {
        **ctx,
        "title": f"تعديل التقييم: {assessment['title']}",
        "item": assessment,
        "sections": sections,
        "subjects": subjects,
        "teachers": teachers,
        "students": students_with_grades,
        "now": datetime.now(),
        **get_message(request),
    }
    
    return templates.TemplateResponse("grades/update.html", context)


@router.post("/{assessment_id}/update", name="grades.update")
async def update_assessment(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    """Handle assessment update (POST)."""
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
        url="/grades?success=updated",
        status_code=303
    )


@router.post("/{assessment_id}/grades/save", name="grades.save_grades")
async def save_grades(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """Save grades for assessment (Batch)."""
    service = GradeService(db)
    form_data = await request.form()
    
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
    
    if records:
        try:
            batch_data = GradeRecordBatch(
                assessment_id=assessment_id,
                records=records
            )
            await service.batch_record(user.id, batch_data)
            
            return RedirectResponse(
                url="/grades?success=grades_saved",
                status_code=303
            )
        except Exception as e:
            return RedirectResponse(
                url=f"/grades/{assessment_id}/update?error={str(e)}",
                status_code=303
            )
    
    return RedirectResponse(
        url=f"/grades/{assessment_id}/update?warning=no_grades",
        status_code=303
    )


@router.post("/{assessment_id}/delete", name="grades.delete")
async def delete_assessment(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete assessment (POST)."""
    service = GradeService(db)
    
    assessment = await service.assessments.get(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    await service.assessments.delete(assessment)
    
    return RedirectResponse(
        url="/grades?success=deleted",
        status_code=303
    )


# ============= API Routes =============

@router.post("/api/assessments/create", name="grades.api.create")
async def create_assessment_api(
    req: AssessmentCreate,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: Create assessment."""
    service = GradeService(db)
    academic_service = AcademicService(db)
    
    try:
        current_year = await academic_service.get_current_year(user.school_id)
        year_id = current_year.id
    except NotFoundException:
        years = await academic_service.years.list_by_school(user.school_id)
        if not years:
            raise HTTPException(status_code=400, detail="لا يوجد عام دراسي")
        year_id = years[0].id
    
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
    """API: Update assessment."""
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
    """API: Delete assessment."""
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
    """API: Batch create grades."""
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
    """API: Create single grade."""
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
    """API: List assessments."""
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
    """API: Get assessment details."""
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
    """API: Get assessment grades."""
    service = GradeService(db)
    grades = await service.grades.list_by_assessment(assessment_id)
    return {"success": True, "items": grades}


@router.get("/api/students/{student_id}/grades", name="grades.api.student")
async def get_student_grades_api(
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: Get student grades."""
    service = GradeService(db)
    grades = await service.student_grades(student_id)
    return {"success": True, "items": grades}
