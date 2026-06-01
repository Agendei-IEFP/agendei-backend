"""initial clean

Revision ID: 0001_initial_clean
Revises:
Create Date: 2026-05-29 17:40:00
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_clean"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------
    # ENUMS
    # -----------------------------


    # -----------------------------
    # USERS
    # -----------------------------
    op.create_table(
        "users",
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("role", sa.Enum("client", "professional", "store_admin", name="roleenum"), nullable=False),
        sa.Column("accepted_terms_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_terms_version", sa.String(10), nullable=True),
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
    )

    # -----------------------------
    # STORES
    # -----------------------------
    op.create_table(
        "stores",
        sa.Column("owner_id", sa.String(26), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
    )

    # -----------------------------
    # PROFESSIONALS
    # -----------------------------
    op.create_table(
        "professionals",
        sa.Column("user_id", sa.String(26), nullable=False),
        sa.Column("store_id", sa.String(26), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    # -----------------------------
    # OFFERINGS
    # -----------------------------
    op.create_table(
        "offerings",
        sa.Column("professional_id", sa.String(26), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
    )

    # -----------------------------
    # WORK SCHEDULES
    # -----------------------------
    op.create_table(
        "work_schedules",
        sa.Column("professional_id", sa.String(26), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(26), primary_key=True),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
    )

    # -----------------------------
    # APPOINTMENTS
    # -----------------------------
    op.create_table(
        "appointments",
        sa.Column("client_id", sa.String(26), nullable=False),
        sa.Column("professional_id", sa.String(26), nullable=False),
        sa.Column("offering_id", sa.String(26), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("pending", "confirmed", "cancelled", "completed", name="statusenum"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancelled_by", sa.String(26), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["offering_id"], ["offerings.id"]),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
    )

    # -----------------------------
    # NOTIFICATIONS
    # -----------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("notification_type", sa.Enum("reminder", "confirmation", "cancellation", "evaluation", name="notificationtype"), nullable=False),
        sa.Column("channel", sa.Enum("email", "sms", "whatsapp", name="notificationchannel"), nullable=False),
        sa.Column("recipient_id", sa.String(26), nullable=False),
        sa.Column("recipient_contact", sa.String(255), nullable=False),
        sa.Column("recipient_type", sa.Enum("customer", "professional", name="recipientType"), nullable=False),
        sa.Column("appointment_id", sa.String(26), sa.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "scheduled", "sent", "failed", "cancelled", name="notificationStatus"), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("appointments")
    op.drop_table("work_schedules")
    op.drop_table("offerings")
    op.drop_table("professionals")
    op.drop_table("stores")
    op.drop_table("users")

    op.execute('DROP TYPE "notificationStatus";')
    op.execute('DROP TYPE "recipientType";')
    op.execute("DROP TYPE notificationchannel;")
    op.execute("DROP TYPE notificationtype;")
    op.execute("DROP TYPE statusenum;")
    op.execute("DROP TYPE roleenum;")
