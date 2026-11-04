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
├── AGENT_GUIDE.md                    # This document
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
│   │   ├── dashboard.html            # 2:1 Analytics grid (Spline wave chart, Donut gauge, Scanner, Dossier)
│   │   ├── employees.html            # Personnel management, Add/Edit modals, Biometric registration
│   │   ├── departments.html          # Organizational departments directory & CRUD modals
│   │   ├── scanner.html              # Dedicated full-screen interactive face recognition scanner
│   │   ├── attendance.html           # Live attendance logs, shift status filter, confidence tracking
│   │   ├── audit_logs.html           # Immutable system event logs, security audit trail
│   │   ├── reports.html              # Workforce analytics, department percentages, CSV/JSON exports
│   │   ├── settings.html             # 5-tab system settings (Security, Profile, Notifications, System, Privacy)
│   │   ├── security.html             # User operators table, clearance provisioning, cryptographic sessions
│   │   └── login.html                # Zero-trust login view with 1-click test role credentials (DEV ONLY)
│   │
│   └── static/
│       ├── css/
│       │   └── styles.css            # Master styles, Khmer typography engine, animations, cards
│       └── js/
│           ├── main.js               # Global UI utilities, alerts, audio chimes, modal helpers
│           └── scanner.js            # Video stream processing, bounding boxes, biometrics API bridge
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
[Quality & Liveness Check] ──► Checks width (>60px), confidence (>0.70), lighting
       │
       ▼
[OpenCV SFace Alignment]  ──► Warps and crops face to normalized 112x112 canonical view
       │
       ▼
[128-d Feature Vector]    ──► Extracts floating-point embedding vector
       │
       ▼
[Cosine Matcher]          ──► Compares against stored vectors in Database
       │
       ├── Cosine similarity ≥ 0.32 (Match Found) ──► Log Attendance Check-In / Check-Out
       └── Cosine similarity < 0.32 (Unknown)     ──► Raise Alert / Display Unidentified
```

### Models & Calibrated Parameters
- `face_detection_yunet_2023mar.onnx` (Detection)
- `face_recognition_sface_2021dec.onnx` (Recognition)
- `COSINE_MATCH_THRESHOLD = 0.32` (Calibrated for real-world webcam recall with zero false positives)
- `MIN_FACE_WIDTH_PX = 60`
- `DUPLICATE_SCAN_COOLDOWN_SEC = 45`

---

## 9. Database Design (PostgreSQL-first, SQLite-compatible)

- Use portable SQLAlchemy types.
- Plural snake_case table names (`employees`, `departments`, `attendance_records`, `face_embeddings`, `audit_logs`).
- Every table has surrogate primary key and UTC timestamps.
- Neon PostgreSQL connection: `pool_pre_ping=True`, `pool_recycle=300`, `connect_args={"sslmode": "require"}`.

---

## 10. Localization & Khmer Typography Engine

### Language Handling
- Routes prefixed with `/{lang}/...` (`/en` and `/kh`).
- Redirects dynamically infer active language from `Referer` header.

### Khmer Typography Rules
- Fonts: **Kantumruy Pro**, **Battambang**, and **Noto Sans Khmer**.
- **Critical Rule**: Never apply `uppercase`, `tracking-wider`, or `tracking-widest` to Khmer script.
- Khmer table headers use `0.8125rem` (13px) with `font-weight: 700` and high-contrast color (`#475569` light mode, `#94a3b8` dark mode).

---

## 11. UI/UX Design System & Avatar Fallbacks

### Theme Tokens
- Dark mode: `--bg-app: #181818; --bg-surface: #222225; --border: #333338;`
- Light mode: `--bg-app: #f8fafc; --bg-surface: #ffffff; --border: #e2e8f0;`

### Mandatory Avatar Fallback Pattern
Always include `onerror` fallback on avatar images to prevent broken image icons:
```html
<img src="{{ avatar_url }}" alt="{{ name }}" class="h-9 w-9 rounded-full object-cover" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
<span class="h-9 w-9 rounded-full items-center justify-center bg-slate-600 text-white text-sm" style="display:none;">
  {{ initials }}
</span>
```

---

## 12. Developer Commands & Operational Guide

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\activate

# 2. Run web server
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 3. Run test suites
.\.venv\Scripts\python tests/test_rbac_matrix.py
.\.venv\Scripts\python tests/test_roles_navbar_logout.py
```

---

## 13. Definition of Done Checklist

Before submitting changes, ensure:
- [ ] Meets functional requirements and handles edge cases.
- [ ] Works cleanly on both SQLite and Neon PostgreSQL.
- [ ] Auth & RBAC enforced server-side; test suites green.
- [ ] Dark and light themes verified for high contrast.
- [ ] `/en` and `/kh` bilingual parity preserved.
- [ ] Avatar `onerror` fallbacks included.
- [ ] No secrets committed; `.env` remains in `.gitignore`.
