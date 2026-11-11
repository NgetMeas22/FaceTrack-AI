"""Server-side validation and persistence logic for appointment requests and contact messages."""

import re
import secrets
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.clinic_data import DENTIST_MAP, SERVICE_MAP
from app.config import AVAILABLE_TIME_SLOTS, CLINIC_HOLIDAYS, CLINIC_HOURS, get_clinic_now
from app.models import AppointmentRequest, BookingStatusAudit, ContactMessage
from app.notifications import notify_clinic_contact_message, notify_clinic_new_booking

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,120}\.[^@\s]{2,20}$")
PHONE_ALLOWED_CHARS_RE = re.compile(r"^[+\d\s().-]{7,30}$")


def normalize_phone(raw_phone: str) -> Optional[str]:
    """Validate and normalize international/Cambodian phone numbers cleanly."""
    trimmed = raw_phone.strip()
    if not PHONE_ALLOWED_CHARS_RE.match(trimmed):
        return None
    digits = re.sub(r"\D", "", trimmed)
    if len(digits) < 7 or len(digits) > 15:
        return None
    return trimmed


def generate_reference_code(prefix: str = "DC") -> str:
    """Generate non-sequential, high-readability reference number."""
    local_day = get_clinic_now().strftime("%Y%m%d")
    suffix = secrets.token_hex(3).upper()
    return f"{prefix}-{local_day}-{suffix}"


