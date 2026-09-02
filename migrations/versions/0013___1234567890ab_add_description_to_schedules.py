# migrations/versions/1234567890ab_add_description_to_schedules.py

"""add_description_to_schedules

Revision ID: 1234567890ab
Revises: abcdef123456
Create Date: 2026-09-02 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """إضافة عمود description إلى جدول schedules"""
    # إضافة العمود
    op.add_column(
        'schedules',
        sa.Column('description', sa.Text(), nullable=True)
    )
    
    # (اختياري) إضافة فهرس للبحث
    # op.create_index('ix_schedules_description', 'schedules', ['description'])


def downgrade() -> None:
    """حذف عمود description من جدول schedules"""
    # حذف العمود
    op.drop_column('schedules', 'description')
    
    # (اختياري) حذف الفهرس
    # op.drop_index('ix_schedules_description', table_name='schedules')
