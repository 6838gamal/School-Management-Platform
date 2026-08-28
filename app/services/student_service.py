"""Student service for managing student data."""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete, update

from app.core.exceptions import NotFoundException, ConflictException, ValidationException
from app.models.students import Student
from app.models.academics import Section, Grade, Stage, AcademicYear
from app.repositories.students import StudentRepository
from app.schemas.students import StudentCreate, StudentUpdate, TransferRequest


class StudentService:
    """خدمة إدارة الطلاب."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = StudentRepository(db)

    # ============================================================
    # 1️⃣ إنشاء طالب جديد
    # ============================================================

    async def create_student(
        self, 
        data: StudentCreate, 
        user_id: str, 
        school_id: str
    ) -> Student:
        """إنشاء طالب جديد."""
        # التحقق من عدم تكرار رقم الطالب
        existing = await self.repo.get_by_student_number(data.student_number)
        if existing:
            raise ConflictException(f"رقم الطالب {data.student_number} موجود بالفعل")
        
        # التحقق من عدم تكرار الرقم الوطني
        if data.national_id:
            existing = await self.repo.get_by_national_id(data.national_id)
            if existing:
                raise ConflictException(f"الرقم الوطني {data.national_id} موجود بالفعل")
        
        # إنشاء الطالب
        student = await self.repo.create(
            school_id=school_id,
            student_number=data.student_number,
            national_id=data.national_id,
            first_name=data.first_name,
            last_name=data.last_name,
            gender=data.gender,
            birth_date=data.birth_date,
            guardian_name=data.guardian_name,
            guardian_phone=data.guardian_phone,
            guardian_email=data.guardian_email,
            address=data.address,
            section_id=data.section_id,
            year_id=data.year_id,
            created_by=user_id,
        )
        
        return student

    # ============================================================
    # 2️⃣ جلب طالب بالمعرف
    # ============================================================

    async def get_student(self, student_id: str) -> Optional[Student]:
        """جلب طالب بواسطة المعرف."""
        return await self.repo.get_by_id(student_id)

    # ============================================================
    # 3️⃣ جلب تفاصيل الطالب (مدمج مع Academics)
    # ============================================================

    async def get_student_detail(self, student_id: str) -> Dict[str, Any]:
        """جلب تفاصيل الطالب مع معلومات من Academics."""
        student = await self.repo.get_by_id(student_id)
        if not student:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        # جلب التفاصيل الإضافية
        section_name = None
        grade_name = None
        stage_name = None
        academic_year_name = None
        
        if student.section_id:
            section = await self.db.get(Section, student.section_id)
            if section:
                section_name = section.name
                if section.grade_id:
                    grade = await self.db.get(Grade, section.grade_id)
                    if grade:
                        grade_name = grade.name
                        if grade.stage_id:
                            stage = await self.db.get(Stage, grade.stage_id)
                            if stage:
                                stage_name = stage.name
        
        if student.year_id:
            year = await self.db.get(AcademicYear, student.year_id)
            if year:
                academic_year_name = year.name
        
        return {
            "id": student.id,
            "student_number": student.student_number,
            "national_id": student.national_id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": student.full_name,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "guardian_name": student.guardian_name,
            "guardian_phone": student.guardian_phone,
            "guardian_email": student.guardian_email,
            "address": student.address,
            "is_active": student.is_active,
            "section_id": student.section_id,
            "section_name": section_name,
            "grade_name": grade_name,
            "stage_name": stage_name,
            "year_id": student.year_id,
            "academic_year": academic_year_name,
            "created_at": student.created_at,
            "updated_at": student.updated_at,
        }

    # ============================================================
    # 4️⃣ تحديث بيانات الطالب
    # ============================================================

    async def update_student(
        self, 
        student_id: str, 
        data: StudentUpdate
    ) -> Student:
        """تحديث بيانات الطالب."""
        student = await self.repo.get_by_id(student_id)
        if not student:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        # تحديث الحقول
        update_data = data.model_dump(exclude_unset=True)
        student = await self.repo.update(student_id, update_data)
        
        return student

    # ============================================================
    # 5️⃣ حذف الطالب (تعطيل)
    # ============================================================

    async def delete_student(self, student_id: str) -> None:
        """حذف الطالب (تعطيل فقط)."""
        student = await self.repo.get_by_id(student_id)
        if not student:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        # تعطيل الطالب بدلاً من حذفه
        await self.repo.update(student_id, {"is_active": False})

    # ============================================================
    # 6️⃣ قائمة الطلاب مع البحث والترقيم - ✅ FIXED
    # ============================================================

    async def list_students(
        self,
        school_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        section_id: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> Dict[str, Any]:
        """جلب قائمة الطلاب مع البحث والترقيم."""
        skip = (page - 1) * page_size
        
        # بناء الاستعلام باستخدام select()
        stmt = select(Student).where(Student.school_id == school_id)
        
        if is_active is not None:
            stmt = stmt.where(Student.is_active == is_active)
        
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
        
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Student.student_number.ilike(search_term),
                    Student.first_name.ilike(search_term),
                    Student.last_name.ilike(search_term),
                    Student.full_name.ilike(search_term),
                    Student.national_id.ilike(search_term),
                )
            )
        
        # حساب العدد الإجمالي - ✅ FIXED
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # جلب النتائج مع الترقيم - ✅ FIXED
        stmt = stmt.offset(skip).limit(page_size)
        result = await self.db.execute(stmt)
        students = result.scalars().all()
        
        # تحويل النتائج إلى قائمة مع التفاصيل
        items = []
        for student in students:
            # جلب تفاصيل الشعبة
            section_name = None
            if student.section_id:
                section = await self.db.get(Section, student.section_id)
                if section:
                    section_name = section.name
            
            items.append({
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "national_id": student.national_id,
                "gender": student.gender,
                "guardian_name": student.guardian_name,
                "guardian_phone": student.guardian_phone,
                "guardian_email": student.guardian_email,
                "section_id": student.section_id,
                "section_name": section_name,
                "is_active": student.is_active,
                "created_at": student.created_at,
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    # ============================================================
    # 7️⃣ جلب الطلاب حسب الشعبة - ✅ FIXED
    # ============================================================

    async def get_by_section(
        self,
        school_id: str,
        section_id: str,
        is_active: bool = True,
    ) -> List[Student]:
        """جلب الطلاب حسب الشعبة."""
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.section_id == section_id,
            Student.is_active == is_active
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # 8️⃣ جلب الطلاب مع التفاصيل (للتكامل مع Attendance) - ✅ FIXED
    # ============================================================

    async def get_students_with_details(
        self,
        school_id: str,
        section_id: Optional[str] = None,
        is_active: Optional[bool] = True,
        include_attendance: bool = False,
        date: Optional[str] = None,
        period_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        جلب الطلاب مع تفاصيل إضافية من Academics Routes.
        هذه الدالة تستخدم لتكامل Attendance مع Students و Academics.
        """
        # بناء الاستعلام
        stmt = select(Student).where(Student.school_id == school_id)
        
        if is_active is not None:
            stmt = stmt.where(Student.is_active == is_active)
        
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
        
        result = await self.db.execute(stmt)
        students = result.scalars().all()
        
        result_data = []
        for student in students:
            # جلب التفاصيل من Academics
            section_name = None
            grade_name = None
            stage_name = None
            academic_year_name = None
            
            if student.section_id:
                section = await self.db.get(Section, student.section_id)
                if section:
                    section_name = section.name
                    if section.grade_id:
                        grade = await self.db.get(Grade, section.grade_id)
                        if grade:
                            grade_name = grade.name
                            if grade.stage_id:
                                stage = await self.db.get(Stage, grade.stage_id)
                                if stage:
                                    stage_name = stage.name
            
            if student.year_id:
                year = await self.db.get(AcademicYear, student.year_id)
                if year:
                    academic_year_name = year.name
            
            student_data = {
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "gender": student.gender,
                "birth_date": student.birth_date,
                "guardian_name": student.guardian_name,
                "guardian_phone": student.guardian_phone,
                "guardian_email": student.guardian_email,
                "address": student.address,
                "is_active": student.is_active,
                "section_id": student.section_id,
                "year_id": student.year_id,
                # --- معلومات من Academics Routes ---
                "section_name": section_name,
                "grade_name": grade_name,
                "stage_name": stage_name,
                "academic_year": academic_year_name,
                # --- حالة الحضور (إذا طلب) ---
                "attendance_status": None,
                "attendance_id": None,
                "has_attendance": False,
                "attendance_note": None,
            }
            
            # جلب حالة الحضور إذا طلب
            if include_attendance and date:
                from app.models.attendance import StudentAttendance
                att_stmt = select(StudentAttendance).where(
                    StudentAttendance.student_id == student.id,
                    StudentAttendance.date == date
                )
                if period_id:
                    att_stmt = att_stmt.where(StudentAttendance.period_id == period_id)
                
                att_result = await self.db.execute(att_stmt)
                attendance = att_result.scalar_one_or_none()
                
                if attendance:
                    student_data["attendance_status"] = attendance.status
                    student_data["attendance_id"] = attendance.id
                    student_data["has_attendance"] = True
                    student_data["attendance_note"] = attendance.note
            
            result_data.append(student_data)
        
        return result_data

    # ============================================================
    # 9️⃣ حساب عدد الطلاب - ✅ FIXED
    # ============================================================

    async def count_students(
        self,
        school_id: str,
        section_id: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> int:
        """حساب عدد الطلاب."""
        stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
        )
        if is_active is not None:
            stmt = stmt.where(Student.is_active == is_active)
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
        
        return await self.db.scalar(stmt) or 0

    # ============================================================
    # 🔟 نقل طالب بين الشعب (Transfer)
    # ============================================================

    async def transfer_student(
        self,
        school_id: str,
        req: TransferRequest
    ) -> Dict[str, Any]:
        """
        نقل طالب بين الشعب.
        
        Args:
            school_id: معرف المدرسة
            req: بيانات النقل (student_id, from_section_id, to_section_id, year_id)
        
        Returns:
            Dict: نتيجة النقل
        """
        # التحقق من وجود الطالب
        student = await self.repo.get_by_id(req.student_id)
        if not student:
            raise NotFoundException(f"الطالب {req.student_id} غير موجود")
        
        # التحقق من أن الطالب ينتمي لنفس المدرسة
        if student.school_id != school_id:
            raise ValidationException("الطالب لا ينتمي إلى مدرستك")
        
        # التحقق من أن الطالب نشط
        if not student.is_active:
            raise ValidationException("الطالب غير نشط")
        
        # التحقق من الشعبة الجديدة (إذا تم تحديدها)
        if req.to_section_id:
            section = await self.db.get(Section, req.to_section_id)
            if not section:
                raise NotFoundException(f"الشعبة {req.to_section_id} غير موجودة")
            
            if section.school_id != school_id:
                raise ValidationException("الشعبة لا تنتمي إلى مدرستك")
            
            if not section.is_active:
                raise ValidationException("الشعبة غير نشطة")
        
        # تسجيل النقل
        old_section_id = student.section_id
        
        # تحديث الطالب
        update_data = {
            "section_id": req.to_section_id,
        }
        if req.year_id:
            update_data["year_id"] = req.year_id
        
        updated_student = await self.repo.update(req.student_id, update_data)
        
        # جلب تفاصيل الشعبة القديمة والجديدة
        old_section_name = None
        if old_section_id:
            old_section = await self.db.get(Section, old_section_id)
            if old_section:
                old_section_name = old_section.name
        
        new_section_name = None
        if req.to_section_id:
            new_section = await self.db.get(Section, req.to_section_id)
            if new_section:
                new_section_name = new_section.name
        
        return {
            "student_id": req.student_id,
            "student_name": updated_student.full_name,
            "from_section_id": old_section_id,
            "from_section_name": old_section_name,
            "to_section_id": req.to_section_id,
            "to_section_name": new_section_name,
            "year_id": req.year_id,
        }

    # ============================================================
    # 1️⃣1️⃣ البحث عن طالب - ✅ FIXED
    # ============================================================

    async def search_students(
        self,
        school_id: str,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """البحث عن طالب بالاسم أو رقم الطالب."""
        search_term = f"%{query}%"
        
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.is_active == True,
            or_(
                Student.student_number.ilike(search_term),
                Student.first_name.ilike(search_term),
                Student.last_name.ilike(search_term),
                Student.full_name.ilike(search_term),
            )
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        students = result.scalars().all()
        
        return [
            {
                "id": s.id,
                "student_number": s.student_number,
                "full_name": s.full_name,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "section_id": s.section_id,
                "is_active": s.is_active,
            }
            for s in students
        ]

    # ============================================================
    # 1️⃣2️⃣ إحصائيات الطلاب - ✅ FIXED
    # ============================================================

    async def get_stats(
        self,
        school_id: str,
        section_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """جلب إحصائيات الطلاب."""
        # العدد الإجمالي
        total_stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        )
        if section_id:
            total_stmt = total_stmt.where(Student.section_id == section_id)
        total = await self.db.scalar(total_stmt) or 0
        
        # عدد الذكور
        males_stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == True,
            Student.gender == "male"
        )
        if section_id:
            males_stmt = males_stmt.where(Student.section_id == section_id)
        males = await self.db.scalar(males_stmt) or 0
        
        # عدد الإناث
        females_stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == True,
            Student.gender == "female"
        )
        if section_id:
            females_stmt = females_stmt.where(Student.section_id == section_id)
        females = await self.db.scalar(females_stmt) or 0
        
        # عدد الطلاب حسب الشعبة
        sections_stats = []
        if not section_id:
            sections_stmt = select(Section).where(
                Section.school_id == school_id,
                Section.is_active == True
            )
            sections_result = await self.db.execute(sections_stmt)
            sections = sections_result.scalars().all()
            
            for section in sections:
                count_stmt = select(func.count()).select_from(Student).where(
                    Student.section_id == section.id,
                    Student.is_active == True
                )
                count = await self.db.scalar(count_stmt) or 0
                
                if count > 0:
                    sections_stats.append({
                        "section_id": section.id,
                        "section_name": section.name,
                        "student_count": count,
                    })
        
        return {
            "total": total,
            "males": males,
            "females": females,
            "sections": sections_stats,
            "school_id": school_id,
            "section_id": section_id,
        }
