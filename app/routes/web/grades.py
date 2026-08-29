"""Grades web routes - Refactored with reduced duplication."""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

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


# ============= Data Transfer Objects =============

@dataclass
class AssessmentDisplay:
    """DTO for assessment display in templates."""
    id: str
    title: str
    description: Optional[str]
    assessment_type: str
    assessment_type_label: str
    max_score: float
    passing_score: Optional[float]
    weight: float
    date: Any
    section_id: Optional[str]
    section_name: str
    subject_id: Optional[str]
    subject_name: str
    teacher_id: Optional[str]
    school_id: str
    year_id: Optional[str]
    created_at: Any
    updated_at: Any

    @classmethod
    def from_assessment(cls, assessment: Any, section_name: str = None, subject_name: str = None) -> "AssessmentDisplay":
        """Create AssessmentDisplay from assessment object."""
        return cls(
            id=assessment.id,
            title=assessment.title,
            description=getattr(assessment, 'description', None),
            assessment_type=assessment.assessment_type,
            assessment_type_label=get_assessment_type_label(assessment.assessment_type),
            max_score=float(assessment.max_score),
            passing_score=float(assessment.passing_score) if hasattr(assessment, 'passing_score') and assessment.passing_score else None,
            weight=float(assessment.weight) if hasattr(assessment, 'weight') else 1.0,
            date=assessment.date,
            section_id=getattr(assessment, 'section_id', None),
            section_name=section_name or getattr(assessment, 'section_name', None) or '—',
            subject_id=getattr(assessment, 'subject_id', None),
            subject_name=subject_name or getattr(assessment, 'subject_name', None) or '—',
            teacher_id=getattr(assessment, 'teacher_id', None),
            school_id=assessment.school_id,
            year_id=getattr(assessment, 'year_id', None),
            created_at=assessment.created_at,
            updated_at=assessment.updated_at
        )


@dataclass
class GradeDisplay:
    """DTO for grade display in templates."""
    id: str
    student_id: str
    student_name: str
    score: Optional[float]
    note: Optional[str]
    graded_by: Optional[str]
    created_at: Any
    updated_at: Any

    @classmethod
    def from_grade(cls, grade: Any, student_name: str = None) -> "GradeDisplay":
        """Create GradeDisplay from grade object."""
        return cls(
            id=grade.id,
            student_id=grade.student_id,
            student_name=student_name or grade.student_id,
            score=float(grade.score) if grade.score is not None else None,
            note=grade.note,
            graded_by=grade.graded_by,
            created_at=grade.created_at,
            updated_at=grade.updated_at
        )


@dataclass
class StudentGradeDisplay:
    """DTO for student grade display."""
    id: str
    name: str
    grade: Optional[float]
    note: Optional[str]
    grade_id: Optional[str]

    @classmethod
    def from_student(cls, student: Any, grade_data: Dict = None) -> "StudentGradeDisplay":
        """Create StudentGradeDisplay from student and optional grade data."""
        grade_data = grade_data or {}
        return cls(
            id=student.id,
            name=student.name,
            grade=grade_data.get("score"),
            note=grade_data.get("note"),
            grade_id=grade_data.get("grade_id")
        )


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


def get_success_message(request: Request, default: str = None) -> Optional[str]:
    """Extract success message from query params."""
    param = request.query_params.get('success')
    if not param:
        return None
    
    messages = {
        'created': '✅ تم إنشاء التقييم بنجاح',
        'updated': '✅ تم تحديث التقييم بنجاح',
        'deleted': '✅ تم حذف التقييم بنجاح',
        'grades_saved': f"✅ تم حفظ الدرجات بنجاح",
    }
    return messages.get(param, default)


def get_error_message(request: Request) -> Optional[str]:
    """Extract error message from query params."""
    error = request.query_params.get('error')
    return f"❌ {error}" if error else None


