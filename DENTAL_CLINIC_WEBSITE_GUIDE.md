# Dental Clinic Official Website — Improvement & Agent Guide

**Status:** Living project standard
**Audience:** AI coding agents, web designers, full-stack developers, UI/UX designers, marketers, QA
**Purpose:** Review the existing dental clinic website and improve it into a modern, minimalist, fast, accessible, SEO-ready, production-quality official website with online booking and easy patient communication.

> **Core rule:** Inspect the existing repository before changing anything. Preserve working behavior, reuse existing patterns, and explain any deviation. Do not claim a feature is complete until it is implemented and tested. Never invent files, test results, clinic data, dentists, credentials, prices, or reviews.

---

## 0. Before you start (mandatory)

1. **Inspect the repo:** stack, routes, templates/pages, forms, database/models, assets, translations, config, tests, Git history.
2. **Record what already works** (booking form, contact form, admin, language switch, etc.) in a short "Preserve" list. Do not break it.
3. **Collect real clinic content** from the owner (see Section 3). Use clearly marked placeholders (`[CLINIC NAME]`, `[PHONE]`) for anything missing. Never fabricate it.
4. **Plan** the affected pages, components, endpoints, tables, translations, and tests. State assumptions.
5. **Implement in small steps.** No full rewrite. No new framework, database, or paid dependency without owner approval.
6. **Test, review, report honestly** (files changed, commands run, results, risks, what could not be tested).

> **Stack note:** This guide is stack-agnostic. Keep the project's current stack. If it is a static site, keep it static; if it is server-rendered (e.g. FastAPI + Jinja2), keep that. Prefer plain HTML, CSS and small vanilla JavaScript. Pin dependency and CDN versions; add SRI where supported.

---

## 1. Product goals

The site exists to help a patient do four things quickly:

1. **Understand** what the clinic offers and whether it fits them.
2. **Trust** the clinic (real dentists, real reviews, clear safety and pricing information).
3. **Book** an appointment in under a minute, on a phone.
4. **Reach** the clinic by call, message, or map with one tap.

Prioritize **clarity, speed, trust, accessibility, and conversion** over decoration. Every element must earn its place.

---

## 2. Information architecture (keep navigation simple)

Maximum 6 top-level items plus a persistent **Book Appointment** button.

| Page | Purpose | Key content |
|---|---|---|
| **Home** | Convert and orient | Hero with one clear CTA, 4–6 top services, why choose us, dentist preview, 3 testimonials, hours/location strip, final CTA |
| **Services** | Explain treatments | Service list grouped by category; one detail page per service |
| **Service detail** | Answer questions, rank for search | What it is, who it's for, procedure steps, duration, recovery, FAQ, price range or "from" price if approved, Book CTA |
| **Our Dentists** | Build trust | Photo, name, title, specialty, languages, qualifications, years of experience, short bio, Book-with-this-dentist CTA |
| **Patient Stories** | Social proof | Verified testimonials, optional before/after (with written consent) |
| **Contact / Book** | Reach and convert | Booking form, phone, messaging apps, address, embedded map, hours, parking/transport notes |
| **About / Clinic** | Credibility | Story, clinic photos, sterilization and safety standards, equipment |
| **FAQ** | Reduce calls | Pricing, insurance/payment, first visit, emergencies, kids, anxiety |
| **Privacy / Terms** | Compliance | Privacy policy, cookie notice if tracking is used |

Footer: address, hours, phone, social links, language switch, privacy link, copyright.

---

## 3. Real content to collect (do not invent)

- Clinic legal name, brand name, logo, brand colors.
- Address, map pin, opening hours (including holidays), phone, messaging handles (WhatsApp, Telegram, Facebook Messenger, etc.), email.
- Services actually offered, with approved descriptions and price ranges (or "contact us for a quote").
- Dentist details: full name, license/registration number (if appropriate to publish), qualifications, specialties, languages, photo, bio.
- Real patient testimonials with **written permission** to publish name/initials and photo.
- Before/after photos only with **explicit written consent**.
- Payment methods, insurance policy, emergency policy, cancellation policy.
- Clinic photos (exterior, reception, treatment rooms). Use real photos; avoid generic stock images of fake "patients."

