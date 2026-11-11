"""Privacy-preserving clinic notification dispatcher for new appointment requests and messages."""

import json
import logging
import smtplib
from email.message import EmailMessage
from urllib import request as urlrequest

from app.config import settings

logger = logging.getLogger("dental_clinic.notifications")


def notify_clinic_new_booking(
    *,
    reference_code: str,
    service_slug: str,
    preferred_date: str,
    preferred_time_slot: str,
) -> None:
    """Notify clinic reception without logging patient PHI (names, phones, symptoms, emails)."""
    logger.info(
        "NEW_BOOKING_REQUEST ref=%s service=%s date=%s slot=%s",
        reference_code,
        service_slug,
        preferred_date,
        preferred_time_slot,
    )

    if settings.notification_webhook_url:
        payload = json.dumps(
            {
                "event": "new_appointment_request",
                "reference_code": reference_code,
                "service": service_slug,
                "preferred_date": preferred_date,
                "preferred_time_slot": preferred_time_slot,
            }
        ).encode("utf-8")
        try:
            req = urlrequest.Request(
                settings.notification_webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=3):
                pass
        except Exception:
            logger.warning("BOOKING_WEBHOOK_FAILED ref=%s", reference_code)

    if settings.smtp_host and settings.notify_email:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"New Appointment Request [{reference_code}]"
            msg["From"] = settings.smtp_user or settings.notify_email
            msg["To"] = settings.notify_email
            msg.set_content(
                f"A new appointment request ({reference_code}) was submitted for {preferred_date} at {preferred_time_slot}.\n"
                f"Service: {service_slug}\n"
                "Please sign in to the clinic booking inbox to review patient details and confirm."
            )
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as server:
                server.starttls()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        except Exception:
            logger.warning("BOOKING_EMAIL_NOTIFY_FAILED ref=%s", reference_code)


def notify_clinic_contact_message(*, reference_code: str) -> None:
    """Log safe contact inquiry event without exposing user PII/message text."""
    logger.info("NEW_CONTACT_MESSAGE ref=%s", reference_code)

