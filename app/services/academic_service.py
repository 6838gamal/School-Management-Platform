"""Academic structure service."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import logging

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
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

logger = logging.getLogger(__name__)


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
        """جلب العام الدراسي الحالي"""
        year = await self.years.get_current(school_id)
        if not year:
            raise NotFoundException("لا يوجد عام دراسي حالي")
        return year

    async def get_year_by_id(self, year_id: str):
        """جلب عام دراسي بواسطة المعرف"""
        year = await self.years.get_by_id(year_id)
        if not year:
            raise NotFoundException("العام الدراسي غير موجود")
        return year

    async def get_stage_by_id(self, stage_id: str):
        """جلب مرحلة بواسطة المعرف"""
        stage = await self.stages.get_by_id(stage_id)
        if not stage:
            raise NotFoundException("المرحلة غير موجودة")
        return stage

    async def get_grade_by_id(self, grade_id: str):
        """جلب صف بواسطة المعرف"""
        grade = await self.grades.get_by_id(grade_id)
        if not grade:
            raise NotFoundException("الصف غير موجود")
        return grade

    async def get_section_by_id(self, section_id: str):
        """✅ جلب شعبة بواسطة المعرف"""
        section = await self.sections.get_by_id(section_id)
        if not section:
            raise NotFoundException("الشعبة غير موجودة")
        return section

    # ============= دوال الشجرة الأكاديمية =============
    
    async def get_full_tree(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب الشجرة الأكاديمية الكاملة مع دعم السنة"""
        try:
            year = await self.get_current_year(school_id)
            return await self._build_tree_for_year(school_id, year.id)
        except NotFoundException:
            return []

    async def get_tree_by_year(self, school_id: str, year_id: str) -> List[Dict[str, Any]]:
        """جلب الشجرة الأكاديمية حسب السنة المحددة"""
        try:
            # التحقق من وجود السنة
            await self.get_year_by_id(year_id)
            return await self._build_tree_for_year(school_id, year_id)
        except NotFoundException:
            return []

    async def _build_tree_for_year(self, school_id: str, year_id: str) -> List[Dict[str, Any]]:
        """بناء الشجرة الأكاديمية لسنة محددة"""
        stages = await self.stages.list_by_year(year_id)
        tree = []
        
        for stage in stages:
            # جلب الصفوف الخاصة بالمرحلة والسنة
            grades = await self.grades.list_by_stage_and_year(stage.id, year_id)
            grade_list = []
            
            for grade in grades:
                sections = await self.sections.list_by_grade(grade.id)
                grade_list.append({
                    "id": grade.id,
                    "name": grade.name,
                    "name_en": grade.name_en,
                    "order": grade.order,
                    "year_id": grade.year_id,
                    "sections": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "capacity": s.capacity,
                            "is_active": s.is_active,
                            "class_teacher_ids": s.class_teacher_ids,  # ✅ إضافة المعلمين
                        }
                        for s in sections
                    ],
                })
            
            tree.append({
                "id": stage.id,
                "name": stage.name,
                "name_en": stage.name_en,
                "order": stage.order,
                "year_id": stage.year_id,
                "grades": grade_list
            })
        
        return tree

    async def get_onboarding_data(self, school_id: str) -> dict:
        """جلب بيانات الإعداد الأولي"""
        try:
            year = await self.years.get_current(school_id)
            year_id = year.id if year else None
        except Exception:
            year = None
            year_id = None
            
        return {
            "years": [
                {"id": y.id, "name": y.name, "is_current": y.is_current}
                for y in await self.years.list_by_school(school_id)
            ],
            "stages": [
                {"id": s.id, "name": s.name, "year_id": s.year_id}
                for s in await self.stages.list_by_year(year_id)
            ] if year_id else [],
            "grades": [
                {"id": g.id, "name": g.name, "stage_id": g.stage_id, "year_id": g.year_id}
                for g in await self.grades.list_by_school(school_id)
            ],
            "subjects": [
                {"id": s.id, "name": s.name}
                for s in await self.subjects.list_by_school(school_id)
            ],
            "sections": [
                {"id": s.id, "name": s.name, "grade_id": s.grade_id, "year_id": s.year_id}  # ✅ إضافة year_id
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
        """إنشاء عام دراسي جديد"""
        return await self.years.create(school_id=school_id, **req.model_dump())

    async def create_stage(self, school_id: str, req: StageCreate):
        """إنشاء مرحلة جديدة مع التحقق من السنة"""
        # التحقق من وجود السنة
        year = await self.years.get_by_id(req.year_id)
        if not year:
            raise NotFoundException("السنة الدراسية غير موجودة")
        
        # التحقق من عدم وجود مرحلة بنفس الاسم في نفس السنة
        existing = await self.stages.get_by(school_id=school_id, year_id=req.year_id, name=req.name)
        if existing:
            raise ConflictException("يوجد مرحلة بنفس الاسم في هذه السنة الدراسية")
        
        return await self.stages.create(school_id=school_id, **req.model_dump())

    async def create_grade(self, school_id: str, req: GradeCreate):
        """إنشاء صف جديد مع التحقق من السنة والمرحلة"""
        # التحقق من وجود السنة
        year = await self.years.get_by_id(req.year_id)
        if not year:
            raise NotFoundException("السنة الدراسية غير موجودة")
        
        # التحقق من وجود المرحلة
        stage = await self.stages.get_by_id(req.stage_id)
        if not stage:
            raise NotFoundException("المرحلة غير موجودة")
        
        # التحقق من أن المرحلة تابعة للسنة المحددة
        if stage.year_id != req.year_id:
            raise ValidationException("المرحلة المحددة لا تنتمي إلى السنة الدراسية المختارة")
        
        # التحقق من عدم وجود صف بنفس الاسم في نفس المرحلة والسنة
        existing = await self.grades.get_by(
            school_id=school_id,
            stage_id=req.stage_id,
            year_id=req.year_id,
            name=req.name
        )
        if existing:
            raise ConflictException("يوجد صف بنفس الاسم في هذه المرحلة والسنة الدراسية")
        
        return await self.grades.create(school_id=school_id, **req.model_dump())

    async def create_section(self, school_id: str, req: SectionCreate):
        """✅ إنشاء شعبة جديدة مع دعم السنة والمعلمين"""
        # التحقق من وجود السنة
        year = await self.years.get_by_id(req.year_id)
        if not year:
            raise NotFoundException("السنة الدراسية غير موجودة")
        
        # التحقق من وجود الصف
        grade = await self.grades.get_by_id(req.grade_id)
        if not grade:
            raise NotFoundException("الصف غير موجود")
        
        # التحقق من أن الصف يتبع السنة المحددة
        if grade.year_id != req.year_id:
            raise ValidationException("الصف المحدد لا ينتمي إلى السنة الدراسية المختارة")
        
        # التحقق من عدم وجود شعبة بنفس الاسم في نفس الصف
        existing = await self.sections.get_by_name_in_grade(
            grade_id=req.grade_id,
            name=req.name
        )
        if existing:
            raise ConflictException("يوجد شعبة بنفس الاسم في هذا الصف")
        
        # تحويل قائمة المعلمين إلى نص مفصول بفواصل
        class_teacher_ids = None
        if req.teacher_ids:
            class_teacher_ids = ",".join(req.teacher_ids)
        
        # إنشاء الشعبة
        return await self.sections.create(
            school_id=school_id,
            grade_id=req.grade_id,
            year_id=req.year_id,  # ✅ إضافة السنة
            name=req.name,
            capacity=req.capacity or 30,
            is_active=req.is_active,
            class_teacher_ids=class_teacher_ids  # ✅ إضافة المعلمين
        )

    async def create_subject(self, school_id: str, req: SubjectCreate):
        """إنشاء مادة جديدة"""
        existing = await self.subjects.get_by(school_id=school_id, name=req.name)
        if existing:
            raise ConflictException("المادة موجودة بالفعل")
        return await self.subjects.create(school_id=school_id, **req.model_dump())

    async def create_room(self, school_id: str, req: RoomCreate):
        """إنشاء قاعة جديدة"""
        existing = await self.rooms.get_by(school_id=school_id, name=req.name)
        if existing:
            raise ConflictException("القاعة موجودة بالفعل")
        return await self.rooms.create(school_id=school_id, **req.model_dump())

    async def create_period(self, school_id: str, req: PeriodCreate):
        """إنشاء فصل جديد"""
        # التحقق من عدم وجود فصل بنفس الترتيب
        existing = await self.periods.get_by(school_id=school_id, order=req.order)
        if existing:
            raise ConflictException(f"يوجد فصل بالترتيب {req.order} بالفعل")
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
        """تحديث مرحلة مع التحقق من السنة"""
        stage = await self.stages.get_by_id(stage_id)
        if not stage:
            raise NotFoundException("المرحلة غير موجودة")
        
        update_data = req.model_dump(exclude_unset=True)
        
        # إذا تم تغيير السنة، التحقق من وجودها
        if req.year_id:
            year = await self.years.get_by_id(req.year_id)
            if not year:
                raise NotFoundException("السنة الدراسية غير موجودة")
        
        return await self.stages.update(stage_id, **update_data)

    async def update_grade(self, grade_id: str, req: GradeUpdate):
        """تحديث صف مع التحقق من السنة والمرحلة"""
        grade = await self.grades.get_by_id(grade_id)
        if not grade:
            raise NotFoundException("الصف غير موجود")
        
        update_data = req.model_dump(exclude_unset=True)
        
        # إذا تم تغيير السنة، التحقق من وجودها
        if req.year_id:
            year = await self.years.get_by_id(req.year_id)
            if not year:
                raise NotFoundException("السنة الدراسية غير موجودة")
        
        # إذا تم تغيير المرحلة، التحقق من وجودها
        if req.stage_id:
            stage = await self.stages.get_by_id(req.stage_id)
            if not stage:
                raise NotFoundException("المرحلة غير موجودة")
            
            # التحقق من أن المرحلة تابعة للسنة المحددة
            year_id = req.year_id or grade.year_id
            if stage.year_id != year_id:
                raise ValidationException("المرحلة المحددة لا تنتمي إلى السنة الدراسية المختارة")
        
        return await self.grades.update(grade_id, **update_data)

    async def update_section(self, section_id: str, req: SectionUpdate):
        """✅ تحديث شعبة مع دعم السنة والمعلمين"""
        section = await self.sections.get_by_id(section_id)
        if not section:
            raise NotFoundException("الشعبة غير موجودة")
        
        update_data = req.model_dump(exclude_unset=True)
        
        # إذا تم تغيير السنة، التحقق من وجودها
        if req.year_id:
            year = await self.years.get_by_id(req.year_id)
            if not year:
                raise NotFoundException("السنة الدراسية غير موجودة")
        
        # إذا تم تغيير الصف، التحقق من وجوده
        if req.grade_id:
            grade = await self.grades.get_by_id(req.grade_id)
            if not grade:
                raise NotFoundException("الصف غير موجود")
            
            # التحقق من أن الصف يتبع السنة المحددة
            year_id = req.year_id or section.year_id
            if grade.year_id != year_id:
                raise ValidationException("الصف المحدد لا ينتمي إلى السنة الدراسية المختارة")
        
        # معالجة قائمة المعلمين
        if req.teacher_ids is not None:
            if req.teacher_ids:
                update_data['class_teacher_ids'] = ",".join(req.teacher_ids)
            else:
                update_data['class_teacher_ids'] = None
        
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

    # ============= دوال إضافية للمعلمين =============
    
    async def get_section_with_teachers(self, section_id: str) -> Dict[str, Any]:
        """✅ جلب تفاصيل الشعبة مع المعلمين"""
        section = await self.sections.get_by_id(section_id)
        if not section:
            raise NotFoundException("الشعبة غير موجودة")
        
        # جلب المعلمين من الـ class_teacher_ids
        teachers = []
        if section.class_teacher_ids:
            teacher_ids = section.class_teacher_ids.split(",")
            # جلب المعلمين من خدمة المعلمين
            from app.services.teacher_service import TeacherService
            teacher_service = TeacherService(self.db)
            for teacher_id in teacher_ids:
                try:
                    teacher = await teacher_service.get_teacher_detail(teacher_id)
                    if teacher:
                        teachers.append(teacher)
                except Exception as e:
                    logger.warning(f"Could not fetch teacher {teacher_id}: {e}")
        
        return {
            "id": section.id,
            "name": section.name,
            "grade_id": section.grade_id,
            "year_id": section.year_id,
            "capacity": section.capacity,
            "is_active": section.is_active,
            "class_teacher_ids": section.class_teacher_ids,
            "class_teachers": teachers,
            "grade_name": section.grade.name if section.grade else None,
            "year_name": section.year.name if hasattr(section, 'year') and section.year else None,
        }


# ============================================================
# ✅ تحديث __all__
# ============================================================

__all__ = [
    "AcademicService",
]