If any item is missing, use a visible placeholder and list it in the final report.

---

## 4. Design system (modern, minimalist, calm)

**Feeling:** clean, bright, reassuring, professional. Generous white space. No heavy gradients, glow, parallax, autoplay video, or decorative animation.

### Tokens (centralize as CSS variables)

- **Colors:** one primary brand color (calm blue/teal works well for dental), one accent for CTAs, neutral grays, white/off-white backgrounds, semantic success/warning/error colors. Light theme by default; dark theme optional.
- **Typography:** one sans-serif family, 2 weights. System font stack or a single self-hosted/pinned web font with `font-display: swap`. If Khmer is supported, add a Khmer-capable font (Kantumruy Pro, Battambang, or Noto Sans Khmer).
- **Scale:** base 16–18px body, 1.5–1.7 line height, modular heading scale.
- **Spacing:** 4/8px grid. Consistent section padding.
- **Radius and shadow:** one or two radius values, one subtle shadow level.
- **Icons:** one consistent icon set (e.g. Lucide), inline SVG preferred.

### Components (build once, reuse)

- Header with logo, simple nav, language switch, and sticky **Book Appointment** button.
- Hero (headline, one sentence, primary CTA, secondary "Call us").
- Service card, dentist card, testimonial card, FAQ accordion (keyboard accessible), info strip (hours/location), footer.
- Buttons (primary, secondary, text), form fields, alerts, badges, modal (only when necessary).
- **Mobile sticky action bar:** Call · Message · Book (visible on small screens).

### Layout rules

- Mobile-first. Test at 360, 390, 768, 1024, 1280, 1440 px.
- One primary CTA per section. Do not compete with multiple equal buttons.
- Tables and long content must not cause horizontal page scroll on mobile.
- Reserve image dimensions to avoid layout shift.

---

## 5. Essential real-world features (only what a clinic needs)

### 5.1 Online appointment booking (priority feature)

**Form fields (keep minimal):**
- Full name (required)
- Phone number (required; validated, international format friendly)
- Email (optional)
- Service (select, optional "Not sure")
- Preferred dentist (optional, "No preference")
- Preferred date and time slot (required)
- Message / symptoms (optional, with length limit)
- Consent checkbox for contact and data processing (required, links to Privacy Policy)

**Behavior:**
- Fully usable with keyboard and on mobile; large touch targets; correct `inputmode`/`autocomplete` attributes.
- Inline validation with clear messages; preserve valid input after errors; disable the submit button while sending (no duplicate submissions).
- Show only valid dates (no past dates, no closed days/holidays) and clinic hours.
- Booking is a **request** unless real-time slot management exists. Show: "We will confirm by phone/message within [X] hours." Do not promise a confirmed slot unless the system enforces it.
- Confirmation page/message with summary and a reference number; optional confirmation email/message to the patient.
- Notify the clinic immediately (email and/or messaging webhook) so requests are not missed.
- Spam protection: honeypot field, rate limiting, and optionally a privacy-friendly CAPTCHA. Do not harm accessibility.
- Emergency notice near the form: "For dental emergencies, call [PHONE]."

**Server rules (if there is a backend):**
- Validate everything server-side with allow-lists, lengths, and types; never trust the client.
- Use parameterized queries/ORM only.
- CSRF protection for state-changing requests; rate limit the endpoint.
- Prevent double-booking of the same dentist/slot if slot management is enabled (database constraint or transaction).
- Store timestamps in UTC; display in the clinic's timezone (default `Asia/Phnom_Penh`).
- Audit status changes (new → contacted → confirmed → completed/cancelled/no-show).

### 5.2 Patient communication

- One-tap **call** (`tel:`) and **message** links (WhatsApp/Telegram/Messenger deep links with a prefilled greeting).
- Click-to-open **Google Maps** directions link plus an embedded map (lazy-loaded).
- Business hours with "Open now" indicator computed in the clinic timezone.
- Optional appointment reminders (SMS/email/messaging) **only with patient consent**, with easy opt-out.
- Contact form for general questions (separate from booking, same spam and validation rules).

### 5.3 Trust and marketing content

