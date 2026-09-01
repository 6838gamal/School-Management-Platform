"""Initial tables for school management system

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | None = None
depends_on: str | None = None


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في جدول."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)


def index_exists(table_name: str, index_name: str) -> bool:
    """التحقق من وجود فهرس في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def create_table_if_not_exists(table_name: str, *columns, **kwargs) -> None:
    """إنشاء جدول إذا لم يكن موجوداً."""
    if not table_exists(table_name):
        op.create_table(table_name, *columns, **kwargs)
        print(f"✅ تم إنشاء جدول: {table_name}")
    else:
        print(f"⏭️  جدول موجود مسبقاً: {table_name}")


def create_index_if_not_exists(table_name: str, index_name: str, columns: list, unique: bool = False) -> None:
    """إنشاء فهرس إذا لم يكن موجوداً والعمود موجود."""
    if not table_exists(table_name):
        return
    
    # التحقق من وجود جميع الأعمدة المطلوبة
    for col in columns:
        if not column_exists(table_name, col):
            print(f"⚠️ العمود {col} غير موجود في جدول {table_name}، تخطي الفهرس {index_name}")
            return
    
    if not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)
        print(f"✅ تم إنشاء فهرس: {index_name}")
    else:
        print(f"⏭️  فهرس موجود مسبقاً: {index_name}")


def add_column_if_not_exists(table_name: str, column_name: str, column_type, **kwargs) -> None:
    """إضافة عمود إذا لم يكن موجوداً."""
    if not table_exists(table_name):
        return
    
    if not column_exists(table_name, column_name):
        op.add_column(table_name, sa.Column(column_name, column_type, **kwargs))
        print(f"✅ تم إضافة عمود: {table_name}.{column_name}")
    else:
        print(f"⏭️  عمود موجود مسبقاً: {table_name}.{column_name}")


