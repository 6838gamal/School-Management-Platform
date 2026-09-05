"""add_school_id_to_schedule_entries

Revision ID: add_school_id_to_schedule_entries
Revises: [ضع هنا الـ revision السابق]
Create Date: 2026-09-05 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = '0028'
down_revision = '0027' # ⚠️ استبدل هذا بالـ revision السابق
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    إضافة عمود school_id إلى جدول schedule_entries
    مع التحقق من وجود الجدول والعمود
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # 1. التحقق من وجود الجدول
    tables = inspector.get_table_names()
    
    if 'schedule_entries' not in tables:
        # إنشاء الجدول إذا لم يكن موجوداً
        op.create_table(
            'schedule_entries',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('schedule_id', sa.String(36), nullable=False),
            sa.Column('school_id', sa.String(36), nullable=False),
            sa.Column('day_of_week', sa.Integer, nullable=False),
            sa.Column('period_id', sa.String(36), nullable=False),
            sa.Column('subject_id', sa.String(36), nullable=False),
            sa.Column('teacher_id', sa.String(36), nullable=True),
            sa.Column('room_id', sa.String(36), nullable=True),
            sa.Column('notes', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )
        print("✅ تم إنشاء جدول schedule_entries")
        
        # إضافة الفهارس الأساسية
        op.create_index('idx_schedule_entries_schedule_id', 'schedule_entries', ['schedule_id'])
        op.create_index('idx_schedule_entries_school_id', 'schedule_entries', ['school_id'])
        op.create_index('idx_schedule_entries_period_id', 'schedule_entries', ['period_id'])
        op.create_index('idx_schedule_entries_subject_id', 'schedule_entries', ['subject_id'])
        op.create_index('idx_schedule_entries_teacher_id', 'schedule_entries', ['teacher_id'])
        
        # إضافة القيود
        op.create_foreign_key(
            'fk_schedule_entries_schedule',
            'schedule_entries',
            'schedules',
            ['schedule_id'],
            ['id'],
            ondelete='CASCADE'
        )
        op.create_foreign_key(
            'fk_schedule_entries_period',
            'schedule_entries',
            'periods',
            ['period_id'],
            ['id'],
            ondelete='CASCADE'
        )
        op.create_foreign_key(
            'fk_schedule_entries_subject',
            'schedule_entries',
            'subjects',
            ['subject_id'],
            ['id'],
            ondelete='CASCADE'
        )
        op.create_foreign_key(
            'fk_schedule_entries_teacher',
            'schedule_entries',
            'teachers',
            ['teacher_id'],
            ['id'],
            ondelete='CASCADE'
        )
        op.create_foreign_key(
            'fk_schedule_entries_room',
            'schedule_entries',
            'rooms',
            ['room_id'],
            ['id'],
            ondelete='SET NULL'
        )
        
        print("✅ تم إنشاء جميع الفهارس والقيود")
        return
    
    print("✅ جدول schedule_entries موجود بالفعل")
    
    # 2. التحقق من وجود عمود school_id
    columns = [col['name'] for col in inspector.get_columns('schedule_entries')]
    
    if 'school_id' in columns:
        print("✅ عمود school_id موجود بالفعل في جدول schedule_entries")
        return
    
    print("⚠️ عمود school_id غير موجود، جاري الإضافة...")
    
    # 3. إضافة العمود (مؤقتاً nullable)
    op.add_column('schedule_entries', 
        sa.Column('school_id', sa.String(36), nullable=True)
    )
    print("✅ تم إضافة عمود school_id (nullable)")
    
    # 4. تحديث القيم من الجدول المرتبط
    try:
        result = conn.execute(text("""
            UPDATE schedule_entries se 
            SET school_id = s.school_id 
            FROM schedules s 
            WHERE se.schedule_id = s.id
            AND se.school_id IS NULL
        """))
        print(f"✅ تم تحديث {result.rowcount} سجل بقيم school_id")
    except Exception as e:
        print(f"⚠️ خطأ في تحديث القيم: {str(e)}")
        # إذا كان الجدول فارغاً، لا مشكلة
        pass
    
    # 5. جعل العمود NOT NULL
    op.alter_column('schedule_entries', 'school_id', nullable=False)
    print("✅ تم جعل عمود school_id NOT NULL")
    
    # 6. إضافة فهرس
    op.create_index('idx_schedule_entries_school_id', 'schedule_entries', ['school_id'])
    print("✅ تم إضافة فهرس idx_schedule_entries_school_id")
    
    print("🎉 تم إكمال إضافة عمود school_id بنجاح")


def downgrade() -> None:
    """
    حذف عمود school_id من جدول schedule_entries
    مع التحقق من وجوده
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # التحقق من وجود الجدول
    if 'schedule_entries' not in inspector.get_table_names():
        print("⚠️ جدول schedule_entries غير موجود")
        return
    
    # التحقق من وجود العمود
    columns = [col['name'] for col in inspector.get_columns('schedule_entries')]
    
    if 'school_id' not in columns:
        print("✅ عمود school_id غير موجود في جدول schedule_entries")
        return
    
    print("⚠️ جاري حذف عمود school_id...")
    
    # حذف الفهرس
    try:
        op.drop_index('idx_schedule_entries_school_id', table_name='schedule_entries')
        print("✅ تم حذف الفهرس idx_schedule_entries_school_id")
    except Exception as e:
        print(f"⚠️ خطأ في حذف الفهرس: {str(e)}")
    
    # حذف العمود
    try:
        op.drop_column('schedule_entries', 'school_id')
        print("✅ تم حذف عمود school_id")
    except Exception as e:
        print(f"⚠️ خطأ في حذف العمود: {str(e)}")
    
    print("🎉 تم إكمال حذف عمود school_id")
