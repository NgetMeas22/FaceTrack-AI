"""Security helpers: CSRF tokens, rate limiting, security headers, Argon2id auth, and CSV formula protection."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any, Deque, Dict, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

CSRF_COOKIE_NAME = "dental_csrf_id"
ADMIN_COOKIE_NAME = "dental_admin_session"
CSRF_TTL_SECONDS = 4 * 3600
ADMIN_SESSION_TTL_SECONDS = 8 * 3600

_password_hasher = PasswordHasher()


def verify_admin_password(plain_password: str, stored_hash: str) -> bool:
    """Verify staff password using Argon2id."""
    if not plain_password or not stored_hash:
        return False
    try:
        return _password_hasher.verify(stored_hash, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_admin_session_token(username: str) -> str:
    """Sign an HttpOnly admin session token."""
    payload = {
        "usr": username,
        "exp": int(time.time()) + ADMIN_SESSION_TTL_SECONDS,
        "nonce": secrets.token_hex(8),
    }
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8")
    sig = hmac.new(settings.secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def verify_admin_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate signature and expiry of an admin session token."""
    if not token or "." not in token:
        return None
    try:
        raw, sig = token.split(".", 1)
        expected = hmac.new(settings.secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(raw.encode("utf-8")).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_or_issue_csrf_id(request: Request) -> str:
    """Retrieve or generate per-browser CSRF cookie identifier."""
    existing = request.cookies.get(CSRF_COOKIE_NAME)
    if existing and len(existing) >= 16 and existing.isalnum():
        return existing
    return secrets.token_hex(16)


def generate_csrf_token(csrf_id: str, scope: str = "clinic") -> str:
    """Create a timestamped, cookie-bound HMAC CSRF token."""
    ts = str(int(time.time()))
    nonce = secrets.token_hex(8)
    msg = f"{csrf_id}:{scope}:{ts}:{nonce}"
    sig = hmac.new(settings.secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{ts}.{nonce}.{sig}"


def verify_csrf_token(submitted_token: Optional[str], csrf_id: Optional[str], scope: str = "clinic") -> bool:
    """Verify submitted CSRF token against browser cookie using constant-time comparison."""
    if not submitted_token or not csrf_id:
        return False
    parts = submitted_token.split(".")
    if len(parts) != 3:
        return False
    ts_str, nonce, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    now = int(time.time())
    if ts > now + 60 or (now - ts) > CSRF_TTL_SECONDS:
        return False
    msg = f"{csrf_id}:{scope}:{ts_str}:{nonce}"
    expected = hmac.new(settings.secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def hash_client_ip(request: Request) -> str:
    """Produce a salted one-way hash of client IP without storing raw IP addresses."""
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    raw_ip = forwarded or (request.client.host if request.client else "unknown")
    return hmac.new(settings.secret_key.encode("utf-8"), raw_ip.encode("utf-8"), hashlib.sha256).hexdigest()


class SlidingWindowRateLimiter:
    """Simple in-memory sliding-window rate limiter keyed by hashed client identifier."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._buckets[key]
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


form_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_max,
    window_seconds=settings.rate_limit_window_seconds,
)


def escape_csv_cell(value: Any) -> str:
    """Protect exported spreadsheets against CSV formula injection."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


def is_safe_relative_redirect(target: str) -> bool:
    """Ensure redirect paths stay strictly relative on the same origin."""
    if not target or not target.startswith("/"):
        return False
    if target.startswith("//") or "\\" in target:
        return False
    return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline security and privacy headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response = await call_next(request)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "frame-src https://www.google.com https://maps.google.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path.startswith("/static/"):
            response.headers.setdefault("Cache-Control", "public, max-age=86400")
        if request.url.scheme == "https" or settings.app_env == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
