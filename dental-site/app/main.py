"""FastAPI entry point and routing for the official Dental Clinic website."""

from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional

from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.booking import create_appointment_request, validate_and_create_contact_message, validate_booking_input
from app.clinic_data import DENTISTS, SERVICES, get_service_by_slug
from app.config import AVAILABLE_TIME_SLOTS, CLINIC_INFO, get_clinic_now, is_clinic_open_now, settings
from app.database import get_db, init_dental_db
from app.models import AppointmentRequest
from app.security import (
    CSRF_COOKIE_NAME,
    SecurityHeadersMiddleware,
    form_rate_limiter,
    generate_csrf_token,
    get_or_issue_csrf_id,
    hash_client_ip,
    verify_csrf_token,
)
from app.translations import TRANSLATIONS

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize SQLite schema in dev; production environments manage schema via Alembic."""
    init_dental_db()
    yield


app = FastAPI(
    title="Dental Clinic Official Website",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def resolve_lang(lang: str) -> str:
    """Normalize supported language route prefixes (/en and /kh)."""
    return "kh" if lang == "kh" else "en"


def validate_lang_or_404(lang: str) -> str:
    if lang not in ("en", "kh"):
        raise StarletteHTTPException(status_code=404)
    return lang


def set_csrf_cookie_if_needed(response: HTMLResponse, csrf_id: str, request: Request) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_id,
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https" or settings.app_env == "production"),
        max_age=4 * 3600,
    )


def build_base_context(request: Request, lang: str, active_nav: str = "home") -> Dict:
    """Build shared template context including language-preserving switcher URLs."""
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    path = request.url.path
    if path.startswith("/en/"):
        suffix = path[3:]
    elif path.startswith("/kh/"):
        suffix = path[3:]
    elif path in ("/en", "/kh"):
        suffix = "/"
    else:
        suffix = "/"

    return {
        "lang": lang,
        "t": t,
        "clinic": CLINIC_INFO,
        "clinic_open": is_clinic_open_now(),
        "active_nav": active_nav,
        "switch_en_url": f"/en{suffix}",
        "switch_kh_url": f"/kh{suffix}",
    }


def _contact_page_context(
    request: Request,
    lang: str,
    csrf_id: str,
    *,
    booking_form: Optional[Dict] = None,
    booking_errors: Optional[Dict[str, str]] = None,
    contact_form: Optional[Dict] = None,
    contact_errors: Optional[Dict[str, str]] = None,
    contact_success_ref: Optional[str] = None,
    utm: Optional[Dict[str, str]] = None,
) -> Dict:
    local_today = get_clinic_now().date()
    ctx = build_base_context(request, lang, active_nav="contact")
    ctx.update(
        {
            "csrf_token": generate_csrf_token(csrf_id, scope="clinic"),
            "services": SERVICES,
            "dentists": DENTISTS,
            "time_slots": AVAILABLE_TIME_SLOTS,
            "min_date": local_today.strftime("%Y-%m-%d"),
            "max_date": (local_today + timedelta(days=180)).strftime("%Y-%m-%d"),
            "booking_form": booking_form or {},
            "booking_errors": booking_errors or {},
            "contact_form": contact_form or {},
            "contact_errors": contact_errors or {},
            "contact_success_ref": contact_success_ref,
            "utm": utm or {"source": "", "medium": "", "campaign": ""},
        }
    )
    return ctx


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Liveness health check endpoint."""
    return {"status": "ok"}


@app.get("/", response_class=RedirectResponse)
def root_redirect() -> RedirectResponse:
    """Redirect bare root to default English clinic home."""
    return RedirectResponse(url="/en/", status_code=302)


@app.get("/en", response_class=RedirectResponse)
@app.get("/kh", response_class=RedirectResponse)
def trailing_lang_redirect(request: Request) -> RedirectResponse:
    """Normalize /en -> /en/ and /kh -> /kh/."""
    lang = "kh" if request.url.path.startswith("/kh") else "en"
    return RedirectResponse(url=f"/{lang}/", status_code=302)


