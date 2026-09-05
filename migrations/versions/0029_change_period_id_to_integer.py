# alembic/versions/0029_change_period_id_to_integer.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # تغيير نوع period_id في schedule_entries
    op.alter_column('schedule_entries', 'period_id',
                    type_=sa.Integer(),
                    existing_type=sa.String(),
                    postgresql_using='period_id::integer')
    
    # تغيير نوع period_id في schedule_template_entries
    op.alter_column('schedule_template_entries', 'period_id',
                    type_=sa.Integer(),
                    existing_type=sa.String(),
                    postgresql_using='period_id::integer')

def downgrade():
    # العودة إلى VARCHAR
    op.alter_column('schedule_entries', 'period_id',
                    type_=sa.String(),
                    existing_type=sa.Integer())
    
    op.alter_column('schedule_template_entries', 'period_id',
                    type_=sa.String(),
                    existing_type=sa.Integer())
