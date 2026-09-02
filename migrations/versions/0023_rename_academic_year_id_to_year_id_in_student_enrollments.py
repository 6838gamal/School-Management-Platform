# alembic/versions/0023_rename_academic_year_id_to_year_id_in_student_enrollments.py

"""Rename academic_year_id to year_id in student_enrollments table

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-02 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import logging

logger = logging.getLogger(__name__)

revision = '0023'
down_revision = '0022'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """التحقق من وجود عمود في الجدول"""
    try:
        inspector = inspect(op.get_bind())
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.warning(f"Error checking column {column_name}: {e}")
        return False


def table_exists(table_name):
    """التحقق من وجود جدول"""
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def index_exists(table_name, index_name):
    """التحقق من وجود فهرس"""
    try:
        inspector = inspect(op.get_bind())
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        return index_name in indexes
    except Exception:
        return False


def upgrade():
    """تغيير اسم العمود من academic_year_id إلى year_id (إذا لم يكن موجوداً)"""
    
    if not table_exists('student_enrollments'):
        logger.warning("Table 'student_enrollments' does not exist, skipping")
        return
    
    # ============================================================
    # 1. إذا كان academic_year_id موجوداً و year_id غير موجود
    # ============================================================
    if column_exists('student_enrollments', 'academic_year_id') and not column_exists('student_enrollments', 'year_id'):
        logger.info("🔄 Renaming column 'academic_year_id' to 'year_id'")
        
        # حذف الفهرس القديم إذا كان موجوداً
        if index_exists('student_enrollments', 'ix_student_enrollments_academic_year_id'):
            try:
                op.drop_index('ix_student_enrollments_academic_year_id', table_name='student_enrollments')
                logger.info("✅ Dropped old index")
            except Exception as e:
                logger.warning(f"Could not drop index: {e}")
        
        # تغيير اسم العمود
        op.alter_column(
            'student_enrollments',
            'academic_year_id',
            new_column_name='year_id',
            nullable=False
        )
        logger.info("✅ Column renamed to 'year_id'")
        
        # إنشاء فهرس جديد
        if not index_exists('student_enrollments', 'ix_student_enrollments_year_id'):
            op.create_index('ix_student_enrollments_year_id', 'student_enrollments', ['year_id'])
            logger.info("✅ Created new index on year_id")
    
    # ============================================================
    # 2. إذا كان year_id موجوداً بالفعل
    # ============================================================
    elif column_exists('student_enrollments', 'year_id'):
        logger.info("⏭️ Column 'year_id' already exists, skipping rename")
        
        # التأكد من وجود فهرس
        if not index_exists('student_enrollments', 'ix_student_enrollments_year_id'):
            op.create_index('ix_student_enrollments_year_id', 'student_enrollments', ['year_id'])
            logger.info("✅ Created index on year_id")
        
        # إذا كان academic_year_id موجوداً أيضاً، احذفه
        if column_exists('student_enrollments', 'academic_year_id'):
            logger.info("🗑️ Dropping duplicate column 'academic_year_id'")
            try:
                if index_exists('student_enrollments', 'ix_student_enrollments_academic_year_id'):
                    op.drop_index('ix_student_enrollments_academic_year_id', table_name='student_enrollments')
                op.drop_column('student_enrollments', 'academic_year_id')
                logger.info("✅ Dropped duplicate column")
            except Exception as e:
                logger.warning(f"Could not drop duplicate column: {e}")
    
    # ============================================================
    # 3. إذا لم يكن أي من العمودين موجوداً
    # ============================================================
    else:
        logger.info("➕ Adding column 'year_id' to student_enrollments")
        op.add_column(
            'student_enrollments',
            sa.Column('year_id', sa.String(36), nullable=False)
        )
        op.create_index('ix_student_enrollments_year_id', 'student_enrollments', ['year_id'])
        logger.info("✅ Column 'year_id' added with index")
    
    # ============================================================
    # 4. تحديث القيود (Unique Constraint)
    # ============================================================
    try:
        op.drop_constraint('uq_enrollment_student_year', 'student_enrollments', type_='unique')
        logger.info("✅ Dropped old unique constraint")
    except Exception:
        pass
    
    try:
        op.create_unique_constraint(
            'uq_enrollment_student_year',
            'student_enrollments',
            ['student_id', 'year_id']
        )
        logger.info("✅ Created new unique constraint")
    except Exception as e:
        logger.warning(f"Could not create unique constraint: {e}")
    
    logger.info("✅ Migration 0023 completed successfully")


def downgrade():
    """التراجع: تغيير اسم العمود من year_id إلى academic_year_id"""
    
    if not table_exists('student_enrollments'):
        return
    
    if column_exists('student_enrollments', 'year_id') and not column_exists('student_enrollments', 'academic_year_id'):
        logger.info("🔄 Renaming column 'year_id' back to 'academic_year_id'")
        
        if index_exists('student_enrollments', 'ix_student_enrollments_year_id'):
            try:
                op.drop_index('ix_student_enrollments_year_id', table_name='student_enrollments')
            except Exception:
                pass
        
        op.alter_column(
            'student_enrollments',
            'year_id',
            new_column_name='academic_year_id',
            nullable=False
        )
        logger.info("✅ Column renamed back to 'academic_year_id'")
        
        if not index_exists('student_enrollments', 'ix_student_enrollments_academic_year_id'):
            op.create_index('ix_student_enrollments_academic_year_id', 'student_enrollments', ['academic_year_id'])
        
        try:
            op.drop_constraint('uq_enrollment_student_year', 'student_enrollments', type_='unique')
        except Exception:
            pass
        
        try:
            op.create_unique_constraint(
                'uq_enrollment_student_year',
                'student_enrollments',
                ['student_id', 'academic_year_id']
            )
        except Exception:
            pass
