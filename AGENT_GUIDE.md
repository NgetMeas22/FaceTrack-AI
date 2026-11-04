# FaceTrack AI — Technical Architecture & Agent Guide

> **Target Audience**: AI Coding Assistants, LLM Agents, and Full-Stack Python Engineers.  
> **Repository Purpose**: Enterprise AI-powered biometric workforce intelligence, real-time facial recognition attendance, personnel directories, and role-governed organizational access.

---

## 1. Architectural Philosophy

FaceTrack AI is engineered as a **100% Pure Python Monolith**. It avoids the operational complexity of Node.js/npm pipelines, webpack, or external front-end build tools while delivering a modern, high-contrast, responsive enterprise application.

```
                    ┌──────────────────────────────────────────┐
                    │      Client Browser (Desktop/Mobile)     │
                    │   Tailwind CDN + Chart.js + Lucide CDN   │
                    └────────────────────┬─────────────────────┘
                                         │ HTTP / REST / Multipart
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │           FastAPI Web Server             │
                    │      Jinja2 Server-Side Rendering        │
                    │   Session Authentication & RBAC Guard    │
                    └────────────┬──────────────────┬──────────┘
                                 │                  │
                SQLAlchemy ORM   │                  │ OpenCV Inference
                                 ▼                  ▼
                    ┌─────────────────────┐  ┌─────────────────┐
                    │   Database Engine   │  │ Biometrics Core │
                    │  Neon PostgreSQL /  │  │  OpenCV YuNet   │
                    │   SQLite Fallback   │  │   OpenCV SFace  │
                    └─────────────────────┘  └─────────────────┘
```

### Core Design Tenets
1. **Zero Node.js/npm**: Tailwind CSS, Chart.js, and Lucide icons are served via trusted CDNs.
2. **Server-Side Rendered (SSR) with Jinja2**: Fast initial load, SEO-friendly, zero client hydration lag, and clean session security.
3. **Bilingual First-Class Citizen**: Complete localized routing via `/{lang}/...` with `/en` (English) and `/kh` (Khmer) coverage.
4. **Adaptive Aesthetic Themes**: High-contrast dark mode (`#181818` / `#222225`) and crisp light mode (`#f8fafc` / `#ffffff`) with instant early script evaluation to eliminate theme flickering.
5. **Dual Database Portability**: Runs out-of-the-box on local SQLite (`data/facetrack.db`) and automatically connects to **Neon Serverless PostgreSQL** when configured in `.env`.

---

## 2. Directory & File Structure

```text
├── .env                              # Private environment secrets (Neon DB URL, SECRET_KEY) - GITIGNORED
├── .env.example                      # Documented environment template
├── requirements.txt                  # Python dependencies
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
│   │   └── login.html                # Zero-trust login view with 1-click test role credentials
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

---

## 4. Role-Based Access Control (RBAC) Matrix

FaceTrack AI enforces strict Zero-Trust role governance on both **view routes** (`GET /{lang}/...`) and **REST API mutations** (`POST /api/...`).

| Page / Route | Path | ADMIN | HR_MANAGER | SECURITY_OFFICER | EMPLOYEE (Staff) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Dashboard** | `/{lang}/dashboard` | ✅ | ✅ | ✅ | ✅ |
| **Live Scanner** | `/{lang}/scanner` | ✅ | ✅ | ✅ | ✅ |
| **Attendance Logs** | `/{lang}/attendance`| ✅ | ✅ | ✅ | ✅ |
| **Employee Directory** | `/{lang}/employees` | ✅ | ✅ | ❌ | ❌ |
| **Departments** | `/{lang}/departments`| ✅ | ✅ | ❌ | ❌ |
| **Audit Logs** | `/{lang}/audit-logs` | ✅ | ❌ | ✅ | ❌ |
| **Reports & Analytics** | `/{lang}/reports` | ✅ | ✅ | ❌ | ❌ |
| **System Settings** | `/{lang}/settings` | ✅ | ❌ | ❌ | ❌ |
| **Security & Roles** | `/{lang}/security` | ✅ | ❌ | ❌ | ❌ |

### Seeded Demo Accounts
- **Admin**: `username: admin` | `password: admin123`
- **HR Manager**: `username: hr` | `password: hr123`
- **Security Officer**: `username: security` | `password: security123`
- **Employee**: `username: staff` | `password: staff123`

---

## 5. Biometrics & Computer Vision Pipeline

Face recognition uses a 2-stage lightweight deep learning pipeline that runs in real-time on standard CPUs:

```
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
[Cosine Distance Matcher] ──► Compares against stored vectors in Database
       │
       ├── Cosine Distance < 0.363 (Match Found) ──► Log Attendance Check-In / Check-Out
       └── Cosine Distance >= 0.363 (Unknown)    ──► Raise Alert / Display Unidentified
