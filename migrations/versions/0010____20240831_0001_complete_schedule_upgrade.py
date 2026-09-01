"""20240831_0001_complete_schedule_upgrade.py - الترقية الشاملة لجداول الجداول الدراسية

هذا الملف يحتوي على جميع التغييرات المطلوبة:
1. إنشاء جداول الجداول الدراسية
2. إضافة القيود والمؤشرات
3. إضافة قوالب الجداول
4. ترقية البيانات الموجودة
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '0010'
down_revision: str | None = '0009'
branch_labels: str | None = None
depends_on: str | None = None


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def type_exists(type_name: str) -> bool:
    """التحقق من وجود نوع (Type) في قاعدة البيانات."""
    conn = op.get_bind()
    result = conn.execute(
        text("SELECT 1 FROM pg_type WHERE typname = :type_name"),
        {"type_name": type_name}
    )
    return result.fetchone() is not None


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


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """التحقق من وجود قيد (Constraint) في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    constraints = inspector.get_foreign_keys(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def upgrade() -> None:
    """تطبيق جميع التغييرات على قاعدة البيانات"""
    
    conn = op.get_bind()
    
    # ============================================================
    # الجزء 1: إنشاء Enum للحالات (بدون IF NOT EXISTS)
    # ============================================================
    if not type_exists('schedulestatus'):
        conn.execute(
            text("""
                CREATE TYPE schedulestatus AS ENUM (
                    'draft', 'published', 'archived', 'cancelled'
                )
            """)
        )
        print("✅ تم إنشاء نوع schedulestatus")
    else:
        print("⏭️ نوع schedulestatus موجود بالفعل")
    
    # ============================================================
    # الجزء 2: إنشاء جدول schedules إذا لم يكن موجوداً
    # ============================================================
    if not table_exists('schedules'):
        op.create_table(
            'schedules',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('school_id', sa.String(36), nullable=False, index=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('section_id', sa.String(36), nullable=False, index=True),
            sa.Column('year_id', sa.String(36), nullable=False, index=True),
            sa.Column('status', sa.Enum('draft', 'published', 'archived', 'cancelled', name='schedulestatus'), 
                      nullable=False, server_default='draft'),
            sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
            sa.Column('is_default', sa.Boolean, nullable=False, server_default=sa.text('false')),
            sa.Column('start_date', sa.Date, nullable=True),
            sa.Column('end_date', sa.Date, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), 
                      onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('school_id', 'section_id', 'year_id', name='uq_schedule_section_year'),
            sa.UniqueConstraint('school_id', 'name', name='uq_schedule_school_name')
        )
        print("✅ تم إنشاء جدول schedules")
        
        # إضافة الفهارس
        op.create_index('idx_schedules_status', 'schedules', ['status'])
        op.create_index('idx_schedules_is_active', 'schedules', ['is_active'])
        op.create_index('idx_schedules_start_date', 'schedules', ['start_date'])
        op.create_index('idx_schedules_end_date', 'schedules', ['end_date'])
        op.create_index('idx_schedules_section_active', 'schedules', ['section_id', 'is_active'])
        print("✅ تم إنشاء فهارس جدول schedules")
    else:
        print("⏭️ جدول schedules موجود بالفعل")
        
        # إضافة الأعمدة المفقودة إذا كانت موجودة
        if not column_exists('schedules', 'year_id') and column_exists('schedules', 'academic_year_id'):
            op.alter_column('schedules', 'academic_year_id', new_column_name='year_id')
            print("✅ تم إعادة تسمية academic_year_id إلى year_id")
        
        if not column_exists('schedules', 'status'):
            op.add_column('schedules', sa.Column('status', sa.Enum('draft', 'published', 'archived', 'cancelled', name='schedulestatus'), nullable=False, server_default='draft'))
            print("✅ تم إضافة عمود status")
        
        if not column_exists('schedules', 'is_default'):
            op.add_column('schedules', sa.Column('is_default', sa.Boolean, nullable=False, server_default=sa.text('false')))
            print("✅ تم إضافة عمود is_default")
        
        if not column_exists('schedules', 'start_date'):
            op.add_column('schedules', sa.Column('start_date', sa.Date, nullable=True))
            print("✅ تم إضافة عمود start_date")
        
        if not column_exists('schedules', 'end_date'):
            op.add_column('schedules', sa.Column('end_date', sa.Date, nullable=True))
            print("✅ تم إضافة عمود end_date")
        
        # إضافة الفهارس المفقودة
        if not index_exists('schedules', 'idx_schedules_status'):
            op.create_index('idx_schedules_status', 'schedules', ['status'])
        
        if not index_exists('schedules', 'idx_schedules_is_active'):
            op.create_index('idx_schedules_is_active', 'schedules', ['is_active'])
        
        if not index_exists('schedules', 'idx_schedules_start_date'):
            op.create_index('idx_schedules_start_date', 'schedules', ['start_date'])
        
        if not index_exists('schedules', 'idx_schedules_end_date'):
            op.create_index('idx_schedules_end_date', 'schedules', ['end_date'])
        
        if not index_exists('schedules', 'idx_schedules_section_active'):
            op.create_index('idx_schedules_section_active', 'schedules', ['section_id', 'is_active'])
    
    # ============================================================
    # الجزء 3: إنشاء جدول schedule_entries
    # ============================================================
    if not table_exists('schedule_entries'):
        op.create_table(
            'schedule_entries',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('schedule_id', sa.String(36), nullable=False, index=True),
            sa.Column('day_of_week', sa.Integer, nullable=False),
            sa.Column('period_id', sa.String(36), nullable=False, index=True),
            sa.Column('subject_id', sa.String(36), nullable=False, index=True),
            sa.Column('teacher_id', sa.String(36), nullable=False, index=True),
            sa.Column('room_id', sa.String(36), nullable=True, index=True),
            sa.Column('notes', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), 
                      onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('schedule_id', 'day_of_week', 'period_id', name='uq_schedule_day_period'),
            sa.UniqueConstraint('schedule_id', 'day_of_week', 'subject_id', name='uq_schedule_day_subject'),
            sa.UniqueConstraint('schedule_id', 'day_of_week', 'period_id', 'teacher_id', name='uq_schedule_day_period_teacher'),
            sa.CheckConstraint('day_of_week BETWEEN 0 AND 6', name='ck_schedule_entries_day_of_week')
        )
        print("✅ تم إنشاء جدول schedule_entries")
        
        # إضافة الفهارس
        op.create_index('idx_entries_day_of_week', 'schedule_entries', ['day_of_week'])
        op.create_index('idx_entries_schedule_day', 'schedule_entries', ['schedule_id', 'day_of_week'])
        op.create_index('idx_entries_teacher_day', 'schedule_entries', ['teacher_id', 'day_of_week'])
        print("✅ تم إنشاء فهارس جدول schedule_entries")
    else:
        print("⏭️ جدول schedule_entries موجود بالفعل")
    
    # ============================================================
    # الجزء 4: إنشاء قوالب الجداول
    # ============================================================
    if not table_exists('schedule_templates'):
        op.create_table(
            'schedule_templates',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('school_id', sa.String(36), nullable=False, index=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('days_count', sa.Integer, nullable=False, server_default='5'),
            sa.Column('periods_per_day', sa.Integer, nullable=False, server_default='5'),
            sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), 
                      onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('school_id', 'name', name='uq_template_school_name')
        )
        print("✅ تم إنشاء جدول schedule_templates")
    else:
        print("⏭️ جدول schedule_templates موجود بالفعل")
    
    # ============================================================
    # الجزء 5: إنشاء جدول schedule_template_entries
    # ============================================================
    if not table_exists('schedule_template_entries'):
        op.create_table(
            'schedule_template_entries',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('template_id', sa.String(36), nullable=False, index=True),
            sa.Column('day_of_week', sa.Integer, nullable=False),
            sa.Column('period_id', sa.String(36), nullable=False, index=True),
            sa.Column('subject_id', sa.String(36), nullable=False, index=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), 
                      onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('template_id', 'day_of_week', 'period_id', name='uq_template_day_period'),
            sa.CheckConstraint('day_of_week BETWEEN 0 AND 6', name='ck_template_entries_day_of_week')
        )
        print("✅ تم إنشاء جدول schedule_template_entries")
    else:
        print("⏭️ جدول schedule_template_entries موجود بالفعل")
    
    # ============================================================
    # الجزء 6: ترقية البيانات الموجودة
    # ============================================================
    if table_exists('schedules'):
        try:
            # تحديث status للجداول الموجودة
            conn.execute(text("""
                UPDATE schedules 
                SET status = 'published' 
                WHERE status IS NULL OR status = ''
            """))
            print("✅ تم تحديث حالة الجداول")
            
            # تحديث is_default للجدول الأول لكل شعبة
            conn.execute(text("""
                WITH first_schedule AS (
                    SELECT DISTINCT ON (section_id) id, section_id 
                    FROM schedules 
                    WHERE is_active = true 
                    ORDER BY section_id, created_at
                )
                UPDATE schedules 
                SET is_default = true 
                FROM first_schedule 
                WHERE schedules.id = first_schedule.id
            """))
            print("✅ تم تحديث الجدول الافتراضي لكل شعبة")
            
        except Exception as e:
            print(f"⚠️ تنبيه أثناء ترقية البيانات: {e}")
    
    print("✅ تم الانتهاء من الترقية الشاملة لجداول الجداول الدراسية")


def downgrade() -> None:
    """الرجوع إلى الإصدار السابق - حذف جميع الجداول المضافة"""
    
    conn = op.get_bind()
    
    # ============================================================
    # 1. حذف جداول القوالب
    # ============================================================
    if table_exists('schedule_template_entries'):
        op.drop_table('schedule_template_entries')
        print("🗑️ تم حذف جدول schedule_template_entries")
    
    if table_exists('schedule_templates'):
        op.drop_table('schedule_templates')
        print("🗑️ تم حذف جدول schedule_templates")
    
    # ============================================================
    # 2. حذف جدول schedule_entries
    # ============================================================
    if table_exists('schedule_entries'):
        op.drop_table('schedule_entries')
        print("🗑️ تم حذف جدول schedule_entries")
    
    # ============================================================
    # 3. حذف جدول schedules
    # ============================================================
    if table_exists('schedules'):
        op.drop_table('schedules')
        print("🗑️ تم حذف جدول schedules")
    
    # ============================================================
    # 4. حذف الـ Enum
    # ============================================================
    if type_exists('schedulestatus'):
        conn.execute(text("DROP TYPE schedulestatus"))
        print("🗑️ تم حذف نوع schedulestatus")
    
    print("✅ تم الانتهاء من التراجع عن الترقية")
