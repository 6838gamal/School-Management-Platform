"""Academic structure repositories."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academics import AcademicYear, Grade, Period, Room, Section, Stage, Subject
from app.models.schools import School
from app.repositories.base import BaseRepository


class SchoolRepository(BaseRepository[School]):
    model = School

    async def get_by_code(self, code: str) -> School | None:
        result = await self.db.execute(select(self.model).where(self.model.code == code))
        return result.scalar_one_or_none()


class AcademicYearRepository(BaseRepository[AcademicYear]):
    model = AcademicYear

    async def get_current(self, school_id: str) -> AcademicYear | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.is_current == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_by_school(self, school_id: str) -> list[AcademicYear]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> AcademicYear | None:
        """جلب عام دراسي بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, id: str, **kwargs) -> AcademicYear:
        """تحديث عام دراسي"""
        item = await self.get_by_id(id)
        if not item:
            raise ValueError("العنصر غير موجود")
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: str) -> bool:
        """حذف عام دراسي"""
        item = await self.get_by_id(id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True


class StageRepository(BaseRepository[Stage]):
    model = Stage

    async def list_by_year(self, year_id: str) -> list[Stage]:
        result = await self.db.execute(
            select(self.model).where(self.model.year_id == year_id).order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[Stage]:
        """جلب جميع المراحل لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Stage | None:
        """جلب مرحلة بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, id: str, **kwargs) -> Stage:
        """تحديث مرحلة"""
        item = await self.get_by_id(id)
        if not item:
            raise ValueError("العنصر غير موجود")
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: str) -> bool:
        """حذف مرحلة"""
        item = await self.get_by_id(id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True


class GradeRepository(BaseRepository[Grade]):
    model = Grade

    async def list_by_stage(self, stage_id: str) -> list[Grade]:
        result = await self.db.execute(
            select(self.model).where(self.model.stage_id == stage_id).order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[Grade]:
        """جلب جميع الصفوف لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Grade | None:
        """جلب صف بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, id: str, **kwargs) -> Grade:
        """تحديث صف"""
        item = await self.get_by_id(id)
        if not item:
            raise ValueError("العنصر غير موجود")
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: str) -> bool:
        """حذف صف"""
        item = await self.get_by_id(id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True


class SectionRepository(BaseRepository[Section]):
    model = Section

    async def list_by_grade(self, grade_id: str) -> list[Section]:
        result = await self.db.execute(
            select(self.model).where(self.model.grade_id == grade_id).order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[Section]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Section | None:
        """جلب شعبة بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, id: str, **kwargs) -> Section:
        """تحديث شعبة"""
        item = await self.get_by_id(id)
        if not item:
            raise ValueError("العنصر غير موجود")
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: str) -> bool:
        """حذف شعبة"""
        item = await self.get_by_id(id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True


class SubjectRepository(BaseRepository[Subject]):
    model = Subject

    async def get_by(self, school_id: str, name: str) -> Subject | None:
        """جلب مادة بالاسم لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.name == name
            )
        )
        return result.scalar_one_or_none()

    async def list_by_school(self, school_id: str) -> list[Subject]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Subject | None:
        """جلب مادة بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, id: str, **kwargs) -> Subject:
        """تحديث مادة"""
        item = await self.get_by_id(id)
        if not item:
            raise ValueError("العنصر غير موجود")
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: str) -> bool:
        """حذف مادة"""
        item = await self.get_by_id(id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True


class RoomRepository(BaseRepository[Room]):
    model = Room

    async def list_by_school(self, school_id: str) -> list[Room]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Room | None:
        """جلب قاعة بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, id: str, **kwargs) -> Room:
        """تحديث قاعة"""
        item = await self.get_by_id(id)
        if not item:
            raise ValueError("العنصر غير موجود")
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: str) -> bool:
        """حذف قاعة"""
        item = await self.get_by_id(id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True


class PeriodRepository(BaseRepository[Period]):
    model = Period

    async def list_by_school(self, school_id: str) -> list[Period]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Period | None:
        """جلب فصل بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, id: str, **kwargs) -> Period:
        """تحديث فصل"""
        item = await self.get_by_id(id)
        if not item:
            raise ValueError("العنصر غير موجود")
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: str) -> bool:
        """حذف فصل"""
        item = await self.get_by_id(id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        return True
