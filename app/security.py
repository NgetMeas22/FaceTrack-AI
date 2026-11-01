"""Enterprise Security & Role-Based Access Control (RBAC) Module.

Pure Python implementation using Python standard library (hashlib, hmac, secrets).
Requires zero native external wheels, guaranteeing 100% cross-platform VPS stability.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Secret key for signing sessions (persisted or fallback to environment)
SECRET_KEY = secrets.token_hex(32)
SESSION_COOKIE_NAME = "facetrack_session"
SESSION_DURATION_SECONDS = 86400  # 24 hours

# Role definitions
ROLE_ADMIN = "ADMIN"
ROLE_HR = "HR_MANAGER"
ROLE_SECURITY = "SECURITY_OFFICER"
ROLE_EMPLOYEE = "EMPLOYEE"

ALL_ROLES = [ROLE_ADMIN, ROLE_HR, ROLE_SECURITY, ROLE_EMPLOYEE]


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        meta, salt, expected_hex = parts
        _, algo, iterations = meta.split(":")
        iterations = int(iterations)

        derived_key = hashlib.pbkdf2_hmac(
            algo,
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(derived_key.hex(), expected_hex)
    except Exception:
        return False


def create_session_token(user_id: int, username: str, role: str) -> str:
    """Generate an HMAC-SHA256 signed session token containing timestamp and user payload."""
    payload = {
        "uid": user_id,
        "usr": username,
        "rol": role,
        "exp": int(time.time()) + SESSION_DURATION_SECONDS,
        "rnd": secrets.token_hex(8),
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")

    sig = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload_b64}.{sig}"


def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Verify session token signature and check expiration. Returns payload dict or None."""
    if not token or "." not in token:
        return None

    try:
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(sig, expected_sig):
            return None

        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def can_access_page(user_role: str, page_name: str) -> bool:
    """Check if a specific role is authorized to view a page."""
    role = (user_role or "").upper()
    if role == ROLE_ADMIN:
        return True  # Admin has unrestricted access

    permissions = {
        ROLE_HR: ["dashboard", "employees", "departments", "attendance", "reports", "scanner"],
        ROLE_SECURITY: ["dashboard", "scanner", "attendance", "audit_logs"],
        ROLE_EMPLOYEE: ["dashboard", "scanner", "attendance"],
    }

    allowed_pages = permissions.get(role, ["dashboard", "scanner"])
    return page_name in allowed_pages