- **Dentist profiles** with real credentials. Do not publish unverifiable qualifications or awards.
- **Testimonials:** real, consented, dated if possible, with an optional link to the original Google review. Never write fake reviews or attribute invented quotes to real people. Do not offer incentives in exchange for positive reviews.
- **Google reviews widget:** link to the clinic's Google Business Profile reviews rather than embedding heavy third-party scripts.
- **Before/after gallery:** only with written consent, honest captions, and a note that results vary.
- **Clinic safety and sterilization** section (describe actual practices only).
- **FAQ** for pricing, first visit, children, anxiety, insurance, payment, and emergencies.
- **Pricing transparency:** show "from" prices or ranges if approved; otherwise explain how quotes work.
- **Medical claims:** no guarantees, no exaggerated claims ("painless," "100% success"), no unverifiable superlatives ("best in the city"). Use honest, plain language and follow local advertising rules for health services.

### 5.4 Optional enhancements (add only if clearly useful)

- Simple blog/articles for SEO (oral-health tips written or reviewed by a dentist).
- Newsletter signup (with consent and double opt-in).
- Simple admin view for appointment requests (search, filter by status/date, pagination, export with formula-injection protection).
- Multilingual support (see Section 9).

**Avoid:** chatbots that give medical advice, popups on page load, autoplay media, live-chat widgets that slow the site, loyalty gamification, and any feature without a clear patient or clinic benefit.

---

## 6. SEO and Google visibility

### Technical SEO

- One `<h1>` per page; logical heading order.
- Unique `<title>` (≈50–60 chars) and meta description (≈140–160 chars) per page, including service and city keywords naturally (e.g. "Dental Implants in Phnom Penh | [Clinic Name]").
- Clean, readable URLs (`/services/teeth-whitening`), canonical tags, and no duplicate content between language versions.
- `hreflang` tags for each language version, plus `x-default`.
- `sitemap.xml` and `robots.txt` (block admin/private paths; allow public pages). Submit the sitemap to Google Search Console.
- Open Graph and Twitter Card tags with a properly sized share image.
- Custom 404 page and correct status codes; 301 redirects for any renamed URLs.
- HTTPS everywhere with HSTS at the proxy.
- Descriptive `alt` text for meaningful images; empty `alt=""` for decorative ones.

### Structured data (JSON-LD)

Add valid schema.org markup using real data only:

- `Dentist` / `LocalBusiness` (name, address, phone, geo, opening hours, price range, logo, image, `sameAs` social links).
- `Physician`/`Person` for dentists where appropriate.
- `FAQPage` on pages with real FAQ content.
- `BreadcrumbList` for service pages.
- Include `AggregateRating` **only** if it reflects genuine, verifiable reviews and complies with Google's review guidelines; otherwise omit it.

Validate with Google's Rich Results Test. Serialize JSON-LD safely (no unescaped user input).

### Local SEO checklist (for the owner/marketer)

- Claim and complete the **Google Business Profile**: correct categories, services, hours, photos, booking link, and Q&A.
- Keep **NAP** (name, address, phone) identical on the site, Google, Facebook, and directories.
- Build a simple review-request process (ask real patients; never buy or fake reviews).
- Add the site to Google Search Console and set up analytics (see Section 8).
- Create a dedicated page per major service and a clear location/contact page.

### Content guidance

- Write for patients: plain language, short paragraphs, question-style headings that match real searches.
- Each service page: 300–600 useful words, a real FAQ, and a clear CTA. Avoid keyword stuffing.
- Link related services and dentists internally.

---

## 7. Performance and Core Web Vitals

**Targets (mobile, 4G):** LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1; Lighthouse Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95, SEO ≥ 95. Verify by measurement, not assumption.

- Optimize images: modern formats (WebP/AVIF) with fallback, responsive `srcset`/`sizes`, explicit `width`/`height`, `loading="lazy"` below the fold, hero image prioritized (`fetchpriority="high"`).
- Remove unused CSS/JS; avoid large libraries. Defer non-critical scripts. Minimize third-party scripts (maps, chat, analytics) and lazy-load them.
- Self-host or preconnect to fonts; limit font weights; use `font-display: swap`.
- Enable gzip/Brotli compression and long-lived cache headers for fingerprinted static assets.
- Avoid layout shift: reserve space for images, embeds, and banners.
- Respect `prefers-reduced-motion`.
- Measure with Lighthouse, PageSpeed Insights, and WebPageTest before and after changes; report the numbers honestly.

