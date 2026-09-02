# alembic/versions/0016_add_academic_fields_to_students.py

"""Add academic fields (year_id, grade_id, section_id, period_id) to students table

Revision ID: xxxx
Revises: previous_revision_id
Create Date: 2026-09-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '0016'
down_revision: Union[str, None] = '0015'  # ضع الـ revision السابق هنا
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في الجدول"""
    try:
        inspector = inspect(op.get_bind())
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.warning(f"Error checking column {column_name}: {e}")
        return False


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول"""
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.warning(f"Error checking table {table_name}: {e}")
        return False


def index_exists(table_name: str, index_name: str) -> bool:
    """التحقق من وجود فهرس"""
    try:
        inspector = inspect(op.get_bind())
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        return index_name in indexes
    except Exception as e:
        logger.warning(f"Error checking index {index_name}: {e}")
        return False


def upgrade() -> None:
    """إضافة الحقول الأكاديمية إلى جدول students مع التحقق الكامل"""
    
    # التحقق من وجود الجدول
    if not table_exists('students'):
        logger.warning("Table 'students' does not exist, skipping migration")
        return
    
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # ========== 1. إضافة year_id ==========
    if not column_exists('students', 'year_id'):
        logger.info("Adding column 'year_id' to 'students'")
        
        # إضافة العمود (nullable مؤقتاً)
        op.add_column(
            'students',
            sa.Column(
                'year_id',
                sa.String(36),
                nullable=True,
                comment='معرف السنة الدراسية'
            )
        )
        
        # إنشاء فهرس
        if not index_exists('students', 'ix_students_year_id'):
            op.create_index('ix_students_year_id', 'students', ['year_id'])
            logger.info("Created index on year_id")
        
        # محاولة تحديث البيانات الموجودة من student_enrollments
        try:
            if table_exists('student_enrollments') and column_exists('student_enrollments', 'year_id'):
                if dialect == 'sqlite':
                    # SQLite
                    op.execute("""
                        UPDATE students 
                        SET year_id = (
                            SELECT year_id FROM student_enrollments 
                            WHERE student_enrollments.student_id = students.id 
                            AND student_enrollments.status = 'active'
                            LIMIT 1
                        )
                        WHERE year_id IS NULL
                    """)
                else:
                    # PostgreSQL, MySQL, etc.
                    op.execute("""
                        UPDATE students s
                        SET year_id = e.year_id
                        FROM student_enrollments e
                        WHERE s.id = e.student_id
                        AND e.status = 'active'
                        AND s.year_id IS NULL
                    """)
                logger.info("Updated year_id from student_enrollments")
            else:
                logger.warning("Table 'student_enrollments' or column 'year_id' not found, skipping data update")
        except Exception as e:
            logger.error(f"Error updating year_id: {e}")
        
        # جعل العمود NOT NULL إذا كانت جميع البيانات محدثة
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM students WHERE year_id IS NULL"))
            count = result.scalar()
            if count == 0:
                op.alter_column('students', 'year_id', nullable=False)
                logger.info("Set year_id as NOT NULL")
            else:
                logger.warning(f"{count} rows have NULL year_id, keeping as nullable")
        except Exception as e:
            logger.error(f"Error setting year_id NOT NULL: {e}")
    else:
        logger.info("Column 'year_id' already exists, skipping")
    
    # ========== 2. إضافة grade_id ==========
    if not column_exists('students', 'grade_id'):
        logger.info("Adding column 'grade_id' to 'students'")
        
        op.add_column(
            'students',
            sa.Column(
                'grade_id',
                sa.String(36),
                nullable=True,
                comment='معرف الصف'
            )
        )
        
        if not index_exists('students', 'ix_students_grade_id'):
            op.create_index('ix_students_grade_id', 'students', ['grade_id'])
            logger.info("Created index on grade_id")
        
        # محاولة تحديث البيانات الموجودة من sections
        try:
            if table_exists('sections') and column_exists('sections', 'grade_id'):
                if dialect == 'sqlite':
                    op.execute("""
                        UPDATE students 
                        SET grade_id = (
                            SELECT grade_id FROM sections 
                            WHERE sections.id = students.section_id
                            LIMIT 1
                        )
                        WHERE grade_id IS NULL AND section_id IS NOT NULL
                    """)
                else:
                    op.execute("""
                        UPDATE students s
                        SET grade_id = sec.grade_id
                        FROM sections sec
                        WHERE s.section_id = sec.id
                        AND s.grade_id IS NULL
                    """)
                logger.info("Updated grade_id from sections")
            else:
                logger.warning("Table 'sections' or column 'grade_id' not found")
        except Exception as e:
            logger.error(f"Error updating grade_id: {e}")
    else:
        logger.info("Column 'grade_id' already exists, skipping")
    
    # ========== 3. section_id (قد يكون موجوداً بالفعل) ==========
    # نتحقق من وجود section_id، إذا لم يكن موجوداً نضيفه
    if not column_exists('students', 'section_id'):
        logger.info("Adding column 'section_id' to 'students'")
        
        op.add_column(
            'students',
            sa.Column(
                'section_id',
                sa.String(36),
                nullable=True,
                comment='معرف الشعبة'
            )
        )
        
        if not index_exists('students', 'ix_students_section_id'):
            op.create_index('ix_students_section_id', 'students', ['section_id'])
            logger.info("Created index on section_id")
        
        # محاولة تحديث البيانات الموجودة من student_enrollments
        try:
            if table_exists('student_enrollments') and column_exists('student_enrollments', 'section_id'):
                if dialect == 'sqlite':
                    op.execute("""
                        UPDATE students 
                        SET section_id = (
                            SELECT section_id FROM student_enrollments 
                            WHERE student_enrollments.student_id = students.id 
                            AND student_enrollments.status = 'active'
                            LIMIT 1
                        )
                        WHERE section_id IS NULL
                    """)
                else:
                    op.execute("""
                        UPDATE students s
                        SET section_id = e.section_id
                        FROM student_enrollments e
                        WHERE s.id = e.student_id
                        AND e.status = 'active'
                        AND s.section_id IS NULL
                    """)
                logger.info("Updated section_id from student_enrollments")
        except Exception as e:
            logger.error(f"Error updating section_id: {e}")
    else:
        logger.info("Column 'section_id' already exists, skipping")
    
    

def downgrade() -> None:
    """حذف الحقول المضافة (التراجع) مع التحقق الكامل"""
    
    if not table_exists('students'):
        return
    
    
    
    # ========== 2. حذف grade_id ==========
    if column_exists('students', 'grade_id'):
        logger.info("Dropping column 'grade_id'")
        
        if index_exists('students', 'ix_students_grade_id'):
            try:
                op.drop_index('ix_students_grade_id', table_name='students')
                logger.info("Dropped index on grade_id")
            except Exception as e:
                logger.warning(f"Could not drop index: {e}")
        
        op.drop_column('students', 'grade_id')
        logger.info("Column 'grade_id' dropped")
    
    # ========== 3. حذف year_id ==========
    if column_exists('students', 'year_id'):
        logger.info("Dropping column 'year_id'")
        
        if index_exists('students', 'ix_students_year_id'):
            try:
                op.drop_index('ix_students_year_id', table_name='students')
                logger.info("Dropped index on year_id")
            except Exception as e:
                logger.warning(f"Could not drop index: {e}")
        
        op.drop_column('students', 'year_id')
        logger.info("Column 'year_id' dropped")
    
    # ========== 4. ملاحظة: لا نحذف section_id لأنه قد يكون موجوداً مسبقاً ==========
    # نتحقق إذا كان section_id موجوداً مسبقاً قبل هذا الترحيل، إذا كان جديداً نحذفه
    # لكن نظراً لأن section_id قد يكون عموداً قديماً، نتركه
    
    logger.info("Downgrade completed. Note: section_id was not dropped as it may be an existing column.")


# ============================================================
# نسخة بديلة للترقية مع إنشاء الجدول من الصفر (إذا لزم الأمر)
# ============================================================

def upgrade_full() -> None:
    """
    نسخة بديلة: إعادة إنشاء الجدول بالكامل مع الحقول الجديدة.
    تستخدم إذا كانت هناك مشاكل مع ALTER TABLE.
    """
    # هذه الطريقة تستخدم فقط إذا كانت قاعدة البيانات تدعم RENAME
    # وتحتاج إلى نسخ البيانات أولاً
    
    # 1. إنشاء جدول جديد بالهيكل الكامل
    op.execute("""
        CREATE TABLE students_new (
            id VARCHAR(36) NOT NULL,
            school_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36),
            year_id VARCHAR(36),
            grade_id VARCHAR(36),
            section_id VARCHAR(36),
            
            student_number VARCHAR(50) NOT NULL,
            national_id VARCHAR(50),
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            first_name_ar VARCHAR(100),
            last_name_ar VARCHAR(100),
            gender VARCHAR(10),
            birth_date DATE,
            nationality VARCHAR(50),
            guardian_name VARCHAR(255),
            guardian_phone VARCHAR(50),
            guardian_email VARCHAR(255),
            guardian_relation VARCHAR(50),
            phone VARCHAR(50),
            address VARCHAR(500),
            photo_url VARCHAR(500),
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            enrollment_status VARCHAR(20) DEFAULT 'active' NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            PRIMARY KEY (id)
        )
    """)
    
    # 2. نسخ البيانات من الجدول القديم
    op.execute("""
        INSERT INTO students_new (
            id, school_id, user_id, student_number, national_id,
            first_name, last_name, first_name_ar, last_name_ar,
            gender, birth_date, nationality,
            guardian_name, guardian_phone, guardian_email, guardian_relation,
            phone, address, photo_url, is_active, enrollment_status,
            created_at, updated_at
        )
        SELECT 
            id, school_id, user_id, student_number, national_id,
            first_name, last_name, first_name_ar, last_name_ar,
            gender, birth_date, nationality,
            guardian_name, guardian_phone, guardian_email, guardian_relation,
            phone, address, photo_url, is_active, enrollment_status,
            created_at, updated_at
        FROM students
    """)
    
    # 3. حذف الجدول القديم
    op.execute("DROP TABLE students")
    
    # 4. إعادة تسمية الجدول الجديد
    op.execute("ALTER TABLE students_new RENAME TO students")
    
    # 5. إنشاء الفهارس
    op.create_index('ix_students_school_id', 'students', ['school_id'])
    op.create_index('ix_students_user_id', 'students', ['user_id'])
    op.create_index('ix_students_year_id', 'students', ['year_id'])
    op.create_index('ix_students_grade_id', 'students', ['grade_id'])
    op.create_index('ix_students_section_id', 'students', ['section_id'])
    
    op.create_index('ix_students_student_number', 'students', ['student_number'])
