# alembic/versions/0025_____20260903_1314_add_notes_column_checked.py

"""إضافة عمود notes إلى جدول schedule_entries مع التحقق

Revision ID: 20260903_1314_checked
Revises: <ضع_معرف_الترحيل_السابق_هنا>
Create Date: 2026-09-03 13:14:21.097258

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0025'
down_revision: Union[str, None] = '0024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    إضافة عمود notes مع التحقق من وجوده مسبقاً
    """
    
    # التحقق من وجود العمود قبل الإضافة
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # التأكد من وجود الجدول
    if 'schedule_entries' not in inspector.get_table_names():
        print("❌ جدول schedule_entries غير موجود في قاعدة البيانات!")
        return
    
    # التحقق من وجود العمود
    existing_columns = [col['name'] for col in inspector.get_columns('schedule_entries')]
    
    if 'notes' not in existing_columns:
        # إضافة العمود
        op.add_column(
            'schedule_entries',
            sa.Column(
                'notes',
                sa.Text(),
                nullable=True,
                comment='ملاحظات على الحصة'
            )
        )
        print("✅ تم إضافة عمود notes إلى جدول schedule_entries")
    else:
        print("ℹ️ عمود notes موجود بالفعل في جدول schedule_entries - لم يتم إجراء أي تغيير")


def downgrade() -> None:
    """
    إزالة عمود notes مع التحقق من وجوده
    """
    
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'schedule_entries' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('schedule_entries')]
        
        if 'notes' in existing_columns:
            op.drop_column('schedule_entries', 'notes')
            print("✅ تم إزالة عمود notes من جدول schedule_entries")
        else:
            print("ℹ️ عمود notes غير موجود - لم يتم إجراء أي تغيير")
