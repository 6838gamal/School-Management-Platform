


"""change period_id to integer

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-05 18:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0029'
down_revision = '0028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. حذف المفتاح الخارجي أولاً
    # ============================================================
    op.execute("""
        ALTER TABLE schedule_entries 
        DROP CONSTRAINT IF EXISTS schedule_entries_period_id_fkey
    """)
    
    # ============================================================
    # 2. تغيير نوع period_id في schedule_entries إلى INTEGER
    # ============================================================
    op.execute("""
        ALTER TABLE schedule_entries 
        ALTER COLUMN period_id TYPE INTEGER USING period_id::integer
    """)
    
    # ============================================================
    # 3. تغيير نوع period_id في schedule_template_entries إلى INTEGER
    # ============================================================
    op.execute("""
        ALTER TABLE schedule_template_entries 
        ALTER COLUMN period_id TYPE INTEGER USING period_id::integer
    """)


def downgrade() -> None:
    # ============================================================
    # 1. العودة إلى VARCHAR في schedule_entries
    # ============================================================
    op.execute("""
        ALTER TABLE schedule_entries 
        ALTER COLUMN period_id TYPE VARCHAR USING period_id::text
    """)
    
    # ============================================================
    # 2. العودة إلى VARCHAR في schedule_template_entries
    # ============================================================
    op.execute("""
        ALTER TABLE schedule_template_entries 
        ALTER COLUMN period_id TYPE VARCHAR USING period_id::text
    """)
