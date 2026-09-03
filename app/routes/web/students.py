"""Students web routes — shared pages used by director, deputy, and teacher."""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, File, UploadFile, Query
from fastapi.responses import RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid
import traceback
from datetime import datetime, date
import pandas as pd
import io
import pdfplumber
import json
import re
from pathlib import Path

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.student_service import StudentService
from app.schemas.students import StudentCreate, StudentUpdate
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ValidationException,
    AppException
)
# النماذج
from app.models.students import Student
from app.models.academics import Section, Grade, Stage, AcademicYear, Period

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# 🔴 IMPORTANT: الترتيب مهم جداً!
#    المسارات الثابتة (مثل /new, /import, /export) يجب أن تأتي قبل المسارات الديناميكية (مثل /{student_id})
# ============================================================

# ============================================================
# دالة مساعدة لتحويل البيانات إلى JSON آمن
# ============================================================
def safe_to_json(obj):
    """تحويل الكائنات إلى صيغة JSON آمنة (معالجة التواريخ)"""
    if isinstance(obj, dict):
        return {k: safe_to_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_to_json(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif hasattr(obj, '__str__'):
        return str(obj)
    else:
        return obj


# ============================================================
# دالة مساعدة لمعالجة تاريخ الميلاد
# ============================================================
def parse_birth_date(value):
    """
    معالجة تنسيق تاريخ الميلاد من مصادر مختلفة
    يدعم: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, DD/MM/YYYY, MM/DD/YYYY
    """
    if not value:
        return None
    
    if isinstance(value, date):
        return value.isoformat()
    
    if isinstance(value, datetime):
        return value.date().isoformat()
    
    if isinstance(value, str):
        value = value.strip()
        
        # ✅ إذا كان التنسيق YYYY-MM-DD HH:MM:SS
        if ' ' in value and '-' in value:
            parts = value.split(' ')
            if len(parts) >= 1:
                value = parts[0]
        
        # ✅ إذا كان التنسيق DD/MM/YYYY
        if '/' in value:
            parts = value.split('/')
            if len(parts) == 3:
                try:
                    # محاولة كـ DD/MM/YYYY
                    return f"{parts[2].zfill(4)}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                except:
                    pass
        
        # ✅ إذا كان التنسيق DD-MM-YYYY
        if '-' in value and not value.startswith('20') and not value.startswith('19'):
            parts = value.split('-')
            if len(parts) == 3:
                try:
                    return f"{parts[2].zfill(4)}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                except:
                    pass
        
        # ✅ التحقق من صحة التنسيق YYYY-MM-DD
        try:
            datetime.strptime(value, '%Y-%m-%d')
            return value
        except ValueError:
            pass
        
        # ✅ محاولة استخدام pandas كحل أخير
        try:
            import pandas as pd
            dt = pd.to_datetime(value)
            return dt.strftime('%Y-%m-%d')
        except:
            pass
    
    return None


# ============================================================
# دالة مساعدة لجلب بيانات الفصول والسنوات والصفوف والفترات
# ============================================================
async def get_onboarding_data(db: AsyncSession, school_id: str):
    """
    جلب بيانات الفصول والسنوات والصفوف والفترات للمدرسة
    """
    try:
        # 1. جلب السنوات الدراسية
        years_result = await db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .order_by(AcademicYear.start_date.desc())
        )
        years = years_result.scalars().all()
        
        # 2. جلب الصفوف
        grades_result = await db.execute(
            select(Grade)
            .where(Grade.school_id == school_id)
            .order_by(Grade.order)
        )
        grades = grades_result.scalars().all()
        
        # 3. جلب الشعب مع العلاقات
        sections_result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade)
            )
            .where(Section.school_id == school_id)
            .order_by(Section.name)
        )
        sections = sections_result.scalars().all()
        
        return {
            "years": years,
            "grades": grades,
            "sections": sections
        }
    except Exception as e:
        print(f"⚠️ Error in get_onboarding_data: {str(e)}")
        return {"years": [], "grades": [], "sections": []}


# ============================================================
# دالة مساعدة للحصول على معرف السنة من الاسم
# ============================================================
async def get_year_id_by_name(db: AsyncSession, school_id: str, year_name: str):
    """الحصول على معرف السنة من الاسم"""
    if not year_name:
        return None
    result = await db.execute(
        select(AcademicYear).where(
            AcademicYear.school_id == school_id,
            AcademicYear.name == year_name.strip()
        )
    )
    year = result.scalar_one_or_none()
    return str(year.id) if year else None


# ============================================================
# دالة مساعدة للحصول على معرف الصف من الاسم
# ============================================================
async def get_grade_id_by_name(db: AsyncSession, school_id: str, grade_name: str):
    """الحصول على معرف الصف من الاسم"""
    if not grade_name:
        return None
    result = await db.execute(
        select(Grade).where(
            Grade.school_id == school_id,
            Grade.name == grade_name.strip()
        )
    )
    grade = result.scalar_one_or_none()
    return str(grade.id) if grade else None


