# alembic/versions/0029_change_period_id_to_integer.py
"""change period_id to integer

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-05 18:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0029'
down_revision = '0028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # تغيير نوع period_id في schedule_entries
    op.execute("""
        ALTER TABLE schedule_entries 
        ALTER COLUMN period_id TYPE INTEGER USING period_id::integer
    """)
    
    # تغيير نوع period_id في schedule_template_entries
    op.execute("""
        ALTER TABLE schedule_template_entries 
        ALTER COLUMN period_id TYPE INTEGER USING period_id::integer
    """)


def downgrade() -> None:
    # العودة إلى VARCHAR
    op.execute("""
        ALTER TABLE schedule_entries 
        ALTER COLUMN period_id TYPE VARCHAR USING period_id::text
    """)
    
    op.execute("""
        ALTER TABLE schedule_template_entries 
        ALTER COLUMN period_id TYPE VARCHAR USING period_id::text
    """)
