# FaceTrack AI — Enterprise Technical Architecture & Agent Operating Guide

**Document Status**: Authoritative / Living Document  
**Audience**: AI Coding Assistants, LLM Agents, Full-Stack Python Engineers, Security Reviewers, UI/UX Designers, DBAs  
**Repository Purpose**: Enterprise AI-powered biometric workforce intelligence, real-time facial recognition attendance, personnel directories, and role-governed organizational access.  
**Precedence Rule**: If this guide conflicts with an ad-hoc instruction in a chat, the guide wins unless the project owner explicitly amends it in the same message. Propose guide changes in a PR; never silently drift from it.

---

## Table of Contents
1. [Architectural Philosophy](#1-architectural-philosophy)
2. [Directory & File Structure](#2-directory--file-structure)
3. [Technology Stack & Key Dependencies](#3-technology-stack--key-dependencies)
4. [Request Lifecycle & Layering Rules](#4-request-lifecycle--layering-rules)
5. [Role-Based Access Control (RBAC)](#5-role-based-access-control-rbac)
6. [Application Security Standards](#6-application-security-standards)
7. [Biometric Data Governance & Privacy](#7-biometric-data-governance--privacy)
8. [Biometrics & Computer Vision Pipeline](#8-biometrics--computer-vision-pipeline)
9. [Database Design (PostgreSQL-first, SQLite-compatible)](#9-database-design-postgresql-first-sqlite-compatible)
10. [HTTP & REST API Conventions](#10-http--rest-api-conventions)
11. [Localization & Khmer Typography Engine](#11-localization--khmer-typography-engine)
12. [UI/UX Design System](#12-uiux-design-system)
13. [Error Handling, Logging & Observability](#13-error-handling-logging--observability)
14. [Performance & Scalability Standards](#14-performance--scalability-standards)
15. [Testing Strategy & Quality Gates](#15-testing-strategy--quality-gates)
16. [Developer Commands & Environment](#16-developer-commands--environment)
17. [Configuration & Secrets Management](#17-configuration--secrets-management)
18. [Deployment & Operations](#18-deployment--operations)
19. [Git Workflow & Change Management](#19-git-workflow--change-management)
20. [Agent Operating Protocol (Mandatory)](#20-agent-operating-protocol-mandatory)
21. [Feature Implementation Playbooks](#21-feature-implementation-playbooks)
22. [Anti-Patterns (Forbidden)](#22-anti-patterns-forbidden)
23. [Definition of Done Checklist](#23-definition-of-done-checklist)
24. [Known Gaps & Hardening Roadmap](#24-known-gaps--hardening-roadmap)
25. [Glossary](#25-glossary)

---

## 1. Architectural Philosophy

FaceTrack AI is engineered as a **100% Pure Python Monolith**. It avoids the operational complexity of Node.js/npm pipelines, webpack, or external front-end build tools while delivering a modern, high-contrast, responsive enterprise application.

```text
┌──────────────────────────────────────────┐
│      Client Browser (Desktop/Mobile)     │
│   Tailwind CDN + Chart.js + Lucide CDN   │
└────────────────────┬─────────────────────┘
                     │ HTTPS / REST / Multipart
                     ▼
┌──────────────────────────────────────────┐
│           FastAPI Web Server             │
│      Jinja2 Server-Side Rendering        │
│   Session Authentication & RBAC Guard    │
└────────────┬──────────────────┬──────────┘
             │                  │
SQLAlchemy ORM │                  │ OpenCV Inference
             ▼                  ▼
┌─────────────────────┐  ┌─────────────────┐
│   Database Engine   │  │ Biometrics Core │
│  Neon PostgreSQL /  │  │  OpenCV YuNet   │
│   SQLite Fallback   │  │   OpenCV SFace  │
└─────────────────────┘  └─────────────────┘
```

### Core Design Tenets
- **Zero Node.js/npm**: Tailwind CSS, Chart.js, and Lucide icons are served via trusted CDNs.
- **Server-Side Rendered (SSR) with Jinja2**: Fast initial load, SEO-friendly, zero client hydration lag, and clean session security.
- **Bilingual First-Class Citizen**: Complete localized routing via `/{lang}/...` with `/en` (English) and `/kh` (Khmer) coverage.
- **Adaptive Aesthetic Themes**: High-contrast dark mode (`#181818` / `#222225`) and crisp light mode (`#f8fafc` / `#ffffff`) with instant early script evaluation to eliminate theme flickering.
- **Dual Database Portability**: Runs out-of-the-box on local SQLite (`data/facetrack.db`) and automatically connects to Neon Serverless PostgreSQL when configured in `.env`.

### Additional Engineering Principles
- **Secure by Default**: Every new route, form, and upload is denied/validated until explicitly allowed. Security is a feature requirement, never a follow-up task.
- **Least Privilege**: Roles receive the minimum permissions needed. Permission checks happen server-side on every request; hidden UI is cosmetic, never a control.
- **Privacy by Design**: Biometric templates are treated as the most sensitive data class in the system (see §7).
- **Single Source of Truth**: Business rules live in one place (service/helper function), not duplicated in routes and templates.
- **Idempotent, Auditable Mutations**: Every state-changing action is attributable to an actor and recorded in the audit trail.
- **Graceful Degradation**: Missing ML models, missing photos, DB fallback, or camera denial must produce a clear UI state, never a stack trace.
- **Boring Technology**: Prefer stable, well-understood libraries over novelty. New dependencies require justification (§20.6).

---

## 2. Directory & File Structure

```text
├── .env                              # Private environment secrets (Neon DB URL, SECRET_KEY) - GITIGNORED
├── .env.example                      # Documented environment template
├── .gitignore                        # Must include .env, data/, ml_models/, .venv/, __pycache__/
├── requirements.txt                  # Python dependencies (pinned)
├── download_models.py                # Automated downloader for OpenCV YuNet & SFace ONNX models
├── AGENT_GUIDE.md                    # This authoritative document
├── README.md                         # Project documentation and developer quickstart
│
├── app/
│   ├── main.py                       # FastAPI entrypoint, HTTP/API routes, SSR views, file upload handlers
│   ├── database.py                   # SQLAlchemy engine, session maker, get_db dependency, seed initial data
│   ├── models.py                     # Declarative ORM models (User, Employee, Department, Attendance, Logs)
│   ├── security.py                   # Role-Based Access Control (RBAC), password hashing, session tokens
│   ├── face_recognition.py           # OpenCV YuNet detector & SFace feature vector engine (128-d SFace)
│   ├── translations.py               # Complete English & Khmer bilingual dictionary
│   │
│   ├── templates/                    # Jinja2 HTML layouts & views
│   │   ├── base.html                 # Master layout (Navbar, Sidebar, Theme switcher, Language switcher)
│   │   ├── dashboard.html            # 2:1 Analytics grid (Spline wave chart, Donut gauge, Scanner HUD, Dossier)
│   │   ├── employees.html            # Personnel management, Add/Edit modals, Biometric registration
│   │   ├── departments.html          # Organizational departments directory & CRUD modals
│   │   ├── scanner.html              # Dedicated full-screen interactive face recognition scanner
│   │   ├── attendance.html           # Live attendance logs, shift status filter, confidence tracking
│   │   ├── audit_logs.html           # Immutable system event logs, security audit trail
│   │   ├── reports.html              # Workforce analytics, department percentages, CSV/JSON exports
│   │   ├── settings.html             # 5-tab system settings (Security, Profile, Notifications, System, Privacy)
│   │   ├── security.html             # User operators table, clearance provisioning, cryptographic sessions
│   │   ├── login.html                # Zero-trust login view with 1-click test role credentials (DEV ONLY)
│   │   └── 403_forbidden.html        # Localized Access Denied error view
│   │
│   └── static/
│       ├── css/
│       │   └── styles.css            # Master styles, Khmer typography engine, HUD animations, radar spinning
│       └── js/
│           ├── main.js               # Global UI utilities, alerts, audio chimes, modal helpers
│           └── scanner.js            # Video stream processing, holographic radar, biometric landmarks, telemetry
│
├── data/                             # Local SQLite database and employee uploaded photos - GITIGNORED
│   ├── facetrack.db                  # Local SQLite database fallback
│   └── uploads/                      # Employee and operator avatar photos
│
├── ml_models/                        # Pretrained ONNX weights - GITIGNORED
│   ├── face_detection_yunet_2023mar.onnx
│   └── face_recognition_sface_2021dec.onnx
│
└── tests/
    ├── test_rbac_matrix.py           # Comprehensive permission tests for all 4 roles across all routes
    └── test_roles_navbar_logout.py   # Test suite for session lifecycle, avatars, and logout alerts
```

### File Ownership & Responsibility Boundaries

| File | Owns | Must NOT contain |
| :--- | :--- | :--- |
| `main.py` | Route definitions, request parsing, response/redirect construction, template context | Raw SQL, ML math, password hashing logic, long business rules |
| `database.py` | Engine/session config, `get_db`, `init_db()`, seeds | Route logic, business rules |
| `models.py` | Table definitions, relationships, constraints, indexes | Query orchestration, HTTP concerns |
| `security.py` | Authentication, RBAC matrix, hashing, session/token helpers, CSRF helpers | Template rendering, DB schema |
| `face_recognition.py` | Detection, quality gate, embedding, matching | DB writes, HTTP concerns |
| `translations.py` | All user-visible strings in `en` and `kh` | Logic, HTML markup beyond trivial inline tags |

**Growth rule**: If `main.py` exceeds ~800 lines or a domain (e.g., employees) exceeds ~10 routes, split into `app/routers/<domain>.py` using `APIRouter`, and move business logic into `app/services/<domain>.py`. Do this as a dedicated refactor PR with zero behavior change and a passing test suite.

---

## 3. Technology Stack & Key Dependencies

| Component | Library / Tool | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | `fastapi` (v0.110+) | High-performance async ASGI web framework |
| **Server Engine** | `uvicorn` (v0.28+) | Standard ASGI server running at `127.0.0.1:8000` |
| **Templating** | `jinja2` (v3.1+) | Server-side rendering for HTML templates |
| **ORM & Database** | `SQLAlchemy` (v2.0+) | Declarative relational database ORM |
| **PostgreSQL Driver** | `psycopg2-binary` | Native PostgreSQL connection adapter for Neon cloud |
| **MySQL Driver** | `pymysql` | Optional driver for cPanel / MariaDB deployment |
| **Environment Loader** | `python-dotenv` | Automatic environment parsing from `.env` |
| **Computer Vision** | `opencv-python-headless` | CPU-optimized computer vision without GUI dependencies |
| **Vector Math** | `numpy` | Array operations on 128-d face embeddings |
| **Frontend Styling** | Tailwind CSS CDN | Modern utility-first CSS framework |
| **Khmer Fonts** | Google Fonts | `Kantumruy Pro`, `Battambang`, and `Noto Sans Khmer` |
| **Data Viz** | Chart.js CDN | Spline wave attendance trends & compliance donut gauges |
| **Icons** | Lucide Icons CDN | Scalable, clean vector interface icons |

### Dependency Policy
- Pin versions in `requirements.txt` (`package==x.y.z`). Use ranges only in documentation.
- Allowed without approval: patch/minor upgrades of existing dependencies after tests pass.
- Requires explicit approval: any new runtime dependency, any dependency requiring a compiler toolchain, any Node/npm-based tool.
- Password hashing: use `argon2-cffi` (preferred) or `bcrypt`. Never use plain SHA/MD5 for passwords.
- CDN assets: pin an exact version in the URL and add integrity (SRI) + `crossorigin="anonymous"` attributes where the CDN supports it. Never use `@latest`.

---

## 4. Request Lifecycle & Layering Rules

### 4.1 Standard Page Request (`GET /{lang}/<page>`)
```text
Request
  │
  ├─ 1. Validate {lang} ∈ {en, kh} → else 404 or redirect to default language
  ├─ 2. require_user() → resolve session → 401/redirect to /{lang}/login
  ├─ 3. check_view_access(user, page) → 403 page (localized) if role not permitted
  ├─ 4. Query via SQLAlchemy session (get_db dependency; parameterized only)
  ├─ 5. Build template context: user, lang, t (translations), data, csrf_token
  └─ 6. TemplateResponse (Jinja2 autoescape ON)
```

### 4.2 Standard Mutation Request (`POST /api/...`)
```text
Request
  │
  ├─ 1. require_user() → authenticate
  ├─ 2. Role permission check → authorize (server-side, per action)
  ├─ 3. CSRF token verification → reject on mismatch
  ├─ 4. Input validation (Pydantic / Form) → type, length, format, allow-list
  ├─ 5. Business rule checks → uniqueness, referential rules, state
  ├─ 6. DB transaction (commit or rollback) → all-or-nothing
  ├─ 7. Audit log entry (same transaction) → actor, action, target, outcome, IP
  └─ 8. Response: redirect (HTML forms, preserve lang) or JSON (fetch/XHR)
```

### 4.3 Layering Rules
- **Routes are thin**: parse ➔ authorize ➔ delegate ➔ respond. Aim for < 40 lines per route handler.
- **Never trust the client**: role, user ID, employee ID, attendance status, and confidence scores are derived server-side. A client-supplied value may only be used as a lookup key after authorization.
- **One transaction per request**: use the `get_db` dependency; commit once on success, rollback on any exception.
- **No business logic in templates**: Jinja2 handles presentation only (loops, conditionals, formatting). Calculations (percentages, aggregates, compliance) happen in Python.
- **Time handling**: Store all timestamps in UTC. Convert to the user's display timezone at render time only (default business zone: `Asia/Phnom_Penh`, UTC+07:00). Never store naive local times.

---

## 5. Role-Based Access Control (RBAC)

FaceTrack AI enforces strict Zero-Trust role governance on both view routes (`GET /{lang}/...`) and REST API mutations (`POST /api/...`).

### 5.1 View Access Matrix

| Page / Route | Path | ADMIN | HR_MANAGER | SECURITY_OFFICER | EMPLOYEE (Staff) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Dashboard** | `/{lang}/dashboard` | ✅ | ✅ | ✅ | ✅ |
| **Live Scanner** | `/{lang}/scanner` | ✅ | ✅ | ✅ | ✅ |
| **Attendance Logs** | `/{lang}/attendance` | ✅ | ✅ | ✅ | ✅ |
| **Employee Directory** | `/{lang}/employees` | ✅ | ✅ | ❌ | ❌ |
| **Departments** | `/{lang}/departments` | ✅ | ✅ | ❌ | ❌ |
| **Audit Logs** | `/{lang}/audit-logs` | ✅ | ❌ | ✅ | ❌ |
| **Reports & Analytics** | `/{lang}/reports` | ✅ | ✅ | ❌ | ❌ |
| **System Settings** | `/{lang}/settings` | ✅ | ❌ | ❌ | ❌ |
| **Security & Roles** | `/{lang}/security` | ✅ | ❌ | ❌ | ❌ |

### 5.2 Mutation Authorization Matrix (API)

| Capability | ADMIN | HR_MANAGER | SECURITY_OFFICER | EMPLOYEE |
| :--- | :---: | :---: | :---: | :---: |
| Create / edit / deactivate employee | ✅ | ✅ | ❌ | ❌ |
| Register / replace employee biometric template | ✅ | ✅ | ❌ | ❌ |
| Delete employee (hard delete) | ✅ | ❌ | ❌ | ❌ |
| Create / edit / delete department | ✅ | ✅ *(no delete if staff assigned)* | ❌ | ❌ |
| Record attendance via scanner | ✅ | ✅ | ✅ | ✅ |
| Manually edit/correct attendance record | ✅ | ✅ | ❌ | ❌ |
| View audit logs | ✅ | ❌ | ✅ | ❌ |
| Delete / alter audit logs | ❌ *(nobody)* | ❌ | ❌ | ❌ |
| Export reports (CSV/JSON) | ✅ | ✅ | ❌ | ❌ |
| Change system settings | ✅ | ❌ | ❌ | ❌ |
| Provision users / change roles / revoke sessions | ✅ | ❌ | ❌ | ❌ |
| Edit own profile / password / avatar | ✅ | ✅ | ✅ | ✅ |

### 5.3 RBAC Implementation Rules
- **Deny by default**: an unmapped route/role combination is forbidden.
- **Centralize**: the permission matrix lives in `security.py` as a single data structure (e.g., `VIEW_ACCESS`). Do not scatter `if user.role == "ADMIN"` checks through routes.
- **Both layers**: protect every view with `check_view_access()` and every endpoint with `require_user()` plus an explicit role guard.
- **Object-level authorization (anti-IDOR)**: when a resource belongs to a user/department, verify ownership or privilege — not just role.
- **Self-protection**: an `ADMIN` cannot demote/deactivate/delete themselves, and the system must always retain at least one active `ADMIN`.
- **Localized 403**: forbidden access renders a friendly localized page for views and 403 JSON for APIs.
- **Navbar/sidebar filtering**: hide inaccessible links per role for UX, but never rely on this for security.

### 5.4 Seeded Demo Accounts (DEVELOPMENT ONLY)
- **Admin**: `admin` / `admin123`
- **HR Manager**: `hr` / `hr123`
- **Security Officer**: `security` / `security123`
- **Employee**: `staff` / `staff123`

> [!WARNING]
> Demo accounts and the "1-click test role credentials" on `login.html` MUST be disabled in production. Gate them behind `APP_ENV=development`.

---

## 6. Application Security Standards

### 6.1 Authentication & Passwords
- Hash passwords with Argon2id (preferred) or bcrypt (cost ≥ 12).
- Constant-time credential comparison; identical error message for unknown user vs. wrong password.
- Brute-force protection: rate-limit login (5 failed attempts per account/IP per 15 min); log every failure.
- Password policy: minimum 12 characters for admin/HR/security roles.

### 6.2 Session Management
- Session tokens: cryptographically random (signed via `SECRET_KEY`).
- Cookie flags: `HttpOnly`, `Secure` (in prod), `SameSite=Lax`, explicit expiry, `Path=/`.
- Rotate session ID on login and privilege change (prevents session fixation).
- Idle timeout (default 30 min) and absolute timeout (default 12 h).
- Logout invalidates the server session and clears cookie.

### 6.3 CSRF Protection
- All state-changing requests (`POST`, `PUT`, `DELETE`) require a CSRF token.
- `GET` requests MUST be side-effect free. Logout should be `POST`.

### 6.4 Input Validation & Injection Defense
- **SQL injection**: use SQLAlchemy ORM or bound parameters only. Never build SQL via f-strings.
- **XSS**: Jinja2 autoescape must stay `ON`. Never use `|safe` on user-controlled data. When embedding data into JavaScript, use `|tojson`.
- **Open redirect prevention**: when redirecting using Referer/next, only accept same-origin relative paths matching `^/(en|kh)/`.

### 6.5 File Upload Security (Avatars & Biometric Photos)

| Control | Requirement |
| :--- | :--- |
| **Size limit** | Max 5 MB per image; reject larger with 413 |
| **Type validation** | Verify magic bytes / decode with OpenCV or Pillow, not just extension |
| **Allowed formats** | `image/jpeg`, `image/png`, `image/webp` |
| **Filename** | Generate server-side: `uuid4().hex + ".jpg"`; discard client filename |
| **Re-encode** | Re-encode to JPEG/PNG to strip EXIF/GPS metadata |
| **Storage** | Outside web root or controlled through route |
| **Fallback UI** | Always include the avatar `onerror` fallback (§12.6) |

---

## 7. Biometric Data Governance & Privacy

Face embeddings are biometric personal data. Treat them accordingly:
1. **Consent**: Explicit consent recorded before enrollment.
2. **Purpose Limitation**: Embeddings used solely for identity/attendance verification.
3. **Data Minimization**: Store the 128-d embedding and optional reference photo. Scan frames are processed in-memory and discarded.
4. **Retention**: On employee termination, delete biometric template within configured window.
5. **Right to Erasure**: HR/Admin must be able to delete biometric template independently of HR record.
6. **Access Restriction**: Embeddings are never returned by any public API or template.

---

## 8. Biometrics & Computer Vision Pipeline

```text
[Camera Video Frame]
       │
       ▼
[OpenCV YuNet Detection]  ──► Extracts bounding box, score, & 5 facial landmarks
       │
       ▼
[Quality & Liveness Check] ──► Checks width (>40px), confidence (>0.70), lighting & blur
       │
       ▼
[OpenCV SFace Alignment]  ──► Rescales landmarks to original coords; warps/crops to 112x112 canonical view
       │
       ▼
[128-d Feature Vector]    ──► Extracts normalized floating-point embedding vector
       │
       ▼
[Cosine Matcher]          ──► Compares against stored vectors in Neon PostgreSQL / SQLite
       │
       ├── Cosine similarity ≥ 0.30 (Match Found) ──► Log Attendance Check-In / Check-Out
       └── Cosine similarity < 0.30 (Unknown)     ──► Raise Alert / Display Unidentified
```

### Models & Calibrated Parameters
- `face_detection_yunet_2023mar.onnx` (Detection)
- `face_recognition_sface_2021dec.onnx` (Recognition)
- **`DEFAULT_COSINE_THRESHOLD = 0.30`**: Calibrated for real-world webcam recall with zero false positives. (Clean benchmarks score ~0.363; ambient indoor lighting and slight head tilt typically score 0.32–0.36; non-registered individuals score < 0.20).
- `MIN_FACE_SIZE = 40` (pixels)
- `DUPLICATE_SCAN_COOLDOWN_SEC = 15`
- `SCAN_INTERVAL_MS = 450` (responsive real-time frame evaluation)

### Critical Frontend Rendering Rules (Canvas vs Video Mirroring)
- **Video Feed**: The `<video>` element has `transform scale-x-[-1]` so users see a natural mirror reflection of themselves.
- **Overlay Canvas**: The `<canvas id="face-canvas">` must **NEVER** have CSS `transform scale-x-[-1]`. Mirroring the canvas inverts all 2D text drawing (`nosreP nwonknU`).
- **Bounding Box Mapping**: When the video is mirrored, JavaScript computes the mirrored X coordinate:
  ```javascript
  const isVideoMirrored = this.video.classList.contains('scale-x-[-1]');
  const x = isVideoMirrored ? (this.overlayCanvas.width - (box.x + box.width)) : box.x;
  ```
  This places the box exactly on the face while drawing upright, left-to-right text tags and labels.
- **5-Point Landmark Visualizer**: Eyes, nose tip, and mouth corners are mapped and rendered on canvas as glowing cyan dots so users can visibly see the AI tracking facial features in real time.
- **Holographic Radar Loading Animation**: When searching for faces, a central animated HUD radar sweeps with rotating outer compass rings (`radar-spin-slow`), counter-rotating inner cyan brackets (`radar-spin-reverse`), concentric radar ping waves, and an animated `AI NEURAL SCANNING...` badge. It auto-fades smoothly upon face detection.
- **Chromium Lifecycle Management**: Video event listeners check `readyState >= 2`, `loadeddata`, and `canplay` to avoid race conditions where `onloadedmetadata` fired prior to listener attachment.

---

## 9. Database Design (PostgreSQL-first, SQLite-compatible)

FaceTrack AI is architected with **Neon Serverless PostgreSQL** as the primary production engine, while preserving 100% offline fallback compatibility with **SQLite** (`data/facetrack.db`).

### Schema Principles
- Use portable SQLAlchemy types (`Integer`, `String`, `Float`, `Boolean`, `DateTime`, `Text`, `JSON`).
- Plural snake_case table names (`employees`, `departments`, `attendance_records`, `face_embeddings`, `audit_logs`, `system_settings`, `users`).
- Every table has a surrogate primary key (`id = Column(Integer, primary_key=True)`) and UTC timestamps (`created_at = Column(DateTime, default=datetime.utcnow)`).
- Relationships use foreign keys with appropriate `ON DELETE` behavior (`CASCADE` for face embeddings; `RESTRICT` for departments with assigned employees).
- Neon PostgreSQL connection string: configure with connection pooler and SSL:
  ```text
  postgresql://neondb_owner:npg_...-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
  ```
- Connection pool engine settings:
  ```python
  engine = create_engine(
      DATABASE_URL,
      pool_pre_ping=True,
      pool_recycle=300,
  )
  ```

---

## 10. HTTP & REST API Conventions

### 10.1 Routing
- **Pages**: `GET /{lang}/<resource>` (kebab-case, e.g., `/audit-logs`, `/departments`).
- **Mutations**: `POST /api/<resource>` and `POST /api/<resource>/{id}/<action>` (e.g., `/api/employees/12/deactivate`).
- Always validate `{lang}` against `{"en", "kh"}`; unknown languages default to `/en`.

### 10.2 Response Standards

| Case | HTML Form Submission | JSON / Fetch API |
| :--- | :--- | :--- |
| **Success** | `303 See Other` redirect to `/{lang}/<page>?message=<key>` | `200` or `201` `{ "ok": true, "data": ... }` |
| **Validation Error** | Re-render form or redirect with `?error=<key>` | `422` `{ "ok": false, "error": { "code": "validation_error", "fields": { ... } } }` |
| **Unauthenticated** | `302` redirect to `/{lang}/login?next=...` | `401` `{ "ok": false, "detail": "Authentication required" }` |
| **Forbidden** | Localized `403_forbidden.html` view | `403` `{ "ok": false, "detail": "Access denied" }` |
| **Not Found** | Localized 404 page | `404` `{ "ok": false, "detail": "Resource not found" }` |
| **Conflict (duplicate)** | Re-render form with `?error=already_exists` | `409` `{ "ok": false, "detail": "Conflict" }` |

---

## 11. Localization & Khmer Typography Engine

### Language Handling
- All routes are prefixed with the language parameter:
  - English: `/en/...`
  - Khmer: `/kh/...`
- Redirects dynamically infer the language from the `Referer` header so form submissions preserve the active language.

### Khmer Typography Rules
- Fonts: **Kantumruy Pro**, **Battambang**, and **Noto Sans Khmer**.
- **Critical Rule**: Never apply `uppercase`, `tracking-wider`, or `tracking-widest` to Khmer script. It breaks diacritics and ligatures.
- Khmer table headers use `0.8125rem` (13px) with `font-weight: 700` and high-contrast color (`#475569` light mode, `#94a3b8` dark mode).

---

## 12. UI/UX Design System

### 12.1 Design Principles
- **Clarity over decoration**: High-density operational interface with crisp visual hierarchy.
- **High contrast & accessible**: WCAG 2.1 AA conformance in both dark and light modes.
- **Theme tokens**:
  - Dark mode: `--bg-app: #181818; --bg-surface: #222225; --border: #333338; text: #f1f5f9;`
  - Light mode: `--bg-app: #f8fafc; --bg-surface: #ffffff; --border: #e2e8f0; text: #0f172a;`
- **Instant Theme Script**: Early `<script>` tag in `<head>` evaluates `localStorage.getItem('theme')` before layout rendering to completely eliminate theme flashing.

### 12.2 Mandatory Avatar Fallback Pattern
Always include `onerror` fallback on avatar images to prevent broken image icons:
```html
<img src="{{ avatar_url }}" alt="{{ name }}" class="h-9 w-9 rounded-full object-cover" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
<span class="h-9 w-9 rounded-full items-center justify-center bg-slate-600 text-white text-sm" style="display:none;">
  {{ initials }}
</span>
```

---

## 13. Error Handling, Logging & Observability

### 13.1 Error Handling
- Register global exception handlers for `HTTPException`, `RequestValidationError`, and unhandled `Exception`.
- Render localized error pages for HTML and structured JSON for `/api/*`.
- Catch specific exceptions (`IntegrityError` $ightarrow$ 409, `OperationalError` $ightarrow$ 503 with retry hint); never use bare `except:`.
- Missing ML models: scanner displays an actionable banner with `download_models.py` instruction; app still boots gracefully.

### 13.2 Logging & Audit Trail
- Structured log format: timestamp, level, request_id, operator, route, status, duration_ms.
- Every state change writes an immutable `AuditLog` row inside the same database transaction.

---

## 14. Performance & Scalability Standards

| Area | Target / Rule |
| :--- | :--- |
| **Page TTFB (list page)** | < 300 ms server response time |
| **Scan API (detect + embed + match)** | < 250 ms on standard CPU for 640px frames |
| **DB queries per page** | Avoid N+1; use `joinedload`/`selectinload`; aim $\le$ 10 queries per request |
| **Dashboard aggregates** | Use SQL `COUNT` / `GROUP BY` — never load full tables into Python memory to count |
| **ONNX Models** | Singleton instance loaded once at startup |
| **Inference Concurrency** | OpenCV inference executed under threading lock to protect native C++ runtime buffers |

---

## 15. Testing Strategy & Quality Gates

### 15.1 Test Suites

| Suite | File | Focus |
| :--- | :--- | :--- |
| **RBAC Matrix** | `tests/test_rbac_matrix.py` | Validates access for all 4 roles across all 9 pages; unauthenticated redirects |
| **Session & Logout** | `tests/test_roles_navbar_logout.py` | Verifies avatar persistence, session lifecycle, CSRF logout, and nav filtering |

### 15.2 Quality Gate Rule
Before any PR or commit, all test suites must pass 100%:
```powershell
.\.venv\Scripts\python tests/test_rbac_matrix.py
.\.venv\Scripts\python tests/test_roles_navbar_logout.py
```

---

## 16. Developer Commands & Environment

### Virtual Environment Activation
```powershell
# Windows PowerShell
.\.venv\Scriptsctivate
```

### Run Web Server
```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000/kh/dashboard](http://127.0.0.1:8000/kh/dashboard).

### Run Test Suites
```powershell
.\.venv\Scripts\python -u tests/test_rbac_matrix.py
.\.venv\Scripts\python -u tests/test_roles_navbar_logout.py
```

### Git Repository Management
```powershell
# Remote URL
git remote -v
# origin  https://github.com/NgetMeas22/FaceTrack-AI.git

# Push changes
git push -u origin main
```

---

## 17. Configuration & Secrets Management

### Environment Variables (`.env`)

| Variable | Required | Example / Default | Purpose |
| :--- | :---: | :--- | :--- |
| `APP_ENV` | ✅ | `development` or `production` | Gates demo accounts, debug, cookie Secure flag |
| `SECRET_KEY` | ✅ | `64+ random hex characters` | Cryptographically signs session cookies & CSRF |
| `DATABASE_URL` | ❌ | `postgresql://user:pass@host/db?sslmode=require` | Neon cloud connection (omit for SQLite fallback) |
| `ALLOWED_HOSTS` | prod | `127.0.0.1,localhost,facetrack.ai` | Trusted host middleware security |
| `SESSION_IDLE_MINUTES` | ❌ | `30` | Idle timeout |
| `SESSION_ABSOLUTE_HOURS` | ❌ | `12` | Absolute session timeout |
| `MAX_UPLOAD_MB` | ❌ | `5` | File upload cap |
| `DEFAULT_LANG` | ❌ | `kh` | Fallback language |
| `BUSINESS_TIMEZONE` | ❌ | `Asia/Phnom_Penh` | Attendance day boundary (UTC+07:00) |

> [!IMPORTANT]
> `.env` must remain in `.gitignore`. Never commit credentials, connection strings, or production secrets to Git.

---

## 18. Deployment & Operations

### 18.1 Production Runtime
- **Linux / Hostinger VPS**:
  ```bash
  gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8000 --timeout 60
  ```
- **Windows Host**: Run `uvicorn` as a background Windows service via NSSM or Task Scheduler.
- **Reverse Proxy**: Place behind Nginx, Caddy, or Cloudflare for TLS/HTTPS termination.
  *Camera access strictly requires HTTPS — plain HTTP outside localhost will disable camera permissions in browsers.*

---

## 19. Git Workflow & Change Management

- `main` branch is always deployable and stable.
- Remote repository: `https://github.com/NgetMeas22/FaceTrack-AI.git`.
- Semantic commit prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Never commit with `--no-verify` or bypass tests.

---

## 20. Agent Operating Protocol (Mandatory)

This section governs how AI coding assistants and LLM agents must operate within this codebase:
1. **Read Before Writing**: Inspect existing patterns, translations dictionary, and models before altering files.
2. **Smallest Correct Change**: Do not rewrite unrelated modules or reformat whole files unnecessarily.
3. **Preserve Documentation & Comments**: Never strip existing architectural docstrings or doc comments.
4. **Bilingual Parity**: Any new UI string must be added to both `en` and `kh` dictionaries in `app/translations.py`.
5. **Enforce Server-Side Security**: Never rely on frontend CSS hiding for authorization.
6. **Verify Before Completion**: Run relevant test scripts and ensure zero regressions.

---

## 21. Feature Implementation Playbooks

### 21.1 Adding a New View Page
1. Define route `GET /{lang}/<page>` in `app/main.py` with `require_user()` and `check_view_access()`.
2. Add page permission mapping in `app/security.py` (`PAGE_REQUIRED_ROLES`).
3. Create `app/templates/<page>.html` extending `base.html`.
4. Add bilingual keys to `app/translations.py` for both `en` and `kh`.
5. Add test coverage in `tests/test_rbac_matrix.py`.

### 21.2 Adding a New Mutation API
1. Define endpoint `POST /api/<resource>` in `app/main.py`.
2. Validate caller via `require_user(allowed_roles=[...])`.
3. Validate inputs with Pydantic or strict Form types.
4. Execute DB changes within a single transaction; write an `AuditLog` row.
5. Return JSON response `{ "ok": true, "data": ... }`.

---

## 22. Anti-Patterns (Forbidden)

| ❌ Forbidden Anti-Pattern | ✅ Approved Engineering Standard |
| :--- | :--- |
| `f"SELECT ... WHERE id = {id}"` | SQLAlchemy ORM queries with parameterized bindings |
| `{{ user_input \| safe }}` | Jinja2 autoescape; use `\|tojson` when embedding in JS |
| `if user.role == "ADMIN"` scattered in HTML | Central `can_access_page()` RBAC helpers |
| Trusting hidden form fields (`user_id`, `role`) | Derive and verify actor on the server from session cookie |
| Storing raw/MD5/SHA-1 passwords | Argon2id or bcrypt (cost $\ge$ 12) |
| Returning face embeddings in API responses | Embeddings are strictly private; never serialize |
| Loading ONNX models on every request | Singleton pattern loaded once during startup |
| `scale-x-[-1]` on `<canvas id="face-canvas">` | Mirror `<video>` only; calculate mirrored box X in JS |
| Upper-case transformations on Khmer text | Follow Khmer typography rules (§11) |

---

## 23. Definition of Done Checklist

Before submitting changes, verify:
- [ ] Meets functional requirements and handles edge cases.
- [ ] Operates cleanly on both Neon Serverless PostgreSQL and local SQLite.
- [ ] Server-side authentication & RBAC verified; test suites passing 100%.
- [ ] Dark and light themes tested for high-contrast visibility.
- [ ] Bilingual parity preserved across English (`/en`) and Khmer (`/kh`).
- [ ] Avatar `onerror` fallbacks included on all user/employee images.
- [ ] No secrets committed; `.env` remains in `.gitignore`.

---

## 24. Known Gaps & Hardening Roadmap

| Priority | Item | Rationale |
| :---: | :--- | :--- |
| 🔴 **High** | Disable demo accounts in production | Default credentials must be gated behind `APP_ENV=development` |
| 🔴 **High** | CSRF token verification on all POSTs | Comprehensive cross-site request forgery defense |
| 🔴 **High** | Rate-limiting on `/api/auth/login` | Brute-force protection (e.g. max 5 attempts / 15 min) |
| 🟠 **Medium** | Alembic database migrations | Structured schema evolution replacing `create_all()` |
| 🟠 **Medium** | Security headers & strict CSP middleware | Browser-level clickjacking and script injection defense |
| 🟢 **Low** | Active 3D RGB-D liveness challenge | Hardware-level anti-spoofing challenge response |

---

## 25. Glossary

| Term | Meaning |
| :--- | :--- |
| **SSR** | Server-Side Rendering — HTML dynamically compiled on server by Jinja2 |
| **RBAC** | Role-Based Access Control — Access governance enforced by user role matrix |
| **IDOR** | Insecure Direct Object Reference — Unauthorized access via manipulated IDs |
| **CSRF** | Cross-Site Request Forgery |
| **CSP / SRI** | Content Security Policy / Subresource Integrity |
| **YuNet** | High-speed lightweight deep learning face detection model (ONNX) |
| **SFace** | Deep learning face recognition model extracting 128-d canonical embeddings (ONNX) |
| **Embedding** | 128-dimensional floating-point biometric feature vector representing a face |
| **Cosine Similarity**| Normalized dot product measuring face vector alignment (threshold = 0.30) |
| **Neon** | Serverless PostgreSQL cloud database with connection pooling and branching |
| **Audit Trail** | Immutable append-only log of organizational and security events |