def get_warning_message(request: Request) -> Optional[str]:
    """Extract warning message from query params."""
    warning = request.query_params.get('warning')
    if warning == 'no_grades':
        return "⚠️ لم يتم إدخال أي درجات للحفظ"
    return None


# ============= Data Fetching Helpers =============

class GradeDataHelper:
    """Helper class to fetch common data with caching per request."""
    
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
        """Get sections with caching."""
        if self._sections is None:
            self._sections = await self.academic_service.sections.list_by_school(self.school_id)
        return self._sections
    
    async def get_subjects(self):
        """Get subjects with caching."""
        if self._subjects is None:
            self._subjects = await self.academic_service.subjects.list_by_school(self.school_id)
        return self._subjects
    
    async def get_teachers(self):
        """Get teachers (placeholder)."""
        if self._teachers is None:
            # TODO: Replace with actual teacher service
            self._teachers = []
        return self._teachers
    
    async def get_current_year(self):
        """Get current academic year with caching."""
        if self._current_year is None:
            try:
                self._current_year = await self.academic_service.get_current_year(self.school_id)
            except NotFoundException:
                years = await self.academic_service.years.list_by_school(self.school_id)
                self._current_year = years[0] if years else None
        return self._current_year


async def get_assessment_with_details(db: AsyncSession, assessment_id: str, school_id: str = None) -> Optional[AssessmentDisplay]:
    """Fetch assessment with details using optimized query."""
    service = GradeService(db)
    assessment = await service.assessments.get(assessment_id)
    
    if not assessment:
        return None
    
    # Fetch section and subject names in single query
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
    
    return AssessmentDisplay.from_assessment(assessment, section_name, subject_name)