def validate_booking_input(
    *,
    full_name: str,
    phone: str,
    email: str,
    service_slug: str,
    preferred_dentist_slug: str,
    preferred_date_str: str,
    preferred_time_slot: str,
    message: str,
    consent: bool,
    t: Dict[str, str],
) -> Tuple[Dict[str, str], Dict]:
    """Validate booking form fields using allow-lists, bounds, and clinic calendar rules."""
    errors: Dict[str, str] = {}
    cleaned: Dict = {}

    name_val = full_name.strip()
    if len(name_val) < 2 or len(name_val) > 120:
        errors["full_name"] = t["err_full_name"]
    else:
        cleaned["full_name"] = name_val

    norm_phone = normalize_phone(phone)
    if not norm_phone:
        errors["phone"] = t["err_phone"]
    else:
        cleaned["phone"] = norm_phone

    email_val = email.strip()
    if email_val:
        if len(email_val) > 150 or not EMAIL_RE.match(email_val):
            errors["email"] = t["err_email"]
        else:
            cleaned["email"] = email_val
    else:
        cleaned["email"] = None

    valid_services = set(SERVICE_MAP.keys()) | {"not-sure"}
    svc = service_slug.strip() or "not-sure"
    if svc not in valid_services:
        errors["service_slug"] = t["err_service"]
    else:
        cleaned["service_slug"] = svc

    valid_dentists = set(DENTIST_MAP.keys()) | {"no-preference"}
    dent = preferred_dentist_slug.strip() or "no-preference"
    if dent not in valid_dentists:
        errors["preferred_dentist_slug"] = t["err_dentist"]
    else:
        cleaned["preferred_dentist_slug"] = dent

    now_local = get_clinic_now()
    today_local = now_local.date()
    parsed_date: Optional[date] = None
    try:
        parsed_date = datetime.strptime(preferred_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        errors["preferred_date"] = t["err_date_format"]

    if parsed_date is not None:
        if parsed_date < today_local:
            errors["preferred_date"] = t["err_date_past"]
        elif parsed_date > today_local + timedelta(days=180):
            errors["preferred_date"] = t["err_date_range"]
        elif parsed_date.strftime("%Y-%m-%d") in CLINIC_HOLIDAYS or CLINIC_HOURS.get(parsed_date.weekday()) is None:
            errors["preferred_date"] = t["err_date_closed"]
        else:
            cleaned["preferred_date"] = parsed_date

    slot = preferred_time_slot.strip()
    if slot not in AVAILABLE_TIME_SLOTS:
        errors["preferred_time_slot"] = t["err_time_slot"]
    elif parsed_date is not None:
        hours = CLINIC_HOURS.get(parsed_date.weekday())
        slot_time = datetime.strptime(slot, "%H:%M").time()
        if hours and not (hours[0] <= slot_time < hours[1]):
            errors["preferred_time_slot"] = t["err_time_outside_hours"]
        elif parsed_date == today_local and slot_time <= now_local.time():
            errors["preferred_time_slot"] = t["err_time_past"]
        else:
            cleaned["preferred_time_slot"] = slot

    msg_val = message.strip()
    if len(msg_val) > 1000:
        errors["message"] = t["err_message_length"]
    else:
        cleaned["message"] = msg_val or None

    if not consent:
        errors["consent"] = t["err_consent"]
    else:
        cleaned["consent_given"] = True

    return errors, cleaned


def create_appointment_request(
    db: Session,
    *,
    cleaned: Dict,
    client_fingerprint: str,
    utm_source: Optional[str],
    utm_medium: Optional[str],
    utm_campaign: Optional[str],
) -> Tuple[Optional[AppointmentRequest], Optional[str]]:
    """Persist appointment request atomically with double-booking prevention."""
    if cleaned["preferred_dentist_slug"] != "no-preference":
        conflict = (
            db.query(AppointmentRequest.id)
            .filter(
                AppointmentRequest.preferred_dentist_slug == cleaned["preferred_dentist_slug"],
                AppointmentRequest.preferred_date == cleaned["preferred_date"],
                AppointmentRequest.preferred_time_slot == cleaned["preferred_time_slot"],
                AppointmentRequest.status.in_(["new", "contacted", "confirmed"]),
            )
            .first()
        )
        if conflict:
            return None, "slot_taken"

    ref = generate_reference_code("DC")
    appt = AppointmentRequest(
        reference_code=ref,
        full_name=cleaned["full_name"],
        phone=cleaned["phone"],
        email=cleaned["email"],
        service_slug=cleaned["service_slug"],
        preferred_dentist_slug=cleaned["preferred_dentist_slug"],
        preferred_date=cleaned["preferred_date"],
        preferred_time_slot=cleaned["preferred_time_slot"],
        message=cleaned["message"],
        consent_given=True,
        status="new",
        utm_source=(utm_source or "").strip()[:80] or None,
        utm_medium=(utm_medium or "").strip()[:80] or None,
        utm_campaign=(utm_campaign or "").strip()[:100] or None,
        client_fingerprint=client_fingerprint,
    )
    db.add(appt)
    db.flush()

    audit = BookingStatusAudit(
        appointment_id=appt.id,
        old_status=None,
        new_status="new",
        changed_by="patient_form",
        note="Initial online appointment request submitted",
    )
    db.add(audit)
    db.commit()
    db.refresh(appt)

    notify_clinic_new_booking(
        reference_code=appt.reference_code,
        service_slug=appt.service_slug,
        preferred_date=appt.preferred_date.strftime("%Y-%m-%d"),
        preferred_time_slot=appt.preferred_time_slot,
    )
    return appt, None


def validate_and_create_contact_message(
    db: Session,
    *,
    full_name: str,
    phone: str,
    email: str,
    subject: str,
    message: str,
    consent: bool,
    t: Dict[str, str],
) -> Tuple[Dict[str, str], Optional[ContactMessage]]:
    """Validate and save general contact inquiry."""
    errors: Dict[str, str] = {}
    name_val = full_name.strip()
    if len(name_val) < 2 or len(name_val) > 120:
        errors["contact_full_name"] = t["err_full_name"]

    norm_phone = normalize_phone(phone)
    if not norm_phone:
        errors["contact_phone"] = t["err_phone"]

    email_val = email.strip()
    if email_val and (len(email_val) > 150 or not EMAIL_RE.match(email_val)):
        errors["contact_email"] = t["err_email"]

    subj_val = subject.strip()[:150]
    msg_val = message.strip()
    if len(msg_val) < 5 or len(msg_val) > 1500:
        errors["contact_message"] = t["err_contact_message"]

    if not consent:
        errors["contact_consent"] = t["err_consent"]

    if errors:
        return errors, None

    msg_obj = ContactMessage(
        reference_code=generate_reference_code("MSG"),
        full_name=name_val,
        phone=norm_phone,  # type: ignore[arg-type]
        email=email_val or None,
        subject=subj_val or None,
        message=msg_val,
        consent_given=True,
        status="new",
    )
    db.add(msg_obj)
    db.commit()
    db.refresh(msg_obj)
    notify_clinic_contact_message(reference_code=msg_obj.reference_code)
    return {}, msg_obj
