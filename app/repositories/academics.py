"""Academic structure repositories."""
from sqlalchemy import select, and_, or_
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
        """جلب العام الدراسي الحالي"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.is_current == True,  # noqa: E712
                self.model.is_active == True,   # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_by_school(self, school_id: str) -> list[AcademicYear]:
        """جلب جميع الأعوام الدراسية لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .order_by(self.model.name.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> AcademicYear | None:
        """جلب عام دراسي بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, school_id: str, name: str) -> AcademicYear | None:
        """جلب عام دراسي بالاسم لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.name == name
            )
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
        """جلب المراحل حسب السنة الدراسية"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.year_id == year_id)
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[Stage]:
        """جلب جميع المراحل لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_school_and_year(self, school_id: str, year_id: str) -> list[Stage]:
        """جلب المراحل حسب المدرسة والسنة الدراسية"""
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.school_id == school_id,
                self.model.year_id == year_id
            )
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Stage | None:
        """جلب مرحلة بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == id)
            .options(selectinload(self.model.year))
        )
        return result.scalar_one_or_none()

    async def get_by(self, school_id: str, year_id: str, name: str) -> Stage | None:
        """جلب مرحلة حسب المدرسة والسنة والاسم"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.year_id == year_id,
                self.model.name == name
            )
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
        """جلب الصفوف حسب المرحلة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.stage_id == stage_id)
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_stage_and_year(self, stage_id: str, year_id: str) -> list[Grade]:
        """جلب الصفوف حسب المرحلة والسنة الدراسية"""
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.stage_id == stage_id,
                self.model.year_id == year_id
            )
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[Grade]:
        """جلب جميع الصفوف لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_school_and_year(self, school_id: str, year_id: str) -> list[Grade]:
        """جلب الصفوف حسب المدرسة والسنة الدراسية"""
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.school_id == school_id,
                self.model.year_id == year_id
            )
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def list_by_school_with_relations(self, school_id: str) -> list[Grade]:
        """جلب الصفوف مع العلاقات (المرحلة والسنة)"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .options(
                selectinload(self.model.stage),
                selectinload(self.model.year)
            )
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Grade | None:
        """جلب صف بواسطة المعرف مع العلاقات"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == id)
            .options(
                selectinload(self.model.stage),
                selectinload(self.model.year)
            )
        )
        return result.scalar_one_or_none()

    async def get_by(self, school_id: str, stage_id: str, year_id: str, name: str) -> Grade | None:
        """جلب صف حسب المدرسة والمرحلة والسنة والاسم"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.stage_id == stage_id,
                self.model.year_id == year_id,
                self.model.name == name
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name_in_stage(self, stage_id: str, name: str, exclude_id: str | None = None) -> Grade | None:
        """جلب صف بالاسم في مرحلة معينة (مع إمكانية الاستبعاد)"""
        query = select(self.model).where(
            self.model.stage_id == stage_id,
            self.model.name == name
        )
        if exclude_id:
            query = query.where(self.model.id != exclude_id)
        result = await self.db.execute(query)
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
        """جلب الشعب حسب الصف"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.grade_id == grade_id)
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[Section]:
        """جلب جميع الشعب لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_by_school_and_year(self, school_id: str, year_id: str) -> list[Section]:
        """✅ جلب الشعب حسب المدرسة والسنة الدراسية"""
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.school_id == school_id,
                self.model.year_id == year_id
            )
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_by_grade_with_relations(self, grade_id: str) -> list[Section]:
        """جلب الشعب مع العلاقة مع الصف"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.grade_id == grade_id)
            .options(selectinload(self.model.grade))
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_by_school_with_relations(self, school_id: str) -> list[Section]:
        """✅ جلب جميع الشعب مع العلاقات (الصف والسنة)"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .options(
                selectinload(self.model.grade),
                selectinload(self.model.year)
            )
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Section | None:
        """جلب شعبة بواسطة المعرف مع العلاقات"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == id)
            .options(
                selectinload(self.model.grade),
                selectinload(self.model.year)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name_in_grade(self, grade_id: str, name: str, exclude_id: str | None = None) -> Section | None:
        """جلب شعبة بالاسم في صف معين (مع إمكانية الاستبعاد)"""
        query = select(self.model).where(
            self.model.grade_id == grade_id,
            self.model.name == name
        )
        if exclude_id:
            query = query.where(self.model.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name_in_school(self, school_id: str, name: str, exclude_id: str | None = None) -> Section | None:
        """✅ جلب شعبة بالاسم في مدرسة معينة (مع إمكانية الاستبعاد)"""
        query = select(self.model).where(
            self.model.school_id == school_id,
            self.model.name == name
        )
        if exclude_id:
            query = query.where(self.model.id != exclude_id)
        result = await self.db.execute(query)
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

    async def get_by_code(self, school_id: str, code: str) -> Subject | None:
        """جلب مادة بالكود لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.code == code
            )
        )
        return result.scalar_one_or_none()

    async def list_by_school(self, school_id: str) -> list[Subject]:
        """جلب جميع المواد لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_active_by_school(self, school_id: str) -> list[Subject]:
        """جلب المواد النشطة لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.school_id == school_id,
                self.model.is_active == True  # noqa: E712
            )
            .order_by(self.model.name)
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
        """جلب جميع القاعات لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_active_by_school(self, school_id: str) -> list[Room]:
        """جلب القاعات النشطة لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.school_id == school_id,
                self.model.is_active == True  # noqa: E712
            )
            .order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Room | None:
        """جلب قاعة بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, school_id: str, name: str) -> Room | None:
        """جلب قاعة بالاسم لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.name == name
            )
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
        """جلب جميع الفصول لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.school_id == school_id)
            .order_by(self.model.order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: str) -> Period | None:
        """جلب فصل بواسطة المعرف"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_order(self, school_id: str, order: int) -> Period | None:
        """جلب فصل بالترتيب لمدرسة معينة"""
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.order == order
            )
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