def upgrade() -> None:
    """إنشاء جميع الجداول الأساسية - آمن للتكرار."""
    
    # ============================================================
    # 1. جدول المدارس (schools)
    # ============================================================
    create_table_if_not_exists(
        'schools',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('onboarding_complete', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('onboarding_step', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول المدارس
    create_index_if_not_exists('schools', 'ix_schools_code', ['code'], unique=True)
    create_index_if_not_exists('schools', 'ix_schools_id', ['id'], unique=False)
    create_index_if_not_exists('schools', 'ix_schools_is_active', ['is_active'], unique=False)
    
    # ============================================================
    # 2. جدول المستخدمين (users)
    # ============================================================
    create_table_if_not_exists(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول المستخدمين
    create_index_if_not_exists('users', 'ix_users_email', ['email'], unique=True)
    create_index_if_not_exists('users', 'ix_users_id', ['id'], unique=False)
    create_index_if_not_exists('users', 'ix_users_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('users', 'ix_users_is_active', ['is_active'], unique=False)
    
    # ============================================================
    # 3. جدول الأدوار (roles)
    # ============================================================
    create_table_if_not_exists(
        'roles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=True),
        sa.Column('key', sa.String(50), nullable=False),
        sa.Column('name_ar', sa.String(100), nullable=False),
        sa.Column('name_en', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول الأدوار
    create_index_if_not_exists('roles', 'ix_roles_id', ['id'], unique=False)
    create_index_if_not_exists('roles', 'ix_roles_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('roles', 'ix_roles_key', ['key'], unique=False)
    create_index_if_not_exists('roles', 'ix_roles_school_key', ['school_id', 'key'], unique=True)
    create_index_if_not_exists('roles', 'ix_roles_is_system', ['is_system'], unique=False)
    
    # ============================================================
    # 4. جدول الصلاحيات (permissions)
    # ============================================================
    create_table_if_not_exists(
        'permissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('label_ar', sa.String(200), nullable=False),
        sa.Column('label_en', sa.String(200), nullable=False),
        sa.Column('group', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول الصلاحيات
    create_index_if_not_exists('permissions', 'ix_permissions_id', ['id'], unique=False)
    create_index_if_not_exists('permissions', 'ix_permissions_key', ['key'], unique=True)
    create_index_if_not_exists('permissions', 'ix_permissions_group', ['group'], unique=False)
    
    # ============================================================
    # 5. جدول ربط الأدوار بالصلاحيات (role_permissions)
    # ============================================================
    create_table_if_not_exists(
        'role_permissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('role_id', sa.String(36), nullable=False),
        sa.Column('permission_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول ربط الأدوار بالصلاحيات
    create_index_if_not_exists('role_permissions', 'ix_role_permissions_id', ['id'], unique=False)
    create_index_if_not_exists('role_permissions', 'ix_role_permissions_role_id', ['role_id'], unique=False)
    create_index_if_not_exists('role_permissions', 'ix_role_permissions_permission_id', ['permission_id'], unique=False)
    create_index_if_not_exists('role_permissions', 'ix_role_permissions_unique', ['role_id', 'permission_id'], unique=True)
    
    # ============================================================
    # 6. جدول ربط المستخدمين بالأدوار (user_roles)
    # ============================================================
    create_table_if_not_exists(
        'user_roles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('role_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول ربط المستخدمين بالأدوار
    create_index_if_not_exists('user_roles', 'ix_user_roles_id', ['id'], unique=False)
    create_index_if_not_exists('user_roles', 'ix_user_roles_user_id', ['user_id'], unique=False)
    create_index_if_not_exists('user_roles', 'ix_user_roles_role_id', ['role_id'], unique=False)
    create_index_if_not_exists('user_roles', 'ix_user_roles_unique', ['user_id', 'role_id'], unique=True)
    
    # ============================================================
    # 7. جدول السنوات الدراسية (academic_years)
    # ============================================================
    create_table_if_not_exists(
        'academic_years',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول السنوات الدراسية
    create_index_if_not_exists('academic_years', 'ix_academic_years_id', ['id'], unique=False)
    create_index_if_not_exists('academic_years', 'ix_academic_years_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('academic_years', 'ix_academic_years_is_current', ['is_current'], unique=False)
    create_index_if_not_exists('academic_years', 'ix_academic_years_is_active', ['is_active'], unique=False)
    create_index_if_not_exists('academic_years', 'ix_academic_years_school_current', ['school_id', 'is_current'], unique=False)
    
    # ============================================================
    # 8. جدول الصفوف (classes)
    # ============================================================
    create_table_if_not_exists(
        'classes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('academic_year_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('grade_level', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول الصفوف
    create_index_if_not_exists('classes', 'ix_classes_id', ['id'], unique=False)
    create_index_if_not_exists('classes', 'ix_classes_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('classes', 'ix_classes_academic_year_id', ['academic_year_id'], unique=False)
    create_index_if_not_exists('classes', 'ix_classes_grade_level', ['grade_level'], unique=False)
    create_index_if_not_exists('classes', 'ix_classes_is_active', ['is_active'], unique=False)
    create_index_if_not_exists('classes', 'ix_classes_unique_name', ['academic_year_id', 'name'], unique=True)
    
    # ============================================================
    # 9. جدول المواد الدراسية (subjects)
    # ============================================================
    create_table_if_not_exists(
        'subjects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('name_ar', sa.String(200), nullable=False),
        sa.Column('name_en', sa.String(200), nullable=True),
        sa.Column('code', sa.String(50), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # فهارس جدول المواد الدراسية
    create_index_if_not_exists('subjects', 'ix_subjects_id', ['id'], unique=False)
    create_index_if_not_exists('subjects', 'ix_subjects_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('subjects', 'ix_subjects_code', ['code'], unique=False)
    create_index_if_not_exists('subjects', 'ix_subjects_is_active', ['is_active'], unique=False)
    create_index_if_not_exists('subjects', 'ix_subjects_school_code', ['school_id', 'code'], unique=True)
    
    # ============================================================
    # 10. جدول الطلاب (students) - مع user_id
    # ============================================================
    # إنشاء الجدول إذا لم يكن موجوداً
    create_table_if_not_exists(
        'students',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),  # ✅ user_id موجود
        sa.Column('student_number', sa.String(50), nullable=False),
        sa.Column('national_id', sa.String(50), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('first_name_ar', sa.String(100), nullable=True),
        sa.Column('last_name_ar', sa.String(100), nullable=True),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('nationality', sa.String(50), nullable=True),
        sa.Column('guardian_name', sa.String(255), nullable=True),
        sa.Column('guardian_phone', sa.String(50), nullable=True),
        sa.Column('guardian_email', sa.String(255), nullable=True),
        sa.Column('guardian_relation', sa.String(50), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('enrollment_status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('enrolled_date', sa.Date(), nullable=True),
        sa.Column('graduation_date', sa.Date(), nullable=True),
        sa.Column('section_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('school_id', 'student_number', name='uq_student_school_number'),
        sa.UniqueConstraint('school_id', 'national_id', name='uq_student_school_national_id')
    )
    
    # ✅ إضافة user_id إذا كان الجدول موجوداً ولكن العمود مفقود
    add_column_if_not_exists('students', 'user_id', sa.String(36), nullable=True)
    
    # فهارس جدول الطلاب
    create_index_if_not_exists('students', 'ix_students_id', ['id'], unique=False)
    create_index_if_not_exists('students', 'ix_students_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('students', 'ix_students_user_id', ['user_id'], unique=False)  # ✅ فهرس user_id
    create_index_if_not_exists('students', 'ix_students_student_number', ['student_number'], unique=False)
    create_index_if_not_exists('students', 'ix_students_is_active', ['is_active'], unique=False)
    create_index_if_not_exists('students', 'ix_students_enrollment_status', ['enrollment_status'], unique=False)
    create_index_if_not_exists('students', 'ix_students_section_id', ['section_id'], unique=False)
    create_index_if_not_exists('students', 'ix_students_school_active', ['school_id', 'is_active'], unique=False)
    create_index_if_not_exists('students', 'ix_students_name_search', ['first_name', 'last_name'], unique=False)
    create_index_if_not_exists('students', 'ix_students_name_ar_search', ['first_name_ar', 'last_name_ar'], unique=False)
    create_index_if_not_exists('students', 'ix_students_school_number', ['school_id', 'student_number'], unique=True)
    
    # ============================================================
    # 11. جدول المعلمين (teachers) - مع user_id
    # ============================================================
    # إنشاء الجدول إذا لم يكن موجوداً
    create_table_if_not_exists(
        'teachers',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),  # ✅ user_id موجود
        sa.Column('teacher_code', sa.String(50), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('first_name_ar', sa.String(100), nullable=True),
        sa.Column('last_name_ar', sa.String(100), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('nationality', sa.String(50), nullable=True),
        sa.Column('national_id', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('qualification', sa.String(200), nullable=True),
        sa.Column('specialization', sa.String(200), nullable=True),
        sa.Column('hire_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('school_id', 'teacher_code', name='uq_teacher_school_code'),
        sa.UniqueConstraint('school_id', 'national_id', name='uq_teacher_school_national_id')
    )
    
    # ✅ إضافة user_id إذا كان الجدول موجوداً ولكن العمود مفقود
    add_column_if_not_exists('teachers', 'user_id', sa.String(36), nullable=True)
    
    # فهارس جدول المعلمين
    create_index_if_not_exists('teachers', 'ix_teachers_id', ['id'], unique=False)
    create_index_if_not_exists('teachers', 'ix_teachers_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('teachers', 'ix_teachers_user_id', ['user_id'], unique=False)  # ✅ فهرس user_id
    create_index_if_not_exists('teachers', 'ix_teachers_teacher_code', ['teacher_code'], unique=False)
    create_index_if_not_exists('teachers', 'ix_teachers_is_active', ['is_active'], unique=False)
    create_index_if_not_exists('teachers', 'ix_teachers_school_code', ['school_id', 'teacher_code'], unique=True)
    
    # ============================================================
    # 12. جدول تسجيل الطلاب في الصفوف (student_enrollments)
    # ============================================================
    create_table_if_not_exists(
        'student_enrollments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('student_id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('academic_year_id', sa.String(36), nullable=False),
        sa.Column('section_id', sa.String(36), nullable=True),
        sa.Column('class_id', sa.String(36), nullable=True),
        sa.Column('grade_level', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('enrolled_at', sa.Date(), nullable=False),
        sa.Column('ended_at', sa.Date(), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'academic_year_id', name='uq_enrollment_student_year'),
        sa.UniqueConstraint('student_id', 'academic_year_id', 'section_id', name='uq_enrollment_student_year_section')
    )
    
    # فهارس جدول تسجيل الطلاب
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_id', ['id'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_student_id', ['student_id'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_school_id', ['school_id'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_academic_year_id', ['academic_year_id'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_section_id', ['section_id'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_class_id', ['class_id'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_status', ['status'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_student_status', ['student_id', 'status'], unique=False)
    create_index_if_not_exists('student_enrollments', 'ix_student_enrollments_year_status', ['academic_year_id', 'status'], unique=False)
    
    # ============================================================
    # 13. جدول توزيع المواد على الصفوف (class_subjects)
    # ============================================================
    create_table_if_not_exists(
        'class_subjects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('class_id', sa.String(36), nullable=False),
        sa.Column('subject_id', sa.String(36), nullable=False),
        sa.Column('teacher_id', sa.String(36), nullable=True),
        sa.Column('academic_year_id', sa.String(36), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('class_id', 'subject_id', 'academic_year_id', name='uq_class_subject_year')
    )
    
    # فهارس جدول توزيع المواد
    create_index_if_not_exists('class_subjects', 'ix_class_subjects_id', ['id'], unique=False)
    create_index_if_not_exists('class_subjects', 'ix_class_subjects_class_id', ['class_id'], unique=False)
    create_index_if_not_exists('class_subjects', 'ix_class_subjects_subject_id', ['subject_id'], unique=False)
    create_index_if_not_exists('class_subjects', 'ix_class_subjects_teacher_id', ['teacher_id'], unique=False)
    create_index_if_not_exists('class_subjects', 'ix_class_subjects_academic_year_id', ['academic_year_id'], unique=False)
    create_index_if_not_exists('class_subjects', 'ix_class_subjects_is_active', ['is_active'], unique=False)
    create_index_if_not_exists('class_subjects', 'ix_class_subjects_unique', ['class_id', 'subject_id', 'academic_year_id'], unique=True)
    
    print("=" * 60)
    print("✅ تم الانتهاء من إنشاء جميع الجداول (13 جدول) بنجاح!")
    print("=" * 60)


def downgrade() -> None:
    """التراجع - حذف جميع الجداول مع التحقق من الوجود."""
    # ترتيب الحذف معكوس لترتيب الإنشاء (مراعاة العلاقات)
    tables = [
        'class_subjects',
        'student_enrollments',
        'teachers',
        'students',
        'subjects',
        'classes',
        'academic_years',
        'user_roles',
        'role_permissions',
        'permissions',
        'roles',
        'users',
        'schools'
    ]
    
    print("=" * 60)
    print("🔄 بدء عملية حذف الجداول...")
    print("=" * 60)
    
    for table in tables:
        if table_exists(table):
            try:
                op.drop_table(table)
                print(f"🗑️  تم حذف جدول: {table}")
            except Exception as e:
                print(f"❌ فشل حذف جدول {table}: {str(e)}")
        else:
            print(f"⏭️  جدول غير موجود: {table}")
    
    print("=" * 60)
    print("✅ تم الانتهاء من حذف جميع الجداول!")
    print("=" * 60)