# ============================================================
# دالة مساعدة للحصول على معرف الشعبة من الاسم
# ============================================================
async def get_section_id_by_name(db: AsyncSession, school_id: str, section_name: str):
    """الحصول على معرف الشعبة من الاسم"""
    if not section_name:
        return None
    result = await db.execute(
        select(Section).where(
            Section.school_id == school_id,
            Section.name == section_name.strip()
        )
    )
    section = result.scalar_one_or_none()
    return str(section.id) if section else None


# ============================================================
# دالة مساعدة لاستخراج قيمة الحقل من الصف
# ============================================================
def get_field_value(row, field_name: str, column_mappings: dict):
    """الحصول على قيمة الحقل من الصف باستخدام الأسماء المختلفة"""
    for key in column_mappings.get(field_name, [field_name]):
        if key in row:
            value = row[key]
            if isinstance(value, str):
                value = value.strip()
            if value and value != 'nan' and value != 'None' and value != '':
                return value
    return None


# ============================================================
# 📥 POST /students/import - استيراد الطلاب من ملف (محدث)
# ============================================================
@router.post("/import")
async def import_students(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """
    استيراد الطلاب من ملف (CSV, Excel, PDF)
    """
    try:
        # التحقق من الملف
        if not file:
            return JSONResponse({
                'success': False,
                'message': 'لم يتم اختيار ملف',
                'imported': 0,
                'errors': ['لم يتم اختيار ملف']
            }, status_code=400)
        
        filename = file.filename.lower()
        content = await file.read()
        
        if not content:
            return JSONResponse({
                'success': False,
                'message': 'الملف فارغ',
                'imported': 0,
                'errors': ['الملف فارغ']
            }, status_code=400)
        
        # تحديد نوع الملف ومعالجته
        data = []
        errors = []
        
        if filename.endswith('.csv'):
            # قراءة CSV
            try:
                text = content.decode('utf-8')
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                if len(lines) < 2:
                    return JSONResponse({
                        'success': False,
                        'message': 'الملف لا يحتوي على بيانات كافية',
                        'imported': 0,
                        'errors': ['الملف لا يحتوي على بيانات كافية']
                    }, status_code=400)
                
                # استخراج العناوين
                headers = [h.strip() for h in lines[0].split(',')]
                print(f"📋 العناوين المستخرجة: {headers}")
                
                # معالجة الصفوف
                for idx, line in enumerate(lines[1:], start=2):
                    if line.strip():
                        values = [v.strip() for v in line.split(',')]
                        if len(values) == len(headers):
                            row = dict(zip(headers, values))
                            data.append(row)
                        else:
                            errors.append(f"الصف {idx}: عدد الأعمدة غير متطابق (متوقع {len(headers)}, وجد {len(values)})")
                            
            except UnicodeDecodeError:
                # محاولة بترميز آخر
                try:
                    text = content.decode('windows-1256')
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    headers = [h.strip() for h in lines[0].split(',')]
                    for idx, line in enumerate(lines[1:], start=2):
                        if line.strip():
                            values = [v.strip() for v in line.split(',')]
                            if len(values) == len(headers):
                                row = dict(zip(headers, values))
                                data.append(row)
                            else:
                                errors.append(f"الصف {idx}: عدد الأعمدة غير متطابق")
                except Exception as e:
                    errors.append(f"خطأ في قراءة الملف: {str(e)}")
                    
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            # قراءة Excel
            try:
                df = pd.read_excel(io.BytesIO(content), engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
                
                # تحويل DataFrame إلى قائمة من القواميس
                data = df.to_dict('records')
                
                # تحويل جميع القيم إلى سلاسل نصية
                for row in data:
                    for key, value in row.items():
                        if pd.isna(value):
                            row[key] = ''
                        else:
                            row[key] = str(value).strip()
                            
                print(f"📋 العناوين المستخرجة من Excel: {list(data[0].keys()) if data else 'لا توجد بيانات'}")
                
            except Exception as e:
                errors.append(f"خطأ في قراءة ملف Excel: {str(e)}")
                
        elif filename.endswith('.pdf'):
            # قراءة PDF
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    text = ''
                    for page in pdf.pages:
                        text += page.extract_text() or ''
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                data = parse_pdf_data(lines)
                
            except Exception as e:
                errors.append(f"خطأ في قراءة ملف PDF: {str(e)}")
        else:
            return JSONResponse({
                'success': False,
                'message': 'نوع الملف غير مدعوم. يرجى استخدام CSV, Excel, أو PDF',
                'imported': 0,
                'errors': ['نوع الملف غير مدعوم']
            }, status_code=400)
        
        # التحقق من وجود بيانات
        if not data:
            return JSONResponse({
                'success': False,
                'message': 'لم يتم العثور على بيانات في الملف',
                'imported': 0,
                'errors': errors or ['لم يتم العثور على بيانات في الملف']
            }, status_code=400)
        
        print(f"📊 عدد الصفوف المستخرجة: {len(data)}")
        
        # ============================================================
        # ✅ أسماء الأعمدة المدعومة (عربي وإنجليزي)
        # ============================================================
        column_mappings = {
            'student_number': ['رقم الطالب', 'student_number', 'Student Number', 'StudentNumber', 'الرقم'],
            'national_id': ['الرقم الوطني', 'national_id', 'National ID', 'NationalID', 'الهوية'],
            'first_name': ['الاسم الأول', 'first_name', 'First Name', 'FirstName', 'الاسم'],
            'last_name': ['اسم العائلة', 'last_name', 'Last Name', 'LastName', 'العائلة', 'اللقب'],
            'gender': ['الجنس', 'gender', 'Gender'],
            'birth_date': ['تاريخ الميلاد', 'birth_date', 'Birth Date', 'BirthDate', 'تاريخ الميلاد'],
            'guardian_name': ['اسم ولي الأمر', 'guardian_name', 'Guardian Name', 'GuardianName', 'ولي الأمر'],
            'guardian_phone': ['هاتف ولي الأمر', 'guardian_phone', 'Guardian Phone', 'GuardianPhone', 'هاتف ولي'],
            'guardian_email': ['البريد الإلكتروني لولي الأمر', 'guardian_email', 'Guardian Email', 'GuardianEmail', 'بريد ولي'],
            'address': ['العنوان', 'address', 'Address'],
            'year_name': ['السنة الدراسية', 'year', 'Year', 'السنة', 'academic_year'],
            'grade_name': ['الصف', 'grade', 'Grade', 'المرحلة'],
            'section_name': ['الشعبة', 'section', 'Section', 'الفصل'],
        }
        
        # ============================================================
        # ✅ معالجة البيانات واستيرادها
        # ============================================================
        
        imported_count = 0
        import_errors = []
        
        for idx, row in enumerate(data, start=2):
            try:
                # استخراج البيانات
                student_number = get_field_value(row, 'student_number', column_mappings)
                national_id = get_field_value(row, 'national_id', column_mappings)
                first_name = get_field_value(row, 'first_name', column_mappings)
                last_name = get_field_value(row, 'last_name', column_mappings)
                gender = get_field_value(row, 'gender', column_mappings)
                
                # ✅ معالجة تاريخ الميلاد بشكل صحيح
                birth_date_raw = get_field_value(row, 'birth_date', column_mappings)
                birth_date = parse_birth_date(birth_date_raw) if birth_date_raw else None
                
                guardian_name = get_field_value(row, 'guardian_name', column_mappings)
                guardian_phone = get_field_value(row, 'guardian_phone', column_mappings)
                guardian_email = get_field_value(row, 'guardian_email', column_mappings)
                address = get_field_value(row, 'address', column_mappings)
                year_name = get_field_value(row, 'year_name', column_mappings)
                grade_name = get_field_value(row, 'grade_name', column_mappings)
                section_name = get_field_value(row, 'section_name', column_mappings)
                
                print(f"🔍 الصف {idx}: رقم={student_number}, الاسم={first_name} {last_name}, تاريخ الميلاد={birth_date}")
                
                # ✅ التحقق من الحقول المطلوبة
                field_errors = []
                
                if not student_number:
                    field_errors.append("رقم الطالب مطلوب")
                
                if not first_name:
                    field_errors.append("الاسم الأول مطلوب")
                
                if not last_name:
                    field_errors.append("اسم العائلة مطلوب")
                
                if field_errors:
                    import_errors.append(f"الصف {idx}: " + "، ".join(field_errors))
                    continue
                
                # ✅ الحصول على المعرفات من الأسماء
                year_id = None
                if year_name:
                    year_id = await get_year_id_by_name(db, user.school_id, year_name)
                    if not year_id:
                        import_errors.append(f"الصف {idx}: السنة الدراسية '{year_name}' غير موجودة")
                        continue
                
                grade_id = None
                if grade_name:
                    grade_id = await get_grade_id_by_name(db, user.school_id, grade_name)
                    if not grade_id:
                        import_errors.append(f"الصف {idx}: الصف '{grade_name}' غير موجود")
                        continue
                
                section_id = None
                if section_name:
                    section_id = await get_section_id_by_name(db, user.school_id, section_name)
                    if not section_id:
                        import_errors.append(f"الصف {idx}: الشعبة '{section_name}' غير موجودة")
                        continue
                
                # ✅ التحقق من تكرار رقم الطالب
                existing = await db.execute(
                    select(Student).where(
                        Student.student_number == student_number,
                        Student.school_id == user.school_id
                    )
                )
                if existing.scalar_one_or_none():
                    import_errors.append(f"الصف {idx}: رقم الطالب '{student_number}' موجود بالفعل")
                    continue
                
                # ✅ إنشاء بيانات الطالب
                student_data = StudentCreate(
                    student_number=student_number,
                    national_id=national_id,
                    first_name=first_name,
                    last_name=last_name,
                    gender=gender,
                    birth_date=birth_date,
                    guardian_name=guardian_name,
                    guardian_phone=guardian_phone,
                    guardian_email=guardian_email,
                    address=address,
                    year_id=year_id,
                    grade_id=grade_id,
                    section_id=section_id,
                )
                
                # ✅ إنشاء الطالب
                service = StudentService(db)
                await service.create_student(student_data, user.id, user.school_id)
                imported_count += 1
                
                print(f"✅ تم استيراد الطالب {student_number} - {first_name} {last_name}")
                
            except ConflictException as e:
                import_errors.append(f"الصف {idx}: {str(e)}")
            except ValidationException as e:
                import_errors.append(f"الصف {idx}: {str(e)}")
            except Exception as e:
                import_errors.append(f"الصف {idx}: {str(e)}")
                print(f"❌ خطأ في الصف {idx}: {str(e)}")
        
        # ============================================================
        # ✅ عرض النتيجة النهائية
        # ============================================================
        
        success_message = f'تم استيراد {imported_count} طالب بنجاح'
        if import_errors:
            success_message += f'، عدد الأخطاء: {len(import_errors)}'
        
        return JSONResponse({
            'success': imported_count > 0,
            'imported': imported_count,
            'errors': import_errors,
            'message': success_message,
            'total_rows': len(data),
            'has_errors': len(import_errors) > 0,
            'error_summary': {
                'total_errors': len(import_errors),
                'error_messages': import_errors[:10]
            }
        })
        
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {str(e)}")
        traceback.print_exc()
        
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ غير متوقع: {str(e)}',
            'imported': 0,
            'errors': [str(e)]
        }, status_code=500)


