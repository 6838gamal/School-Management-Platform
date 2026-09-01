"""Session lifecycle + excused-leaves + substitutes + audit + alerts + attachments.

Revision ID: 007
Revises: 006
Create Date: 2026-08-31

This migration consolidates every new feature from spec (1)..(11):
- audit_log (append-only history for excused-leaves & transfers)
- excused_leaves (deputy-only "استئذان")
- substitute_assignments (تكليف معلم بديل)
- session_lifecycle (state machine: scheduled → ... → completed)
- timetable_alert_settings (timetable-linked alerts, NOT generic notifications)
- student_attachments (📎 مرفقات ملف الطالب)
- adds health_status to students
- adds late_arrival_minutes to student_attendance
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: '0006'
branch_labels: None
depends_on: None


def upgrade() -> None:
    # ============= 1. audit_log =============
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("actor_role", sa.String(50), nullable=True, index=True),
        sa.Column("action", sa.String(80), nullable=False, index=True),
        sa.Column("entity_type", sa.String(60), nullable=False, index=True),
        sa.Column("entity_id", sa.String(36), nullable=True, index=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("extra", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ============= 2. excused_leaves (استئذان) =============
    op.create_table(
        "excused_leaves",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("section_id", sa.String(36), sa.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("date", sa.String(20), nullable=False, index=True),
        sa.Column("requested_at", sa.String(20), nullable=False),
        sa.Column("exit_time", sa.String(10), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("guardian_name", sa.String(255), nullable=False),
        sa.Column("guardian_relation", sa.String(30), nullable=False),
        sa.Column("guardian_phone", sa.String(50), nullable=False),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("recorded_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ============= 3. substitute_assignments (تكليف معلم بديل) =============
    op.create_table(
        "substitute_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("schedule_entry_id", sa.String(36), sa.ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("absent_teacher_id", sa.String(36), sa.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("substitute_teacher_id", sa.String(36), sa.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.String(20), nullable=False, index=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("accepted_at", sa.String(20), nullable=True),
        sa.Column("rejected_at", sa.String(20), nullable=True),
        sa.Column("completed_at", sa.String(20), nullable=True),
        sa.Column("cancel_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ============= 4. session_lifecycle (state machine) =============
    op.create_table(
        "session_lifecycle",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("schedule_entry_id", sa.String(36), sa.ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.String(20), nullable=False, index=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("teacher_id", sa.String(36), sa.ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("substitute_teacher_id", sa.String(36), sa.ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("recorded_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("uq_session_entry_date", "session_lifecycle", ["schedule_entry_id", "date"], unique=True)

    # ============= 5. timetable_alert_settings (timetable-linked, NOT generic) =============
    op.create_table(
        "timetable_alert_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("assembly_lead_minutes", sa.Integer, nullable=False, server_default="10"),
        sa.Column("period_start_lead_minutes", sa.Integer, nullable=False, server_default="5"),
        sa.Column("period_end_lead_minutes", sa.Integer, nullable=False, server_default="5"),
        sa.Column("preparation_lead_minutes", sa.Integer, nullable=False, server_default="3"),
        sa.Column("late_threshold_minutes", sa.Integer, nullable=False, server_default="10"),
        sa.Column("alert_on_late_preparation", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ============= 6. student_attachments =============
    op.create_table(
        "student_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(30), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ============= 7. Students — health_status =============
    op.add_column("students", sa.Column("health_status", sa.String(40), nullable=True))
    op.add_column("students", sa.Column("health_notes", sa.String(2000), nullable=True))

    # ============= 8. StudentAttendance — late_arrival_minutes + official_holiday flag =============
    op.add_column("student_attendance", sa.Column("late_arrival_minutes", sa.Integer, nullable=True))
    # 'status' was a String(15) — extend by widening (idempotent on PG via alter column)
    op.alter_column("student_attendance", "status", type_=sa.String(20), existing_type=sa.String(15))


def downgrade() -> None:
    op.alter_column("student_attendance", "status", type_=sa.String(15), existing_type=sa.String(20))
    op.drop_column("student_attendance", "late_arrival_minutes")
    op.drop_column("students", "health_notes")
    op.drop_column("students", "health_status")
    op.drop_table("student_attachments")
    op.drop_table("timetable_alert_settings")
    op.drop_index("uq_session_entry_date", table_name="session_lifecycle")
    op.drop_table("session_lifecycle")
    op.drop_table("substitute_assignments")
    op.drop_table("excused_leaves")
    op.drop_table("audit_log")
