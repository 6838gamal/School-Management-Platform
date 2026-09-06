"""Add_academic_hierarchy_to_attendance_models

Revision ID: xxxx_add_academic_hierarchy
Revises: previous_revision
Create Date: 2026-09-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '0030'
down_revision = '0029'  # استبدل بـ revision السابق
branch_labels = None
depends_on = None


def get_table_names(conn) -> set:
    """الحصول على أسماء جميع الجداول في قاعدة البيانات"""
    inspector = inspect(conn)
    return set(inspector.get_table_names())


def get_column_names(conn, table_name: str) -> set:
    """الحصول على أسماء الأعمدة في جدول معين"""
    inspector = inspect(conn)
    columns = inspector.get_columns(table_name)
    return {col['name'] for col in columns}


def table_exists(conn, table_name: str) -> bool:
    """التحقق من وجود جدول"""
    return table_name in get_table_names(conn)


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في جدول"""
    return column_name in get_column_names(conn, table_name)


def get_foreign_keys(conn, table_name: str) -> list:
    """الحصول على قائمة المفاتيح الخارجية لجدول"""
    inspector = inspect(conn)
    return inspector.get_foreign_keys(table_name)


def foreign_key_exists(conn, table_name: str, fk_name: str) -> bool:
    """التحقق من وجود مفتاح خارجي معين"""
    fks = get_foreign_keys(conn, table_name)
    return any(fk.get('name') == fk_name for fk in fks)


