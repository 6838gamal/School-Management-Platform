from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime

from app.models.students import Student, StudentEnrollment
from app.schemas.students import StudentCreate, StudentUpdate

# استيراد الاستثناءات من ملفك الموجود
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
    ConflictException,
    ForbiddenException,
    UnauthorizedException
)


class StudentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_students(
        self, 
        school_id: str, 
        page: int, 
        page_size: int, 
        search: Optional[str] = None,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """
        قائمة الطلاب مع دعم البحث والترقيم
        
        Args:
            school_id: معرف المدرسة
            page: رقم الصفحة (يبدأ من 1)
            page_size: عدد العناصر في الصفحة
            search: نص البحث
            include_inactive: تضمين الطلاب غير النشطين
            
        Returns:
            قاموس يحتوي على العناصر والإجمالي
        """
        # بناء شرط البحث الأساسي
        conditions = [Student.school_id == school_id]
        
        if not include_inactive:
            conditions.append(Student.is_active == True)
        
        query = select(Student).where(and_(*conditions))
        count_query = select(func.count()).select_from(Student).where(and_(*conditions))
        
        # إضافة شرط البحث
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            search_filter = or_(
                Student.first_name.ilike(search_term),
                Student.last_name.ilike(search_term),
                Student.student_number.ilike(search_term),
                Student.national_id.ilike(search_term)
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # إضافة التحميل المسبق للعلاقات
        query = query.options(
            selectinload(Student.enrollments).selectinload(StudentEnrollment.year),
            selectinload(Student.enrollments).selectinload(StudentEnrollment.section)
        )
        
        # ترتيب النتائج
        query = query.order_by(Student.last_name, Student.first_name)
        
        # تطبيق الترقيم
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # تنفيذ الاستعلامات
        result = await self.db.execute(query)
        students = result.scalars().all()
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        return {
            "items": students, 
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }

    async def get_student_detail(self, student_id: str) -> Dict[str, Any]:
        """
        الحصول على تفاصيل الطالب مع جميع المعلومات المرتبطة
        
        Args:
            student_id: معرف الطالب
            
        Returns:
            قاموس يحتوي على جميع تفاصيل الطالب
        """
        query = select(Student).where(Student.id == student_id).options(
            selectinload(Student.enrollments).options(
                joinedload(StudentEnrollment.year),
                joinedload(StudentEnrollment.section)
            )
        )
        result = await self.db.execute(query)
        student = result.scalar_one_or_none()
        
        if not student:
            raise NotFoundException("الطالب غير موجود")
        
        # تحويل إلى قاموس مع معلومات إضافية
        detail = {
            "id": student.id,
            "school_id": student.school_id,
            "student_number": student.student_number,
            "national_id": student.national_id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": student.full_name,
            "display_name": student.display_name,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "guardian_name": student.guardian_name,
            "guardian_phone": student.guardian_phone,
            "guardian_email": student.guardian_email,
            "address": student.address,
            "photo_url": student.photo_url,
            "is_active": student.is_active,
            "created_at": student.created_at.isoformat() if hasattr(student, 'created_at') and student.created_at else None,
            "updated_at": student.updated_at.isoformat() if hasattr(student, 'updated_at') and student.updated_at else None,
            "enrollments": []
        }
        
        # إضافة معلومات التسجيل
        for enrollment in student.enrollments:
            enrollment_data = {
                "id": enrollment.id,
                "student_id": enrollment.student_id,
                "school_id": enrollment.school_id,
                "year_id": enrollment.year_id,
                "section_id": enrollment.section_id,
                "status": enrollment.status,
                "enrolled_at": enrollment.enrolled_at,
                "ended_at": enrollment.ended_at,
                "year_name": enrollment.year.name if hasattr(enrollment, 'year') and enrollment.year else None,
                "section_name": enrollment.section.name if hasattr(enrollment, 'section') and enrollment.section else None,
            }
            detail["enrollments"].append(enrollment_data)
        
        # إضافة year_id و section_id من أحدث تسجيل نشط
        active_enrollments = [e for e in student.enrollments if e.status == "active"]
        active_enrollment = active_enrollments[0] if active_enrollments else None
        
        if not active_enrollment and student.enrollments:
            # إذا لم يكن هناك تسجيل نشط، نأخذ آخر تسجيل
            active_enrollment = student.enrollments[-1]
        
        if active_enrollment:
            detail["year_id"] = active_enrollment.year_id
            detail["section_id"] = active_enrollment.section_id
            detail["year_name"] = active_enrollment.year.name if hasattr(active_enrollment, 'year') and active_enrollment.year else None
            detail["section_name"] = active_enrollment.section.name if hasattr(active_enrollment, 'section') and active_enrollment.section else None
        
        return detail

    async def get_student(self, student_id: str) -> Optional[Student]:
        """الحصول على كائن الطالب بدون تحميل العلاقات الإضافية"""
        result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        return result.scalar_one_or_none()

    async def get_student_by_number(self, student_number: str, school_id: str) -> Optional[Student]:
        """الحصول على طالب بواسطة رقم الطالب"""
        result = await self.db.execute(
            select(Student).where(
                Student.school_id == school_id,
                Student.student_number == student_number
            )
        )
        return result.scalar_one_or_none()

    async def create_student(self, data: StudentCreate, user_id: str, school_id: str) -> Student:
        """
        إنشاء طالب جديد
        
        Args:
            data: بيانات الطالب
            user_id: معرف المستخدم المنشئ
            school_id: معرف المدرسة (يأتي من المستخدم الحالي)
            
        Returns:
            كائن الطالب المنشأ
        """
        # التحقق من صحة البيانات
        await self._validate_student_data(data, school_id)
        
        # التحقق من عدم تكرار رقم الطالب
        existing = await self.get_student_by_number(data.student_number, school_id)
        if existing:
            raise ConflictException(f"رقم الطالب '{data.student_number}' موجود بالفعل")
        
        # التحقق من عدم تكرار الرقم الوطني
        if data.national_id:
            existing = await self.db.execute(
                select(Student).where(
                    Student.school_id == school_id,
                    Student.national_id == data.national_id
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictException(f"الرقم الوطني '{data.national_id}' موجود بالفعل")
        
        # إنشاء كائن الطالب
        student = Student(
            school_id=school_id,
            student_number=data.student_number,
            national_id=data.national_id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            gender=data.gender,
            birth_date=data.birth_date,
            guardian_name=data.guardian_name.strip() if data.guardian_name else None,
            guardian_phone=data.guardian_phone.strip() if data.guardian_phone else None,
            guardian_email=data.guardian_email.strip().lower() if data.guardian_email else None,
            address=data.address.strip() if data.address else None,
            is_active=True,
            created_by=user_id,
            updated_by=user_id
        )
        
        self.db.add(student)
        await self.db.flush()
        
        # إنشاء تسجيل إذا تم تحديد year_id
        if data.year_id:
            enrollment = StudentEnrollment(
                student_id=student.id,
                school_id=school_id,  # ✅ نفس school_id من المستخدم
                year_id=data.year_id,
                section_id=data.section_id,
                status="active",
                enrolled_at=datetime.now().isoformat(),
                ended_at=None,
                created_by=user_id,
                updated_by=user_id
            )
            self.db.add(enrollment)
        
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def update_student(self, student_id: str, data: StudentUpdate) -> Student:
        """
        تحديث بيانات الطالب
        
        Args:
            student_id: معرف الطالب
            data: بيانات التحديث
            
        Returns:
            كائن الطالب المحدث
        """
        student = await self.get_student(student_id)
        if not student:
            raise NotFoundException("الطالب غير موجود")
        
        update_data = data.model_dump(exclude_unset=True)
        
        # التحقق من صحة البيانات المحدثة
        if "first_name" in update_data and update_data["first_name"]:
            update_data["first_name"] = update_data["first_name"].strip()
            if len(update_data["first_name"]) < 2:
                raise ValidationException("الاسم الأول يجب أن يكون حرفين على الأقل")
        
        if "last_name" in update_data and update_data["last_name"]:
            update_data["last_name"] = update_data["last_name"].strip()
            if len(update_data["last_name"]) < 2:
                raise ValidationException("اسم العائلة يجب أن يكون حرفين على الأقل")
        
        # التحقق من عدم تكرار الرقم الوطني (إذا تم تغييره)
        if "national_id" in update_data and update_data["national_id"]:
            update_data["national_id"] = update_data["national_id"].strip()
            existing = await self.db.execute(
                select(Student).where(
                    Student.school_id == student.school_id,
                    Student.national_id == update_data["national_id"],
                    Student.id != student_id
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictException(f"الرقم الوطني '{update_data['national_id']}' موجود بالفعل")
        
        # تحديث الحقول
        for key, value in update_data.items():
            if value is not None and key not in ["id", "school_id", "student_number", "created_at", "created_by"]:
                setattr(student, key, value)
        
        # تحديث معلومات التعديل
        if hasattr(student, 'updated_at'):
            student.updated_at = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def delete_student(self, student_id: str) -> None:
        """
        حذف الطالب وجميع سجلاته المرتبطة
        
        Args:
            student_id: معرف الطالب
        """
        student = await self.get_student(student_id)
        if not student:
            raise NotFoundException("الطالب غير موجود")
        
        # حذف سجلات التسجيل المرتبطة
        enrollments = await self.db.execute(
            select(StudentEnrollment).where(StudentEnrollment.student_id == student_id)
        )
        for enrollment in enrollments.scalars().all():
            await self.db.delete(enrollment)
        
        # حذف الطالب
        await self.db.delete(student)
        await self.db.commit()

    async def deactivate_student(self, student_id: str) -> Student:
        """
        إلغاء تنشيط الطالب (بدلاً من الحذف)
        
        Args:
            student_id: معرف الطالب
            
        Returns:
            كائن الطالب المحدث
        """
        student = await self.get_student(student_id)
        if not student:
            raise NotFoundException("الطالب غير موجود")
        
        student.is_active = False
        if hasattr(student, 'updated_at'):
            student.updated_at = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def _validate_student_data(self, data: StudentCreate, school_id: str) -> None:
        """
        التحقق من صحة بيانات الطالب
        
        Args:
            data: بيانات الطالب
            school_id: معرف المدرسة
        """
        # التحقق من رقم الطالب
        if not data.student_number or len(data.student_number.strip()) < 3:
            raise ValidationException("رقم الطالب يجب أن يكون 3 أحرف على الأقل")
        
        # التحقق من الاسم الأول
        if not data.first_name or len(data.first_name.strip()) < 2:
            raise ValidationException("الاسم الأول يجب أن يكون حرفين على الأقل")
        
        # التحقق من اسم العائلة
        if not data.last_name or len(data.last_name.strip()) < 2:
            raise ValidationException("اسم العائلة يجب أن يكون حرفين على الأقل")
        
        # التحقق من البريد الإلكتروني لولي الأمر (إذا تم توفيره)
        if data.guardian_email and "@" not in data.guardian_email:
            raise ValidationException("البريد الإلكتروني لولي الأمر غير صحيح")
        
        # التحقق من هاتف ولي الأمر (إذا تم توفيره)
        if data.guardian_phone:
            phone = data.guardian_phone.strip()
            if len(phone) < 8 or not phone.replace("+", "").replace("-", "").replace(" ", "").isdigit():
                raise ValidationException("رقم هاتف ولي الأمر غير صحيح")
        
        # التحقق من year_id إذا تم توفيره
        if data.year_id:
            from app.models.academic import AcademicYear
            year = await self.db.execute(
                select(AcademicYear).where(
                    AcademicYear.id == data.year_id,
                    AcademicYear.school_id == school_id
                )
            )
            if not year.scalar_one_or_none():
                raise ValidationException("السنة الدراسية غير موجودة")

    async def get_students_by_section(self, section_id: str, school_id: str) -> List[Student]:
        """الحصول على جميع الطلاب في شعبة معينة"""
        query = select(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        ).join(StudentEnrollment).where(
            StudentEnrollment.section_id == section_id,
            StudentEnrollment.status == "active"
        ).options(
            selectinload(Student.enrollments)
        ).order_by(Student.last_name, Student.first_name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_students_by_year(self, year_id: str, school_id: str) -> List[Student]:
        """الحصول على جميع الطلاب في سنة دراسية معينة"""
        query = select(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        ).join(StudentEnrollment).where(
            StudentEnrollment.year_id == year_id,
            StudentEnrollment.status == "active"
        ).options(
            selectinload(Student.enrollments)
        ).order_by(Student.last_name, Student.first_name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_active_students(self, school_id: str) -> int:
        """عدد الطلاب النشطين في المدرسة"""
        result = await self.db.execute(
            select(func.count()).select_from(Student).where(
                Student.school_id == school_id,
                Student.is_active == True
            )
        )
        return result.scalar() or 0

    async def search_students(self, school_id: str, query: str) -> List[Student]:
        """البحث السريع عن الطلاب"""
        if not query or len(query.strip()) < 2:
            return []
        
        search_term = f"%{query.strip()}%"
        conditions = [
            Student.school_id == school_id,
            Student.is_active == True,
            or_(
                Student.first_name.ilike(search_term),
                Student.last_name.ilike(search_term),
                Student.student_number.ilike(search_term),
                Student.national_id.ilike(search_term)
            )
        ]
        
        result = await self.db.execute(
            select(Student).where(and_(*conditions)).limit(10)
        )
        return result.scalars().all()
