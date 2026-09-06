"""Complete academic hierarchy and attendance models update

Revision ID: 0030_complete_academic_attendance_update
Revises: 0029
Create Date: 2026-09-06 10:00:00.000000

This migration includes:
1. Academic structure updates (stages, grades, sections, periods)
2. Student model updates (stage_id, attendance_status, attendance_updated_at)
3. Attendance models updates (grade_id, stage_id, year_id for student_attendance)
4. Teacher attendance updates (section_id, grade_id, stage_id, year_id, period_id)
5. New tables: attendance_summaries, attendance_audit_logs

All without Foreign Keys - using simple indexed string columns.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from datetime import datetime
import uuid

# revision identifiers, used by Alembic.
revision = '0030'
down_revision = '0029'
branch_labels = None
depends_on = None


# ============================================================
# دوال مساعدة للتحقق
# ============================================================

def table_exists(conn, table_name: str) -> bool:
    """التحقق من وجود جدول"""
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في جدول"""
    inspector = inspect(conn)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)


def constraint_exists(conn, table_name: str, constraint_name: str) -> bool:
    """التحقق من وجود قيد في جدول"""
    inspector = inspect(conn)
    constraints = inspector.get_unique_constraints(table_name)
    return any(c.get('name') == constraint_name for c in constraints)


def index_exists(conn, table_name: str, index_name: str) -> bool:
    """التحقق من وجود فهرس في جدول"""
    inspector = inspect(conn)
    indexes = inspector.get_indexes(table_name)
    return any(idx.get('name') == index_name for idx in indexes)


# ============================================================
# الترقية (Upgrade)
# ============================================================

