"""20240831_0001_complete_schedule_upgrade.py - الترقية الشاملة لجداول الجداول الدراسية

هذا الملف يحتوي على جميع التغييرات المطلوبة:
1. إنشاء جداول الجداول الدراسية
2. إضافة القيود والمؤشرات
3. إضافة قوالب الجداول
4. ترقية البيانات الموجودة
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text
import uuid

# revision identifiers, used by Alembic.
revision = '20240831_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """تطبيق جميع التغييرات على قاعدة البيانات"""
    
    conn = op.get_bind()
    
    # ============================================================
    # الجزء 1: إنشاء الجداول الأساسية
    # ============================================================
    
    # 1.1 إنشاء Enum للحالات
    op.execute("""
        CREATE TYPE IF NOT EXISTS schedulestatus AS ENUM (
            'draft', 'published', 'archived', 'cancelled'
        )
    """)
    
    # 1.2 إنشاء جدول schedules
    op.create_table(
        'schedules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('school_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('section_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('year_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', 'cancelled', name='schedulestatus'), 
                  nullable=False, server_default='draft'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), 
                  onupdate=sa.func.now()),
    )
    
    # 1.3 إضافة القيود الأجنبية لجدول schedules
    op.create_foreign_key(
        'fk_schedules_school', 'schedules', 'schools',
        ['school_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_schedules_section', 'schedules', 'sections',
        ['section_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_schedules_year', 'schedules', 'academic_years',
        ['year_id'], ['id'], ondelete='CASCADE'
    )
    
    # 1.4 إنشاء جدول schedule_entries
    op.create_table(
        'schedule_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('schedule_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('day_of_week', sa.Integer, nullable=False),
        sa.Column('period_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('subject_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('teacher_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('room_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), 
                  onupdate=sa.func.now()),
    )
    
    # 1.5 إضافة القيود الأجنبية لجدول schedule_entries
    op.create_foreign_key(
        'fk_schedule_entries_schedule', 'schedule_entries', 'schedules',
        ['schedule_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_schedule_entries_period', 'schedule_entries', 'periods',
        ['period_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_schedule_entries_subject', 'schedule_entries', 'subjects',
        ['subject_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_schedule_entries_teacher', 'schedule_entries', 'teachers',
        ['teacher_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_schedule_entries_room', 'schedule_entries', 'rooms',
        ['room_id'], ['id'], ondelete='SET NULL'
    )
    
    # ============================================================
    # الجزء 2: إضافة القيود والمؤشرات
    # ============================================================
    
    # 2.1 قيود جدول schedules
    op.create_unique_constraint(
        'uq_schedule_section_year',
        'schedules',
        ['school_id', 'section_id', 'year_id']
    )
    
    op.create_unique_constraint(
        'uq_schedule_school_name',
        'schedules',
        ['school_id', 'name']
    )
    
    # 2.2 مؤشرات جدول schedules
    op.create_index('idx_schedules_status', 'schedules', ['status'])
    op.create_index('idx_schedules_is_active', 'schedules', ['is_active'])
    op.create_index('idx_schedules_start_date', 'schedules', ['start_date'])
    op.create_index('idx_schedules_end_date', 'schedules', ['end_date'])
    op.create_index('idx_schedules_section_active', 'schedules', ['section_id', 'is_active'])
    
    # 2.3 قيود جدول schedule_entries
    op.create_unique_constraint(
        'uq_schedule_day_period',
        'schedule_entries',
        ['schedule_id', 'day_of_week', 'period_id']
    )
    
    op.create_unique_constraint(
        'uq_schedule_day_subject',
        'schedule_entries',
        ['schedule_id', 'day_of_week', 'subject_id']
    )
    
    op.create_unique_constraint(
        'uq_schedule_day_period_teacher',
        'schedule_entries',
        ['schedule_id', 'day_of_week', 'period_id', 'teacher_id']
    )
    
    # 2.4 مؤشرات جدول schedule_entries
    op.create_index('idx_entries_day_of_week', 'schedule_entries', ['day_of_week'])
    op.create_index('idx_entries_schedule_day', 'schedule_entries', ['schedule_id', 'day_of_week'])
    op.create_index('idx_entries_teacher_day', 'schedule_entries', ['teacher_id', 'day_of_week'])
    
    # 2.5 قيد التحقق من day_of_week (0-6)
    op.create_check_constraint(
        'ck_schedule_entries_day_of_week',
        'schedule_entries',
        'day_of_week BETWEEN 0 AND 6'
    )
    
    # ============================================================
    # الجزء 3: إنشاء قوالب الجداول
    # ============================================================
    
    # 3.1 إنشاء جدول schedule_templates
    op.create_table(
        'schedule_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('school_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('days_count', sa.Integer, nullable=False, server_default='5'),
        sa.Column('periods_per_day', sa.Integer, nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), 
                  onupdate=sa.func.now()),
    )
    
    # 3.2 إضافة القيود لجدول schedule_templates
    op.create_foreign_key(
        'fk_templates_school', 'schedule_templates', 'schools',
        ['school_id'], ['id'], ondelete='CASCADE'
    )
    
    op.create_unique_constraint(
        'uq_template_school_name',
        'schedule_templates',
        ['school_id', 'name']
    )
    
    # 3.3 إنشاء جدول schedule_template_entries
    op.create_table(
        'schedule_template_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('template_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('day_of_week', sa.Integer, nullable=False),
        sa.Column('period_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('subject_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), 
                  onupdate=sa.func.now()),
    )
    
    # 3.4 إضافة القيود لجدول schedule_template_entries
    op.create_foreign_key(
        'fk_template_entries_template', 'schedule_template_entries', 'schedule_templates',
        ['template_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_template_entries_period', 'schedule_template_entries', 'periods',
        ['period_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_template_entries_subject', 'schedule_template_entries', 'subjects',
        ['subject_id'], ['id'], ondelete='CASCADE'
    )
    
    op.create_unique_constraint(
        'uq_template_day_period',
        'schedule_template_entries',
        ['template_id', 'day_of_week', 'period_id']
    )
    
    op.create_check_constraint(
        'ck_template_entries_day_of_week',
        'schedule_template_entries',
        'day_of_week BETWEEN 0 AND 6'
    )
    
    # ============================================================
    # الجزء 4: ترقية البيانات الموجودة
    # ============================================================
    
    # 4.1 التحقق من وجود جداول قديمة وترقيتها
    try:
        # التحقق من وجود عمود academic_year_id في schedules
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('schedules')]
        
        if 'academic_year_id' in columns:
            # نقل البيانات من academic_year_id إلى year_id
            conn.execute(text("""
                UPDATE schedules 
                SET year_id = academic_year_id 
                WHERE year_id IS NULL AND academic_year_id IS NOT NULL
            """))
            
            # حذف العمود القديم
            op.drop_column('schedules', 'academic_year_id')
        
        # تحديث status للجداول الموجودة
        conn.execute(text("""
            UPDATE schedules 
            SET status = 'published' 
            WHERE status IS NULL OR status = ''
        """))
        
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
        
        # 4.2 ترقية schedule_entries إذا كانت موجودة مسبقاً
        if 'schedule_id' in columns:
            # إضافة عمود notes إذا لم يكن موجوداً
            if 'notes' not in columns:
                op.add_column('schedule_entries', sa.Column('notes', sa.Text, nullable=True))
            
            # إضافة عمود room_id إذا لم يكن موجوداً
            if 'room_id' not in columns:
                op.add_column('schedule_entries', sa.Column('room_id', UUID(as_uuid=True), nullable=True))
                op.create_foreign_key(
                    'fk_schedule_entries_room', 'schedule_entries', 'rooms',
                    ['room_id'], ['id'], ondelete='SET NULL'
                )
                
    except Exception as e:
        # تجاهل الأخطاء إذا كانت الجداول غير موجودة
        print(f"⚠️ تنبيه: {e}")
        pass
    
    # ============================================================
    # الجزء 5: دوال مساعدة (Functions)
    # ============================================================
    
    # 5.1 دالة للحصول على عدد الحصص في الجدول
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION get_schedule_entry_count(schedule_id UUID)
        RETURNS INTEGER AS $$
        BEGIN
            RETURN (SELECT COUNT(*) FROM schedule_entries WHERE schedule_id = $1);
        END;
        $$ LANGUAGE plpgsql;
    """))
    
    # 5.2 دالة للحصول على عدد الأيام في الجدول
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION get_schedule_days_count(schedule_id UUID)
        RETURNS INTEGER AS $$
        BEGIN
            RETURN (SELECT COUNT(DISTINCT day_of_week) FROM schedule_entries WHERE schedule_id = $1);
        END;
        $$ LANGUAGE plpgsql;
    """))
    
    # 5.3 دالة للحصول على إجمالي الحصص في الأسبوع
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION get_schedule_total_periods(schedule_id UUID)
        RETURNS INTEGER AS $$
        DECLARE
            total INTEGER;
        BEGIN
            SELECT COUNT(*) INTO total 
            FROM schedule_entries 
            WHERE schedule_id = $1;
            RETURN total;
        END;
        $$ LANGUAGE plpgsql;
    """))
    
    # 5.4 دالة للتحقق من صحة الجدول
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION validate_schedule(schedule_id UUID)
        RETURNS TABLE(
            is_valid BOOLEAN,
            error_message TEXT
        ) AS $$
        DECLARE
            entry_count INTEGER;
            day_count INTEGER;
        BEGIN
            -- التحقق من وجود حصص
            SELECT COUNT(*) INTO entry_count FROM schedule_entries WHERE schedule_id = $1;
            
            IF entry_count = 0 THEN
                RETURN QUERY SELECT false, 'الجدول لا يحتوي على أي حصص';
                RETURN;
            END IF;
            
            -- التحقق من وجود أيام
            SELECT COUNT(DISTINCT day_of_week) INTO day_count FROM schedule_entries WHERE schedule_id = $1;
            
            IF day_count = 0 THEN
                RETURN QUERY SELECT false, 'الجدول لا يحتوي على أي أيام';
                RETURN;
            END IF;
            
            -- التحقق من عدم وجود حصص مكررة
            IF EXISTS (
                SELECT 1 
                FROM schedule_entries 
                WHERE schedule_id = $1 
                GROUP BY day_of_week, period_id 
                HAVING COUNT(*) > 1
            ) THEN
                RETURN QUERY SELECT false, 'يوجد حصص مكررة في نفس اليوم والفترة';
                RETURN;
            END IF;
            
            RETURN QUERY SELECT true, 'الجدول صحيح';
        END;
        $$ LANGUAGE plpgsql;
    """))


def downgrade() -> None:
    """الرجوع إلى الإصدار السابق - حذف جميع الجداول المضافة"""
    
    conn = op.get_bind()
    
    # ============================================================
    # 1. حذف الدوال المساعدة
    # ============================================================
    try:
        conn.execute(text("DROP FUNCTION IF EXISTS validate_schedule(UUID)"))
        conn.execute(text("DROP FUNCTION IF EXISTS get_schedule_total_periods(UUID)"))
        conn.execute(text("DROP FUNCTION IF EXISTS get_schedule_days_count(UUID)"))
        conn.execute(text("DROP FUNCTION IF EXISTS get_schedule_entry_count(UUID)"))
    except Exception:
        pass
    
    # ============================================================
    # 2. حذف جداول القوالب
    # ============================================================
    try:
        op.drop_table('schedule_template_entries')
    except Exception:
        pass
    
    try:
        op.drop_table('schedule_templates')
    except Exception:
        pass
    
    # ============================================================
    # 3. حذف جدول schedule_entries
    # ============================================================
    try:
        op.drop_constraint('ck_schedule_entries_day_of_week', 'schedule_entries')
    except Exception:
        pass
    
    try:
        op.drop_constraint('uq_schedule_day_period_teacher', 'schedule_entries')
    except Exception:
        pass
    
    try:
        op.drop_constraint('uq_schedule_day_subject', 'schedule_entries')
    except Exception:
        pass
    
    try:
        op.drop_constraint('uq_schedule_day_period', 'schedule_entries')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_entries_teacher_day', 'schedule_entries')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_entries_schedule_day', 'schedule_entries')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_entries_day_of_week', 'schedule_entries')
    except Exception:
        pass
    
    try:
        op.drop_table('schedule_entries')
    except Exception:
        pass
    
    # ============================================================
    # 4. حذف جدول schedules
    # ============================================================
    try:
        op.drop_constraint('uq_schedule_school_name', 'schedules')
    except Exception:
        pass
    
    try:
        op.drop_constraint('uq_schedule_section_year', 'schedules')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_schedules_section_active', 'schedules')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_schedules_end_date', 'schedules')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_schedules_start_date', 'schedules')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_schedules_is_active', 'schedules')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_schedules_status', 'schedules')
    except Exception:
        pass
    
    try:
        op.drop_table('schedules')
    except Exception:
        pass
    
    # ============================================================
    # 5. حذف الـ Enum
    # ============================================================
    try:
        op.execute('DROP TYPE IF EXISTS schedulestatus')
    except Exception:
        pass