def parse_pdf_data(lines):
    """
    معالجة البيانات المستخرجة من PDF
    يمكن تخصيص هذه الدالة حسب تنسيق ملف PDF الخاص بك
    """
    students = []
    current_student = {}
    
    for line in lines:
        # البحث عن رقم الطالب
        if 'رقم الطالب' in line or 'Student Number' in line or 'StudentNumber' in line:
            if current_student:
                students.append(current_student)
            current_student = {}
            parts = line.split(':')
            if len(parts) > 1:
                current_student['student_number'] = parts[1].strip()
            else:
                # محاولة استخراج الرقم من النص
                numbers = re.findall(r'\d+', line)
                if numbers:
                    current_student['student_number'] = numbers[0]
        
        # البحث عن الاسم
        elif 'الاسم' in line or 'Name' in line:
            parts = line.split(':')
            if len(parts) > 1:
                name = parts[1].strip()
                name_parts = name.split()
                if len(name_parts) >= 2:
                    current_student['first_name'] = name_parts[0]
                    current_student['last_name'] = ' '.join(name_parts[1:])
                else:
                    current_student['first_name'] = name
        
        # البحث عن السنة
        elif 'السنة' in line or 'Year' in line:
            parts = line.split(':')
            if len(parts) > 1:
                current_student['year'] = parts[1].strip()
        
        # البحث عن الصف
        elif 'الصف' in line or 'Grade' in line:
            parts = line.split(':')
            if len(parts) > 1:
                current_student['grade'] = parts[1].strip()
        
        # البحث عن الشعبة
        elif 'الشعبة' in line or 'Section' in line:
            parts = line.split(':')
            if len(parts) > 1:
                current_student['section'] = parts[1].strip()
        
        # البحث عن الجنس
        elif 'الجنس' in line or 'Gender' in line:
            parts = line.split(':')
            if len(parts) > 1:
                current_student['gender'] = parts[1].strip()
        
        # البحث عن تاريخ الميلاد
        elif 'تاريخ الميلاد' in line or 'Birth Date' in line:
            parts = line.split(':')
            if len(parts) > 1:
                current_student['birth_date'] = parts[1].strip()
        
        # البحث عن ولي الأمر
        elif 'ولي الأمر' in line or 'Guardian' in line:
            parts = line.split(':')
            if len(parts) > 1:
                if 'اسم' in line or 'Name' in line:
                    current_student['guardian_name'] = parts[1].strip()
                elif 'هاتف' in line or 'Phone' in line:
                    current_student['guardian_phone'] = parts[1].strip()
                elif 'بريد' in line or 'Email' in line:
                    current_student['guardian_email'] = parts[1].strip()
        
        # البحث عن العنوان
        elif 'العنوان' in line or 'Address' in line:
            parts = line.split(':')
            if len(parts) > 1:
                current_student['address'] = parts[1].strip()
    
    # إضافة آخر طالب
    if current_student:
        students.append(current_student)
    
    return students