@app.get("/{lang}/", response_class=HTMLResponse)
def home_page(lang: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    ctx = build_base_context(request, lang, active_nav="home")
    return templates.TemplateResponse(request=request, name="home.html", context=ctx)


@app.get("/{lang}/contact", response_class=HTMLResponse)
def contact_page(
    lang: str,
    request: Request,
    service: Optional[str] = Query(None),
    dentist: Optional[str] = Query(None),
    msg_ref: Optional[str] = Query(None),
    utm_source: Optional[str] = Query(None),
    utm_medium: Optional[str] = Query(None),
    utm_campaign: Optional[str] = Query(None),
) -> HTMLResponse:
    validate_lang_or_404(lang)
    csrf_id = get_or_issue_csrf_id(request)
    prefill = {
        "service_slug": service or "not-sure",
        "preferred_dentist_slug": dentist or "no-preference",
    }
    utm = {
        "source": (utm_source or "")[:80],
        "medium": (utm_medium or "")[:80],
        "campaign": (utm_campaign or "")[:100],
    }
    ctx = _contact_page_context(
        request,
        lang,
        csrf_id,
        booking_form=prefill,
        contact_success_ref=msg_ref,
        utm=utm,
    )
    resp = templates.TemplateResponse(request=request, name="contact.html", context=ctx)
    set_csrf_cookie_if_needed(resp, csrf_id, request)
    return resp


@app.post("/{lang}/book")
def submit_booking(
    lang: str,
    request: Request,
    csrf_token: str = Form(""),
    website: str = Form(""),
    full_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    service_slug: str = Form("not-sure"),
    preferred_dentist_slug: str = Form("no-preference"),
    preferred_date: str = Form(""),
    preferred_time_slot: str = Form(""),
    message: str = Form(""),
    consent: Optional[str] = Form(None),
    utm_source: str = Form(""),
    utm_medium: str = Form(""),
    utm_campaign: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_lang_or_404(lang)
    t = TRANSLATIONS[lang]
    csrf_id = get_or_issue_csrf_id(request)
    submitted_form = {
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "service_slug": service_slug,
        "preferred_dentist_slug": preferred_dentist_slug,
        "preferred_date": preferred_date,
        "preferred_time_slot": preferred_time_slot,
        "message": message,
        "consent": bool(consent),
    }
    utm = {"source": utm_source[:80], "medium": utm_medium[:80], "campaign": utm_campaign[:100]}

    def render_error(errors: Dict[str, str], status_code: int) -> HTMLResponse:
        ctx = _contact_page_context(
            request,
            lang,
            csrf_id,
            booking_form=submitted_form,
            booking_errors=errors,
            utm=utm,
        )
        resp = templates.TemplateResponse(
            request=request, name="contact.html", context=ctx, status_code=status_code
        )
        set_csrf_cookie_if_needed(resp, csrf_id, request)
        return resp

    if not verify_csrf_token(csrf_token, request.cookies.get(CSRF_COOKIE_NAME), scope="clinic"):
        return render_error({"_form": t["err_csrf"]}, 403)

    if website.strip():
        return render_error({"_form": t["err_spam"]}, 400)

    ip_hash = hash_client_ip(request)
    if not form_rate_limiter.allow(f"book:{ip_hash}"):
        return render_error({"_form": t["err_rate_limit"]}, 429)

    errors, cleaned = validate_booking_input(
        full_name=full_name,
        phone=phone,
        email=email,
        service_slug=service_slug,
        preferred_dentist_slug=preferred_dentist_slug,
        preferred_date_str=preferred_date,
        preferred_time_slot=preferred_time_slot,
        message=message,
        consent=bool(consent),
        t=t,
    )
    if errors:
        return render_error(errors, 422)

    appt, conflict_err = create_appointment_request(
        db,
        cleaned=cleaned,
        client_fingerprint=ip_hash,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )
    if conflict_err == "slot_taken" or not appt:
        return render_error({"preferred_time_slot": t["err_slot_taken"]}, 409)

    return RedirectResponse(url=f"/{lang}/booking-confirmed?ref={appt.reference_code}", status_code=303)


@app.get("/{lang}/booking-confirmed", response_class=HTMLResponse)
def booking_confirmed_page(
    lang: str,
    request: Request,
    ref: str = Query(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    validate_lang_or_404(lang)
    t = TRANSLATIONS[lang]
    appt = db.query(AppointmentRequest).filter(AppointmentRequest.reference_code == ref.strip()).first()
    if not appt:
        raise StarletteHTTPException(status_code=404)

    svc = get_service_by_slug(appt.service_slug)
    if svc:
        svc_label = svc["title_en"] if lang == "en" else svc["title_kh"]
    else:
        svc_label = t["option_not_sure"]

    ctx = build_base_context(request, lang, active_nav="contact")
    ctx["summary"] = {
        "reference_code": appt.reference_code,
        "service_label": svc_label,
        "preferred_date": appt.preferred_date.strftime("%Y-%m-%d"),
        "preferred_time_slot": appt.preferred_time_slot,
    }
    return templates.TemplateResponse(request=request, name="booking_success.html", context=ctx)


@app.post("/{lang}/contact/send")
def submit_contact_message(
    lang: str,
    request: Request,
    csrf_token: str = Form(""),
    website: str = Form(""),
    full_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    subject: str = Form(""),
    message: str = Form(""),
    consent: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    validate_lang_or_404(lang)
    t = TRANSLATIONS[lang]
    csrf_id = get_or_issue_csrf_id(request)
    c_form = {
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "subject": subject,
        "message": message,
        "consent": bool(consent),
    }

    def render_contact_err(errors: Dict[str, str], status_code: int) -> HTMLResponse:
        ctx = _contact_page_context(
            request,
            lang,
            csrf_id,
            contact_form=c_form,
            contact_errors=errors,
        )
        resp = templates.TemplateResponse(
            request=request, name="contact.html", context=ctx, status_code=status_code
        )
        set_csrf_cookie_if_needed(resp, csrf_id, request)
        return resp

    if not verify_csrf_token(csrf_token, request.cookies.get(CSRF_COOKIE_NAME), scope="clinic"):
        return render_contact_err({"_form": t["err_csrf"]}, 403)

    if website.strip():
        return render_contact_err({"_form": t["err_spam"]}, 400)

    ip_hash = hash_client_ip(request)
    if not form_rate_limiter.allow(f"contact:{ip_hash}"):
        return render_contact_err({"_form": t["err_rate_limit"]}, 429)

    errors, msg_obj = validate_and_create_contact_message(
        db,
        full_name=full_name,
        phone=phone,
        email=email,
        subject=subject,
        message=message,
        consent=bool(consent),
        t=t,
    )
    if errors or not msg_obj:
        return render_contact_err(errors, 422)

    return RedirectResponse(url=f"/{lang}/contact?msg_ref={msg_obj.reference_code}#contact-form", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render accessible bilingual 404 page instead of raw JSON/stack traces."""
    if exc.status_code == 404:
        lang = "kh" if request.url.path.startswith("/kh") else "en"
        ctx = build_base_context(request, lang, active_nav="")
        return templates.TemplateResponse(
            request=request, name="404.html", context=ctx, status_code=404
        )
    return HTMLResponse(content="Request could not be completed.", status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _: Exception):
    """Never expose stack traces, SQL errors, or internal paths to visitors."""
    lang = "kh" if request.url.path.startswith("/kh") else "en"
    t = TRANSLATIONS[lang]
    return HTMLResponse(content=t["error_500_desc"], status_code=500)
