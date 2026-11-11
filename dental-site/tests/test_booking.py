"""Step 3.2 Tests: Booking flow, server-side validation, CSRF, honeypot, rate limits, XSS, and contact inquiries."""

import re
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app


def _next_valid_clinic_date() -> str:
    """Return a future Monday–Saturday date guaranteed not to be Sunday."""
    candidate = date.today() + timedelta(days=2)
    while candidate.weekday() == 6:  # Skip Sunday (closed)
        candidate += timedelta(days=1)
    return candidate.strftime("%Y-%m-%d")


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert m, "CSRF token hidden field not found in rendered HTML"
    return m.group(1)


def test_booking_happy_path_and_confirmation():
    client = TestClient(app)
    r_get = client.get("/en/contact?service=dental-implants&utm_source=google&utm_medium=cpc")
    assert r_get.status_code == 200
    assert "For dental emergencies, call" in r_get.text
    csrf_token = _extract_csrf(r_get.text)

    valid_date = _next_valid_clinic_date()
    r_post = client.post(
        "/en/book",
        data={
            "csrf_token": csrf_token,
            "website": "",
            "full_name": "Sokha Chea",
            "phone": "+855 12 888 999",
            "email": "sokha@example.com",
            "service_slug": "dental-implants",
            "preferred_dentist_slug": "dentist-placeholder-1",
            "preferred_date": valid_date,
            "preferred_time_slot": "09:30",
            "message": "Interested in consultation.",
            "consent": "1",
            "utm_source": "google",
            "utm_medium": "cpc",
        },
        follow_redirects=False,
    )
    assert r_post.status_code == 303
    location = r_post.headers["location"]
    assert location.startswith("/en/booking-confirmed?ref=DC-")
    # No patient PII (name/phone/email) leaked in URL
    assert "Sokha" not in location
    assert "888" not in location

    r_confirm = client.get(location)
    assert r_confirm.status_code == 200
    assert "Pending clinic confirmation" in r_confirm.text
    assert valid_date in r_confirm.text
    assert "09:30" in r_confirm.text
    # Ensure confirmation page does NOT publicly expose patient's personal phone or email
    assert "888" not in r_confirm.text
    assert "sokha@example.com" not in r_confirm.text


def test_booking_prevents_double_booking_same_dentist_slot():
    client = TestClient(app)
    csrf_token = _extract_csrf(client.get("/en/contact").text)
    valid_date = _next_valid_clinic_date()

    payload = {
        "csrf_token": csrf_token,
        "website": "",
        "full_name": "Patient One",
        "phone": "012333444",
        "service_slug": "general-checkup-cleaning",
        "preferred_dentist_slug": "dentist-placeholder-2",
        "preferred_date": valid_date,
        "preferred_time_slot": "10:30",
        "consent": "1",
    }
    r1 = client.post("/en/book", data=payload, follow_redirects=False)
    assert r1.status_code == 303

    r2 = client.post("/en/book", data={**payload, "full_name": "Patient Two"}, follow_redirects=False)
    assert r2.status_code == 409
    assert "Patient Two" in r2.text  # Valid input preserved on error
    assert "already has an active request" in r2.text


def test_booking_validation_and_preserved_input():
    client = TestClient(app)
    csrf_token = _extract_csrf(client.get("/kh/contact").text)

    # Compute next Sunday (closed day)
    sunday = date.today() + timedelta(days=1)
    while sunday.weekday() != 6:
        sunday += timedelta(days=1)

    r_err = client.post(
        "/kh/book",
        data={
            "csrf_token": csrf_token,
            "website": "",
            "full_name": "Dara <script>alert(1)</script>",
            "phone": "bad",
            "service_slug": "not-sure",
            "preferred_dentist_slug": "no-preference",
            "preferred_date": sunday.strftime("%Y-%m-%d"),
            "preferred_time_slot": "09:30",
            "message": "Checkup",
            # consent omitted intentionally
        },
    )
    assert r_err.status_code == 422
    # XSS payload must be HTML-escaped by Jinja2 autoescaping
    assert "<script>alert(1)</script>" not in r_err.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r_err.text
    # Localized Khmer validation messages rendered
    assert "ថ្ងៃអាទិត្យ" in r_err.text
    assert "ការយល់ព្រម" in r_err.text


def test_booking_security_csrf_honeypot_and_rate_limit():
    client = TestClient(app)

    # 1. Missing/invalid CSRF rejected with 403
    r_csrf = client.post(
        "/en/book",
        data={"csrf_token": "tampered", "full_name": "Tester", "phone": "012345678"},
    )
    assert r_csrf.status_code == 403

    # Fetch real token
    csrf_token = _extract_csrf(client.get("/en/contact").text)
    valid_date = _next_valid_clinic_date()

    # 2. Honeypot trap triggered -> 400
    r_hp = client.post(
        "/en/book",
        data={
            "csrf_token": csrf_token,
            "website": "http://spam-bot.invalid",
            "full_name": "Bot",
            "phone": "012345678",
            "preferred_date": valid_date,
            "preferred_time_slot": "08:30",
            "consent": "1",
        },
    )
    assert r_hp.status_code == 400

    # 3. Sliding-window rate limit triggers 429 after max requests (default 6)
    for idx in range(6):
        r_ok = client.post(
            "/en/book",
            data={
                "csrf_token": csrf_token,
                "website": "",
                "full_name": f"RateTester {idx}",
                "phone": "012999000",
                "service_slug": "not-sure",
                "preferred_dentist_slug": "no-preference",
                "preferred_date": valid_date,
                "preferred_time_slot": "14:30",
                "consent": "1",
            },
            follow_redirects=False,
        )
        assert r_ok.status_code == 303

    r_limited = client.post(
        "/en/book",
        data={
            "csrf_token": csrf_token,
            "website": "",
            "full_name": "RateTester Exceeded",
            "phone": "012999000",
            "service_slug": "not-sure",
            "preferred_dentist_slug": "no-preference",
            "preferred_date": valid_date,
            "preferred_time_slot": "14:30",
            "consent": "1",
        },
    )
    assert r_limited.status_code == 429
    assert "Too many submissions" in r_limited.text


def test_general_contact_inquiry_flow():
    client = TestClient(app)
    csrf_token = _extract_csrf(client.get("/en/contact").text)

    r_msg = client.post(
        "/en/contact/send",
        data={
            "csrf_token": csrf_token,
            "website": "",
            "full_name": "Bopha Keo",
            "phone": "015444555",
            "subject": "Parking question",
            "message": "Is motorbike parking available near the entrance?",
            "consent": "1",
        },
        follow_redirects=False,
    )
    assert r_msg.status_code == 303
    assert "msg_ref=MSG-" in r_msg.headers["location"]

    r_done = client.get(r_msg.headers["location"])
    assert r_done.status_code == 200
    assert "Message received" in r_done.text

