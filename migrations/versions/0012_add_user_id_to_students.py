"""Add user_id to students table

Revision ID: 0012
Revises: 0011
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: str | None = '0011'
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


def upgrade() -> None:
    """إضافة عمود user_id إلى جدول students إذا لم يكن موجوداً"""
    
    # التحقق من وجود جدول students
    if not table_exists('students'):
        print("⚠️ جدول students غير موجود، تخطي")
        return
    
    # 1. إضافة العمود user_id إذا لم يكن موجوداً
    if not column_exists('students', 'user_id'):
        op.add_column('students', sa.Column('user_id', sa.String(36), nullable=True))
        print("✅ تم إضافة عمود user_id إلى جدول students")
    else:
        print("⏭️ عمود user_id موجود بالفعل في جدول students")
    
    # 2. إضافة فهرس إذا لم يكن موجوداً
    if not index_exists('students', 'ix_students_user_id'):
        op.create_index('ix_students_user_id', 'students', ['user_id'])
        print("✅ تم إنشاء فهرس ix_students_user_id")
    else:
        print("⏭️ فهرس ix_students_user_id موجود بالفعل")


def downgrade() -> None:
    """حذف عمود user_id من جدول students"""
    
    if not table_exists('students'):
        print("⚠️ جدول students غير موجود، تخطي")
        return
    
    # 1. حذف الفهرس إذا كان موجوداً
    if index_exists('students', 'ix_students_user_id'):
        op.drop_index('ix_students_user_id', table_name='students')
        print("🗑️ تم حذف فهرس ix_students_user_id")
    else:
        print("⏭️ فهرس ix_students_user_id غير موجود")
    
    # 2. حذف العمود إذا كان موجوداً
    if column_exists('students', 'user_id'):
        op.drop_column('students', 'user_id')
        print("🗑️ تم حذف عمود user_id من جدول students")
    else:
        print("⏭️ عمود user_id غير موجود في جدول students")