def upgrade() -> None:
    """إضافة الهيكل الأكاديمي إلى جداول الحضور"""
    
    conn = op.get_bind()
    
    # ============================================================
    # 1️⃣ تحديث جدول student_attendance
    # ============================================================
    
    if table_exists(conn, 'student_attendance'):
        # إضافة الحقول الجديدة
        if not column_exists(conn, 'student_attendance', 'grade_id'):
            op.add_column('student_attendance', sa.Column('grade_id', sa.String(36), nullable=True))
        
        if not column_exists(conn, 'student_attendance', 'stage_id'):
            op.add_column('student_attendance', sa.Column('stage_id', sa.String(36), nullable=True))
        
        if not column_exists(conn, 'student_attendance', 'year_id'):
            op.add_column('student_attendance', sa.Column('year_id', sa.String(36), nullable=True))
        
        # إضافة الفهارس
        op.create_index('idx_student_attendance_grade_id', 'student_attendance', ['grade_id'], unique=False)
        op.create_index('idx_student_attendance_stage_id', 'student_attendance', ['stage_id'], unique=False)
        op.create_index('idx_student_attendance_year_id', 'student_attendance', ['year_id'], unique=False)
        
        # تحديث القيد الفريد
        if column_exists(conn, 'student_attendance', 'period_id'):
            try:
                op.drop_constraint('uq_student_att_day_period', 'student_attendance', type_='unique')
            except Exception:
                pass
            
            try:
                op.drop_constraint('uq_student_att_student_date_period', 'student_attendance', type_='unique')
            except Exception:
                pass
            
            op.create_unique_constraint(
                'uq_student_att_student_date_period',
                'student_attendance',
                ['student_id', 'date', 'period_id']
            )
    
    # ============================================================
    # 2️⃣ تحديث جدول teacher_attendance
    # ============================================================
    
    if table_exists(conn, 'teacher_attendance'):
        # إضافة الحقول الجديدة
        if not column_exists(conn, 'teacher_attendance', 'section_id'):
            op.add_column('teacher_attendance', sa.Column('section_id', sa.String(36), nullable=True))
        
        if not column_exists(conn, 'teacher_attendance', 'grade_id'):
            op.add_column('teacher_attendance', sa.Column('grade_id', sa.String(36), nullable=True))
        
        if not column_exists(conn, 'teacher_attendance', 'stage_id'):
            op.add_column('teacher_attendance', sa.Column('stage_id', sa.String(36), nullable=True))
        
        if not column_exists(conn, 'teacher_attendance', 'year_id'):
            op.add_column('teacher_attendance', sa.Column('year_id', sa.String(36), nullable=True))
        
        if not column_exists(conn, 'teacher_attendance', 'period_id'):
            op.add_column('teacher_attendance', sa.Column('period_id', sa.String(36), nullable=True))
        
        # إضافة الفهارس
        op.create_index('idx_teacher_attendance_section_id', 'teacher_attendance', ['section_id'], unique=False)
        op.create_index('idx_teacher_attendance_grade_id', 'teacher_attendance', ['grade_id'], unique=False)
        op.create_index('idx_teacher_attendance_stage_id', 'teacher_attendance', ['stage_id'], unique=False)
        op.create_index('idx_teacher_attendance_year_id', 'teacher_attendance', ['year_id'], unique=False)
        op.create_index('idx_teacher_attendance_period_id', 'teacher_attendance', ['period_id'], unique=False)
    
    # ============================================================
    # 3️⃣ إنشاء جدول attendance_summaries (ملخص الإحصائيات)
    # ============================================================
    
    if not table_exists(conn, 'attendance_summaries'):
        op.create_table(
            'attendance_summaries',
            sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
            sa.Column('school_id', sa.String(36), nullable=False),
            sa.Column('date', sa.String(20), nullable=False),
            sa.Column('section_id', sa.String(36), nullable=True),
            sa.Column('grade_id', sa.String(36), nullable=True),
            sa.Column('stage_id', sa.String(36), nullable=True),
            sa.Column('year_id', sa.String(36), nullable=True),
            
            # إحصائيات الطلاب
            sa.Column('total_students', sa.Integer, nullable=False, server_default='0'),
            sa.Column('present_students', sa.Integer, nullable=False, server_default='0'),
            sa.Column('absent_students', sa.Integer, nullable=False, server_default='0'),
            sa.Column('late_students', sa.Integer, nullable=False, server_default='0'),
            sa.Column('excused_students', sa.Integer, nullable=False, server_default='0'),
            sa.Column('attendance_percentage', sa.Float, nullable=False, server_default='0.0'),
            
            # إحصائيات المعلمين
            sa.Column('total_teachers', sa.Integer, nullable=False, server_default='0'),
            sa.Column('present_teachers', sa.Integer, nullable=False, server_default='0'),
            sa.Column('absent_teachers', sa.Integer, nullable=False, server_default='0'),
            sa.Column('late_teachers', sa.Integer, nullable=False, server_default='0'),
            sa.Column('leave_teachers', sa.Integer, nullable=False, server_default='0'),
            sa.Column('teacher_percentage', sa.Float, nullable=False, server_default='0.0'),
            
            # الطوابع الزمنية
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        
        # إضافة الفهارس
        op.create_index('idx_att_summary_date', 'attendance_summaries', ['date'], unique=False)
        op.create_index('idx_att_summary_section_id', 'attendance_summaries', ['section_id'], unique=False)
        op.create_index('idx_att_summary_grade_id', 'attendance_summaries', ['grade_id'], unique=False)
        op.create_index('idx_att_summary_stage_id', 'attendance_summaries', ['stage_id'], unique=False)
        op.create_index('idx_att_summary_year_id', 'attendance_summaries', ['year_id'], unique=False)
        
        # القيد الفريد
        op.create_unique_constraint(
            'uq_att_summary_school_date_section',
            'attendance_summaries',
            ['school_id', 'date', 'section_id']
        )
    
    # ============================================================
    # 4️⃣ إنشاء جدول attendance_audit_logs (سجل التدقيق)
    # ============================================================
    
    if not table_exists(conn, 'attendance_audit_logs'):
        op.create_table(
            'attendance_audit_logs',
            sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
            sa.Column('school_id', sa.String(36), nullable=False),
            sa.Column('attendance_type', sa.String(20), nullable=False),
            sa.Column('attendance_id', sa.String(36), nullable=False),
            sa.Column('action', sa.String(20), nullable=False),
            sa.Column('old_data', sa.Text, nullable=True),
            sa.Column('new_data', sa.Text, nullable=True),
            sa.Column('changed_by', sa.String(36), nullable=True),
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
        
        # إضافة الفهارس
        op.create_index('idx_att_audit_attendance_id', 'attendance_audit_logs', ['attendance_id'], unique=False)
        op.create_index('idx_att_audit_type', 'attendance_audit_logs', ['attendance_type'], unique=False)
        op.create_index('idx_att_audit_action', 'attendance_audit_logs', ['action'], unique=False)
        op.create_index('idx_att_audit_changed_by', 'attendance_audit_logs', ['changed_by'], unique=False)
        op.create_index('idx_att_audit_created_at', 'attendance_audit_logs', ['created_at'], unique=False)
    
    # ============================================================
    # 5️⃣ تحديث جدول academic_years (إضافة حقول إضافية)
    # ============================================================
    
    if table_exists(conn, 'academic_years'):
        if not column_exists(conn, 'academic_years', 'is_active'):
            op.add_column('academic_years', sa.Column('is_active', sa.Boolean, server_default='1'))
        
        if not column_exists(conn, 'academic_years', 'is_current'):
            op.add_column('academic_years', sa.Column('is_current', sa.Boolean, server_default='0'))
    
    # ============================================================
    # 6️⃣ تحديث جدول students (إضافة section_id إذا لم يكن موجوداً)
    # ============================================================
    
    if table_exists(conn, 'students'):
        if not column_exists(conn, 'students', 'section_id'):
            op.add_column('students', sa.Column('section_id', sa.String(36), nullable=True))
            op.create_index('idx_students_section_id', 'students', ['section_id'], unique=False)
        
        # إضافة سنة دراسية للطلاب إذا لم تكن موجودة
        if not column_exists(conn, 'students', 'year_id'):
            op.add_column('students', sa.Column('year_id', sa.String(36), nullable=True))
            op.create_index('idx_students_year_id', 'students', ['year_id'], unique=False)
        
        # إضافة صف للطلاب إذا لم يكن موجوداً
        if not column_exists(conn, 'students', 'grade_id'):
            op.add_column('students', sa.Column('grade_id', sa.String(36), nullable=True))
            op.create_index('idx_students_grade_id', 'students', ['grade_id'], unique=False)
    
    # ============================================================
    # 7️⃣ تحديث البيانات الموجودة (ربط السجلات القديمة)
    # ============================================================
    
    # ربط student_attendance بالـ section_id من جدول students
    if (table_exists(conn, 'student_attendance') and 
        table_exists(conn, 'students') and
        column_exists(conn, 'student_attendance', 'section_id') and
        column_exists(conn, 'students', 'section_id')):
        
        op.execute("""
            UPDATE student_attendance sa
            SET section_id = s.section_id
            FROM students s
            WHERE sa.student_id = s.id
            AND sa.section_id IS NULL
            AND s.section_id IS NOT NULL
        """)
    
    # ربط student_attendance بالـ grade_id من جدول sections
    if (table_exists(conn, 'student_attendance') and 
        table_exists(conn, 'sections') and
        column_exists(conn, 'student_attendance', 'grade_id') and
        column_exists(conn, 'sections', 'grade_id')):
        
        op.execute("""
            UPDATE student_attendance sa
            SET grade_id = sec.grade_id
            FROM sections sec
            WHERE sa.section_id = sec.id
            AND sa.grade_id IS NULL
        """)
    
    # ربط student_attendance بالـ stage_id من جدول grades
    if (table_exists(conn, 'student_attendance') and 
        table_exists(conn, 'grades') and
        column_exists(conn, 'student_attendance', 'stage_id') and
        column_exists(conn, 'grades', 'stage_id')):
        
        op.execute("""
            UPDATE student_attendance sa
            SET stage_id = g.stage_id
            FROM grades g
            WHERE sa.grade_id = g.id
            AND sa.stage_id IS NULL
        """)
    
    # ربط student_attendance بالـ year_id من جدول stages
    if (table_exists(conn, 'student_attendance') and 
        table_exists(conn, 'stages') and
        column_exists(conn, 'student_attendance', 'year_id') and
        column_exists(conn, 'stages', 'year_id')):
        
        op.execute("""
            UPDATE student_attendance sa
            SET year_id = s.year_id
            FROM stages s
            WHERE sa.stage_id = s.id
            AND sa.year_id IS NULL
        """)
    
    # ============================================================
    # 8️⃣ تحديث جدول sections (إضافة حقول إضافية)
    # ============================================================
    
    if table_exists(conn, 'sections'):
        if not column_exists(conn, 'sections', 'academic_year_id'):
            op.add_column('sections', sa.Column('academic_year_id', sa.String(36), nullable=True))
            op.create_index('idx_sections_academic_year_id', 'sections', ['academic_year_id'], unique=False)
        
        if not column_exists(conn, 'sections', 'capacity'):
            op.add_column('sections', sa.Column('capacity', sa.Integer, server_default='30'))
        
        if not column_exists(conn, 'sections', 'is_active'):
            op.add_column('sections', sa.Column('is_active', sa.Boolean, server_default='1'))
    
    # ============================================================
    # 9️⃣ تحديث جدول grades (إضافة حقول إضافية)
    # ============================================================
    
    if table_exists(conn, 'grades'):
        if not column_exists(conn, 'grades', 'order'):
            op.add_column('grades', sa.Column('order', sa.Integer, server_default='0'))
        
        if not column_exists(conn, 'grades', 'is_active'):
            op.add_column('grades', sa.Column('is_active', sa.Boolean, server_default='1'))
    
    # ============================================================
    # 🔟 تحديث جدول stages (إضافة حقول إضافية)
    # ============================================================
    
    if table_exists(conn, 'stages'):
        if not column_exists(conn, 'stages', 'order'):
            op.add_column('stages', sa.Column('order', sa.Integer, server_default='0'))
        
        if not column_exists(conn, 'stages', 'is_active'):
            op.add_column('stages', sa.Column('is_active', sa.Boolean, server_default='1'))


def downgrade() -> None:
    """التراجع عن التغييرات (حذف كل ما تم إضافته)"""
    
    conn = op.get_bind()
    
    # ============================================================
    # 1️⃣ حذف الجداول الجديدة
    # ============================================================
    
    if table_exists(conn, 'attendance_audit_logs'):
        op.drop_table('attendance_audit_logs')
    
    if table_exists(conn, 'attendance_summaries'):
        op.drop_table('attendance_summaries')
    
    # ============================================================
    # 2️⃣ التراجع عن تحديثات teacher_attendance
    # ============================================================
    
    if table_exists(conn, 'teacher_attendance'):
        # حذف الفهارس
        op.drop_index('idx_teacher_attendance_period_id', table_name='teacher_attendance')
        op.drop_index('idx_teacher_attendance_year_id', table_name='teacher_attendance')
        op.drop_index('idx_teacher_attendance_stage_id', table_name='teacher_attendance')
        op.drop_index('idx_teacher_attendance_grade_id', table_name='teacher_attendance')
        op.drop_index('idx_teacher_attendance_section_id', table_name='teacher_attendance')
        
        # حذف الحقول
        if column_exists(conn, 'teacher_attendance', 'period_id'):
            op.drop_column('teacher_attendance', 'period_id')
        if column_exists(conn, 'teacher_attendance', 'year_id'):
            op.drop_column('teacher_attendance', 'year_id')
        if column_exists(conn, 'teacher_attendance', 'stage_id'):
            op.drop_column('teacher_attendance', 'stage_id')
        if column_exists(conn, 'teacher_attendance', 'grade_id'):
            op.drop_column('teacher_attendance', 'grade_id')
        if column_exists(conn, 'teacher_attendance', 'section_id'):
            op.drop_column('teacher_attendance', 'section_id')
    
    # ============================================================
    # 3️⃣ التراجع عن تحديثات student_attendance
    # ============================================================
    
    if table_exists(conn, 'student_attendance'):
        # حذف الفهارس
        op.drop_index('idx_student_attendance_year_id', table_name='student_attendance')
        op.drop_index('idx_student_attendance_stage_id', table_name='student_attendance')
        op.drop_index('idx_student_attendance_grade_id', table_name='student_attendance')
        
        # حذف الحقول
        if column_exists(conn, 'student_attendance', 'year_id'):
            op.drop_column('student_attendance', 'year_id')
        if column_exists(conn, 'student_attendance', 'stage_id'):
            op.drop_column('student_attendance', 'stage_id')
        if column_exists(conn, 'student_attendance', 'grade_id'):
            op.drop_column('student_attendance', 'grade_id')
        
        # إعادة القيد الفريد القديم
        try:
            op.drop_constraint('uq_student_att_student_date_period', 'student_attendance', type_='unique')
        except Exception:
            pass
        
        if column_exists(conn, 'student_attendance', 'period_id'):
            op.create_unique_constraint(
                'uq_student_att_day_period',
                'student_attendance',
                ['student_id', 'date', 'period_id']
            )
    
    # ============================================================
    # 4️⃣ التراجع عن تحديثات students
    # ============================================================
    
    if table_exists(conn, 'students'):
        if column_exists(conn, 'students', 'grade_id'):
            op.drop_index('idx_students_grade_id', table_name='students')
            op.drop_column('students', 'grade_id')
        
        if column_exists(conn, 'students', 'year_id'):
            op.drop_index('idx_students_year_id', table_name='students')
            op.drop_column('students', 'year_id')
        
        if column_exists(conn, 'students', 'section_id'):
            op.drop_index('idx_students_section_id', table_name='students')
            op.drop_column('students', 'section_id')
    
    # ============================================================
    # 5️⃣ التراجع عن تحديثات sections
    # ============================================================
    
    if table_exists(conn, 'sections'):
        if column_exists(conn, 'sections', 'is_active'):
            op.drop_column('sections', 'is_active')
        if column_exists(conn, 'sections', 'capacity'):
            op.drop_column('sections', 'capacity')
        if column_exists(conn, 'sections', 'academic_year_id'):
            op.drop_index('idx_sections_academic_year_id', table_name='sections')
            op.drop_column('sections', 'academic_year_id')
    
    # ============================================================
    # 6️⃣ التراجع عن تحديثات grades
    # ============================================================
    
    if table_exists(conn, 'grades'):
        if column_exists(conn, 'grades', 'is_active'):
            op.drop_column('grades', 'is_active')
        if column_exists(conn, 'grades', 'order'):
            op.drop_column('grades', 'order')
    
    # ============================================================
    # 7️⃣ التراجع عن تحديثات stages
    # ============================================================
    
    if table_exists(conn, 'stages'):
        if column_exists(conn, 'stages', 'is_active'):
            op.drop_column('stages', 'is_active')
        if column_exists(conn, 'stages', 'order'):
            op.drop_column('stages', 'order')
    
    # ============================================================
    # 8️⃣ التراجع عن تحديثات academic_years
    # ============================================================
    
    if table_exists(conn, 'academic_years'):
        if column_exists(conn, 'academic_years', 'is_current'):
            op.drop_column('academic_years', 'is_current')
        if column_exists(conn, 'academic_years', 'is_active'):
            op.drop_column('academic_years', 'is_active')