# ============================================================
# 📤 GET /students/export - تصدير بيانات الطلاب
# ============================================================
@router.get("/export")
async def export_students(
    request: Request,
    format: str = Query("excel", regex="^(excel|csv|pdf)$"),
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    تصدير بيانات الطلاب بصيغة Excel, CSV, أو PDF
    """
    try:
        service = StudentService(db)
        students = await service.get_all_students(user.school_id)
        
        if format == "excel":
            # تصدير Excel
            data = []
            for student in students:
                data.append({
                    "رقم الطالب": student.student_number,
                    "الاسم الأول": student.first_name,
                    "اسم العائلة": student.last_name,
                    "الاسم الكامل": student.full_name,
                    "الرقم الوطني": student.national_id or "",
                    "الجنس": student.gender or "",
                    "تاريخ الميلاد": student.birth_date or "",
                    "اسم ولي الأمر": student.guardian_name or "",
                    "هاتف ولي الأمر": student.guardian_phone or "",
                    "البريد الإلكتروني": student.guardian_email or "",
                    "العنوان": student.address or "",
                    "السنة الدراسية": student.year.name if student.year else "",
                    "الصف": student.grade.name if student.grade else "",
                    "الشعبة": student.section.name if student.section else "",
                    "الحالة": "نشط" if student.is_active else "معطل"
                })
            
            df = pd.DataFrame(data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Students')
            output.seek(0)
            
            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=students_{date.today()}.xlsx"}
            )
        
        elif format == "csv":
            # تصدير CSV
            data = []
            for student in students:
                data.append({
                    "student_number": student.student_number,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "full_name": student.full_name,
                    "national_id": student.national_id or "",
                    "gender": student.gender or "",
                    "birth_date": student.birth_date or "",
                    "guardian_name": student.guardian_name or "",
                    "guardian_phone": student.guardian_phone or "",
                    "guardian_email": student.guardian_email or "",
                    "address": student.address or "",
                    "year": student.year.name if student.year else "",
                    "grade": student.grade.name if student.grade else "",
                    "section": student.section.name if student.section else "",
                    "status": "active" if student.is_active else "inactive"
                })
            
            df = pd.DataFrame(data)
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            
            return Response(
                content=output.getvalue().encode('utf-8-sig'),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=students_{date.today()}.csv"}
            )
        
        elif format == "pdf":
            # تصدير PDF (سيتم تنفيذه لاحقاً)
            return JSONResponse({
                'success': False,
                'message': 'تصدير PDF قيد التطوير'
            }, status_code=501)
        
        else:
            return JSONResponse({
                'success': False,
                'message': 'صيغة غير مدعومة'
            }, status_code=400)
            
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status_code=500)


# ============================================================
# 📊 GET /students/stats - إحصائيات الطلاب
# ============================================================
@router.get("/stats")
async def get_student_stats(
    request: Request,
    year_id: Optional[str] = None,
    grade_id: Optional[str] = None,
    section_id: Optional[str] = None,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    الحصول على إحصائيات الطلاب
    """
    try:
        service = StudentService(db)
        stats = await service.get_student_stats(
            school_id=user.school_id,
            year_id=year_id,
            grade_id=grade_id,
            section_id=section_id
        )
        return JSONResponse(safe_to_json(stats))
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status_code=500)


