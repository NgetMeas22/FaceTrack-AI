# Dental Clinic Official Website (`/dental-site`)

Clean, lightweight, accessible, bilingual (English `/en/` and Khmer `/kh/`), SEO-ready official dental clinic web application built with **FastAPI**, **Jinja2**, **SQLAlchemy 2.x**, **Alembic**, **Argon2id**, and calm light-first CSS without blocking JS frameworks.

Completely isolated from the parent **FaceTrack AI** application:
- Dedicated database configuration (`DENTAL_DATABASE_URL`, defaulting to `dental-site/data/dental_clinic.db`).
- Runs independently on port `8001` via `run.bat` or Uvicorn.

---

## Local Quickstart

From inside `dental-site/`:

```bash
# 1. Copy environment config template
copy .env.example .env

# 2. Apply database schema migrations
..\.venv\Scripts\python.exe -m alembic upgrade head

# 3. Run the application locally on port 8001
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# 4. Run full test suite
..\.venv\Scripts\python.exe -m pytest -v tests/
```

---

## Enabling Staff Booking Inbox (`/admin/bookings`)

By default, `/admin/login` is **locked (fail-closed)** unless environment variables are provided. Generate a strong Argon2id hash locally:

```bash
..\.venv\Scripts\python.exe -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('YOUR_STRONG_PASSWORD'))"
```

Set `CLINIC_ADMIN_USERNAME` and `CLINIC_ADMIN_PASSWORD_HASH` in `dental-site/.env` (never commit real passwords or hashes to Git).

---

## Pre-Launch Content Replacement Checklist (Owner Actions)

All bracketed items are intentional placeholders; zero names, credentials, prices, or reviews were fabricated:

1. **`dental-site/app/config.py` (`CLINIC_INFO`, `CLINIC_HOURS`, `CLINIC_HOLIDAYS`)**:
   - `[CLINIC LEGAL NAME]`, `[CLINIC BRAND NAME]`, `[ឈ្មោះគ្លីនិកធ្មេញ]`
   - Phone display & `tel:` link (`[PHONE: +855 XX XXX XXX]`), emergency phone, clinic email
   - Exact street address (EN & KH), parking notes, Geo coordinates (`geo_lat`, `geo_lng`), Google Maps embed URL & directions link
   - Official WhatsApp, Telegram, Facebook Messenger links, and Google Reviews profile URL
   - Official opening hours & Cambodian public holidays list
2. **`dental-site/app/clinic_data.py`**:
   - Approved treatment fee ranges / quote notes (`price_en`, `price_kh`)
   - Real dentist profiles (`DENTISTS`): names, degrees, license numbers (where appropriate), languages, bios
   - Genuine, consented patient testimonials (`TESTIMONIAL_PLACEHOLDERS`) and written-consent cases
   - Clinic story, equipment list, and payment/insurance methods (`CLINIC_FAQS`)
3. **`dental-site/app/static/img/`**:
   - Replace `clinic-hero.svg`, `dentist-placeholder.svg`, and `og-share.svg` with real clinic WebP/AVIF photos (1200x800 hero, 1200x630 OG image).
4. **`dental-site/app/translations.py`**:
   - Have a native Khmer speaker review all medical and legal wording before launch.

---

## Production Deployment Checklist

- Set `APP_ENV=production`, `SITE_BASE_URL=https://your-clinic-domain.com`, and a strong random `DENTAL_SECRET_KEY`.
- Configure PostgreSQL in `DENTAL_DATABASE_URL` and run `alembic upgrade head` before starting workers.
- Terminate TLS at Nginx/Caddy/Cloudflare (app automatically emits HSTS headers in production/HTTPS).
- Configure regular automated database backups and test restores.
