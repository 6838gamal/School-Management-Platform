"""Grades service: assessments and grade entry."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.repositories.grades import AssessmentRepository, GradeRecordRepository
from app.repositories.students import StudentRepository
from app.schemas.grades import AssessmentCreate, AssessmentUpdate, GradeRecordBatch, GradeRecordCreate


class GradeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.assessments = AssessmentRepository(db)
        self.grades = GradeRecordRepository(db)
        self.students = StudentRepository(db)

    async def create_assessment(self, school_id: str, req: AssessmentCreate) -> dict:
        assessment = await self.assessments.create(school_id=school_id, **req.model_dump())
        return {"id": assessment.id}

    async def update_assessment(self, assessment_id: str, req: AssessmentUpdate) -> dict:
        assessment = await self.assessments.get(assessment_id)
        if not assessment:
            raise NotFoundException("التقييم غير موجود")
        assessment = await self.assessments.update(assessment, **req.model_dump(exclude_unset=True))
        return {"id": assessment.id}

    async def list_assessments(self, section_id: str) -> list[dict]:
        items = await self.assessments.list_by_section(section_id)
        return [
            {"id": a.id, "title": a.title, "type": a.assessment_type, "max_score": float(a.max_score), "date": a.date}
            for a in items
        ]

    async def record_grade(self, user_id: str, req: GradeRecordCreate) -> dict:
        existing = await self.grades.get_by_assessment_student(req.assessment_id, req.student_id)
        if existing:
            existing.score = req.score
            existing.note = req.note
            existing.graded_by = user_id
            await self.db.flush()
            return {"id": existing.id}
        record = await self.grades.create(
            assessment_id=req.assessment_id,
            student_id=req.student_id,
            school_id=(await self.assessments.get(req.assessment_id)).school_id if await self.assessments.get(req.assessment_id) else "",
            score=req.score,
            note=req.note,
            graded_by=user_id,
        )
        return {"id": record.id}

    async def batch_record(self, user_id: str, req: GradeRecordBatch) -> dict:
        count = 0
        for r in req.records:
            student_id = r.get("student_id")
            score = r.get("score")
            if not student_id or score is None:
                continue
            note = r.get("note")
            existing = await self.grades.get_by_assessment_student(req.assessment_id, student_id)
            if existing:
                existing.score = score
                existing.note = note
                existing.graded_by = user_id
            else:
                assessment = await self.assessments.get(req.assessment_id)
                if not assessment:
                    continue
                await self.grades.create(
                    assessment_id=req.assessment_id,
                    student_id=student_id,
                    school_id=assessment.school_id,
                    score=score,
                    note=note,
                    graded_by=user_id,
                )
            count += 1
        await self.db.flush()
        return {"recorded": count}

    async def student_grades(self, student_id: str) -> list[dict]:
        records = await self.grades.list_by_student(student_id)
        result = []
        for r in records:
            assessment = await self.assessments.get(r.assessment_id)
            if assessment:
                result.append({
                    "assessment_id": r.assessment_id,
                    "title": assessment.title,
                    "type": assessment.assessment_type,
                    "score": float(r.score) if r.score is not None else None,
                    "max_score": float(assessment.max_score),
                    "weight": float(assessment.weight),
                })
        return result
