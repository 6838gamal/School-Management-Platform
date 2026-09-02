"""Student service for managing student data."""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.core.exceptions import NotFoundException, ConflictException, ValidationException
from app.models.students import Student, StudentEnrollment
from app.models.academics import Section, Grade, Stage, AcademicYear, Period
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
        """✅ إنشاء طالب جديد مع الحقول الأكاديمية."""
        # التحقق من عدم تكرار رقم الطالب
        existing = await self.repo.get_by_student_number(data.student_number, school_id)
        if existing:
            raise ConflictException(f"رقم الطالب {data.student_number} موجود بالفعل")
        
        # التحقق من عدم تكرار الرقم الوطني
        if data.national_id:
            existing = await self.repo.get_by_national_id(data.national_id, school_id)
            if existing:
                raise ConflictException(f"الرقم الوطني {data.national_id} موجود بالفعل")
        
        # ✅ التحقق من صحة الحقول الأكاديمية إذا تم توفيرها
        if data.section_id:
            section = await self._get_section(data.section_id, school_id)
            if not section:
                raise NotFoundException(f"الشعبة {data.section_id} غير موجودة")
            
            # التحقق من أن الشعبة تنتمي للمدرسة
            if section.school_id != school_id:
                raise ValidationException("الشعبة لا تنتمي إلى مدرستك")
        
        if data.grade_id:
            grade = await self._get_grade(data.grade_id, school_id)
            if not grade:
                raise NotFoundException(f"الصف {data.grade_id} غير موجود")
            
            if grade.school_id != school_id:
                raise ValidationException("الصف لا ينتمي إلى مدرستك")
        
        if data.year_id:
            year = await self._get_year(data.year_id, school_id)
            if not year:
                raise NotFoundException(f"السنة الدراسية {data.year_id} غير موجودة")
            
            if year.school_id != school_id:
                raise ValidationException("السنة الدراسية لا تنتمي إلى مدرستك")
        
        # ✅ إنشاء الطالب مع جميع الحقول
        student = await self.repo.create(
            school_id=school_id,
            student_number=data.student_number,
            national_id=data.national_id,
            first_name=data.first_name,
            last_name=data.last_name,
            first_name_ar=data.first_name_ar,
            last_name_ar=data.last_name_ar,
            gender=data.gender,
            birth_date=data.birth_date.isoformat() if data.birth_date else None,
            nationality=data.nationality,
            guardian_name=data.guardian_name,
            guardian_phone=data.guardian_phone,
            guardian_email=data.guardian_email,
            guardian_relation=data.guardian_relation,
            phone=data.phone,
            address=data.address,
            photo_url=data.photo_url,
            # ✅ الحقول الأكاديمية
            year_id=data.year_id,
            grade_id=data.grade_id,
            section_id=data.section_id,
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
        """✅ جلب تفاصيل الطالب مع معلومات من Academics."""
        # جلب بيانات الطالب
        student = await self.repo.get_by_id(student_id)
        if not student:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        # ✅ جلب التفاصيل الإضافية من الحقول المباشرة
        section_name = None
        grade_name = None
        stage_name = None
        year_name = None
        
        
        # جلب اسم الشعبة
        if student.section_id:
            section = await self._get_section(student.section_id)
            if section:
                section_name = section.name
        
        # جلب اسم الصف
        if student.grade_id:
            grade = await self._get_grade(student.grade_id)
            if grade:
                grade_name = grade.name
                
                # جلب اسم المرحلة
                if grade.stage_id:
                    stage = await self._get_stage(grade.stage_id)
                    if stage:
                        stage_name = stage.name
        
        # جلب اسم السنة
        if student.year_id:
            year = await self._get_year(student.year_id)
            if year:
                year_name = year.name
        
        
        
        # ✅ جلب التسجيل النشط (اختياري)
        current_enrollment = None
        try:
            enrollment_stmt = select(StudentEnrollment).where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.status == "active"
            ).limit(1)
            enrollment_result = await self.db.execute(enrollment_stmt)
            current_enrollment = enrollment_result.scalar_one_or_none()
        except Exception:
            pass
        
        return {
            "id": student.id,
            "student_number": student.student_number,
            "national_id": student.national_id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "first_name_ar": student.first_name_ar,
            "last_name_ar": student.last_name_ar,
            "full_name": student.full_name,
            "full_name_ar": student.full_name_ar,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "age": student.age,
            "nationality": student.nationality,
            "guardian_name": student.guardian_name,
            "guardian_phone": student.guardian_phone,
            "guardian_email": student.guardian_email,
            "guardian_relation": student.guardian_relation,
            "phone": student.phone,
            "address": student.address,
            "photo_url": student.photo_url,
            "is_active": student.is_active,
            "enrollment_status": student.enrollment_status,
            # ✅ الحقول الأكاديمية
            "year_id": student.year_id,
            "year_name": year_name,
            "grade_id": student.grade_id,
            "grade_name": grade_name,
            "section_id": student.section_id,
            "section_name": section_name,
            "period_name": period_name,
            "stage_name": stage_name,
            "current_enrollment": current_enrollment,
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
        """✅ تحديث بيانات الطالب مع الحقول الأكاديمية."""
        student = await self.repo.get_by_id(student_id)
        if not student:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        # ✅ التحقق من صحة الحقول الأكاديمية إذا تم توفيرها
        if data.section_id is not None:
            if data.section_id:
                section = await self._get_section(data.section_id, student.school_id)
                if not section:
                    raise NotFoundException(f"الشعبة {data.section_id} غير موجودة")
                if section.school_id != student.school_id:
                    raise ValidationException("الشعبة لا تنتمي إلى مدرستك")
            # إذا كانت None، نتركها None (إزالة الشعبة)
        
        if data.grade_id is not None:
            if data.grade_id:
                grade = await self._get_grade(data.grade_id, student.school_id)
                if not grade:
                    raise NotFoundException(f"الصف {data.grade_id} غير موجود")
                if grade.school_id != student.school_id:
                    raise ValidationException("الصف لا ينتمي إلى مدرستك")
        
        if data.year_id is not None:
            if data.year_id:
                year = await self._get_year(data.year_id, student.school_id)
                if not year:
                    raise NotFoundException(f"السنة الدراسية {data.year_id} غير موجودة")
                if year.school_id != student.school_id:
                    raise ValidationException("السنة الدراسية لا تنتمي إلى مدرستك")
        
        # تحديث الحقول
        update_data = data.model_dump(exclude_unset=True)
        
        # تحويل birth_date إذا كان موجوداً
        if 'birth_date' in update_data and update_data['birth_date']:
            update_data['birth_date'] = update_data['birth_date'].isoformat()
        
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
    # 6️⃣ قائمة الطلاب مع البحث والترقيم
    # ============================================================

    async def list_students(
        self,
        school_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        year_id: Optional[str] = None,
        grade_id: Optional[str] = None,
        section_id: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> Dict[str, Any]:
        """✅ جلب قائمة الطلاب مع البحث والترقيم والتصفية."""
        
        # استخدام الـ Repository مع التصفية
        students, total = await self.repo.list_by_school(
            school_id=school_id,
            page=page,
            page_size=page_size,
            search=search,
            year_id=year_id,
            grade_id=grade_id,
            section_id=section_id,
        )
        
        # تحويل النتائج إلى قائمة مع التفاصيل
        items = []
        for student in students:
            # جلب الأسماء للعرض
            section_name = None
            grade_name = None
            year_name = None
            
            if student.section_id:
                section = await self._get_section(student.section_id)
                if section:
                    section_name = section.name
            
            if student.grade_id:
                grade = await self._get_grade(student.grade_id)
                if grade:
                    grade_name = grade.name
            
            if student.year_id:
                year = await self._get_year(student.year_id)
                if year:
                    year_name = year.name
            
            items.append({
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name,
                "full_name_ar": student.full_name_ar,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "first_name_ar": student.first_name_ar,
                "last_name_ar": student.last_name_ar,
                "national_id": student.national_id,
                "gender": student.gender,
                "guardian_name": student.guardian_name,
                "guardian_phone": student.guardian_phone,
                "guardian_email": student.guardian_email,
                "phone": student.phone,
                "address": student.address,
                "photo_url": student.photo_url,
                "is_active": student.is_active,
                "enrollment_status": student.enrollment_status,
                # ✅ الحقول الأكاديمية
                "year_id": student.year_id,
                "year_name": year_name,
                "grade_id": student.grade_id,
                "grade_name": grade_name,
                "section_id": student.section_id,
                "section_name": section_name,
                
                "created_at": student.created_at,
                "updated_at": student.updated_at,
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    # ============================================================
    # 7️⃣ جلب الطلاب حسب الشعبة
    # ============================================================

    async def get_by_section(
        self,
        school_id: str,
        section_id: str,
        is_active: bool = True,
        year_id: Optional[str] = None,
    ) -> List[Student]:
        """✅ جلب الطلاب حسب الشعبة مباشرة."""
        return await self.repo.list_by_section(
            school_id=school_id,
            section_id=section_id,
            is_active=is_active,
            year_id=year_id,
        )

    # ============================================================
    # 8️⃣ جلب الطلاب حسب الصف
    # ============================================================

    async def get_by_grade(
        self,
        school_id: str,
        grade_id: str,
        is_active: bool = True,
        year_id: Optional[str] = None,
    ) -> List[Student]:
        """✅ جلب الطلاب حسب الصف."""
        return await self.repo.list_by_grade(
            school_id=school_id,
            grade_id=grade_id,
            is_active=is_active,
            year_id=year_id,
        )

    # ============================================================
    # 9️⃣ جلب الطلاب حسب السنة
    # ============================================================

    async def get_by_year(
        self,
        school_id: str,
        year_id: str,
        is_active: bool = True,
    ) -> List[Student]:
        """✅ جلب الطلاب حسب السنة الدراسية."""
        return await self.repo.list_by_year(
            school_id=school_id,
            year_id=year_id,
            is_active=is_active,
        )

    # ============================================================
    # 🔟 جلب الطلاب مع التفاصيل (للتكامل مع Attendance)
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
        ✅ جلب الطلاب مع تفاصيل إضافية من Academics.
        هذه الدالة تستخدم لتكامل Attendance مع Students و Academics.
        """
        # جلب الطلاب
        students = await self.repo.list_by_section(
            school_id=school_id,
            section_id=section_id or "",
            is_active=is_active if is_active is not None else True,
        ) if section_id else await self.repo.list_by_school(school_id, 1, 1000, None)[0]
        
        result_data = []
        for student in students:
            # جلب التفاصيل
            section_name = None
            grade_name = None
            stage_name = None
            year_name = None
            
            if student.section_id:
                section = await self._get_section(student.section_id)
                if section:
                    section_name = section.name
                    
                    if section.grade_id:
                        grade = await self._get_grade(section.grade_id)
                        if grade:
                            grade_name = grade.name
                            
                            if grade.stage_id:
                                stage = await self._get_stage(grade.stage_id)
                                if stage:
                                    stage_name = stage.name
            
            if student.year_id:
                year = await self._get_year(student.year_id)
                if year:
                    year_name = year.name
            
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
                # ✅ الحقول الأكاديمية
                "year_id": student.year_id,
                "year_name": year_name,
                "grade_id": student.grade_id,
                "grade_name": grade_name,
                "section_id": student.section_id,
                "section_name": section_name,
                
                "stage_name": stage_name,
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
    # 1️⃣1️⃣ حساب عدد الطلاب
    # ============================================================

    async def count_students(
        self,
        school_id: str,
        section_id: Optional[str] = None,
        grade_id: Optional[str] = None,
        year_id: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> int:
        """✅ حساب عدد الطلاب مع خيارات التصفية."""
        return await self.repo.count(
            school_id=school_id,
            section_id=section_id,
            grade_id=grade_id,
            year_id=year_id,
            is_active=is_active,
        )

    # ============================================================
    # 1️⃣2️⃣ نقل طالب بين الشعب (Transfer)
    # ============================================================

    async def transfer_student(
        self,
        school_id: str,
        req: TransferRequest
    ) -> Dict[str, Any]:
        """
        ✅ نقل طالب بين الشعب.
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
        
        # التحقق من الشعبة الجديدة
        if req.to_section_id:
            section = await self._get_section(req.to_section_id, school_id)
            if not section:
                raise NotFoundException(f"الشعبة {req.to_section_id} غير موجودة")
            if section.school_id != school_id:
                raise ValidationException("الشعبة لا تنتمي إلى مدرستك")
        
        # تحديث الطالب بالشعبة الجديدة
        old_section_id = student.section_id
        await self.repo.update(student.id, {
            "section_id": req.to_section_id,
            "year_id": req.academic_year_id,
        })
        
        # جلب أسماء الشعب للعرض
        old_section_name = None
        if old_section_id:
            old_section = await self._get_section(old_section_id)
            if old_section:
                old_section_name = old_section.name
        
        new_section_name = None
        if req.to_section_id:
            new_section = await self._get_section(req.to_section_id)
            if new_section:
                new_section_name = new_section.name
        
        return {
            "student_id": req.student_id,
            "student_name": student.full_name,
            "from_section_id": old_section_id,
            "from_section_name": old_section_name,
            "to_section_id": req.to_section_id,
            "to_section_name": new_section_name,
            "year_id": req.academic_year_id,
        }

    # ============================================================
    # 1️⃣3️⃣ البحث عن طالب
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
                "year_id": s.year_id,
                "grade_id": s.grade_id,
                "section_id": s.section_id,
                "is_active": s.is_active,
            }
            for s in students
        ]

    # ============================================================
    # 1️⃣4️⃣ إحصائيات الطلاب
    # ============================================================

    async def get_stats(
        self,
        school_id: str,
        year_id: Optional[str] = None,
        grade_id: Optional[str] = None,
        section_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """✅ جلب إحصائيات الطلاب مع التصفية حسب السنة والصف والشعبة."""
        
        # العدد الإجمالي للطلاب النشطين
        total = await self.repo.count(
            school_id=school_id,
            year_id=year_id,
            grade_id=grade_id,
            section_id=section_id,
            is_active=True,
        )
        
        # عدد الذكور
        males_stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == True,
            Student.gender == "male"
        )
        if year_id:
            males_stmt = males_stmt.where(Student.year_id == year_id)
        if grade_id:
            males_stmt = males_stmt.where(Student.grade_id == grade_id)
        if section_id:
            males_stmt = males_stmt.where(Student.section_id == section_id)
        males = await self.db.scalar(males_stmt) or 0
        
        # عدد الإناث
        females_stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == True,
            Student.gender == "female"
        )
        if year_id:
            females_stmt = females_stmt.where(Student.year_id == year_id)
        if grade_id:
            females_stmt = females_stmt.where(Student.grade_id == grade_id)
        if section_id:
            females_stmt = females_stmt.where(Student.section_id == section_id)
        females = await self.db.scalar(females_stmt) or 0
        
        # ✅ إحصائيات حسب السنة
        years_stats = []
        if not year_id:
            years = await self._get_years(school_id)
            for year in years:
                count = await self.repo.count(
                    school_id=school_id,
                    year_id=year.id,
                    is_active=True,
                )
                if count > 0:
                    years_stats.append({
                        "year_id": year.id,
                        "year_name": year.name,
                        "student_count": count,
                    })
        
        # ✅ إحصائيات حسب الصف
        grades_stats = []
        if not grade_id:
            grades = await self._get_grades(school_id, year_id)
            for grade in grades:
                count = await self.repo.count(
                    school_id=school_id,
                    grade_id=grade.id,
                    year_id=year_id,
                    is_active=True,
                )
                if count > 0:
                    grades_stats.append({
                        "grade_id": grade.id,
                        "grade_name": grade.name,
                        "student_count": count,
                    })
        
        # إحصائيات حسب الشعبة
        sections_stats = []
        if not section_id:
            sections = await self._get_sections(school_id, year_id, grade_id)
            for section in sections:
                count = await self.repo.count(
                    school_id=school_id,
                    section_id=section.id,
                    year_id=year_id,
                    grade_id=grade_id,
                    is_active=True,
                )
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
            "years": years_stats,
            "grades": grades_stats,
            "sections": sections_stats,
            "school_id": school_id,
            "year_id": year_id,
            "grade_id": grade_id,
            "section_id": section_id,
        }

    # ============================================================
    # 🔧 دوال مساعدة للجلب من Academics
    # ============================================================

    async def _get_section(self, section_id: str, school_id: Optional[str] = None) -> Optional[Section]:
        """جلب الشعبة من قاعدة البيانات."""
        stmt = select(Section).where(Section.id == section_id)
        if school_id:
            stmt = stmt.where(Section.school_id == school_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_grade(self, grade_id: str, school_id: Optional[str] = None) -> Optional[Grade]:
        """جلب الصف من قاعدة البيانات."""
        stmt = select(Grade).where(Grade.id == grade_id)
        if school_id:
            stmt = stmt.where(Grade.school_id == school_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_stage(self, stage_id: str) -> Optional[Stage]:
        """جلب المرحلة من قاعدة البيانات."""
        stmt = select(Stage).where(Stage.id == stage_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_year(self, year_id: str, school_id: Optional[str] = None) -> Optional[AcademicYear]:
        """جلب السنة الدراسية من قاعدة البيانات."""
        stmt = select(AcademicYear).where(AcademicYear.id == year_id)
        if school_id:
            stmt = stmt.where(AcademicYear.school_id == school_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_period(self, period_id: str) -> Optional[Period]:
        """جلب الفصل/الحصة من قاعدة البيانات."""
        stmt = select(Period).where(Period.id == period_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_years(self, school_id: str) -> List[AcademicYear]:
        """جلب جميع السنوات الدراسية للمدرسة."""
        stmt = select(AcademicYear).where(
            AcademicYear.school_id == school_id,
            AcademicYear.is_active == True
        ).order_by(AcademicYear.start_date.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_grades(self, school_id: str, year_id: Optional[str] = None) -> List[Grade]:
        """جلب جميع الصفوف للمدرسة."""
        stmt = select(Grade).where(
            Grade.school_id == school_id,
            Grade.is_active == True
        )
        if year_id:
            stmt = stmt.where(Grade.year_id == year_id)
        stmt = stmt.order_by(Grade.order)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_sections(self, school_id: str, year_id: Optional[str] = None, grade_id: Optional[str] = None) -> List[Section]:
        """جلب جميع الشعب للمدرسة."""
        stmt = select(Section).where(
            Section.school_id == school_id,
            Section.is_active == True
        )
        if year_id:
            stmt = stmt.where(Section.year_id == year_id)
        if grade_id:
            stmt = stmt.where(Section.grade_id == grade_id)
        stmt = stmt.order_by(Section.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
