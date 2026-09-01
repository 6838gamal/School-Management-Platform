"""add academic_year_id to schedules

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | None = None
depends_on: str | None = None


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في جدول."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)


def index_exists(table_name: str, index_name: str) -> bool:
    """التحقق من وجود فهرس في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """التحقق من وجود قيد (Constraint) في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    constraints = inspector.get_foreign_keys(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def upgrade() -> None:
    """إضافة عمود academic_year_id إلى جدول schedules إذا لم يكن موجوداً"""
    
    # التحقق من وجود الجدول
    if not table_exists('schedules'):
        print("⚠️ جدول schedules غير موجود، تخطي")
        return
    
    # 1. إضافة العمود إذا لم يكن موجوداً
    if not column_exists('schedules', 'academic_year_id'):
        op.add_column('schedules', 
            sa.Column('academic_year_id', sa.String(36), nullable=True)
        )
        print("✅ تم إضافة عمود academic_year_id إلى جدول schedules")
    else:
        print("⏭️ عمود academic_year_id موجود بالفعل في جدول schedules")
    
    # 2. إضافة المفتاح الخارجي إذا لم يكن موجوداً
    if table_exists('academic_years') and not constraint_exists('schedules', 'fk_schedules_academic_year_id'):
        try:
            op.create_foreign_key(
                'fk_schedules_academic_year_id',
                'schedules',
                'academic_years',
                ['academic_year_id'],
                ['id'],
                ondelete='CASCADE'
            )
            print("✅ تم إضافة المفتاح الخارجي fk_schedules_academic_year_id")
        except Exception as e:
            print(f"⚠️ فشل إضافة المفتاح الخارجي: {e}")
    else:
        print("⏭️ المفتاح الخارجي fk_schedules_academic_year_id موجود بالفعل أو جدول academic_years غير موجود")
    
    # 3. إضافة فهرس إذا لم يكن موجوداً
    if not index_exists('schedules', 'ix_schedules_academic_year_id'):
        op.create_index(
            'ix_schedules_academic_year_id',
            'schedules',
            ['academic_year_id']
        )
        print("✅ تم إضافة الفهرس ix_schedules_academic_year_id")
    else:
        print("⏭️ الفهرس ix_schedules_academic_year_id موجود بالفعل")


def downgrade() -> None:
    """حذف عمود academic_year_id من جدول schedules"""
    
    if not table_exists('schedules'):
        print("⚠️ جدول schedules غير موجود، تخطي")
        return
    
    # 1. حذف المفتاح الخارجي إذا كان موجوداً
    if constraint_exists('schedules', 'fk_schedules_academic_year_id'):
        try:
            op.drop_constraint('fk_schedules_academic_year_id', 'schedules', type_='foreignkey')
            print("🗑️ تم حذف المفتاح الخارجي fk_schedules_academic_year_id")
        except Exception as e:
            print(f"⚠️ فشل حذف المفتاح الخارجي: {e}")
    else:
        print("⏭️ المفتاح الخارجي fk_schedules_academic_year_id غير موجود")
    
    # 2. حذف الفهرس إذا كان موجوداً
    if index_exists('schedules', 'ix_schedules_academic_year_id'):
        op.drop_index('ix_schedules_academic_year_id', table_name='schedules')
        print("🗑️ تم حذف الفهرس ix_schedules_academic_year_id")
    else:
        print("⏭️ الفهرس ix_schedules_academic_year_id غير موجود")
    
    # 3. حذف العمود إذا كان موجوداً
    if column_exists('schedules', 'academic_year_id'):
        op.drop_column('schedules', 'academic_year_id')
        print("🗑️ تم حذف عمود academic_year_id من جدول schedules")
    else:
        print("⏭️ عمود academic_year_id غير موجود في جدول schedules")