---

## 8. Analytics and marketing measurement

- Use privacy-friendly analytics where possible (or Google Analytics 4 with consent if required by local law).
- Track **conversions only**: booking form submitted, call tap, message tap, directions tap.
- Use UTM parameters on campaign links; record the source on booking requests.
- Do not record form contents (names, phone numbers, symptoms) in analytics or logs.
- Show a concise cookie/consent notice only if non-essential tracking is used; no dark patterns.

---

## 9. Localization (optional, recommended for Cambodia)

If the clinic serves English and Khmer speakers:

- Use language routes (`/en/...`, `/kh/...`) and a visible language switch that preserves the current page.
- Keep all user-facing strings in one translation layer; every key must exist in both languages.
- Translate navigation, forms, validation errors, statuses, confirmations, metadata, and `alt` text.
- Avoid uppercase transforms and wide letter spacing on Khmer text; use a Khmer-capable font; test wrapping and clipping.
- Set `<html lang="en">` / `lang="km"` correctly, with consistent date, time, and number formats; show the timezone where relevant.
- Have a native speaker review medical and legal wording. Do not rely on machine translation alone.

---

## 10. Accessibility (WCAG 2.1 AA)

- Semantic landmarks (`header`, `nav`, `main`, `footer`), a "Skip to content" link, and a logical tab order.
- Visible focus indicators; all interactive elements usable by keyboard (menus, accordions, dialogs, date pickers).
- Color contrast ≥ 4.5:1 for text; do not rely on color alone for status or errors.
- Labels connected to every form field; errors announced (`aria-live`/`aria-describedby`); required fields clearly marked.
- Accessible names for icon-only buttons; `alt` text for images; captions/transcripts for any video.
- Touch targets ≥ 44×44 px; text resizable to 200% without breaking layout.
- Test with a screen reader and keyboard-only navigation, not just automated tools.

---

## 11. Security and privacy

Patient inquiries can contain health information. Treat all submissions as sensitive personal data.

- HTTPS only; secure headers (CSP, `X-Content-Type-Options`, frame protection, Referrer-Policy).
- Keep autoescaping on in templates; never insert user input into HTML or scripts unescaped.
- Validate and sanitize all input server-side; limit request size; rate limit forms.
- CSRF protection on state-changing requests; `GET` must not change state.
- Store only the data you need; define a retention period; allow patients to request deletion/correction.
- Restrict admin access: strong passwords hashed with Argon2id or bcrypt, rate-limited login, role-based access, and logout/session expiry. No default or demo credentials in production.
- Never commit secrets, `.env` files, patient data, or databases to Git.
- Do not expose stack traces, internal paths, or SQL errors to visitors.
- Do not log phone numbers, messages, or health details in plain text.
- Provide a clear Privacy Policy describing what is collected, why, how long, who can access it, and how to contact the clinic.
- Back up data regularly and test restores.

---

## 12. Engineering standards

- **Reuse before adding.** Prefer existing components, utilities, and patterns.
- **Separation:** presentation in templates/CSS, validation and business rules on the server, minimal JavaScript for interaction only.
- **Database changes** (if any) require migrations with rollback notes; never drop user data silently. Add constraints and indexes only where queries need them.
- **Lists in admin** (appointments, messages): server-side pagination, allow-listed sorting, search, status/date filters, empty and error states.
- **Errors:** friendly messages for users, detailed structured logs for operators (with a request ID), no swallowed exceptions.
- **Config:** environment variables validated at startup; fail safely when production configuration is missing.
- **Git:** small, focused commits (`feat:`, `fix:`, `seo:`, `perf:`, `a11y:`, `test:`, `docs:`); keep `main` deployable; do not bypass tests.

---

## 13. Testing and quality gates