# ============================================================
# 📊 GET /students/{student_id}/stats - إحصائيات طالب محدد
# ============================================================
@router.get("/{student_id}/stats")
async def get_student_stats_detail(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    الحصول على إحصائيات طالب محدد (الحضور، الواجبات، الأنشطة)
    """
    try:
        service = StudentService(db)
        stats = await service.get_student_detailed_stats(student_id)
        return JSONResponse(safe_to_json(stats))
    except NotFoundException as e:
        return JSONResponse({
            'success': False,
            'message': str(e)
        }, status_code=404)
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status_code=500)


# ============================================================
# 📝 POST /students/{student_id}/attendance - تحديث حالة الحضور
# ============================================================
@router.post("/{student_id}/attendance")
async def update_student_attendance(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث حالة حضور الطالب
    """
    try:
        data = await request.json()
        status = data.get('status')
        date_val = data.get('date', datetime.now().date().isoformat())
        
        if not status:
            return JSONResponse({
                'success': False,
                'message': 'حالة الحضور مطلوبة'
            }, status_code=400)
        
        service = StudentService(db)
        await service.update_attendance(
            student_id=student_id,
            status=status,
            date=date_val,
            updated_by=user.id
        )
        return JSONResponse({
            'success': True,
            'message': 'تم تحديث حالة الحضور بنجاح'
        })
    except NotFoundException as e:
        return JSONResponse({
            'success': False,
            'message': str(e)
        }, status_code=404)
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status_code=500)


# ============================================================
# 📝 POST /students/{student_id}/late - تحديث حالة التأخر
# ============================================================
@router.post("/{student_id}/late")
async def update_student_late(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث حالة التأخر للطالب
    """
    try:
        data = await request.json()
        periods = data.get('periods', [])
        
        service = StudentService(db)
        await service.update_late_status(
            student_id=student_id,
            periods=periods,
            updated_by=user.id
        )
        return JSONResponse({
            'success': True,
            'message': 'تم تحديث حالة التأخر بنجاح'
        })
    except NotFoundException as e:
        return JSONResponse({
            'success': False,
            'message': str(e)
        }, status_code=404)
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status_code=500)


# ============================================================
# 📝 POST /students/{student_id}/assignments - تحديث الواجبات
# ============================================================
@router.post("/{student_id}/assignments")
async def update_student_assignments(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث واجبات الطالب
    """
    try:
        data = await request.json()
        assignments = data.get('assignments', [])
        
        service = StudentService(db)
        await service.update_assignments(
            student_id=student_id,
            assignments=assignments,
            updated_by=user.id
        )
        return JSONResponse({
            'success': True,
            'message': 'تم تحديث الواجبات بنجاح'
        })
    except NotFoundException as e:
        return JSONResponse({
            'success': False,
            'message': str(e)
        }, status_code=404)
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status_code=500)


