"""Enterprise Security & Role-Based Access Control (RBAC) Module.

Hardened security implementation adhering to OWASP & AGENT_GUIDE standards:
- Password Hashing: Argon2id (preferred) with automatic PBKDF2-HMAC-SHA256 fallback
- Session Tokens: Cryptographic HMAC-SHA256 signatures with expiration & tamper protection
- CSRF Protection: Session-bound CSRF token generation and constant-time verification
- Role-Based Access Control: Granular Zero-Trust authorization matrix for pages and APIs
"""

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _argon2_hasher = PasswordHasher()
except ImportError:
    _argon2_hasher = None

# Secret key for signing sessions (persisted in data/.session_secret or environment)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SECRET_FILE = DATA_DIR / ".session_secret"

if os.getenv("SECRET_KEY"):
    SECRET_KEY = os.getenv("SECRET_KEY")
elif SECRET_FILE.exists():
    try:
        SECRET_KEY = SECRET_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        SECRET_KEY = secrets.token_hex(32)
else:
    SECRET_KEY = secrets.token_hex(32)
    try:
        SECRET_FILE.write_text(SECRET_KEY, encoding="utf-8")
    except Exception:
        pass

SESSION_COOKIE_NAME = "facetrack_session"
CSRF_HEADER_NAME = "X-CSRF-Token"
SESSION_DURATION_SECONDS = 86400  # 24 hours

# Role definitions
ROLE_ADMIN = "ADMIN"
ROLE_HR = "HR_MANAGER"
ROLE_SECURITY = "SECURITY_OFFICER"
ROLE_EMPLOYEE = "EMPLOYEE"

ALL_ROLES = [ROLE_ADMIN, ROLE_HR, ROLE_SECURITY, ROLE_EMPLOYEE]


# ============================================================================
# PASSWORD HASHING (Argon2id + PBKDF2 Backward Compatibility)
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using Argon2id (preferred) with fallback to PBKDF2-HMAC-SHA256."""
    if _argon2_hasher:
        return _argon2_hasher.hash(password)
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against Argon2id or legacy PBKDF2 hash using constant-time comparison."""
    if not hashed_password:
        return False

    # Check Argon2id hash
    if hashed_password.startswith("$argon2"):
        if _argon2_hasher:
            try:
                return _argon2_hasher.verify(hashed_password, plain_password)
            except VerifyMismatchError:
                return False
            except Exception:
                return False
        return False

    # Check legacy PBKDF2 hash
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


# ============================================================================
# CRYPTOGRAPHIC SESSION MANAGEMENT
# ============================================================================

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


# ============================================================================
# CSRF PROTECTION HELPERS
# ============================================================================

def generate_csrf_token(session_token: str) -> str:
    """Generate a cryptographic CSRF token bound to the current session token."""
    if not session_token:
        return ""
    h = hmac.new(SECRET_KEY.encode("utf-8"), f"csrf:{session_token}".encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


def verify_csrf_token(submitted_token: Optional[str], session_token: str) -> bool:
    """Verify a CSRF token using constant-time comparison."""
    if not submitted_token or not session_token:
        return False
    expected = generate_csrf_token(session_token)
    return hmac.compare_digest(submitted_token, expected)


# ============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC) MATRIX
# ============================================================================

PAGE_PERMISSIONS: Dict[str, List[str]] = {
    ROLE_ADMIN: [
        "dashboard", "employees", "departments", "scanner", "attendance",
        "audit-logs", "audit_logs", "reports", "settings", "security",
        "shifts", "leave", "devices"
    ],
    ROLE_HR: [
        "dashboard", "employees", "departments", "scanner", "attendance",
        "reports", "shifts", "leave"
    ],
    ROLE_SECURITY: [
        "dashboard", "scanner", "attendance", "audit-logs", "audit_logs",
        "devices", "leave"
    ],
    ROLE_EMPLOYEE: [
        "dashboard", "scanner", "attendance", "leave"
    ],
}


def can_access_page(user_role: str, page_name: str) -> bool:
    """Check if a specific role is authorized to view a page."""
    role = (user_role or "").upper()
    if role == ROLE_ADMIN:
        return True  # Admin has unrestricted access

    clean_page = page_name.replace("_", "-")
    allowed_pages = PAGE_PERMISSIONS.get(role, ["dashboard", "scanner"])
    allowed_pages_clean = [p.replace("_", "-") for p in allowed_pages]

    return clean_page in allowed_pages_clean