| Area | What to verify |
|---|---|
| **Functional** | Booking submission (valid, invalid, duplicate, spam), contact form, navigation, language switch, admin workflows |
| **Validation** | Required fields, phone/email formats, date/time limits, length limits, error messages preserved input |
| **Security** | CSRF, XSS payloads, SQL injection attempts, rate limiting, unauthorized admin access, safe headers |
| **Responsive** | 360/390/768/1024/1280/1440 px, portrait and landscape, no horizontal scroll |
| **Accessibility** | Keyboard-only flow, screen reader pass, contrast, focus order, form labels, axe/Lighthouse |
| **SEO** | Titles/descriptions, canonicals, hreflang, sitemap, robots, JSON-LD validation, broken links, redirects |
| **Performance** | Lighthouse and PageSpeed (mobile), image sizes, third-party script impact |
| **Cross-browser** | Latest Chrome, Safari (iOS), Firefox, Edge; Android Chrome |
| **Content** | No placeholder text, fake reviews, or dummy phone numbers left in production |

Run the existing test suite first, then add focused tests for new behavior. Do not report passing tests unless the commands were actually run and passed. State clearly what could not be tested.

---

## 14. Forbidden patterns

- Rewriting the whole site or switching stacks without owner approval.
- Fake dentists, fake credentials, fake testimonials, fake review counts, or stock photos presented as real staff or patients.
- Publishing patient photos, names, or before/after images without written consent.
- Misleading medical claims, guarantees, or unverifiable "best" claims.
- Frontend-only validation or trusting hidden fields.
- Raw SQL string interpolation; unvalidated redirects; unescaped user content.
- Hard-coded secrets, demo credentials, or committed personal data.
- Heavy autoplay video, intrusive popups, or layout-shifting banners.
- Keyword stuffing, hidden text, purchased reviews, or other spam SEO tactics.
- Tracking scripts that capture form contents or health information.
- Features added only to look "advanced."

---

## 15. Definition of done

- [ ] Existing working functionality inspected, listed, and preserved.
- [ ] Modern minimalist design applied consistently with shared tokens and components.
- [ ] Simple navigation (≤ 6 items) and a persistent Book Appointment CTA.
- [ ] Home, Services (with detail pages), Dentists, Patient Stories, Contact/Book, About, FAQ, and Privacy pages complete with real or clearly flagged placeholder content.
- [ ] Booking flow works end to end: validation, spam protection, clinic notification, patient confirmation, and an emergency notice.
- [ ] One-tap call, message, and directions on mobile; mobile sticky action bar works.
- [ ] SEO complete: titles, descriptions, canonicals, hreflang (if multilingual), sitemap, robots, Open Graph, valid JSON-LD.
- [ ] Core Web Vitals and Lighthouse targets measured and reported.
- [ ] WCAG 2.1 AA checks passed, including keyboard and screen reader testing.
- [ ] Security and privacy controls in place; no secrets or patient data in Git.
- [ ] English/Khmer (or chosen languages) complete and visually checked.
- [ ] Tests run and results reported honestly; known risks and untested items listed.
- [ ] Setup, deployment, and content-update instructions documented.

---

## 16. Implementation priority

1. **Foundation:** inspect the repo, fix security and data-integrity issues, preserve working features, set design tokens and the responsive layout.
2. **Conversion core:** booking flow, call/message/map actions, clear homepage, contact page.
3. **Trust content:** services, dentist profiles, testimonials (real), FAQ, about and safety information.
4. **Visibility:** on-page SEO, structured data, sitemap, local SEO checklist, analytics conversions.
5. **Performance and accessibility pass:** image optimization, script trimming, Lighthouse and WCAG fixes.
6. **Polish and operations:** admin view for requests, notifications/reminders (consent-based), documentation, monitoring, backups.
7. **Optional:** blog content, newsletter, additional languages, advanced reporting.

Implement in small, testable steps. Do not add complexity to appear enterprise-grade.

---

## 17. Final report template (agent must provide)

1. **Summary:** what was improved and why.
2. **Preserved:** existing features confirmed working.
3. **Files changed/added:** list with one-line purpose each.
4. **Features delivered:** mapped to the requirements above.
5. **Commands and tests run:** exact commands and results.
6. **Metrics:** Lighthouse/PageSpeed before and after (if measured).
7. **Migrations/config changes:** with rollback notes.
8. **Placeholders and missing content:** what the owner must supply.
9. **Risks and untested areas:** stated honestly.
10. **Recommended next steps:** short, prioritized.
