"""Step 3.3 Tests: All clinic pages, service details, bilingual preservation, admin RBAC, and CSV safety."""

import html
import os
import re
from datetime import date, timedelta

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from app.clinic_data import SERVICES
from app.database import SessionLocal
from app.main import app
from app.models import AppointmentRequest, BookingStatusAudit


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert m
    return m.group(1)


def test_all_public_pages_en_and_kh():
    client = TestClient(app)
    paths = [
        "/",
        "/services",
        "/dentists",
        "/patient-stories",
        "/about",
        "/faq",
        "/privacy",
        "/contact",
    ]
    for lang in ("en", "kh"):
        for sub in paths:
            r = client.get(f"/{lang}{sub}")
            assert r.status_code == 200, f"Failed /{lang}{sub}: {r.status_code}"
            expected_html_lang = "en" if lang == "en" else "km"
            assert f'<html lang="{expected_html_lang}">' in r.text

        for svc in SERVICES:
            r_det = client.get(f"/{lang}/services/{svc['slug']}")
            assert r_det.status_code == 200
            title = svc["title_en"] if lang == "en" else svc["title_kh"]
            assert html.escape(title) in r_det.text

    assert client.get("/en/services/nonexistent-service").status_code == 404


def test_language_switch_preserves_route():
    client = TestClient(app)
    r_en = client.get("/en/services/teeth-whitening")
    assert r_en.status_code == 200
    assert 'href="/kh/services/teeth-whitening"' in r_en.text

    r_kh = client.get("/kh/services/teeth-whitening")
    assert r_kh.status_code == 200
    assert 'href="/en/services/teeth-whitening"' in r_kh.text


def test_admin_fails_closed_when_unconfigured():
    client = TestClient(app)
    r_redir = client.get("/admin/bookings", follow_redirects=False)
    assert r_redir.status_code == 302
    assert r_redir.headers["location"] == "/admin/login"

    r_exp = client.get("/admin/bookings/export", follow_redirects=False)
    assert r_exp.status_code == 401

    r_login = client.get("/admin/login")
    assert r_login.status_code == 200
    assert "not configured" in r_login.text


def test_admin_inbox_status_audit_and_csv_formula_protection(monkeypatch):
    ph = PasswordHasher()
    test_secret_pw = "temporary-test-admin-secret-99"
    monkeypatch.setenv("CLINIC_ADMIN_USERNAME", "clinic_staff")
    monkeypatch.setenv("CLINIC_ADMIN_PASSWORD_HASH", ph.hash(test_secret_pw))

    client = TestClient(app)

    # Create a booking containing an Excel formula injection attempt in full_name
    contact_csrf = _extract_csrf(client.get("/en/contact").text)
    d = date.today() + timedelta(days=3)
    if d.weekday() == 6:
        d += timedelta(days=1)

    r_book = client.post(
        "/en/book",
        data={
            "csrf_token": contact_csrf,
            "website": "",
            "full_name": "=CMD|' /C calc'!A0",
            "phone": "012555666",
            "service_slug": "teeth-whitening",
            "preferred_dentist_slug": "no-preference",
            "preferred_date": d.strftime("%Y-%m-%d"),
            "preferred_time_slot": "10:30",
            "consent": "1",
        },
        follow_redirects=False,
    )
    assert r_book.status_code == 303

    # Sign in to admin
    login_html = client.get("/admin/login").text
    admin_csrf = _extract_csrf(login_html)
    r_in = client.post(
        "/admin/login",
        data={
            "csrf_token": admin_csrf,
            "username": "clinic_staff",
            "password": test_secret_pw,
        },
        follow_redirects=False,
    )
    assert r_in.status_code == 303

    r_inbox = client.get("/admin/bookings")
    assert r_inbox.status_code == 200
    assert "Clinic Booking Inbox" in r_inbox.text
    assert "=CMD|" in r_inbox.text

    # Verify status transition & audit history
    db = SessionLocal()
    appt = db.query(AppointmentRequest).order_by(AppointmentRequest.id.desc()).first()
    assert appt is not None
    appt_id = appt.id
    db.close()

    inbox_csrf = _extract_csrf(r_inbox.text)
    r_status = client.post(
        f"/admin/bookings/{appt_id}/status",
        data={"csrf_token": inbox_csrf, "status": "confirmed"},
        follow_redirects=False,
    )
    assert r_status.status_code == 303

    db = SessionLocal()
    audits = db.query(BookingStatusAudit).filter_by(appointment_id=appt_id).all()
    assert len(audits) == 2
    assert audits[-1].old_status == "new"
    assert audits[-1].new_status == "confirmed"
    db.close()

    # Verify CSV export escapes spreadsheet formula characters
    r_csv = client.get("/admin/bookings/export")
    assert r_csv.status_code == 200
    assert "'=CMD|" in r_csv.text
