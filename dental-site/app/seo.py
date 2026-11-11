"""SEO metadata, canonical/hreflang builder, JSON-LD structured data, sitemap.xml, and robots.txt helpers."""

import json
from typing import Any, Dict, List

from app.clinic_data import DENTISTS, SERVICES
from app.config import CLINIC_INFO, settings


def safe_json_ld(payload: Dict[str, Any]) -> str:
    """Serialize dict to JSON-LD string with '<' escaped to prevent script-tag breakout."""
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def build_local_business_schema(lang: str) -> Dict[str, Any]:
    """Build schema.org Dentist / LocalBusiness markup using clinic info (no fake ratings)."""
    base = settings.site_base_url
    name = CLINIC_INFO["brand_name"] if lang == "en" else CLINIC_INFO["brand_name_kh"]
    address_street = CLINIC_INFO["address_en"] if lang == "en" else CLINIC_INFO["address_kh"]
    return {
        "@context": "https://schema.org",
        "@type": "Dentist",
        "@id": f"{base}/#dentist",
        "name": name,
        "legalName": CLINIC_INFO["legal_name"],
        "url": f"{base}/{lang}/",
        "telephone": CLINIC_INFO["phone_display"],
        "priceRange": CLINIC_INFO["price_range"],
        "image": f"{base}/static/img/og-share.svg",
        "logo": f"{base}/static/img/clinic-hero.svg",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": address_street,
            "addressLocality": "Phnom Penh",
            "addressCountry": "KH",
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": CLINIC_INFO["geo_lat"],
            "longitude": CLINIC_INFO["geo_lng"],
        },
        "openingHoursSpecification": [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "opens": "08:00",
                "closes": "18:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Saturday"],
                "opens": "08:00",
                "closes": "17:00",
            },
        ],
    }


def build_faq_schema(faqs: List[Dict[str, str]], lang: str) -> Dict[str, Any]:
    """Build schema.org FAQPage JSON-LD from Q&A pairs."""
    entities = []
    for item in faqs:
        q = item["q_en"] if lang == "en" else item["q_kh"]
        a = item["a_en"] if lang == "en" else item["a_kh"]
        entities.append(
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a,
                },
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }


def build_breadcrumb_schema(items: List[Dict[str, str]]) -> Dict[str, Any]:
    """Build schema.org BreadcrumbList JSON-LD."""
    base = settings.site_base_url
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": idx,
                "name": entry["name"],
                "item": f"{base}{entry['path']}",
            }
            for idx, entry in enumerate(items, start=1)
        ],
    }


def build_dentists_schema(lang: str) -> Dict[str, Any]:
    """Build ItemList of Dentist/Physician entries."""
    base = settings.site_base_url
    members = []
    for idx, d in enumerate(DENTISTS, start=1):
        members.append(
            {
                "@type": "ListItem",
                "position": idx,
                "item": {
                    "@type": "Person",
                    "name": d["name_en"] if lang == "en" else d["name_kh"],
                    "jobTitle": d["title_en"] if lang == "en" else d["title_kh"],
                    "worksFor": {"@id": f"{base}/#dentist"},
                },
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": members,
    }


def get_public_sitemap_suffixes() -> List[str]:
    """Return every indexable public sub-path suffix for sitemap.xml generation."""
    suffixes = [
        "/",
        "/services",
        "/dentists",
        "/patient-stories",
        "/about",
        "/faq",
        "/contact",
        "/privacy",
    ]
    for svc in SERVICES:
        suffixes.append(f"/services/{svc['slug']}")
    return suffixes


def render_sitemap_xml() -> str:
    """Build valid bilingual XML sitemap with xhtml:link hreflang alternates."""
    base = settings.site_base_url
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for suffix in get_public_sitemap_suffixes():
        en_url = f"{base}/en{suffix}"
        kh_url = f"{base}/kh{suffix}"
        for loc in (en_url, kh_url):
            lines.extend(
                [
                    "  <url>",
                    f"    <loc>{loc}</loc>",
                    f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>',
                    f'    <xhtml:link rel="alternate" hreflang="km" href="{kh_url}"/>',
                    f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_url}"/>',
                    "  </url>",
                ]
            )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_robots_txt() -> str:
    """Build robots.txt blocking admin/private confirmation routes."""
    base = settings.site_base_url
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /admin/\n"
        "Disallow: /en/booking-confirmed\n"
        "Disallow: /kh/booking-confirmed\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )

