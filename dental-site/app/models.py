"""Database models for dental clinic appointment requests, contact inquiries, and audit history."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


VALID_BOOKING_STATUSES = (
    "new",
    "contacted",
    "confirmed",
    "completed",
    "cancelled",
    "no-show",
)


class AppointmentRequest(Base):
    """Patient online appointment request with UTM attribution, consent, and audit workflow."""

    __tablename__ = "appointment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    service_slug: Mapped[str] = mapped_column(String(80), nullable=False, default="not-sure")
    preferred_dentist_slug: Mapped[str] = mapped_column(String(80), nullable=False, default="no-preference")
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    preferred_time_slot: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new", index=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    client_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    audits: Mapped[list["BookingStatusAudit"]] = relationship(
        "BookingStatusAudit",
        back_populates="appointment",
        cascade="all, delete-orphan",
        order_by="BookingStatusAudit.created_at",
    )

    __table_args__ = (
        Index("idx_appt_date_status", "preferred_date", "status"),
        Index("idx_appt_dentist_slot", "preferred_dentist_slug", "preferred_date", "preferred_time_slot"),
    )


class ContactMessage(Base):
    """General inquiry submitted via contact form."""

    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class BookingStatusAudit(Base):
    """Append-only status change history for appointment requests."""

    __tablename__ = "booking_status_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("appointment_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    appointment: Mapped["AppointmentRequest"] = relationship("AppointmentRequest", back_populates="audits")