def upgrade() -> None:
    """تطبيق جميع التغييرات"""
    
    conn = op.get_bind()
    
    # ============================================================
    # 1️⃣ تحديث جدول academic_years
    # ============================================================
    
    if table_exists(conn, 'academic_years'):
        if not column_exists(conn, 'academic_years', 'is_active'):
            op.add_column('academic_years', sa.Column('is_active', sa.Boolean, server_default='1'))
        
        if not column_exists(conn, 'academic_years', 'is_current'):
            op.add_column('academic_years', sa.Column('is_current', sa.Boolean, server_default='0'))
    
    # ============================================================
    # 2️⃣ تحديث جدول stages
    # ============================================================
    
    if table_exists(conn, 'stages'):
        if not column_exists(conn, 'stages', 'year_id'):
            op.add_column('stages', sa.Column('year_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'stages', 'idx_stages_year_id'):
                op.create_index('idx_stages_year_id', 'stages', ['year_id'])
        
        if not column_exists(conn, 'stages', 'is_active'):
            op.add_column('stages', sa.Column('is_active', sa.Boolean, server_default='1'))
        
        if not column_exists(conn, 'stages', 'order'):
            op.add_column('stages', sa.Column('order', sa.Integer, server_default='0'))
    
    # ============================================================
    # 3️⃣ تحديث جدول grades
    # ============================================================
    
    if table_exists(conn, 'grades'):
        if not column_exists(conn, 'grades', 'year_id'):
            op.add_column('grades', sa.Column('year_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'grades', 'idx_grades_year_id'):
                op.create_index('idx_grades_year_id', 'grades', ['year_id'])
        
        if not column_exists(conn, 'grades', 'is_active'):
            op.add_column('grades', sa.Column('is_active', sa.Boolean, server_default='1'))
        
        if not column_exists(conn, 'grades', 'order'):
            op.add_column('grades', sa.Column('order', sa.Integer, server_default='0'))
    
    # ============================================================
    # 4️⃣ تحديث جدول sections
    # ============================================================
    
    if table_exists(conn, 'sections'):
        if not column_exists(conn, 'sections', 'year_id'):
            op.add_column('sections', sa.Column('year_id', sa.String(36), nullable=False, server_default=''))
            if not index_exists(conn, 'sections', 'idx_sections_year_id'):
                op.create_index('idx_sections_year_id', 'sections', ['year_id'])
        
        if not column_exists(conn, 'sections', 'class_teacher_ids'):
            op.add_column('sections', sa.Column('class_teacher_ids', sa.String(500), nullable=True))
        
        if not column_exists(conn, 'sections', 'is_active'):
            op.add_column('sections', sa.Column('is_active', sa.Boolean, server_default='1'))
        
        if not column_exists(conn, 'sections', 'capacity'):
            op.add_column('sections', sa.Column('capacity', sa.Integer, server_default='30'))
    
    # ============================================================
    # 5️⃣ تحديث جدول periods
    # ============================================================
    
    if table_exists(conn, 'periods'):
        if not column_exists(conn, 'periods', 'is_active'):
            op.add_column('periods', sa.Column('is_active', sa.Boolean, server_default='1'))
    
    # ============================================================
    # 6️⃣ تحديث جدول students
    # ============================================================
    
    if table_exists(conn, 'students'):
        if not column_exists(conn, 'students', 'section_id'):
            op.add_column('students', sa.Column('section_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'students', 'idx_students_section_id'):
                op.create_index('idx_students_section_id', 'students', ['section_id'])
        
        if not column_exists(conn, 'students', 'grade_id'):
            op.add_column('students', sa.Column('grade_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'students', 'idx_students_grade_id'):
                op.create_index('idx_students_grade_id', 'students', ['grade_id'])
        
        if not column_exists(conn, 'students', 'stage_id'):
            op.add_column('students', sa.Column('stage_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'students', 'idx_students_stage_id'):
                op.create_index('idx_students_stage_id', 'students', ['stage_id'])
        
        if not column_exists(conn, 'students', 'year_id'):
            op.add_column('students', sa.Column('year_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'students', 'idx_students_year_id'):
                op.create_index('idx_students_year_id', 'students', ['year_id'])
        
        if not column_exists(conn, 'students', 'attendance_status'):
            op.add_column('students', sa.Column('attendance_status', sa.String(20), nullable=True))
        
        if not column_exists(conn, 'students', 'attendance_updated_at'):
            op.add_column('students', sa.Column('attendance_updated_at', sa.DateTime, nullable=True))
    
    # ============================================================
    # 7️⃣ تحديث جدول student_attendance
    # ============================================================
    
    if table_exists(conn, 'student_attendance'):
        if not column_exists(conn, 'student_attendance', 'grade_id'):
            op.add_column('student_attendance', sa.Column('grade_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'student_attendance', 'idx_student_attendance_grade_id'):
                op.create_index('idx_student_attendance_grade_id', 'student_attendance', ['grade_id'])
        
        if not column_exists(conn, 'student_attendance', 'stage_id'):
            op.add_column('student_attendance', sa.Column('stage_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'student_attendance', 'idx_student_attendance_stage_id'):
                op.create_index('idx_student_attendance_stage_id', 'student_attendance', ['stage_id'])
        
        if not column_exists(conn, 'student_attendance', 'year_id'):
            op.add_column('student_attendance', sa.Column('year_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'student_attendance', 'idx_student_attendance_year_id'):
                op.create_index('idx_student_attendance_year_id', 'student_attendance', ['year_id'])
    
    # ============================================================
    # 8️⃣ تحديث جدول teacher_attendance
    # ============================================================
    
    if table_exists(conn, 'teacher_attendance'):
        if not column_exists(conn, 'teacher_attendance', 'section_id'):
            op.add_column('teacher_attendance', sa.Column('section_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_section_id'):
                op.create_index('idx_teacher_attendance_section_id', 'teacher_attendance', ['section_id'])
        
        if not column_exists(conn, 'teacher_attendance', 'grade_id'):
            op.add_column('teacher_attendance', sa.Column('grade_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_grade_id'):
                op.create_index('idx_teacher_attendance_grade_id', 'teacher_attendance', ['grade_id'])
        
        if not column_exists(conn, 'teacher_attendance', 'stage_id'):
            op.add_column('teacher_attendance', sa.Column('stage_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_stage_id'):
                op.create_index('idx_teacher_attendance_stage_id', 'teacher_attendance', ['stage_id'])
        
        if not column_exists(conn, 'teacher_attendance', 'year_id'):
            op.add_column('teacher_attendance', sa.Column('year_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_year_id'):
                op.create_index('idx_teacher_attendance_year_id', 'teacher_attendance', ['year_id'])
        
        if not column_exists(conn, 'teacher_attendance', 'period_id'):
            op.add_column('teacher_attendance', sa.Column('period_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_period_id'):
                op.create_index('idx_teacher_attendance_period_id', 'teacher_attendance', ['period_id'])
    
    # ============================================================
    # 9️⃣ تحديث جدول student_enrollments
    # ============================================================
    
    if table_exists(conn, 'student_enrollments'):
        if not column_exists(conn, 'student_enrollments', 'stage_id'):
            op.add_column('student_enrollments', sa.Column('stage_id', sa.String(36), nullable=True))
            if not index_exists(conn, 'student_enrollments', 'idx_enrollments_stage_id'):
                op.create_index('idx_enrollments_stage_id', 'student_enrollments', ['stage_id'])
    
    # ============================================================
    # 🔟 إنشاء جدول attendance_summaries
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
        if not index_exists(conn, 'attendance_summaries', 'idx_att_summary_date'):
            op.create_index('idx_att_summary_date', 'attendance_summaries', ['date'])
        if not index_exists(conn, 'attendance_summaries', 'idx_att_summary_section_id'):
            op.create_index('idx_att_summary_section_id', 'attendance_summaries', ['section_id'])
        if not index_exists(conn, 'attendance_summaries', 'idx_att_summary_grade_id'):
            op.create_index('idx_att_summary_grade_id', 'attendance_summaries', ['grade_id'])
        if not index_exists(conn, 'attendance_summaries', 'idx_att_summary_stage_id'):
            op.create_index('idx_att_summary_stage_id', 'attendance_summaries', ['stage_id'])
        if not index_exists(conn, 'attendance_summaries', 'idx_att_summary_year_id'):
            op.create_index('idx_att_summary_year_id', 'attendance_summaries', ['year_id'])
        
        # القيد الفريد
        if not constraint_exists(conn, 'attendance_summaries', 'uq_att_summary_school_date_section'):
            op.create_unique_constraint(
                'uq_att_summary_school_date_section',
                'attendance_summaries',
                ['school_id', 'date', 'section_id']
            )
    
    # ============================================================
    # 1️⃣1️⃣ إنشاء جدول attendance_audit_logs
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
        if not index_exists(conn, 'attendance_audit_logs', 'idx_att_audit_attendance_id'):
            op.create_index('idx_att_audit_attendance_id', 'attendance_audit_logs', ['attendance_id'])
        if not index_exists(conn, 'attendance_audit_logs', 'idx_att_audit_type'):
            op.create_index('idx_att_audit_type', 'attendance_audit_logs', ['attendance_type'])
        if not index_exists(conn, 'attendance_audit_logs', 'idx_att_audit_action'):
            op.create_index('idx_att_audit_action', 'attendance_audit_logs', ['action'])
        if not index_exists(conn, 'attendance_audit_logs', 'idx_att_audit_changed_by'):
            op.create_index('idx_att_audit_changed_by', 'attendance_audit_logs', ['changed_by'])
        if not index_exists(conn, 'attendance_audit_logs', 'idx_att_audit_created_at'):
            op.create_index('idx_att_audit_created_at', 'attendance_audit_logs', ['created_at'])
    
    # ============================================================
    # 1️⃣2️⃣ تحديث القيد الفريد في student_attendance
    # ============================================================
    
    if table_exists(conn, 'student_attendance'):
        # التحقق من وجود period_id قبل إنشاء القيد
        if column_exists(conn, 'student_attendance', 'period_id'):
            # حذف القيود القديمة إذا وجدت
            for old_constraint in ['uq_student_att_day_period', 'uq_student_att_student_date_period']:
                if constraint_exists(conn, 'student_attendance', old_constraint):
                    try:
                        op.drop_constraint(old_constraint, 'student_attendance', type_='unique')
                    except Exception:
                        pass
            
            # إضافة القيد الجديد إذا لم يكن موجوداً
            if not constraint_exists(conn, 'student_attendance', 'uq_student_att_student_date_period'):
                op.create_unique_constraint(
                    'uq_student_att_student_date_period',
                    'student_attendance',
                    ['student_id', 'date', 'period_id']
                )
    
    # ============================================================
    # 1️⃣3️⃣ تحديث البيانات الموجودة (ربط السجلات القديمة)
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
# الرجوع للخلف (Downgrade)
# ============================================================

def downgrade() -> None:
    """التراجع عن جميع التغييرات"""
    
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
        if index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_period_id'):
            op.drop_index('idx_teacher_attendance_period_id', table_name='teacher_attendance')
        if index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_year_id'):
            op.drop_index('idx_teacher_attendance_year_id', table_name='teacher_attendance')
        if index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_stage_id'):
            op.drop_index('idx_teacher_attendance_stage_id', table_name='teacher_attendance')
        if index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_grade_id'):
            op.drop_index('idx_teacher_attendance_grade_id', table_name='teacher_attendance')
        if index_exists(conn, 'teacher_attendance', 'idx_teacher_attendance_section_id'):
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
        if index_exists(conn, 'student_attendance', 'idx_student_attendance_year_id'):
            op.drop_index('idx_student_attendance_year_id', table_name='student_attendance')
        if index_exists(conn, 'student_attendance', 'idx_student_attendance_stage_id'):
            op.drop_index('idx_student_attendance_stage_id', table_name='student_attendance')
        if index_exists(conn, 'student_attendance', 'idx_student_attendance_grade_id'):
            op.drop_index('idx_student_attendance_grade_id', table_name='student_attendance')
        
        # حذف الحقول
        if column_exists(conn, 'student_attendance', 'year_id'):
            op.drop_column('student_attendance', 'year_id')
        if column_exists(conn, 'student_attendance', 'stage_id'):
            op.drop_column('student_attendance', 'stage_id')
        if column_exists(conn, 'student_attendance', 'grade_id'):
            op.drop_column('student_attendance', 'grade_id')
    
    # ============================================================
    # 4️⃣ التراجع عن تحديثات students
    # ============================================================
    
    if table_exists(conn, 'students'):
        # حذف الفهارس
        if index_exists(conn, 'students', 'idx_students_year_id'):
            op.drop_index('idx_students_year_id', table_name='students')
        if index_exists(conn, 'students', 'idx_students_stage_id'):
            op.drop_index('idx_students_stage_id', table_name='students')
        if index_exists(conn, 'students', 'idx_students_grade_id'):
            op.drop_index('idx_students_grade_id', table_name='students')
        if index_exists(conn, 'students', 'idx_students_section_id'):
            op.drop_index('idx_students_section_id', table_name='students')
        
        # حذف الحقول
        if column_exists(conn, 'students', 'attendance_updated_at'):
            op.drop_column('students', 'attendance_updated_at')
        if column_exists(conn, 'students', 'attendance_status'):
            op.drop_column('students', 'attendance_status')
        if column_exists(conn, 'students', 'year_id'):
            op.drop_column('students', 'year_id')
        if column_exists(conn, 'students', 'stage_id'):
            op.drop_column('students', 'stage_id')
        if column_exists(conn, 'students', 'grade_id'):
            op.drop_column('students', 'grade_id')
        if column_exists(conn, 'students', 'section_id'):
            op.drop_column('students', 'section_id')
    
    # ============================================================
    # 5️⃣ التراجع عن تحديثات sections
    # ============================================================
    
    if table_exists(conn, 'sections'):
        # حذف الفهارس
        if index_exists(conn, 'sections', 'idx_sections_year_id'):
            op.drop_index('idx_sections_year_id', table_name='sections')
        
        # حذف الحقول
        if column_exists(conn, 'sections', 'is_active'):
            op.drop_column('sections', 'is_active')
        if column_exists(conn, 'sections', 'capacity'):
            op.drop_column('sections', 'capacity')
        if column_exists(conn, 'sections', 'class_teacher_ids'):
            op.drop_column('sections', 'class_teacher_ids')
        if column_exists(conn, 'sections', 'year_id'):
            op.drop_column('sections', 'year_id')
    
    # ============================================================
    # 6️⃣ التراجع عن تحديثات grades
    # ============================================================
    
    if table_exists(conn, 'grades'):
        # حذف الفهارس
        if index_exists(conn, 'grades', 'idx_grades_year_id'):
            op.drop_index('idx_grades_year_id', table_name='grades')
        
        # حذف الحقول
        if column_exists(conn, 'grades', 'is_active'):
            op.drop_column('grades', 'is_active')
        if column_exists(conn, 'grades', 'order'):
            op.drop_column('grades', 'order')
        if column_exists(conn, 'grades', 'year_id'):
            op.drop_column('grades', 'year_id')
    
    # ============================================================
    # 7️⃣ التراجع عن تحديثات stages
    # ============================================================
    
    if table_exists(conn, 'stages'):
        # حذف الفهارس
        if index_exists(conn, 'stages', 'idx_stages_year_id'):
            op.drop_index('idx_stages_year_id', table_name='stages')
        
        # حذف الحقول
        if column_exists(conn, 'stages', 'is_active'):
            op.drop_column('stages', 'is_active')
        if column_exists(conn, 'stages', 'order'):
            op.drop_column('stages', 'order')
        if column_exists(conn, 'stages', 'year_id'):
            op.drop_column('stages', 'year_id')
    
    # ============================================================
    # 8️⃣ التراجع عن تحديثات periods
    # ============================================================
    
    if table_exists(conn, 'periods'):
        if column_exists(conn, 'periods', 'is_active'):
            op.drop_column('periods', 'is_active')
    
    # ============================================================
    # 9️⃣ التراجع عن تحديثات academic_years
    # ============================================================
    
    if table_exists(conn, 'academic_years'):
        if column_exists(conn, 'academic_years', 'is_current'):
            op.drop_column('academic_years', 'is_current')
        if column_exists(conn, 'academic_years', 'is_active'):
            op.drop_column('academic_years', 'is_active')
    
    # ============================================================
    # 🔟 التراجع عن تحديثات student_enrollments
    # ============================================================
    
    if table_exists(conn, 'student_enrollments'):
        if index_exists(conn, 'student_enrollments', 'idx_enrollments_stage_id'):
            op.drop_index('idx_enrollments_stage_id', table_name='student_enrollments')
        if column_exists(conn, 'student_enrollments', 'stage_id'):
            op.drop_column('student_enrollments', 'stage_id')