# ============================================================
# 📝 POST /students/{student_id}/activities - تحديث الأنشطة
# ============================================================
@router.post("/{student_id}/activities")
async def update_student_activities(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
):
    """
    تحديث أنشطة الطالب
    """
    try:
        data = await request.json()
        activities = data.get('activities', [])
        
        service = StudentService(db)
        await service.update_activities(
            student_id=student_id,
            activities=activities,
            updated_by=user.id
        )
        return JSONResponse({
            'success': True,
            'message': 'تم تحديث الأنشطة بنجاح'
        })
    except NotFoundException as e:
        return JSONResponse({
            'success': False,
            'message': str(e)
        }, status_code=404)
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status_code=500)


# ============================================================
# 1️⃣ GET /students/new - صفحة إضافة طالب جديد
# ============================================================
@router.get("/new")
async def student_new(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    try:
        data = await get_onboarding_data(db, user.school_id)
        
        # تحويل البيانات إلى صيغة مناسبة للقالب
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": safe_to_json(sections_data), 
                "years": safe_to_json(data.get("years", [])),
                "grades": safe_to_json(data.get("grades", [])),
                "student": None,
                "error": None
            },
        )
    except Exception as e:
        print(f"❌ Error in student_new: {str(e)}")
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": [], 
                "years": [],
                "grades": [],
                "student": None,
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 2️⃣ POST /students - إنشاء طالب جديد
# ============================================================
@router.post("")
async def student_create(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.create")),
    db: AsyncSession = Depends(get_db),
    student_number: str = Form(...),
    national_id: Optional[str] = Form(None),
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_phone: Optional[str] = Form(None),
    guardian_email: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    year_id: Optional[str] = Form(None),
    grade_id: Optional[str] = Form(None),
    section_id: Optional[str] = Form(None),
):
    service = StudentService(db)
    ctx = await template_context(request)
    
    # ✅ جمع الأخطاء لعرضها للمستخدم
    errors = {}
    
    # التحقق من صحة البيانات الأساسية
    if not student_number or len(student_number.strip()) < 3:
        errors["student_number"] = "رقم الطالب يجب أن يكون 3 أحرف على الأقل"
    
    if not first_name or len(first_name.strip()) < 2:
        errors["first_name"] = "الاسم الأول يجب أن يكون حرفين على الأقل"
    
    if not last_name or len(last_name.strip()) < 2:
        errors["last_name"] = "اسم العائلة يجب أن يكون حرفين على الأقل"
    
    # إذا كان هناك أخطاء، ارجع الصفحة مع رسائل الخطأ
    if errors:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": safe_to_json(sections_data), 
                "years": safe_to_json(data.get("years", [])),
                "grades": safe_to_json(data.get("grades", [])),
                "student": None,
                "error": "الرجاء تصحيح الأخطاء التالية:<br>• " + "<br>• ".join(errors.values())
            },
            status_code=422
        )
    
    student_data = StudentCreate(
        student_number=student_number.strip(),
        national_id=national_id.strip() if national_id else None,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        gender=gender,
        birth_date=birth_date,
        guardian_name=guardian_name.strip() if guardian_name else None,
        guardian_phone=guardian_phone.strip() if guardian_phone else None,
        guardian_email=guardian_email.strip().lower() if guardian_email else None,
        address=address.strip() if address else None,
        year_id=year_id,
        grade_id=grade_id,
        section_id=section_id,
    )
    
    try:
        student = await service.create_student(student_data, user.id, user.school_id)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except ConflictException as e:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": safe_to_json(sections_data), 
                "years": safe_to_json(data.get("years", [])),
                "grades": safe_to_json(data.get("grades", [])),
                "student": None,
                "error": str(e)
            },
            status_code=409
        )
    except ValidationException as e:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": safe_to_json(sections_data), 
                "years": safe_to_json(data.get("years", [])),
                "grades": safe_to_json(data.get("grades", [])),
                "student": None,
                "error": str(e)
            },
            status_code=422
        )
    except AppException as e:
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": safe_to_json(sections_data), 
                "years": safe_to_json(data.get("years", [])),
                "grades": safe_to_json(data.get("grades", [])),
                "student": None,
                "error": str(e)
            },
            status_code=400
        )
    except Exception as e:
        print(f"❌ Error in student_create: {str(e)}")
        data = await get_onboarding_data(db, user.school_id)
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "إضافة طالب", 
                "mode": "create", 
                "sections": safe_to_json(sections_data), 
                "years": safe_to_json(data.get("years", [])),
                "grades": safe_to_json(data.get("grades", [])),
                "student": None,
                "error": f"حدث خطأ غير متوقع: {str(e)}"
            },
            status_code=500
        )


