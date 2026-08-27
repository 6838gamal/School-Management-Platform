"""Academic structure service."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.academics import (
    AcademicYearRepository, GradeRepository, PeriodRepository,
    RoomRepository, SectionRepository, StageRepository, SubjectRepository,
)
from app.schemas.academics import (
    AcademicYearCreate, AcademicYearUpdate,
    GradeCreate, GradeUpdate,
    PeriodCreate, PeriodUpdate,
    RoomCreate, RoomUpdate,
    SectionCreate, SectionUpdate,
    StageCreate, StageUpdate,
    SubjectCreate, SubjectUpdate,
)


class AcademicService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.years = AcademicYearRepository(db)
        self.stages = StageRepository(db)
        self.grades = GradeRepository(db)
        self.sections = SectionRepository(db)
        self.subjects = SubjectRepository(db)
        self.rooms = RoomRepository(db)
        self.periods = PeriodRepository(db)

    # ============= دوال جلب البيانات =============
    
    async def get_current_year(self, school_id: str):
        year = await self.years.get_current(school_id)
        if not year:
            raise NotFoundException("لا يوجد عام دراسي حالي")
        return year

    async def get_full_tree(self, school_id: str) -> list[dict]:
        try:
            year = await self.get_current_year(school_id)
            stages = await self.stages.list_by_year(year.id)
            tree = []
            for stage in stages:
                grades = await self.grades.list_by_stage(stage.id)
                grade_list = []
                for grade in grades:
                    sections = await self.sections.list_by_grade(grade.id)
                    grade_list.append({
                        "id": grade.id,
                        "name": grade.name,
                        "sections": [
                            {"id": s.id, "name": s.name, "capacity": s.capacity}
                            for s in sections
                        ],
                    })
                tree.append({"id": stage.id, "name": stage.name, "grades": grade_list})
            return tree
        except NotFoundException:
            return []

    async def get_onboarding_data(self, school_id: str) -> dict:
        try:
            year = await self.years.get_current(school_id)
        except Exception:
            year = None
            
        return {
            "years": [
                {"id": y.id, "name": y.name, "is_current": y.is_current}
                for y in await self.years.list_by_school(school_id)
            ],
            "stages": [
                {"id": s.id, "name": s.name}
                for s in await self.stages.list_by_year(year.id)
            ] if year else [],
            "subjects": [
                {"id": s.id, "name": s.name}
                for s in await self.subjects.list_by_school(school_id)
            ],
            "sections": [
                {"id": s.id, "name": s.name}
                for s in await self.sections.list_by_school(school_id)
            ],
            "rooms": [
                {"id": r.id, "name": r.name}
                for r in await self.rooms.list_by_school(school_id)
            ],
            "periods": [
                {"id": p.id, "name": p.name, "order": p.order}
                for p in await self.periods.list_by_school(school_id)
            ],
        }

    # ============= دوال الإنشاء (Create) =============
    
    async def create_year(self, school_id: str, req: AcademicYearCreate):
        return await self.years.create(school_id=school_id, **req.model_dump())

    async def create_stage(self, school_id: str, req: StageCreate):
        return await self.stages.create(school_id=school_id, **req.model_dump())

    async def create_grade(self, school_id: str, req: GradeCreate):
        return await self.grades.create(school_id=school_id, **req.model_dump())

    async def create_section(self, school_id: str, req: SectionCreate):
        return await self.sections.create(school_id=school_id, **req.model_dump())

    async def create_subject(self, school_id: str, req: SubjectCreate):
        existing = await self.subjects.get_by(school_id=school_id, name=req.name)
        if existing:
            raise ConflictException("المادة موجودة بالفعل")
        return await self.subjects.create(school_id=school_id, **req.model_dump())

    async def create_room(self, school_id: str, req: RoomCreate):
        return await self.rooms.create(school_id=school_id, **req.model_dump())

    async def create_period(self, school_id: str, req: PeriodCreate):
        return await self.periods.create(school_id=school_id, **req.model_dump())

    # ============= دوال التحديث (Update) =============
    
    async def update_year(self, year_id: str, req: AcademicYearUpdate):
        """تحديث عام دراسي"""
        year = await self.years.get_by_id(year_id)
        if not year:
            raise NotFoundException("العام الدراسي غير موجود")
        update_data = req.model_dump(exclude_unset=True)
        return await self.years.update(year_id, **update_data)

    async def update_stage(self, stage_id: str, req: StageUpdate):
        """تحديث مرحلة"""
        stage = await self.stages.get_by_id(stage_id)
        if not stage:
            raise NotFoundException("المرحلة غير موجودة")
        update_data = req.model_dump(exclude_unset=True)
        return await self.stages.update(stage_id, **update_data)

    async def update_grade(self, grade_id: str, req: GradeUpdate):
        """تحديث صف"""
        grade = await self.grades.get_by_id(grade_id)
        if not grade:
            raise NotFoundException("الصف غير موجود")
        update_data = req.model_dump(exclude_unset=True)
        return await self.grades.update(grade_id, **update_data)

    async def update_section(self, section_id: str, req: SectionUpdate):
        """تحديث شعبة"""
        section = await self.sections.get_by_id(section_id)
        if not section:
            raise NotFoundException("الشعبة غير موجودة")
        update_data = req.model_dump(exclude_unset=True)
        return await self.sections.update(section_id, **update_data)

    async def update_subject(self, subject_id: str, req: SubjectUpdate):
        """تحديث مادة"""
        subject = await self.subjects.get_by_id(subject_id)
        if not subject:
            raise NotFoundException("المادة غير موجودة")
        update_data = req.model_dump(exclude_unset=True)
        return await self.subjects.update(subject_id, **update_data)

    async def update_room(self, room_id: str, req: RoomUpdate):
        """تحديث قاعة"""
        room = await self.rooms.get_by_id(room_id)
        if not room:
            raise NotFoundException("القاعة غير موجودة")
        update_data = req.model_dump(exclude_unset=True)
        return await self.rooms.update(room_id, **update_data)

    async def update_period(self, period_id: str, req: PeriodUpdate):
        """تحديث فصل"""
        period = await self.periods.get_by_id(period_id)
        if not period:
            raise NotFoundException("الفصل غير موجود")
        update_data = req.model_dump(exclude_unset=True)
        return await self.periods.update(period_id, **update_data)

    # ============= دوال الحذف (Delete) =============
    
    async def delete_year(self, year_id: str):
        """حذف عام دراسي"""
        year = await self.years.get_by_id(year_id)
        if not year:
            raise NotFoundException("العام الدراسي غير موجود")
        return await self.years.delete(year_id)

    async def delete_stage(self, stage_id: str):
        """حذف مرحلة"""
        stage = await self.stages.get_by_id(stage_id)
        if not stage:
            raise NotFoundException("المرحلة غير موجودة")
        return await self.stages.delete(stage_id)

    async def delete_grade(self, grade_id: str):
        """حذف صف"""
        grade = await self.grades.get_by_id(grade_id)
        if not grade:
            raise NotFoundException("الصف غير موجود")
        return await self.grades.delete(grade_id)

    async def delete_section(self, section_id: str):
        """حذف شعبة"""
        section = await self.sections.get_by_id(section_id)
        if not section:
            raise NotFoundException("الشعبة غير موجودة")
        return await self.sections.delete(section_id)

    async def delete_subject(self, subject_id: str):
        """حذف مادة"""
        subject = await self.subjects.get_by_id(subject_id)
        if not subject:
            raise NotFoundException("المادة غير موجودة")
        return await self.subjects.delete(subject_id)

    async def delete_room(self, room_id: str):
        """حذف قاعة"""
        room = await self.rooms.get_by_id(room_id)
        if not room:
            raise NotFoundException("القاعة غير موجودة")
        return await self.rooms.delete(room_id)

    async def delete_period(self, period_id: str):
        """حذف فصل"""
        period = await self.periods.get_by_id(period_id)
        if not period:
            raise NotFoundException("الفصل غير موجود")
        return await self.periods.delete(period_id)