```

- **Models**:
  - `face_detection_yunet_2023mar.onnx` (Fast, lightweight face detector)
  - `face_recognition_sface_2021dec.onnx` (Compact, high-accuracy 128-d recognition model)
- **Automatic Model Download**:
  ```powershell
  .\.venv\Scripts\python download_models.py
  ```

---

## 6. Khmer Typography & Localization Engine

### Language Handling
All routes are prefixed with the language parameter:
- English: `/en/...`
- Khmer: `/kh/...`

Redirects dynamically infer the language from the `Referer` header so form submissions (such as adding an employee) preserve the active language.

### Khmer Typography Rules
In [`app/static/css/styles.css`](file:///d:/Code%20All/Python_All/FaceTrack%20AI%20%E2%80%94%20Face%20Recognition%20&%20People%20Management%20System/app/static/css/styles.css):
- `html[lang="kh"]` loads the **Kantumruy Pro**, **Battambang**, and **Noto Sans Khmer** font stack.
- **Critical Rule**: Never apply `uppercase`, `tracking-wider`, or `tracking-widest` to Khmer script. In Khmer, vowels and subscript consonants (ជ, ្ជ, ្គ) must remain contiguous; artificial letter-spacing destroys the ligatures.
- Khmer table headers use `0.8125rem` (13px) with `font-weight: 700` and high-contrast color (`#475569` light mode, `#94a3b8` dark mode).

---

## 7. Developer & Agent Commands

### Virtual Environment Activation
Always use the virtual environment located in `.venv`:
```powershell
# Windows PowerShell
.\.venv\Scripts\activate
```

### Running the Web Server
Avoid typing bare `python` if your system has other Python installations (e.g. MSYS2). Run directly via the virtual environment:
```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*(or)*
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```

### Running Test Suites
Always run test suites to ensure zero regressions before committing code:
```powershell
# 1. Test RBAC permissions across all roles
.\.venv\Scripts\python tests/test_rbac_matrix.py

# 2. Test avatar persistence, sessions, and logout
.\.venv\Scripts\python tests/test_roles_navbar_logout.py
```

### Database Management
- **Switching to Neon PostgreSQL**: Provide `DATABASE_URL` in `.env`.
- **Switching to SQLite**: Leave `DATABASE_URL` unset or set to `sqlite:///data/facetrack.db`.
- **Database Initialization**: The tables are automatically created and seeded on application startup via `init_db()`.

---

## 8. Guidelines for AI Assistants Modifying This Codebase

When assisting on this project:
1. **Preserve Documentation & Comments**: Never strip existing architectural docstrings, comments, or translation keys.
2. **Never Introduce Node/NPM dependencies**: Keep everything in pure Python with CDN scripts for UI assets.
3. **Maintain Dual-Language Integrity**: Whenever you add a new UI element or string, add its matching translations to both `en` and `kh` dictionaries in [`app/translations.py`](file:///d:/Code%20All/Python_All/FaceTrack%20AI%20%E2%80%94%20Face%20Recognition%20&%20People%20Management%20System/app/translations.py).
4. **Enforce RBAC**: When adding a new view or endpoint, protect it with `check_view_access()` and `require_user()`.
5. **Handle Avatar Image Fallbacks**: Always add `onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"` to avatar images to prevent broken image icons when photos are missing.
6. **Protect Secrets**: Never commit `.env` or production credentials to Git. Always keep `.env` in `.gitignore`.
