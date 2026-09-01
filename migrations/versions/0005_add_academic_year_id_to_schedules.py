"""add academic_year_id to schedules

Revision ID: 004
Revises: previous_revision_id
Create Date: 2026-08-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'  # استخدم الرقم الذي تم إنشاؤه
down_revision: str | None = '0004' # استخدم الـ revision السابق
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # إضافة العمود academic_year_id إلى جدول schedules
    op.add_column('schedules', 
        sa.Column('academic_year_id', sa.String(36), nullable=True)
    )
    
    # إضافة المفتاح الخارجي
    op.create_foreign_key(
        'fk_schedules_academic_year_id',
        'schedules',
        'academic_years',
        ['academic_year_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # إضافة فهرس
    op.create_index(
        'ix_schedules_academic_year_id',
        'schedules',
        ['academic_year_id']
    )


def downgrade() -> None:
    # حذف المفتاح الخارجي
    op.drop_constraint('fk_schedules_academic_year_id', 'schedules', type_='foreignkey')
    
    # حذف الفهرس
    op.drop_index('ix_schedules_academic_year_id', table_name='schedules')
    
    # حذف العمود
    op.drop_column('schedules', 'academic_year_id')
