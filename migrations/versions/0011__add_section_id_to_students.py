"""add_section_id_to_students

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-29 04:37:35.284564

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: str | None = '0010'
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
    """إضافة عمود section_id إلى جدول students إذا لم يكن موجوداً"""
    
    # التحقق من وجود جدول students
    if not table_exists('students'):
        print("⚠️ جدول students غير موجود، تخطي")
        return
    
    # 1. إضافة العمود section_id إذا لم يكن موجوداً
    if not column_exists('students', 'section_id'):
        op.add_column('students', sa.Column('section_id', sa.String(36), nullable=True))
        print("✅ تم إضافة عمود section_id إلى جدول students")
    else:
        print("⏭️ عمود section_id موجود بالفعل في جدول students")
    
    # 2. إضافة فهرس إذا لم يكن موجوداً (بدون مفتاح خارجي)
    if not index_exists('students', 'ix_students_section_id'):
        op.create_index('ix_students_section_id', 'students', ['section_id'])
        print("✅ تم إنشاء فهرس ix_students_section_id")
    else:
        print("⏭️ فهرس ix_students_section_id موجود بالفعل")


def downgrade() -> None:
    """حذف عمود section_id من جدول students"""
    
    if not table_exists('students'):
        print("⚠️ جدول students غير موجود، تخطي")
        return
    
    # 1. حذف الفهرس إذا كان موجوداً
    if index_exists('students', 'ix_students_section_id'):
        op.drop_index('ix_students_section_id', table_name='students')
        print("🗑️ تم حذف فهرس ix_students_section_id")
    else:
        print("⏭️ فهرس ix_students_section_id غير موجود")
    
    # 2. حذف العمود إذا كان موجوداً
    if column_exists('students', 'section_id'):
        op.drop_column('students', 'section_id')
        print("🗑️ تم حذف عمود section_id من جدول students")
    else:
        print("⏭️ عمود section_id غير موجود في جدول students")
