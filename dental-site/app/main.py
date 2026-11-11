"""FastAPI entry point and routing for the official Dental Clinic website."""

import csv
import hmac
import io
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.booking import create_appointment_request, validate_and_create_contact_message, validate_booking_input
from app.clinic_data import CLINIC_FAQS, DENTISTS, SERVICES, TESTIMONIAL_PLACEHOLDERS, get_service_by_slug
from app.config import AVAILABLE_TIME_SLOTS, CLINIC_INFO, get_clinic_now, is_clinic_open_now, settings
from app.database import get_db, init_dental_db
from app.models import AppointmentRequest, BookingStatusAudit, VALID_BOOKING_STATUSES
from app.security import (
    ADMIN_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    SecurityHeadersMiddleware,
    create_admin_session_token,
    escape_csv_cell,
    form_rate_limiter,
    generate_csrf_token,
    get_or_issue_csrf_id,
    hash_client_ip,
    verify_admin_password,
    verify_admin_session_token,
    verify_csrf_token,
)
from app.seo import (
    build_breadcrumb_schema,
    build_dentists_schema,
    build_faq_schema,
    build_local_business_schema,
    render_robots_txt,
    render_sitemap_xml,
    safe_json_ld,
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


def build_base_context(
    request: Request,
    lang: str,
    active_nav: str = "home",
    *,
    noindex: bool = False,
    extra_schemas: Optional[List[Dict]] = None,
) -> Dict:
    """Build shared template context including canonical URL, hreflang links, and JSON-LD."""
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

    base = settings.site_base_url
    switch_en = f"/en{suffix}"
    switch_kh = f"/kh{suffix}"
    canonical = f"{base}{switch_en if lang == 'en' else switch_kh}"

    schemas: List[Dict] = []
    if not noindex:
        schemas.append(build_local_business_schema(lang))
    if extra_schemas:
        schemas.extend(extra_schemas)

    return {
        "lang": lang,
        "t": t,
        "clinic": CLINIC_INFO,
        "clinic_open": is_clinic_open_now(),
        "active_nav": active_nav,
        "switch_en_url": switch_en,
        "switch_kh_url": switch_kh,
        "canonical_url": canonical,
        "hreflang_en": f"{base}{switch_en}",
        "hreflang_km": f"{base}{switch_kh}",
        "og_image_url": f"{base}/static/img/og-share.svg",
        "noindex": noindex,
        "json_ld_strings": [safe_json_ld(s) for s in schemas],
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


@app.get("/sitemap.xml")
def sitemap_xml() -> Response:
    """Serve dynamic XML sitemap with bilingual hreflang alternates."""
    return Response(content=render_sitemap_xml(), media_type="application/xml")


@app.get("/robots.txt")
def robots_txt() -> Response:
    """Serve robots.txt blocking admin and booking confirmation routes."""
    return Response(content=render_robots_txt(), media_type="text/plain")


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
    ctx.update(
        {
            "services": SERVICES[:6],
            "dentists": DENTISTS,
            "testimonials": TESTIMONIAL_PLACEHOLDERS[:3],
        }
    )
    return templates.TemplateResponse(request=request, name="home.html", context=ctx)


@app.get("/{lang}/services", response_class=HTMLResponse)
def services_page(lang: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    t = TRANSLATIONS[lang]
    groups_map: Dict[str, Dict] = {}
    for svc in SERVICES:
        cat = svc["category"]
        if cat not in groups_map:
            groups_map[cat] = {
                "category_label": svc["category_en"] if lang == "en" else svc["category_kh"],
                "services": [],
            }
        groups_map[cat]["services"].append(svc)
    breadcrumb = build_breadcrumb_schema(
        [
            {"name": t["nav_home"], "path": f"/{lang}/"},
            {"name": t["nav_services"], "path": f"/{lang}/services"},
        ]
    )
    ctx = build_base_context(request, lang, active_nav="services", extra_schemas=[breadcrumb])
    ctx["grouped_services"] = list(groups_map.values())
    return templates.TemplateResponse(request=request, name="services.html", context=ctx)


@app.get("/{lang}/services/{slug}", response_class=HTMLResponse)
def service_detail_page(lang: str, slug: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    t = TRANSLATIONS[lang]
    svc = get_service_by_slug(slug)
    if not svc:
        raise StarletteHTTPException(status_code=404)
    related = [s for s in SERVICES if s["slug"] != slug][:3]
    svc_title = svc["title_en"] if lang == "en" else svc["title_kh"]
    extra = [
        build_breadcrumb_schema(
            [
                {"name": t["nav_home"], "path": f"/{lang}/"},
                {"name": t["nav_services"], "path": f"/{lang}/services"},
                {"name": svc_title, "path": f"/{lang}/services/{slug}"},
            ]
        )
    ]
    if svc.get("faqs"):
        extra.append(build_faq_schema(svc["faqs"], lang))
    ctx = build_base_context(request, lang, active_nav="services", extra_schemas=extra)
    ctx.update({"service": svc, "related_services": related})
    return templates.TemplateResponse(request=request, name="service_detail.html", context=ctx)


@app.get("/{lang}/dentists", response_class=HTMLResponse)
def dentists_page(lang: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    ctx = build_base_context(
        request, lang, active_nav="dentists", extra_schemas=[build_dentists_schema(lang)]
    )
    ctx["dentists"] = DENTISTS
    return templates.TemplateResponse(request=request, name="dentists.html", context=ctx)


@app.get("/{lang}/patient-stories", response_class=HTMLResponse)
def patient_stories_page(lang: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    ctx = build_base_context(request, lang, active_nav="stories")
    ctx["testimonials"] = TESTIMONIAL_PLACEHOLDERS
    return templates.TemplateResponse(request=request, name="patient_stories.html", context=ctx)


@app.get("/{lang}/about", response_class=HTMLResponse)
def about_page(lang: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    ctx = build_base_context(request, lang, active_nav="about")
    return templates.TemplateResponse(request=request, name="about.html", context=ctx)


@app.get("/{lang}/faq", response_class=HTMLResponse)
def faq_page(lang: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    ctx = build_base_context(
        request, lang, active_nav="faq", extra_schemas=[build_faq_schema(CLINIC_FAQS, lang)]
    )
    ctx["faqs"] = CLINIC_FAQS
    return templates.TemplateResponse(request=request, name="faq.html", context=ctx)


@app.get("/{lang}/privacy", response_class=HTMLResponse)
def privacy_page(lang: str, request: Request) -> HTMLResponse:
    validate_lang_or_404(lang)
    ctx = build_base_context(request, lang, active_nav="")
    return templates.TemplateResponse(request=request, name="privacy.html", context=ctx)


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

    ctx = build_base_context(request, lang, active_nav="contact", noindex=True)
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


def _get_admin_username() -> str:
    return os.getenv("CLINIC_ADMIN_USERNAME", settings.admin_username).strip()


def _get_admin_password_hash() -> str:
    return os.getenv("CLINIC_ADMIN_PASSWORD_HASH", settings.admin_password_hash).strip()


def _require_admin(request: Request) -> Optional[str]:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    payload = verify_admin_session_token(token)
    if not payload or payload.get("usr") != _get_admin_username():
        return None
    return payload.get("usr")


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request) -> HTMLResponse:
    csrf_id = get_or_issue_csrf_id(request)
    admin_configured = bool(_get_admin_username() and _get_admin_password_hash())
    ctx = build_base_context(request, "en", active_nav="", noindex=True)
    ctx.update(
        {
            "csrf_token": generate_csrf_token(csrf_id, scope="admin"),
            "admin_configured": admin_configured,
            "error": None,
        }
    )
    resp = templates.TemplateResponse(request=request, name="admin_login.html", context=ctx)
    set_csrf_cookie_if_needed(resp, csrf_id, request)
    return resp


@app.post("/admin/login")
def admin_login_submit(
    request: Request,
    csrf_token: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
):
    csrf_id = get_or_issue_csrf_id(request)
    cfg_user = _get_admin_username()
    cfg_hash = _get_admin_password_hash()
    admin_configured = bool(cfg_user and cfg_hash)

    def render_login_err(err: str, status: int) -> HTMLResponse:
        ctx = build_base_context(request, "en", active_nav="", noindex=True)
        ctx.update(
            {
                "csrf_token": generate_csrf_token(csrf_id, scope="admin"),
                "admin_configured": admin_configured,
                "error": err,
            }
        )
        resp = templates.TemplateResponse(
            request=request, name="admin_login.html", context=ctx, status_code=status
        )
        set_csrf_cookie_if_needed(resp, csrf_id, request)
        return resp

    if not admin_configured:
        return render_login_err("Admin access is disabled until configured.", 403)
    if not verify_csrf_token(csrf_token, request.cookies.get(CSRF_COOKIE_NAME), scope="admin"):
        return render_login_err("Security session expired.", 403)

    ip_hash = hash_client_ip(request)
    if not form_rate_limiter.allow(f"admin_login:{ip_hash}"):
        return render_login_err("Too many login attempts. Please wait and try again.", 429)

    user_ok = hmac.compare_digest(username.strip(), cfg_user)
    pass_ok = verify_admin_password(password, cfg_hash)
    if not (user_ok and pass_ok):
        return render_login_err("Invalid username or password.", 401)

    token = create_admin_session_token(cfg_user)
    resp = RedirectResponse(url="/admin/bookings", status_code=303)
    resp.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https" or settings.app_env == "production"),
        max_age=8 * 3600,
    )
    return resp


@app.post("/admin/logout")
def admin_logout(request: Request, csrf_token: str = Form("")):
    if not verify_csrf_token(csrf_token, request.cookies.get(CSRF_COOKIE_NAME), scope="admin"):
        raise StarletteHTTPException(status_code=403)
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie(ADMIN_COOKIE_NAME)
    return resp


@app.get("/admin/bookings", response_class=HTMLResponse)
def admin_bookings_view(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    admin_usr = _require_admin(request)
    if not admin_usr:
        return RedirectResponse(url="/admin/login", status_code=302)

    query = db.query(AppointmentRequest)
    clean_status = (status or "").strip()
    if clean_status and clean_status in VALID_BOOKING_STATUSES:
        query = query.filter(AppointmentRequest.status == clean_status)
    clean_q = (q or "").strip()
    if clean_q:
        like = f"%{clean_q}%"
        query = query.filter(
            (AppointmentRequest.reference_code.ilike(like))
            | (AppointmentRequest.full_name.ilike(like))
            | (AppointmentRequest.phone.ilike(like))
        )

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    appointments = (
        query.order_by(desc(AppointmentRequest.created_at), desc(AppointmentRequest.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    csrf_id = get_or_issue_csrf_id(request)
    ctx = build_base_context(request, "en", active_nav="", noindex=True)
    ctx.update(
        {
            "csrf_token": generate_csrf_token(csrf_id, scope="admin"),
            "appointments": appointments,
            "valid_statuses": VALID_BOOKING_STATUSES,
            "status_filter": clean_status,
            "q": clean_q,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        }
    )
    resp = templates.TemplateResponse(request=request, name="admin_bookings.html", context=ctx)
    set_csrf_cookie_if_needed(resp, csrf_id, request)
    return resp


@app.post("/admin/bookings/{appt_id}/status")
def admin_update_booking_status(
    appt_id: int,
    request: Request,
    csrf_token: str = Form(""),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    admin_usr = _require_admin(request)
    if not admin_usr:
        raise StarletteHTTPException(status_code=401)
    if not verify_csrf_token(csrf_token, request.cookies.get(CSRF_COOKIE_NAME), scope="admin"):
        raise StarletteHTTPException(status_code=403)

    new_status = status.strip()
    if new_status not in VALID_BOOKING_STATUSES:
        raise StarletteHTTPException(status_code=422)

    appt = db.query(AppointmentRequest).filter(AppointmentRequest.id == appt_id).first()
    if not appt:
        raise StarletteHTTPException(status_code=404)

    old_status = appt.status
    if old_status != new_status:
        appt.status = new_status
        audit = BookingStatusAudit(
            appointment_id=appt.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=admin_usr,
            note="Updated via booking inbox",
        )
        db.add(audit)
        db.commit()

    return RedirectResponse(url="/admin/bookings", status_code=303)


@app.get("/admin/bookings/export")
def admin_export_bookings_csv(
    request: Request,
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    admin_usr = _require_admin(request)
    if not admin_usr:
        raise StarletteHTTPException(status_code=401)

    query = db.query(AppointmentRequest)
    clean_status = (status or "").strip()
    if clean_status and clean_status in VALID_BOOKING_STATUSES:
        query = query.filter(AppointmentRequest.status == clean_status)
    clean_q = (q or "").strip()
    if clean_q:
        like = f"%{clean_q}%"
        query = query.filter(
            (AppointmentRequest.reference_code.ilike(like))
            | (AppointmentRequest.full_name.ilike(like))
            | (AppointmentRequest.phone.ilike(like))
        )

    rows = query.order_by(desc(AppointmentRequest.created_at), desc(AppointmentRequest.id)).limit(5000).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Reference", "Name", "Phone", "Email", "Service", "Dentist", "Date", "Slot", "Status", "Created At"])
    for a in rows:
        writer.writerow(
            [
                escape_csv_cell(a.reference_code),
                escape_csv_cell(a.full_name),
                escape_csv_cell(a.phone),
                escape_csv_cell(a.email or ""),
                escape_csv_cell(a.service_slug),
                escape_csv_cell(a.preferred_dentist_slug),
                escape_csv_cell(a.preferred_date.strftime("%Y-%m-%d")),
                escape_csv_cell(a.preferred_time_slot),
                escape_csv_cell(a.status),
                escape_csv_cell(a.created_at.isoformat()),
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clinic_appointments.csv"},
    )


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render accessible bilingual 404 page instead of raw JSON/stack traces."""
    if exc.status_code == 404:
        lang = "kh" if request.url.path.startswith("/kh") else "en"
        ctx = build_base_context(request, lang, active_nav="", noindex=True)
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
