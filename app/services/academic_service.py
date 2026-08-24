"""Academic structure service."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.academics import (
    AcademicYearRepository, GradeRepository, PeriodRepository,
    RoomRepository, SectionRepository, StageRepository, SubjectRepository,
)
from app.repositories.academics import SchoolRepository
from app.schemas.academics import (
    AcademicYearCreate, GradeCreate, PeriodCreate, RoomCreate,
    SectionCreate, StageCreate, SubjectCreate,
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

    async def get_current_year(self, school_id: str):
        year = await self.years.get_current(school_id)
        if not year:
            raise NotFoundException("لا يوجد عام دراسي حالي")
        return year

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

    async def get_full_tree(self, school_id: str) -> list[dict]:
        year = await self.get_current_year(school_id)
        stages = await self.stages.list_by_year(year.id)
        tree = []
        for stage in stages:
            grades = await self.grades.list_by_stage(stage.id)
            grade_list = []
            for grade in grades:
                sections = await self.sections.list_by_grade(grade.id)
                grade_list.append({
                    "id": grade.id, "name": grade.name, "sections": [
                        {"id": s.id, "name": s.name, "capacity": s.capacity} for s in sections
                    ],
                })
            tree.append({"id": stage.id, "name": stage.name, "grades": grade_list})
        return tree

    async def get_onboarding_data(self, school_id: str) -> dict:
        year = await self.years.get_current(school_id)
        return {
            "years": [{"id": y.id, "name": y.name, "is_current": y.is_current} for y in await self.years.list_by_school(school_id)],
            "stages": [{"id": s.id, "name": s.name} for s in await self.stages.list_by_year(year.id if year else "")] if year else [],
            "subjects": [{"id": s.id, "name": s.name} for s in await self.subjects.list_by_school(school_id)],
            "sections": [{"id": s.id, "name": s.name} for s in await self.sections.list_by_school(school_id)],
            "rooms": [{"id": r.id, "name": r.name} for r in await self.rooms.list_by_school(school_id)],
            "periods": [{"id": p.id, "name": p.name, "order": p.order} for p in await self.periods.list_by_school(school_id)],
        }
