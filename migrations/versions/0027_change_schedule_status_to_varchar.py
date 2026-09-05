"""change_schedule_status_to_varchar

Revision ID: change_schedule_status_to_varchar
Revises: [ضع هنا الـ revision السابق]
Create Date: 2026-09-05 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0027'
down_revision = '0026'  # ضع هنا الـ revision السابق
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    تغيير عمود status من ENUM إلى VARCHAR
    وحذف الـ ENUM type
    """
    
    # 1. تغيير نوع العمود إلى VARCHAR
    op.alter_column(
        'schedules', 
        'status',
        type_=sa.String(50),
        existing_type=postgresql.ENUM('draft', 'published', 'archived', 'cancelled', name='schedulestatus'),
        nullable=False,
        existing_nullable=False,
        server_default='draft'
    )
    
    # 2. حذف الـ ENUM type
    op.execute('DROP TYPE IF EXISTS schedulestatus')


def downgrade() -> None:
    """
    العودة إلى استخدام ENUM
    """
    
    # 1. إعادة إنشاء الـ ENUM
    op.execute("""
        CREATE TYPE schedulestatus AS ENUM (
            'draft', 
            'published', 
            'archived', 
            'cancelled'
        )
    """)
    
    # 2. تغيير نوع العمود إلى ENUM
    op.alter_column(
        'schedules', 
        'status',
        type_=postgresql.ENUM('draft', 'published', 'archived', 'cancelled', name='schedulestatus'),
        existing_type=sa.String(50),
        nullable=False,
        existing_nullable=False,
        server_default='draft'
    )
