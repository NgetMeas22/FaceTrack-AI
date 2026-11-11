"""Step 3.4 Tests: Canonical URLs, hreflang alternates, Open Graph, sitemap.xml, robots.txt, and JSON-LD."""

import json
import re
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from app.main import app


def _extract_json_ld_blocks(html: str):
    matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.DOTALL)
    return [json.loads(block) for block in matches]


def test_sitemap_xml_and_robots_txt():
    client = TestClient(app)

    r_map = client.get("/sitemap.xml")
    assert r_map.status_code == 200
    assert "application/xml" in r_map.headers["content-type"]
    root = ET.fromstring(r_map.text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [el.text for el in root.findall("sm:url/sm:loc", ns)]
    assert any(loc.endswith("/en/services/dental-implants") for loc in locs if loc)
    assert any(loc.endswith("/kh/services/dental-implants") for loc in locs if loc)

    r_rob = client.get("/robots.txt")
    assert r_rob.status_code == 200
    assert "Disallow: /admin" in r_rob.text
    assert "Disallow: /en/booking-confirmed" in r_rob.text
    assert "Sitemap:" in r_rob.text


def test_canonical_hreflang_og_and_json_ld():
    client = TestClient(app)

    # Canonical must drop UTM / prefill query strings
    r_contact = client.get("/en/contact?service=teeth-whitening&utm_source=fb")
    assert r_contact.status_code == 200
    assert '<link rel="canonical" href="http://127.0.0.1:8001/en/contact">' in r_contact.text
    assert '<link rel="alternate" hreflang="en" href="http://127.0.0.1:8001/en/contact">' in r_contact.text
    assert '<link rel="alternate" hreflang="km" href="http://127.0.0.1:8001/kh/contact">' in r_contact.text
    assert '<link rel="alternate" hreflang="x-default" href="http://127.0.0.1:8001/en/contact">' in r_contact.text
    assert 'property="og:title"' in r_contact.text
    assert 'property="og:image"' in r_contact.text

    # Verify JSON-LD on FAQ and Service Detail
    r_faq = client.get("/kh/faq")
    assert r_faq.status_code == 200
    schemas_faq = _extract_json_ld_blocks(r_faq.text)
    types_faq = [s.get("@type") for s in schemas_faq]
    assert "Dentist" in types_faq
    assert "FAQPage" in types_faq
    # No fabricated AggregateRating
    assert "AggregateRating" not in r_faq.text

    r_svc = client.get("/en/services/teeth-whitening")
    schemas_svc = _extract_json_ld_blocks(r_svc.text)
    types_svc = [s.get("@type") for s in schemas_svc]
    assert "Dentist" in types_svc
    assert "BreadcrumbList" in types_svc
    assert "FAQPage" in types_svc


def test_noindex_on_private_and_error_pages():
    client = TestClient(app)
    r_adm = client.get("/admin/login")
    assert '<meta name="robots" content="noindex, nofollow">' in r_adm.text

    r_404 = client.get("/en/does-not-exist")
    assert r_404.status_code == 404
    assert '<meta name="robots" content="noindex, nofollow">' in r_404.text