# ============================================================
# 3️⃣ GET /students - قائمة الطلاب (محدثة)
# ============================================================
@router.get("")
async def students_list(
    request: Request,
    page: int = 1,
    search: str = "",
    status: Optional[str] = None,
    grade_id: Optional[str] = None,
    year_id: Optional[str] = None,
    section_id: Optional[str] = None,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    try:
        service = StudentService(db)
        
        # جلب بيانات التصفية
        data = await get_onboarding_data(db, user.school_id)
        
        result = await service.list_students(
            school_id=user.school_id,
            page=page,
            page_size=20,
            search=search or None,
            status=status,
            grade_id=grade_id,
            year_id=year_id,
            section_id=section_id,
            is_active=True,
        )
        
        # ✅ تحويل البيانات إلى JSON آمن للاستخدام في Alpine.js
        students_safe = safe_to_json(result.get("items", []))
        
        return templates.TemplateResponse(
            "students/list.html",
            {
                **ctx, 
                "title": "الطلاب", 
                "students": students_safe,
                "total": result.get("total", 0),
                "page": page, 
                "page_size": 20, 
                "search": search,
                "status_filter": status,
                "grade_filter": grade_id,
                "year_filter": year_id,
                "section_filter": section_id,
                "grades": safe_to_json(data.get("grades", [])),
                "years": safe_to_json(data.get("years", [])),
                "sections": safe_to_json(data.get("sections", [])),
                "error": None
            },
        )
    except Exception as e:
        print(f"❌ Error in students_list: {str(e)}")
        return templates.TemplateResponse(
            "students/list.html",
            {
                **ctx, 
                "title": "الطلاب", 
                "students": [], 
                "total": 0,
                "page": page, 
                "page_size": 20, 
                "search": search,
                "status_filter": None,
                "grade_filter": None,
                "year_filter": None,
                "section_filter": None,
                "grades": [],
                "years": [],
                "sections": [],
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 4️⃣ GET /students/{student_id}/edit - صفحة تعديل الطالب
# ============================================================
@router.get("/{student_id}/edit")
async def student_edit(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = StudentService(db)
    try:
        detail = await service.get_student_detail(student_id)
        data = await get_onboarding_data(db, user.school_id)
        
        sections_data = []
        for section in data.get("sections", []):
            sections_data.append({
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "year_id": section.year_id if hasattr(section, 'year_id') else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
            })
        
        return templates.TemplateResponse(
            "students/form.html",
            {
                **ctx, 
                "title": "تعديل طالب", 
                "mode": "edit", 
                "student": safe_to_json(detail), 
                "sections": safe_to_json(sections_data), 
                "years": safe_to_json(data.get("years", [])),
                "grades": safe_to_json(data.get("grades", [])),
                "error": None
            },
        )
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error in student_edit: {str(e)}")
        return templates.TemplateResponse(
            "errors/error.html",
            {**ctx, "message": f"حدث خطأ: {str(e)}"},
            status_code=400
        )


# ============================================================
# 5️⃣ POST /students/{student_id}/edit - تحديث بيانات الطالب
# ============================================================
@router.post("/{student_id}/edit")
async def student_update(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.update")),
    db: AsyncSession = Depends(get_db),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    national_id: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_phone: Optional[str] = Form(None),
    guardian_email: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    year_id: Optional[str] = Form(None),
    grade_id: Optional[str] = Form(None),
    section_id: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
):
    service = StudentService(db)
    ctx = await template_context(request)
    
    # ✅ جمع الأخطاء لعرضها للمستخدم
    errors = {}
    
    if first_name is not None and first_name.strip() and len(first_name.strip()) < 2:
        errors["first_name"] = "الاسم الأول يجب أن يكون حرفين على الأقل"
    
    if last_name is not None and last_name.strip() and len(last_name.strip()) < 2:
        errors["last_name"] = "اسم العائلة يجب أن يكون حرفين على الأقل"
    
    if errors:
        try:
            detail = await service.get_student_detail(student_id)
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": safe_to_json(detail),
                    "sections": safe_to_json(sections_data), 
                    "years": safe_to_json(data.get("years", [])),
                    "grades": safe_to_json(data.get("grades", [])),
                    "error": "الرجاء تصحيح الأخطاء التالية:<br>• " + "<br>• ".join(errors.values())
                },
                status_code=422
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    
    student_update = StudentUpdate(
        first_name=first_name.strip() if first_name else None,
        last_name=last_name.strip() if last_name else None,
        national_id=national_id.strip() if national_id else None,
        gender=gender,
        birth_date=birth_date,
        guardian_name=guardian_name.strip() if guardian_name else None,
        guardian_phone=guardian_phone.strip() if guardian_phone else None,
        guardian_email=guardian_email.strip().lower() if guardian_email else None,
        address=address.strip() if address else None,
        year_id=year_id,
        grade_id=grade_id,
        section_id=section_id,
        is_active=is_active,
    )
    
    try:
        student = await service.update_student(student_id, student_update)
        return RedirectResponse(url=f"/students/{student.id}", status_code=303)
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except ConflictException as e:
        try:
            detail = await service.get_student_detail(student_id)
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": safe_to_json(detail),
                    "sections": safe_to_json(sections_data), 
                    "years": safe_to_json(data.get("years", [])),
                    "grades": safe_to_json(data.get("grades", [])),
                    "error": str(e)
                },
                status_code=409
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    except ValidationException as e:
        try:
            detail = await service.get_student_detail(student_id)
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": safe_to_json(detail),
                    "sections": safe_to_json(sections_data), 
                    "years": safe_to_json(data.get("years", [])),
                    "grades": safe_to_json(data.get("grades", [])),
                    "error": str(e)
                },
                status_code=422
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )
    except Exception as e:
        print(f"❌ Error in student_update: {str(e)}")
        try:
            detail = await service.get_student_detail(student_id)
            data = await get_onboarding_data(db, user.school_id)
            sections_data = []
            for section in data.get("sections", []):
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "year_id": section.year_id if hasattr(section, 'year_id') else None,
                    "grade_name": section.grade.name if section.grade else "غير محدد",
                })
            return templates.TemplateResponse(
                "students/form.html",
                {
                    **ctx, 
                    "title": "تعديل طالب", 
                    "mode": "edit", 
                    "student": safe_to_json(detail),
                    "sections": safe_to_json(sections_data), 
                    "years": safe_to_json(data.get("years", [])),
                    "grades": safe_to_json(data.get("grades", [])),
                    "error": f"حدث خطأ غير متوقع: {str(e)}"
                },
                status_code=500
            )
        except NotFoundException:
            return templates.TemplateResponse(
                "errors/404.html",
                {**ctx, "message": "الطالب غير موجود"},
                status_code=404
            )


