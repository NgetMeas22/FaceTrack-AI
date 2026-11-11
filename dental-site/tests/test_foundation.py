"""Step 3.1 Foundation tests: config, security headers, layout, bilingual switching, and 404 handling."""

import sys
from pathlib import Path

DENTAL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DENTAL_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.translations import find_missing_translation_keys


def test_health_and_root_redirect():
    client = TestClient(app)
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json() == {"status": "ok"}

    r_root = client.get("/", follow_redirects=False)
    assert r_root.status_code == 302
    assert r_root.headers["location"] == "/en/"


def test_foundation_home_en_and_kh():
    client = TestClient(app)

    r_en = client.get("/en/")
    assert r_en.status_code == 200
    assert '<html lang="en">' in r_en.text
    assert 'Skip to main content' in r_en.text
    assert 'Book Appointment' in r_en.text
    assert '[CLINIC BRAND NAME]' in r_en.text

    # Verify strict security headers
    assert r_en.headers.get("x-content-type-options") == "nosniff"
    assert r_en.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in r_en.headers

    r_kh = client.get("/kh/")
    assert r_kh.status_code == 200
    assert '<html lang="km">' in r_kh.text
    assert 'ណាត់ជួបពេទ្យ' in r_kh.text


def test_custom_404_rendering():
    client = TestClient(app)
    r_404 = client.get("/en/non-existent-page-xyz")
    assert r_404.status_code == 404
    assert "Page not found" in r_404.text

    r_404_kh = client.get("/kh/non-existent-page-xyz")
    assert r_404_kh.status_code == 404
    assert "រកមិនឃើញទំព័រនេះទេ" in r_404_kh.text


def test_translation_keys_match():
    diff = find_missing_translation_keys()
    assert diff["missing_in_kh"] == []
    assert diff["missing_in_en"] == []
