"""Application configuration, clinic placeholders, and timezone helpers."""

import os
import secrets
from datetime import datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Only load dental-site/.env so we never accidentally read the parent system's .env
_ENV_FILE = BASE_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)


def resolve_timezone(tz_name: str) -> tzinfo:
    """Resolve configured IANA timezone with safe UTC+07:00 fallback for minimal containers."""
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        if tz_name == "Asia/Phnom_Penh":
            return timezone(timedelta(hours=7), name="Asia/Phnom_Penh")
        return timezone.utc


class Settings:
    """Validated runtime configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.app_env: str = os.getenv("APP_ENV", "development").strip().lower()
        self.site_base_url: str = os.getenv("SITE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
        self.database_url: str = os.getenv("DENTAL_DATABASE_URL", "").strip() or (
            f"sqlite:///{(DATA_DIR / 'dental_clinic.db').as_posix()}"
        )
        self.clinic_tz_name: str = os.getenv("CLINIC_TIMEZONE", "Asia/Phnom_Penh").strip()
        self.clinic_tz: tzinfo = resolve_timezone(self.clinic_tz_name)

        env_secret = os.getenv("DENTAL_SECRET_KEY", "").strip()
        if not env_secret:
            if self.app_env == "production":
                raise RuntimeError(
                    "CRITICAL: DENTAL_SECRET_KEY must be set when APP_ENV=production."
                )
            secret_file = DATA_DIR / ".dental_secret"
            if secret_file.exists():
                env_secret = secret_file.read_text(encoding="utf-8").strip()
            else:
                env_secret = secrets.token_hex(32)
                try:
                    secret_file.write_text(env_secret, encoding="utf-8")
                except OSError:
                    pass
        self.secret_key: str = env_secret

        self.notification_webhook_url: str = os.getenv("CLINIC_NOTIFICATION_WEBHOOK_URL", "").strip()
        self.notify_email: str = os.getenv("CLINIC_NOTIFY_EMAIL", "").strip()
        self.smtp_host: str = os.getenv("SMTP_HOST", "").strip()
        self.smtp_port: int = int(os.getenv("SMTP_PORT", "587") or 587)
        self.smtp_user: str = os.getenv("SMTP_USER", "").strip()
        self.smtp_password: str = os.getenv("SMTP_PASSWORD", "").strip()

        self.admin_username: str = os.getenv("CLINIC_ADMIN_USERNAME", "").strip()
        self.admin_password_hash: str = os.getenv("CLINIC_ADMIN_PASSWORD_HASH", "").strip()

        self.rate_limit_max: int = max(1, int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "6") or 6))
        self.rate_limit_window_seconds: int = max(10, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "600") or 600))


settings = Settings()

# ---------------------------------------------------------------------------
# Clearly flagged clinic profile placeholders (Owner must replace before launch)
# ---------------------------------------------------------------------------
CLINIC_INFO: Dict[str, str] = {
    "legal_name": "[CLINIC LEGAL NAME]",
    "brand_name": "[CLINIC BRAND NAME]",
    "brand_name_kh": "[ឈ្មោះគ្លីនិកធ្មេញ]",
    "tagline_en": "[CLINIC TAGLINE — GENERAL & FAMILY DENTISTRY IN PHNOM PENH]",
    "tagline_kh": "[ពាក្យស្លោកគ្លីនិក — សេវាថែទាំធ្មេញសម្រាប់គ្រួសារនៅរាជធានីភ្នំពេញ]",
    "phone_display": "[PHONE: +855 XX XXX XXX]",
    "phone_href": "tel:+85500000000",
    "emergency_phone_display": "[EMERGENCY PHONE: +855 XX XXX XXX]",
    "email": "[CLINIC EMAIL: reception@example-clinic.kh]",
    "address_en": "[CLINIC STREET ADDRESS, KHAN, PHNOM PENH, CAMBODIA]",
    "address_kh": "[អាសយដ្ឋានគ្លីនិក រាជធានីភ្នំពេញ កម្ពុជា]",
    "parking_en": "[PARKING & TRANSPORT NOTES — e.g. Ground-floor motorbike/car spaces available]",
    "parking_kh": "[ព័ត៌មានចំណតរថយន្ត និងមធ្យោបាយធ្វើដំណើរ]",
    "whatsapp_url": "#contact-channels",
    "telegram_url": "#contact-channels",
    "messenger_url": "#contact-channels",
    "google_maps_directions_url": "https://maps.google.com/?q=Phnom+Penh+Cambodia",
    "google_maps_embed_url": "https://www.google.com/maps?q=Phnom+Penh+Cambodia&output=embed",
    "google_reviews_url": "#patient-reviews",
    "facebook_url": "#social-facebook",
    "instagram_url": "#social-instagram",
    "price_range": "[PRICE RANGE PLACEHOLDER e.g. $–$$]",
    "geo_lat": "11.5564",
    "geo_lng": "104.9282",
    "confirm_sla_hours": "2",
    "retention_years": "7",
    "copyright_year": "2026",
}

# Weekday indices: 0=Mon ... 5=Sat, 6=Sun (None = closed)
CLINIC_HOURS: Dict[int, Optional[Tuple[time, time]]] = {
    0: (time(8, 0), time(18, 0)),
    1: (time(8, 0), time(18, 0)),
    2: (time(8, 0), time(18, 0)),
    3: (time(8, 0), time(18, 0)),
    4: (time(8, 0), time(18, 0)),
    5: (time(8, 0), time(17, 0)),
    6: None,  # Closed Sunday
}

# Placeholder public holidays (YYYY-MM-DD strings, replace with official clinic holiday calendar)
CLINIC_HOLIDAYS: List[str] = []

AVAILABLE_TIME_SLOTS: List[str] = [
    "08:30",
    "09:30",
    "10:30",
    "11:30",
    "13:30",
    "14:30",
    "15:30",
    "16:30",
    "17:00",
]


def get_clinic_now(now_utc: Optional[datetime] = None) -> datetime:
    """Return current time converted to configured clinic timezone."""
    base = now_utc or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(settings.clinic_tz)


def is_clinic_open_now(now_utc: Optional[datetime] = None) -> bool:
    """Compute whether the clinic is currently open in clinic timezone."""
    local_now = get_clinic_now(now_utc)
    if local_now.strftime("%Y-%m-%d") in CLINIC_HOLIDAYS:
        return False
    hours = CLINIC_HOURS.get(local_now.weekday())
    if not hours:
        return False
    open_t, close_t = hours
    return open_t <= local_now.time() < close_t

