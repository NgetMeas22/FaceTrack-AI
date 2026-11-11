"""Step 3.5 Tests: Performance headers (GZip, Cache-Control), WCAG 2.1 AA structure, and bilingual parity."""

import re

from fastapi.testclient import TestClient

from app.clinic_data import SERVICES
from app.main import app
from app.translations import find_missing_translation_keys


def test_static_caching_and_gzip_compression():
    client = TestClient(app)

    r_css = client.get("/static/css/dental.css")
    assert r_css.status_code == 200
    assert "max-age=" in r_css.headers.get("cache-control", "")

    r_js = client.get("/static/js/dental.js")
    assert r_js.status_code == 200
    assert "max-age=" in r_js.headers.get("cache-control", "")

    r_html = client.get("/en/", headers={"Accept-Encoding": "gzip"})
    assert r_html.status_code == 200
    assert r_html.headers.get("content-encoding") == "gzip"


def test_accessibility_landmarks_headings_and_zero_inline_js():
    client = TestClient(app)
    routes = [
        "/en/",
        "/en/services",
        f"/en/services/{SERVICES[0]['slug']}",
        "/en/dentists",
        "/en/patient-stories",
        "/en/about",
        "/en/faq",
        "/en/privacy",
        "/en/contact",
        "/kh/",
        "/kh/services",
        "/kh/contact",
    ]
    seen_titles = set()
    seen_descriptions = set()

    for url in routes:
        r = client.get(url)
        assert r.status_code == 200, f"Failed {url}"
        html_body = r.text

        # Exactly one H1 per page
        h1_matches = re.findall(r"<h1\b", html_body)
        assert len(h1_matches) == 1, f"Expected 1 <h1> on {url}, found {len(h1_matches)}"

        # Required ARIA landmarks and skip link
        assert 'class="skip-link"' in html_body
        assert "<header" in html_body
        assert "<nav" in html_body
        assert '<main id="main-content"' in html_body
        assert "<footer" in html_body

        # Every <img> must specify alt, width, and height to avoid layout shift
        for img_tag in re.findall(r"<img\b[^>]*>", html_body):
            assert "alt=" in img_tag, f"Missing alt on img in {url}: {img_tag}"
            assert "width=" in img_tag, f"Missing width on img in {url}: {img_tag}"
            assert "height=" in img_tag, f"Missing height on img in {url}: {img_tag}"

        # CSP integrity: zero executable inline <script> blocks (only deferred dental.js or ld+json allowed)
        script_tags = re.findall(r"<script\b([^>]*)>", html_body)
        for attrs in script_tags:
            is_external = 'src="/static/js/dental.js"' in attrs and "defer" in attrs
            is_json_ld = 'type="application/ld+json"' in attrs
            assert is_external or is_json_ld, f"Disallowed script tag on {url}: <script {attrs}>"

        # Unique titles and descriptions for English indexable pages
        if url.startswith("/en/"):
            m_title = re.search(r"<title>(.*?)</title>", html_body)
            m_desc = re.search(r'<meta name="description" content="(.*?)">', html_body)
            assert m_title and m_desc
            assert m_title.group(1) not in seen_titles, f"Duplicate title on {url}"
            assert m_desc.group(1) not in seen_descriptions, f"Duplicate description on {url}"
            seen_titles.add(m_title.group(1))
            seen_descriptions.add(m_desc.group(1))


def test_khmer_css_typography_rules_and_full_translation_parity():
    client = TestClient(app)
    r_css = client.get("/static/css/dental.css")
    assert 'html[lang="km"]' in r_css.text
    assert "text-transform: none !important;" in r_css.text
    assert "prefers-reduced-motion: reduce" in r_css.text

    diff = find_missing_translation_keys()
    assert diff == {"missing_in_kh": [], "missing_in_en": []}
