"""initial_dental_schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-11

Rollback note:
Run `alembic downgrade base` to drop `booking_status_audits`, `contact_messages`, and `appointment_requests` if rolling back initial creation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointment_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reference_code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("service_slug", sa.String(length=80), nullable=False),
        sa.Column("preferred_dentist_slug", sa.String(length=80), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_time_slot", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("consent_given", sa.Boolean(), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("utm_source", sa.String(length=80), nullable=True),
        sa.Column("utm_medium", sa.String(length=80), nullable=True),
        sa.Column("utm_campaign", sa.String(length=100), nullable=True),
        sa.Column("client_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointment_requests_reference_code", "appointment_requests", ["reference_code"], unique=True)
    op.create_index("ix_appointment_requests_preferred_date", "appointment_requests", ["preferred_date"], unique=False)
    op.create_index("ix_appointment_requests_status", "appointment_requests", ["status"], unique=False)
    op.create_index("idx_appt_date_status", "appointment_requests", ["preferred_date", "status"], unique=False)
    op.create_index(
        "idx_appt_dentist_slot",
        "appointment_requests",
        ["preferred_dentist_slug", "preferred_date", "preferred_time_slot"],
        unique=False,
    )

    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reference_code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("subject", sa.String(length=150), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("consent_given", sa.Boolean(), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contact_messages_reference_code", "contact_messages", ["reference_code"], unique=True)
    op.create_index("ix_contact_messages_status", "contact_messages", ["status"], unique=False)

    op.create_table(
        "booking_status_audits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("old_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("changed_by", sa.String(length=100), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointment_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_booking_status_audits_appointment_id", "booking_status_audits", ["appointment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_booking_status_audits_appointment_id", table_name="booking_status_audits")
    op.drop_table("booking_status_audits")
    op.drop_index("ix_contact_messages_status", table_name="contact_messages")
    op.drop_index("ix_contact_messages_reference_code", table_name="contact_messages")
    op.drop_table("contact_messages")
    op.drop_index("idx_appt_dentist_slot", table_name="appointment_requests")
    op.drop_index("idx_appt_date_status", table_name="appointment_requests")
    op.drop_index("ix_appointment_requests_status", table_name="appointment_requests")
    op.drop_index("ix_appointment_requests_preferred_date", table_name="appointment_requests")
    op.drop_index("ix_appointment_requests_reference_code", table_name="appointment_requests")
    op.drop_table("appointment_requests")