# ============================================================
# 6️⃣ POST /students/{student_id}/delete - حذف الطالب
# ============================================================
@router.post("/{student_id}/delete")
async def student_delete(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    try:
        await service.delete_student(student_id)
        return RedirectResponse(url="/students", status_code=303)
    except Exception as e:
        print(f"❌ Error in student_delete: {str(e)}")
        return RedirectResponse(url="/students", status_code=303)


# ============================================================
# 7️⃣ GET /students/{student_id} - تفاصيل الطالب
# ============================================================
@router.get("/{student_id}")
async def student_detail(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = StudentService(db)
    try:
        detail = await service.get_student_detail(student_id)
        
        return templates.TemplateResponse(
            "students/detail.html",
            {**ctx, "title": detail.get("full_name", "تفاصيل الطالب"), "student": safe_to_json(detail)},
        )
    except NotFoundException as e:
        return templates.TemplateResponse(
            "errors/404.html",
            {**ctx, "message": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error in student_detail: {str(e)}")
        return templates.TemplateResponse(
            "errors/error.html",
            {**ctx, "message": f"حدث خطأ: {str(e)}"},
            status_code=400
        )


# ============================================================
# 8️⃣ POST /students/{student_id} - حذف الطالب (مسار بديل)
# ============================================================
@router.post("/{student_id}")
async def student_delete_alt(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_any_permission("students.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    try:
        await service.delete_student(student_id)
        return RedirectResponse(url="/students", status_code=303)
    except Exception as e:
        print(f"❌ Error in student_delete_alt: {str(e)}")
        return RedirectResponse(url="/students", status_code=303)


# ============================================================
# 🔧 مسار تصحيح إضافي - عرض جميع الطلاب مع فصولهم
# ============================================================
@router.get("/debug/all")
async def debug_all_students(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    عرض جميع الطلاب مع فصولهم (للتأكد من ارتباطهم)
    """
    try:
        students_result = await db.execute(
            select(Student, Section, Grade, AcademicYear)
            .outerjoin(Section, Student.section_id == Section.id)
            .outerjoin(Grade, Student.grade_id == Grade.id)
            .outerjoin(AcademicYear, Student.year_id == AcademicYear.id)
            .where(Student.school_id == user.school_id)
        )
        students = students_result.all()
        
        result = []
        for student, section, grade, year in students:
            result.append({
                "id": str(student.id),
                "name": student.full_name,
                "year_id": str(student.year_id) if student.year_id else None,
                "year_name": year.name if year else None,
                "grade_id": str(student.grade_id) if student.grade_id else None,
                "grade_name": grade.name if grade else None,
                "section_id": str(student.section_id) if student.section_id else None,
                "section_name": section.name if section else None,
                "school_id": str(student.school_id),
                "is_active": student.is_active if hasattr(student, 'is_active') else True
            })
        
        return JSONResponse(safe_to_json({
            "total": len(result),
            "students": result
        }))
        
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)