async def fetch_assessments(
    db: AsyncSession, 
    school_id: str, 
    section_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> tuple[List[AssessmentDisplay], int]:
    """Fetch assessments with filtering and pagination."""
    # Build query
    query = """
        SELECT 
            a.id, a.title, a.description, a.assessment_type, 
            a.max_score, a.passing_score, a.weight, a.date,
            a.section_id, a.subject_id, a.teacher_id,
            a.school_id, a.year_id, a.created_at, a.updated_at,
            s.name as section_name,
            sub.name as subject_name
        FROM assessments a
        LEFT JOIN sections s ON s.id = a.section_id
        LEFT JOIN subjects sub ON sub.id = a.subject_id
        WHERE a.school_id = :school_id
    """
    params = {"school_id": school_id}
    
    if section_id:
        query += " AND a.section_id = :section_id"
        params["section_id"] = section_id
    
    if search:
        query += " AND (a.title ILIKE :search OR a.description ILIKE :search)"
        params["search"] = f"%{search}%"
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM ({query}) as subquery"
    count_result = await db.execute(text(count_query), params)
    total = count_result.scalar()
    
    # Get paginated results
    query += " ORDER BY a.created_at DESC"
    query += f" LIMIT {page_size} OFFSET {(page - 1) * page_size}"
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    assessments = []
    for row in rows:
        # Create a simple object to pass to AssessmentDisplay
        class AssessmentObj:
            pass
        
        assessment = AssessmentObj()
        for key in ['id', 'title', 'description', 'assessment_type', 'max_score', 
                   'passing_score', 'weight', 'date', 'section_id', 'subject_id',
                   'teacher_id', 'school_id', 'year_id', 'created_at', 'updated_at']:
            setattr(assessment, key, getattr(row, key, None))
        setattr(assessment, 'section_name', getattr(row, 'section_name', None))
        setattr(assessment, 'subject_name', getattr(row, 'subject_name', None))
        
        assessments.append(AssessmentDisplay.from_assessment(assessment))
    
    return assessments, total


async def fetch_students_with_grades(
    db: AsyncSession, 
    assessment_id: str, 
    school_id: str
) -> List[StudentGradeDisplay]:
    """Fetch students and their grades for an assessment."""
    service = GradeService(db)
    
    # Get assessment first
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
    
    # Build student displays
    return [StudentGradeDisplay.from_student(student, grades_map.get(student.id)) for student in students]


# ============= Context Builder =============

class GradePageContext:
    """Helper to build context for grade pages."""
    
    def __init__(self, request: Request, ctx: dict):
        self.request = request
        self.base_ctx = ctx
        self._messages = None
    
    @property
    def messages(self):
        if self._messages is None:
            self._messages = {
                'success': get_success_message(self.request),
                'error': get_error_message(self.request),
                'warning': get_warning_message(self.request)
            }
        return self._messages
    
    def build(self, **kwargs) -> dict:
        """Build complete context with base, messages, and additional data."""
        context = {
            **self.base_ctx,
            **self.messages,
            'now': datetime.now(),
            **kwargs
        }
        # Remove None values for messages
        for key in ['success', 'error', 'warning']:
            if context.get(key) is None:
                del context[key]
        return context


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
    """Display main grades page."""
    # Fetch assessments
    assessments, total = await fetch_assessments(
        db, user.school_id, section_id, search, page, page_size
    )
    
    # Fetch sections and subjects for filters
    helper = GradeDataHelper(db, user.school_id)
    sections = await helper.get_sections()
    subjects = await helper.get_subjects()
    
    # Build context
    page_ctx = GradePageContext(request, ctx)
    context = page_ctx.build(
        title="الدرجات",
        assessments=assessments,
        total=total,
        page=page,
        page_size=page_size,
        search=search or "",
        sections=sections,
        subjects=subjects,
        selected_section=section_id,
    )
    
    return templates.TemplateResponse("grades/index.html", context)


@router.get("/list", name="grades.list")
async def list_assessments(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    section_id: Optional[str] = None,
):
    """Display assessments list (for AJAX)."""
    service = GradeService(db)
    
    if section_id:
        assessments = await service.list_assessments(section_id)
    else:
        assessments = []
    
    page_ctx = GradePageContext(request, ctx)
    context = page_ctx.build(
        title="قائمة التقييمات",
        items=assessments
    )
    
    return templates.TemplateResponse("grades/list.html", context)


# ============= Assessment CRUD =============

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
    
    page_ctx = GradePageContext(request, ctx)
    context = page_ctx.build(
        title="إنشاء تقييم جديد",
        sections=sections,
        subjects=subjects,
        teachers=teachers,
    )
    
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
    
    # Get current academic year
    helper = GradeDataHelper(db, user.school_id)
    current_year = await helper.get_current_year()
    
    if not current_year:
        return RedirectResponse(
            url="/grades/create?error=يجب إنشاء عام دراسي أولاً",
            status_code=303
        )
    
    # Build assessment data
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
    
    try:
        assessment = await service.assessments.create(**data)
        return RedirectResponse(
            url=f"/grades/{assessment.id}?success=created",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/grades/create?error={str(e)}",
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
    """Display edit assessment page."""
    assessment = await get_assessment_with_details(db, assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    helper = GradeDataHelper(db, user.school_id)
    sections = await helper.get_sections()
    subjects = await helper.get_subjects()
    teachers = await helper.get_teachers()
    
    page_ctx = GradePageContext(request, ctx)
    context = page_ctx.build(
        title="تعديل التقييم",
        item=assessment,
        sections=sections,
        subjects=subjects,
        teachers=teachers,
    )
    
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
    
    # Build update data
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
    """Display assessment details."""
    assessment = await get_assessment_with_details(db, assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # Fetch grades with student names
    service = GradeService(db)
    grades = await service.grades.list_by_assessment(assessment_id)
    
    # Get student names
    student_names = {}
    for g in grades:
        student = await service.students.get(g.student_id)
        if student:
            student_names[g.student_id] = student.name
    
    formatted_grades = [GradeDisplay.from_grade(g, student_names.get(g.student_id)) for g in grades]
    
    page_ctx = GradePageContext(request, ctx)
    context = page_ctx.build(
        title=f"تفاصيل التقييم: {assessment.title}",
        item=assessment,
        grades=formatted_grades,
    )
    
    return templates.TemplateResponse("grades/show.html", context)


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


# ============= Grade Entry =============

@router.get("/{assessment_id}/grades", name="grades.entry")
async def view_assessment_grades(
    request: Request,
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """Display grade entry page."""
    service = GradeService(db)
    assessment = await service.assessments.get(assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # Fetch students with their grades
    students_with_grades = await fetch_students_with_grades(db, assessment_id, user.school_id)
    
    page_ctx = GradePageContext(request, ctx)
    
    # Get count for success message
    success = request.query_params.get('success')
    if success == 'grades_saved':
        count = request.query_params.get('count', '0')
        page_ctx._messages = {
            'success': f"✅ تم حفظ {count} درجة بنجاح",
            'error': get_error_message(request),
            'warning': get_warning_message(request)
        }
    
    context = page_ctx.build(
        title=f"إدخال درجات: {assessment.title}",
        assessment={
            "id": assessment.id,
            "title": assessment.title,
            "max_score": float(assessment.max_score),
            "passing_score": float(assessment.passing_score) if hasattr(assessment, 'passing_score') else None,
            "weight": float(assessment.weight) if hasattr(assessment, 'weight') else 1.0,
        },
        students=students_with_grades,
    )
    
    return templates.TemplateResponse("grades/entry.html", context)


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
    
    # Collect grades from form
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
    
    # Save grades
    if records:
        try:
            batch_data = GradeRecordBatch(
                assessment_id=assessment_id,
                records=records
            )
            result = await service.batch_record(user.id, batch_data)
            
            return RedirectResponse(
                url=f"/grades/{assessment_id}/grades?success=grades_saved&count={result.get('recorded', 0)}",
                status_code=303
            )
        except Exception as e:
            return RedirectResponse(
                url=f"/grades/{assessment_id}/grades?error={str(e)}",
                status_code=303
            )
    
    return RedirectResponse(
        url=f"/grades/{assessment_id}/grades?warning=no_grades",
        status_code=303
    )


# ============= Student Grades =============

@router.get("/students/{student_id}", name="grades.student")
async def student_grades(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """Display student grades."""
    service = GradeService(db)
    grades = await service.student_grades(student_id)
    student = await service.students.get(student_id)
    
    # Calculate average
    total_weighted = 0
    total_weight = 0
    for g in grades:
        if g.get("score") is not None:
            total_weighted += g["score"] * g.get("weight", 1.0)
            total_weight += g.get("weight", 1.0)
    
    average = total_weighted / total_weight if total_weight > 0 else 0
    
    page_ctx = GradePageContext(request, ctx)
    context = page_ctx.build(
        title=f"درجات الطالب: {student.name if student else student_id}",
        student=student,
        grades=grades,
        average=round(average, 2),
        total_weighted=round(total_weighted, 2),
    )
    
    return templates.TemplateResponse("grades/student_grades.html", context)


# ============= API Routes =============

class GradeAPIHandler:
    """Base handler for grade API endpoints."""
    
    def __init__(self, db: AsyncSession, user: CurrentUser):
        self.db = db
        self.user = user
        self.service = GradeService(db)
        self.academic_service = AcademicService(db)
    
    async def get_or_404(self, assessment_id: str):
        """Get assessment or raise 404."""
        assessment = await self.service.assessments.get(assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="التقييم غير موجود")
        return assessment
    
    async def get_current_year_id(self):
        """Get current year ID or raise error."""
        try:
            current_year = await self.academic_service.get_current_year(self.user.school_id)
            return current_year.id
        except NotFoundException:
            years = await self.academic_service.years.list_by_school(self.user.school_id)
            if not years:
                raise HTTPException(status_code=400, detail="لا يوجد عام دراسي")
            return years[0].id
    
    def success_response(self, message: str, **extra) -> dict:
        """Create standardized success response."""
        return {"success": True, "message": message, **extra}


@router.post("/api/assessments/create", name="grades.api.create")
async def create_assessment_api(
    req: AssessmentCreate,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: Create assessment."""
    handler = GradeAPIHandler(db, user)
    year_id = await handler.get_current_year_id()
    
    req_data = req.model_dump()
    req_data["year_id"] = year_id
    req_data["school_id"] = user.school_id
    
    assessment = await handler.service.assessments.create(**req_data)
    return handler.success_response(
        "تم إنشاء التقييم بنجاح",
        id=assessment.id
    )


@router.put("/api/assessments/{assessment_id}", name="grades.api.update")
async def update_assessment_api(
    assessment_id: str,
    req: AssessmentUpdate,
    user: CurrentUser = Depends(require_any_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    """API: Update assessment."""
    handler = GradeAPIHandler(db, user)
    assessment = await handler.get_or_404(assessment_id)
    
    update_data = req.model_dump(exclude_unset=True)
    await handler.service.assessments.update(assessment, **update_data)
    
    return handler.success_response("تم تحديث التقييم بنجاح")


@router.delete("/api/assessments/{assessment_id}", name="grades.api.delete")
async def delete_assessment_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.delete")),
    db: AsyncSession = Depends(get_db),
):
    """API: Delete assessment."""
    handler = GradeAPIHandler(db, user)
    assessment = await handler.get_or_404(assessment_id)
    await handler.service.assessments.delete(assessment)
    
    return handler.success_response("تم حذف التقييم بنجاح")


@router.post("/api/grades/batch", name="grades.api.batch")
async def create_grades_batch_api(
    req: GradeRecordBatch,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: Batch create grades."""
    handler = GradeAPIHandler(db, user)
    result = await handler.service.batch_record(user.id, req)
    
    return handler.success_response(
        f"تم إدخال {result['recorded']} درجة بنجاح",
        count=result["recorded"]
    )


@router.post("/api/grades/single", name="grades.api.single")
async def create_grade_api(
    req: GradeRecordCreate,
    user: CurrentUser = Depends(require_any_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    """API: Create single grade."""
    handler = GradeAPIHandler(db, user)
    result = await handler.service.record_grade(user.id, req)
    
    return handler.success_response(
        "تم إدخال الدرجة بنجاح",
        id=result["id"]
    )


@router.get("/api/assessments", name="grades.api.list")
async def get_assessments_api(
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
    section_id: Optional[str] = None,
):
    """API: List assessments."""
    handler = GradeAPIHandler(db, user)
    
    if section_id:
        assessments = await handler.service.list_assessments(section_id)
    else:
        assessments = []
    
    return handler.success_response(
        "تم جلب التقييمات بنجاح",
        items=assessments,
        total=len(assessments)
    )


@router.get("/api/assessments/{assessment_id}", name="grades.api.show")
async def get_assessment_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: Get assessment details."""
    handler = GradeAPIHandler(db, user)
    assessment = await get_assessment_with_details(db, assessment_id)
    
    if not assessment:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    return handler.success_response(
        "تم جلب التقييم بنجاح",
        item=assessment
    )


@router.get("/api/assessments/{assessment_id}/grades", name="grades.api.grades")
async def get_assessment_grades_api(
    assessment_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: Get assessment grades."""
    handler = GradeAPIHandler(db, user)
    grades = await handler.service.grades.list_by_assessment(assessment_id)
    
    return handler.success_response(
        "تم جلب الدرجات بنجاح",
        items=grades
    )


@router.get("/api/students/{student_id}/grades", name="grades.api.student")
async def get_student_grades_api(
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    """API: Get student grades."""
    handler = GradeAPIHandler(db, user)
    grades = await handler.service.student_grades(student_id)
    
    return handler.success_response(
        "تم جلب درجات الطالب بنجاح",
        items=grades
    )
