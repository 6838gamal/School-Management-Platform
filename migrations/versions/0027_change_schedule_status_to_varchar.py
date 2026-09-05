# alembic/versions/0027_change_schedule_status_to_varchar.py
from alembic import op
import sqlalchemy as sa


revision = '0027'
down_revision = '0026'  # استبدل بالـ revision السابق
branch_labels = None
depends_on = None

def upgrade():
    # تغيير نوع العمود إلى VARCHAR
    op.alter_column('schedules', 'status',
                    type_=sa.String(50),
                    existing_type=sa.Enum('draft', 'published', 'archived', 'cancelled', name='schedulestatus'),
                    nullable=True)
    # حذف الـ ENUM
    op.execute('DROP TYPE IF EXISTS schedulestatus')

def downgrade():
    # إعادة إنشاء الـ ENUM
    op.execute("CREATE TYPE schedulestatus AS ENUM ('draft', 'published', 'archived', 'cancelled')")
    op.alter_column('schedules', 'status',
                    type_=sa.Enum('draft', 'published', 'archived', 'cancelled', name='schedulestatus'),
                    existing_type=sa.String(50),
                    nullable=True)
