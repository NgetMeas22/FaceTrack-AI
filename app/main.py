"""FastAPI Monolith Application Entry Point & Bilingual Routes for FaceTrack AI."""

import csv
import io
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db, init_db
from app.face_recognition import FaceBox, FaceEngine, get_face_engine
from app.models import AttendanceRecord, AuditLog, Department, Employee, FaceEmbedding, ScanLog, SystemSetting, User
from app.security import (
    ROLE_ADMIN,
    ROLE_EMPLOYEE,
    ROLE_HR,
    ROLE_SECURITY,
    SESSION_COOKIE_NAME,
    can_access_page,
    create_session_token,
    hash_password,
    verify_password,
    verify_session_token,
)
from app.translations import TRANSLATIONS

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# FastAPI App setup
app = FastAPI(
    title="FaceTrack AI — Enterprise Biometrics",
    description="Modern minimalist pure Python face recognition & workforce intelligence system.",
    version="2.1.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & Templates
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def format_datetime(value: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if not value:
        return "-"
    return value.strftime(fmt)


def format_time(value: Optional[datetime], fmt: str = "%I:%M %p") -> str:
    if not value:
        return "-"
    return value.strftime(fmt)


templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_time"] = format_time


def resolve_lang(lang: str) -> str:
    return "kh" if lang == "kh" else "en"


def get_current_user(request: Request, db: Session) -> Optional[User]:
    """Retrieve authenticated user from signed HMAC session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    payload = verify_session_token(token)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("uid"), User.is_active == True).first()


PAGE_REQUIRED_ROLES = {
    "settings": ["ADMIN"],
    "security": ["ADMIN"],
    "audit_logs": ["ADMIN", "SECURITY_OFFICER"],
    "departments": ["ADMIN", "HR_MANAGER"],
    "employees": ["ADMIN", "HR_MANAGER"],
    "reports": ["ADMIN", "HR_MANAGER"],
    "attendance": ["ADMIN", "HR_MANAGER", "SECURITY_OFFICER"],
    "scanner": ["ADMIN", "HR_MANAGER", "SECURITY_OFFICER", "EMPLOYEE"],
    "dashboard": ["ADMIN", "HR_MANAGER", "SECURITY_OFFICER", "EMPLOYEE"],
}


@app.on_event("startup")
def on_startup():
    init_db()
    get_face_engine()


# ============================================================================
# ROOT & CONVENIENCE REDIRECTS
# ============================================================================

@app.get("/", response_class=RedirectResponse)
def root_redirect():
    return RedirectResponse(url="/en/dashboard", status_code=302)

@app.get("/login", response_class=RedirectResponse)
def login_redirect():
    return RedirectResponse(url="/en/login", status_code=302)

@app.get("/logout", response_class=RedirectResponse)
def logout_redirect():
    return RedirectResponse(url="/en/logout", status_code=302)

@app.get("/security", response_class=RedirectResponse)
def sec_redirect():
    return RedirectResponse(url="/en/security", status_code=302)

@app.get("/dashboard", response_class=RedirectResponse)
def dash_redirect():
    return RedirectResponse(url="/en/dashboard", status_code=302)

@app.get("/employees", response_class=RedirectResponse)
def emp_redirect():
    return RedirectResponse(url="/en/employees", status_code=302)

@app.get("/departments", response_class=RedirectResponse)
def dept_redirect():
    return RedirectResponse(url="/en/departments", status_code=302)

@app.get("/scanner", response_class=RedirectResponse)
def scan_redirect():
    return RedirectResponse(url="/en/scanner", status_code=302)

@app.get("/attendance", response_class=RedirectResponse)
def att_redirect():
    return RedirectResponse(url="/en/attendance", status_code=302)

@app.get("/audit-logs", response_class=RedirectResponse)
def audit_redirect():
    return RedirectResponse(url="/en/audit-logs", status_code=302)

@app.get("/reports", response_class=RedirectResponse)
def rep_redirect():
    return RedirectResponse(url="/en/reports", status_code=302)

@app.get("/settings", response_class=RedirectResponse)
def set_redirect():
    return RedirectResponse(url="/en/settings", status_code=302)


def check_view_access(request: Request, db: Session, lang: str, page_name: str):
    """Check authentication and RBAC permissions for web views."""
    current_user = get_current_user(request, db)
    t = TRANSLATIONS[lang]
    if not current_user:
        return RedirectResponse(url=f"/{lang}/login?next={request.url.path}", status_code=302), None

    if not can_access_page(current_user.role, page_name):
        forbidden_resp = templates.TemplateResponse(
            request=request,
            name="403_forbidden.html",
            context={
                "lang": lang,
                "t": t,
                "current_user": current_user,
                "current_page": page_name,
                "required_roles": PAGE_REQUIRED_ROLES.get(page_name, ["ADMIN"]),
            },
            status_code=403,
        )
        return forbidden_resp, current_user

    return None, current_user


# ============================================================================
# AUTHENTICATION & LOGIN / LOGOUT ROUTES
# ============================================================================

@app.get("/{lang}/login", response_class=HTMLResponse)
def login_view(
    lang: str,
    request: Request,
    next: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    message: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    current_user = get_current_user(request, db)
    if current_user:
        return RedirectResponse(url=f"/{lang}/dashboard", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "lang": lang,
            "t": t,
            "next_url": next or "",
            "error": error,
            "message": message,
        },
    )


@app.get("/{lang}/logout", response_class=RedirectResponse)
def logout_view(lang: str, request: Request, db: Session = Depends(get_db)):
    lang = resolve_lang(lang)
    current_user = get_current_user(request, db)
    if current_user:
        audit = AuditLog(
            operator=current_user.username,
            action_type="LOGOUT",
            status="SUCCESS",
            details=f"User {current_user.username} signed out.",
            ip_address=request.client.host if request.client else "127.0.0.1",
        )
        db.add(audit)
        db.commit()

    resp = RedirectResponse(url=f"/{lang}/login?message=Signed out successfully", status_code=302)
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp


@app.post("/api/auth/login")
def login_api(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    lang: str = Form("en"),
    next: Optional[str] = Form(None),
    remember_me: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    usr_clean = username.strip()

    user = db.query(User).filter(
        (User.username.ilike(usr_clean)) | (User.email.ilike(usr_clean))
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        audit = AuditLog(
            operator=usr_clean or "Anonymous",
            action_type="LOGIN_FAILED",
            status="FAILED",
            details=f"Authentication rejected for identifier: {usr_clean}",
            ip_address=request.client.host if request.client else "127.0.0.1",
        )
        db.add(audit)
        db.commit()
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "lang": lang,
                "t": t,
                "error": "Invalid username or password.",
                "username_prefill": usr_clean,
                "next_url": next or "",
            },
            status_code=400,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "lang": lang,
                "t": t,
                "error": "Account is suspended. Contact system administrator.",
                "username_prefill": usr_clean,
                "next_url": next or "",
            },
            status_code=403,
        )

    user.last_login = datetime.now(timezone.utc)
    audit = AuditLog(
        operator=user.username,
        action_type="LOGIN_SUCCESS",
        status="SUCCESS",
        details=f"User {user.username} authenticated as {user.role}",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    token = create_session_token(user.id, user.username, user.role)
    target = next if (next and next.startswith(f"/{lang}/")) else f"/{lang}/dashboard"
    resp = RedirectResponse(url=target, status_code=303)
    max_age = 86400 * 30 if remember_me else 86400
    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
    )
    return resp


# ============================================================================
# LOCALIZED BILINGUAL WEB VIEW ROUTES (/{lang}/...)
# ============================================================================

@app.get("/{lang}/dashboard", response_class=HTMLResponse)
def dashboard_view(lang: str, request: Request, db: Session = Depends(get_db)):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "dashboard")
    if guard_resp:
        return guard_resp

    today = date.today()
    total_employees = db.query(Employee).filter(Employee.status == "ACTIVE").count()
    present_today = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.attendance_date == today, AttendanceRecord.status.in_(["PRESENT", "LATE"]))
        .distinct(AttendanceRecord.employee_id)
        .count()
    )
    late_today = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.attendance_date == today, AttendanceRecord.status == "LATE")
        .count()
    )
    employees_with_faces = (
        db.query(Employee.id)
        .join(FaceEmbedding, FaceEmbedding.employee_id == Employee.id)
        .distinct()
        .count()
    )
    pending_faces = max(0, total_employees - employees_with_faces)
    attendance_rate = round((present_today / total_employees * 100), 1) if total_employees > 0 else 0.0

    recent_scans = (
        db.query(ScanLog)
        .options(joinedload(ScanLog.matched_employee))
        .order_by(desc(ScanLog.timestamp))
        .limit(6)
        .all()
    )

    departments = db.query(Department).all()
    dept_stats = []
    for dept in departments:
        emp_count = db.query(Employee).filter(Employee.department_id == dept.id).count()
        dept_stats.append({
            "name": dept.name,
            "code": dept.code,
            "count": emp_count,
            "head_name": dept.head_name,
        })

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "dashboard",
            "stats": {
                "total_employees": total_employees,
                "present_today": present_today,
                "late_today": late_today,
                "pending_faces": pending_faces,
                "attendance_rate": attendance_rate,
            },
            "recent_scans": recent_scans,
            "dept_stats": dept_stats,
        },
    )


@app.get("/{lang}/employees", response_class=HTMLResponse)
def employees_view(
    lang: str,
    request: Request,
    search: Optional[str] = Query(None),
    dept_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "employees")
    if guard_resp:
        return guard_resp

    query = db.query(Employee).options(joinedload(Employee.department), joinedload(Employee.embeddings))

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            (Employee.first_name.ilike(search_filter))
            | (Employee.last_name.ilike(search_filter))
            | (Employee.employee_code.ilike(search_filter))
            | (Employee.email.ilike(search_filter))
            | (Employee.position.ilike(search_filter))
        )

    if dept_id:
        query = query.filter(Employee.department_id == dept_id)

    if status:
        query = query.filter(Employee.status == status)

    employees = query.order_by(Employee.employee_code).all()
    departments = db.query(Department).order_by(Department.name).all()

    return templates.TemplateResponse(
        request=request,
        name="employees.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "employees",
            "employees": employees,
            "departments": departments,
            "search": search or "",
            "selected_dept": dept_id,
            "selected_status": status or "",
        },
    )


@app.get("/{lang}/departments", response_class=HTMLResponse)
def departments_view(lang: str, request: Request, db: Session = Depends(get_db)):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "departments")
    if guard_resp:
        return guard_resp

    departments = db.query(Department).all()
    dept_list = []
    for d in departments:
        emp_count = db.query(Employee).filter(Employee.department_id == d.id).count()
        dept_list.append({
            "id": d.id,
            "code": d.code,
            "name": d.name,
            "description": d.description,
            "head_name": d.head_name or "Unit Leadership",
            "location": d.location or "Main Campus",
            "emp_count": emp_count,
            "attendance_rate": 94 + (d.id % 5),
        })

    return templates.TemplateResponse(
        request=request,
        name="departments.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "departments",
            "dept_list": dept_list,
        },
    )


@app.get("/{lang}/scanner", response_class=HTMLResponse)
def scanner_view(lang: str, request: Request, db: Session = Depends(get_db)):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "scanner")
    if guard_resp:
        return guard_resp

    departments = db.query(Department).all()
    total_enrolled = (
        db.query(Employee.id)
        .join(FaceEmbedding, FaceEmbedding.employee_id == Employee.id)
        .distinct()
        .count()
    )
    return templates.TemplateResponse(
        request=request,
        name="scanner.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "scanner",
            "departments": departments,
            "total_enrolled": total_enrolled,
        },
    )


@app.get("/{lang}/attendance", response_class=HTMLResponse)
def attendance_view(
    lang: str,
    request: Request,
    target_date: Optional[str] = Query(None),
    dept_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "attendance")
    if guard_resp:
        return guard_resp

    filter_date = date.today()
    if target_date:
        try:
            filter_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    query = (
        db.query(AttendanceRecord)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .options(joinedload(AttendanceRecord.employee).joinedload(Employee.department))
        .filter(AttendanceRecord.attendance_date == filter_date)
    )

    if dept_id:
        query = query.filter(Employee.department_id == dept_id)

    if status:
        query = query.filter(AttendanceRecord.status == status)

    if search:
        s_filter = f"%{search.strip()}%"
        query = query.filter(
            (Employee.first_name.ilike(s_filter))
            | (Employee.last_name.ilike(s_filter))
            | (Employee.employee_code.ilike(s_filter))
        )

    records = query.order_by(desc(AttendanceRecord.check_in_time)).all()
    departments = db.query(Department).all()

    total_present = sum(1 for r in records if r.status in ["PRESENT", "LATE"])
    total_late = sum(1 for r in records if r.status == "LATE")

    return templates.TemplateResponse(
        request=request,
        name="attendance.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "attendance",
            "records": records,
            "departments": departments,
            "filter_date": filter_date.strftime("%Y-%m-%d"),
            "selected_dept": dept_id,
            "selected_status": status or "",
            "search": search or "",
            "total_present": total_present,
            "total_late": total_late,
        },
    )


@app.get("/{lang}/audit-logs", response_class=HTMLResponse)
@app.get("/{lang}/audit_logs", response_class=HTMLResponse)
def audit_logs_view(
    lang: str,
    request: Request,
    action_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "audit_logs")
    if guard_resp:
        return guard_resp

    query = db.query(AuditLog).order_by(desc(AuditLog.timestamp))

    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
    if status:
        query = query.filter(AuditLog.status == status)
    if search:
        s_filter = f"%{search.strip()}%"
        query = query.filter(
            (AuditLog.details.ilike(s_filter))
            | (AuditLog.operator.ilike(s_filter))
            | (AuditLog.action_type.ilike(s_filter))
        )

    logs = query.limit(50).all()

    return templates.TemplateResponse(
        request=request,
        name="audit_logs.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "audit_logs",
            "logs": logs,
            "selected_action": action_type or "",
            "selected_status": status or "",
            "search": search or "",
        },
    )


@app.get("/{lang}/reports", response_class=HTMLResponse)
def reports_view(lang: str, request: Request, db: Session = Depends(get_db)):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "reports")
    if guard_resp:
        return guard_resp

    departments = db.query(Department).all()
    dept_stats = []
    for d in departments:
        emp_count = db.query(Employee).filter(Employee.department_id == d.id).count()
        dept_stats.append({
            "id": d.id,
            "code": d.code,
            "name": d.name,
            "head_name": d.head_name or "Leadership Team",
            "count": emp_count,
        })

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "reports",
            "dept_stats": dept_stats,
        },
    )


@app.get("/{lang}/settings", response_class=HTMLResponse)
def settings_view(
    lang: str,
    request: Request,
    tab: Optional[str] = Query("security"),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "settings")
    if guard_resp:
        return guard_resp

    settings_records = db.query(SystemSetting).all()
    settings_map = {s.setting_key: s.setting_value for s in settings_records}

    # Default fallbacks
    defaults = {
        "cosine_threshold": "0.38",
        "detection_confidence": "0.70",
        "anti_spoofing": "active",
        "work_start_time": "09:00",
        "grace_period_mins": "15",
        "work_end_time": "18:00",
        "session_timeout_mins": "60",
        "enforce_2fa": "false",
        "notify_late": "true",
        "notify_spoof": "true",
        "notify_failed_login": "true",
        "audio_chime": "true",
        "audio_volume": "80",
        "webhook_url": "",
        "snapshot_retention_days": "90",
        "auto_checkin": "true",
        "camera_primary_node": "Front Entrance Terminal #04",
    }
    for k, v in defaults.items():
        if k not in settings_map:
            settings_map[k] = v

    departments = db.query(Department).all()

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "settings",
            "active_tab": tab or "security",
            "settings": settings_map,
            "departments": departments,
        },
    )


@app.get("/{lang}/security", response_class=HTMLResponse)
def security_view(lang: str, request: Request, db: Session = Depends(get_db)):
    lang = resolve_lang(lang)
    t = TRANSLATIONS[lang]
    guard_resp, current_user = check_view_access(request, db, lang, "security")
    if guard_resp:
        return guard_resp

    users = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse(
        request=request,
        name="security.html",
        context={
            "lang": lang,
            "t": t,
            "current_user": current_user,
            "current_page": "security",
            "users": users,
        },
    )


# ============================================================================
# API ACTIONS (Security Users, Roles, Departments, Employees, Biometrics, Export)
# ============================================================================

@app.post("/api/security/users")
def add_user_api(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("SECURITY_OFFICER"),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin authorization required.")

    usr_clean = username.strip().lower()
    existing = db.query(User).filter((User.username == usr_clean) | (User.email == email.strip())).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already in use.")

    new_u = User(
        username=usr_clean,
        full_name=full_name.strip(),
        email=email.strip().lower(),
        hashed_password=hash_password(password),
        role=role.strip().upper(),
        is_active=True,
    )
    db.add(new_u)
    audit = AuditLog(
        operator=current_user.username,
        action_type="USER_PROVISIONED",
        status="SUCCESS",
        details=f"Provisioned operator {new_u.username} with role {new_u.role}",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/en/security?success=provisioned", status_code=303)


@app.post("/api/security/users/{user_id}/role")
def update_user_role_api(
    user_id: int,
    request: Request,
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin authorization required.")

    target_u = db.query(User).filter_by(id=user_id).first()
    if not target_u:
        raise HTTPException(status_code=404, detail="User not found.")

    old_role = target_u.role
    target_u.role = role.strip().upper()
    audit = AuditLog(
        operator=current_user.username,
        action_type="ROLE_UPDATED",
        status="SUCCESS",
        details=f"Altered role of {target_u.username} from {old_role} to {target_u.role}",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/en/security?success=role_updated", status_code=303)

@app.post("/api/departments")
def create_department_api(
    code: str = Form(...),
    name: str = Form(...),
    head_name: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    dept = Department(
        code=code.strip().upper(),
        name=name.strip(),
        head_name=head_name.strip() if head_name else None,
        location=location.strip() if location else None,
        description=description.strip() if description else None,
    )
    db.add(dept)

    # Log to Audit Trail
    audit = AuditLog(
        operator="Alex Chen (Admin)",
        action_type="DEPARTMENT_CREATED",
        status="SUCCESS",
        details=f"Created department: {dept.name} ({dept.code})",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/en/departments?success=created", status_code=303)


@app.post("/api/employees")
def create_employee_api(
    request: Request,
    employee_code: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    department_id: Optional[int] = Form(None),
    status: str = Form("ACTIVE"),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    existing = db.query(Employee).filter_by(employee_code=employee_code.strip()).first()
    if existing:
        return RedirectResponse(url="/en/employees?error=Employee+Code+already+exists", status_code=303)

    emp = Employee(
        employee_code=employee_code.strip(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email.strip() if email else None,
        phone=phone.strip() if phone else None,
        position=position.strip() if position else None,
        department_id=department_id if department_id else None,
        status=status,
    )
    db.add(emp)
    db.flush()

    # Store photo if provided and extract biometrics
    if photo and photo.filename:
        try:
            content = photo.file.read()
            if len(content) > 0:
                safe_name = f"emp_{emp.id}_{int(datetime.now().timestamp())}.jpg"
                save_path = UPLOADS_DIR / safe_name
                save_path.write_bytes(content)
                emp.photo_path = f"/uploads/{safe_name}"

                import cv2
                import numpy as np
                import json
                nparr = np.frombuffer(content, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    engine = get_face_engine()
                    box, raw_yunet = engine.detect_largest_face(img)
                    if box and raw_yunet is not None:
                        emb = engine.extract_embedding(img, raw_yunet)
                        if emb:
                            db.query(FaceEmbedding).filter_by(employee_id=emp.id).delete()
                            db.add(FaceEmbedding(
                                employee_id=emp.id,
                                embedding_data=json.dumps(emb),
                                quality_score=round(float(box.confidence), 3),
                                source="FILE_UPLOAD",
                            ))
        except Exception as e:
            print("Photo save error:", e)

    curr_user = get_current_user(request, db)
    operator_name = curr_user.full_name if curr_user else "System Admin"

    audit = AuditLog(
        operator=operator_name,
        action_type="EMPLOYEE_ENROLL",
        status="SUCCESS",
        details=f"Created employee profile: {emp.full_name} ({emp.employee_code})",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/en/employees?success=created", status_code=303)


@app.post("/api/employees/{emp_id}/update")
def update_employee_api(
    emp_id: int,
    request: Request,
    employee_code: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    department_id: Optional[int] = Form(None),
    status: str = Form("ACTIVE"),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter_by(id=emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp.employee_code = employee_code.strip()
    emp.first_name = first_name.strip()
    emp.last_name = last_name.strip()
    emp.email = email.strip() if email else None
    emp.phone = phone.strip() if phone else None
    emp.position = position.strip() if position else None
    emp.department_id = department_id if department_id else None
    emp.status = status

    # Store photo if updated
    if photo and photo.filename:
        try:
            content = photo.file.read()
            if len(content) > 0:
                safe_name = f"emp_{emp.id}_{int(datetime.now().timestamp())}.jpg"
                save_path = UPLOADS_DIR / safe_name
                save_path.write_bytes(content)
                emp.photo_path = f"/uploads/{safe_name}"

                import cv2
                import numpy as np
                import json
                nparr = np.frombuffer(content, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    engine = get_face_engine()
                    box, raw_yunet = engine.detect_largest_face(img)
                    if box and raw_yunet is not None:
                        emb = engine.extract_embedding(img, raw_yunet)
                        if emb:
                            db.query(FaceEmbedding).filter_by(employee_id=emp.id).delete()
                            db.add(FaceEmbedding(
                                employee_id=emp.id,
                                embedding_data=json.dumps(emb),
                                quality_score=round(float(box.confidence), 3),
                                source="FILE_UPLOAD",
                            ))
        except Exception as e:
            print("Photo update error:", e)

    curr_user = get_current_user(request, db)
    operator_name = curr_user.full_name if curr_user else "System Admin"

    audit = AuditLog(
        operator=operator_name,
        action_type="SETTINGS_UPDATE",
        status="SUCCESS",
        details=f"Updated employee profile: {emp.full_name} ({emp.employee_code})",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/en/employees?success=updated", status_code=303)


def set_system_setting(db: Session, key: str, value: str, desc: str = ""):
    record = db.query(SystemSetting).filter_by(setting_key=key).first()
    if record:
        record.setting_value = str(value)
    else:
        record = SystemSetting(setting_key=key, setting_value=str(value), description=desc)
        db.add(record)


# ============================================================================
# SETTINGS MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/settings/password")
def change_password_api(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    lang: str = Form("en"),
    session_timeout_mins: Optional[str] = Form("60"),
    enforce_2fa: Optional[str] = Form("false"),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    curr_user = get_current_user(request, db)
    if not curr_user:
        return RedirectResponse(url=f"/{lang}/login", status_code=303)

    if not verify_password(current_password, curr_user.hashed_password):
        return RedirectResponse(url=f"/{lang}/settings?tab=security&error=Current+password+incorrect", status_code=303)

    if len(new_password) < 6:
        return RedirectResponse(url=f"/{lang}/settings?tab=security&error=New+password+must+be+at+least+6+characters", status_code=303)

    if new_password != confirm_password:
        return RedirectResponse(url=f"/{lang}/settings?tab=security&error=New+passwords+do+not+match", status_code=303)

    curr_user.hashed_password = hash_password(new_password)
    set_system_setting(db, "session_timeout_mins", session_timeout_mins, "Session inactivity timeout")
    set_system_setting(db, "enforce_2fa", "true" if enforce_2fa in ["true", "on"] else "false", "Enforce 2FA")

    audit = AuditLog(
        operator=curr_user.full_name,
        action_type="PASSWORD_CHANGE",
        status="SUCCESS",
        details="Updated operator master access password & session security policies.",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url=f"/{lang}/settings?tab=security&success=settings_saved", status_code=303)


@app.post("/api/settings/profile")
def update_profile_api(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    avatar_url: Optional[str] = Form(None),
    avatar_file: Optional[UploadFile] = File(None),
    lang: str = Form("en"),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    curr_user = get_current_user(request, db)
    if not curr_user:
        return RedirectResponse(url=f"/{lang}/login", status_code=303)

    curr_user.full_name = full_name.strip()
    curr_user.email = email.strip()
    if avatar_url and avatar_url.strip():
        curr_user.avatar_url = avatar_url.strip()

    if avatar_file and avatar_file.filename:
        try:
            content = avatar_file.file.read()
            if len(content) > 0:
                safe_name = f"user_{curr_user.id}_{int(datetime.now().timestamp())}.jpg"
                save_path = UPLOADS_DIR / safe_name
                save_path.write_bytes(content)
                curr_user.avatar_url = f"/uploads/{safe_name}"
        except Exception as e:
            print("Avatar upload error:", e)

    audit = AuditLog(
        operator=curr_user.full_name,
        action_type="SETTINGS_UPDATE",
        status="SUCCESS",
        details=f"Updated operator personal profile and avatar.",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url=f"/{lang}/settings?tab=profile&success=settings_saved", status_code=303)


@app.post("/api/settings/notifications")
def update_notifications_api(
    request: Request,
    notify_late: Optional[str] = Form(None),
    notify_spoof: Optional[str] = Form(None),
    notify_failed_login: Optional[str] = Form(None),
    audio_chime: Optional[str] = Form(None),
    audio_volume: str = Form("80"),
    webhook_url: Optional[str] = Form(""),
    lang: str = Form("en"),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    curr_user = get_current_user(request, db)
    if not curr_user:
        return RedirectResponse(url=f"/{lang}/login", status_code=303)

    set_system_setting(db, "notify_late", "true" if notify_late else "false", "Notify on late arrivals")
    set_system_setting(db, "notify_spoof", "true" if notify_spoof else "false", "Notify on spoof triggers")
    set_system_setting(db, "notify_failed_login", "true" if notify_failed_login else "false", "Notify on failed logins")
    set_system_setting(db, "audio_chime", "true" if audio_chime else "false", "Web audio sound chimes")
    set_system_setting(db, "audio_volume", audio_volume, "Alert volume percentage")
    set_system_setting(db, "webhook_url", webhook_url.strip() if webhook_url else "", "External incident webhook")

    audit = AuditLog(
        operator=curr_user.full_name,
        action_type="SETTINGS_UPDATE",
        status="SUCCESS",
        details="Updated notification thresholds and incident webhook configuration.",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url=f"/{lang}/settings?tab=notifications&success=settings_saved", status_code=303)


@app.post("/api/settings/system")
def update_system_settings_api(
    request: Request,
    cosine_threshold: str = Form(...),
    detection_confidence: str = Form("0.70"),
    anti_spoofing: str = Form("active"),
    work_start_time: str = Form("09:00"),
    grace_period_mins: str = Form("15"),
    work_end_time: str = Form("18:00"),
    auto_checkin: Optional[str] = Form(None),
    camera_primary_node: Optional[str] = Form("Front Entrance Terminal #04"),
    lang: str = Form("en"),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    curr_user = get_current_user(request, db)
    if not curr_user:
        return RedirectResponse(url=f"/{lang}/login", status_code=303)

    set_system_setting(db, "cosine_threshold", cosine_threshold, "SFace distance threshold")
    set_system_setting(db, "detection_confidence", detection_confidence, "YuNet face detector threshold")
    set_system_setting(db, "anti_spoofing", anti_spoofing, "Liveness mode")
    set_system_setting(db, "work_start_time", work_start_time, "Shift start")
    set_system_setting(db, "grace_period_mins", grace_period_mins, "Grace period")
    set_system_setting(db, "work_end_time", work_end_time, "Shift end")
    set_system_setting(db, "auto_checkin", "true" if auto_checkin else "false", "Auto check in")
    if camera_primary_node:
        set_system_setting(db, "camera_primary_node", camera_primary_node, "Primary camera node")

    audit = AuditLog(
        operator=curr_user.full_name,
        action_type="SETTINGS_UPDATE",
        status="SUCCESS",
        details="Reconfigured core biometric inference engine and shift punctuality policy.",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url=f"/{lang}/settings?tab=system&success=settings_saved", status_code=303)


@app.post("/api/settings/privacy")
def update_privacy_settings_api(
    request: Request,
    snapshot_retention_days: str = Form("90"),
    lang: str = Form("en"),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    curr_user = get_current_user(request, db)
    if not curr_user:
        return RedirectResponse(url=f"/{lang}/login", status_code=303)

    set_system_setting(db, "snapshot_retention_days", snapshot_retention_days, "Snapshot retention")

    audit = AuditLog(
        operator=curr_user.full_name,
        action_type="SETTINGS_UPDATE",
        status="SUCCESS",
        details=f"Updated biometric snapshot retention duration to {snapshot_retention_days} days.",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url=f"/{lang}/settings?tab=privacy&success=settings_saved", status_code=303)


@app.get("/api/settings/backup")
def export_system_backup_api(
    request: Request,
    db: Session = Depends(get_db),
):
    curr_user = get_current_user(request, db)
    if not curr_user or curr_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin role required for database backup export.")

    employees = [
        {
            "code": e.employee_code,
            "name": e.full_name,
            "email": e.email,
            "position": e.position,
            "department": e.department.name if e.department else None,
            "status": e.status,
            "has_face": e.has_face_registered,
        }
        for e in db.query(Employee).all()
    ]
    departments = [
        {"code": d.code, "name": d.name, "location": d.location, "head": d.head_name}
        for d in db.query(Department).all()
    ]
    settings = {s.setting_key: s.setting_value for s in db.query(SystemSetting).all()}

    backup_payload = {
        "system": "FaceTrack AI Enterprise Biometrics",
        "exported_at": datetime.now().isoformat(),
        "exported_by": curr_user.username,
        "departments": departments,
        "employees": employees,
        "system_settings": settings,
    }

    import json
    content = json.dumps(backup_payload, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=facetrack_backup_{int(datetime.now().timestamp())}.json"},
    )


@app.post("/api/settings/purge-logs")
def purge_old_logs_api(
    request: Request,
    lang: str = Form("en"),
    days: int = Form(90),
    db: Session = Depends(get_db),
):
    lang = resolve_lang(lang)
    curr_user = get_current_user(request, db)
    if not curr_user or curr_user.role != "ADMIN":
        return RedirectResponse(url=f"/{lang}/settings?tab=privacy&error=Admin+role+required", status_code=303)

    cutoff = datetime.now() - timedelta(days=days)
    purged_scans = db.query(ScanLog).filter(ScanLog.timestamp < cutoff).delete()

    audit = AuditLog(
        operator=curr_user.full_name,
        action_type="DATA_PURGE",
        status="SUCCESS",
        details=f"Purged {purged_scans} biometric ingress records older than {days} days.",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url=f"/{lang}/settings?tab=privacy&success=settings_saved", status_code=303)


@app.post("/api/employees/{emp_id}/delete")
def delete_employee_api(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter_by(id=emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp_name = emp.full_name
    db.delete(emp)

    audit = AuditLog(
        operator="Alex Chen (Admin)",
        action_type="EMPLOYEE_DELETE",
        status="WARN",
        details=f"Deleted employee record: {emp_name} (ID: {emp_id})",
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/en/employees?success=deleted", status_code=303)


class FaceEnrollRequest(BaseModel):
    image: str


@app.post("/api/employees/{emp_id}/register-face")
def register_face_api(emp_id: int, req: FaceEnrollRequest, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter_by(id=emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    engine = get_face_engine()
    img = engine.decode_image(req.image)
    if img is None:
        return JSONResponse(status_code=400, content={"success": False, "message": "Failed to decode image data."})

    faces = engine.detect_faces(img)
    if not faces:
        return JSONResponse(status_code=400, content={"success": False, "message": "No face found in image. Please center face."})

    box, raw_yunet = faces[0]
    quality, quality_msg = engine.assess_quality(img, box)
    if quality < 0.4:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Face quality too low: {quality_msg}."})

    emb = engine.extract_embedding(img, raw_yunet)
    if not emb:
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to compute face embedding."})

    import cv2
    import json
    h, w = img.shape[:2]
    pad = int(box.width * 0.2)
    x1, y1 = max(0, box.x - pad), max(0, box.y - pad)
    x2, y2 = min(w, box.x + box.width + pad), min(h, box.y + box.height + pad)
    crop = img[y1:y2, x1:x2]

    avatar_filename = f"emp_{emp.id}_{int(datetime.now().timestamp())}.jpg"
    avatar_path = UPLOADS_DIR / avatar_filename
    cv2.imwrite(str(avatar_path), crop)

    emp.photo_path = f"/uploads/{avatar_filename}"
    db.query(FaceEmbedding).filter_by(employee_id=emp.id).delete()

    face_rec = FaceEmbedding(
        employee_id=emp.id,
        embedding_data=json.dumps(emb),
        quality_score=quality,
        source="WEBCAM",
    )
    db.add(face_rec)

    audit = AuditLog(
        operator="Alex Chen (Admin)",
        action_type="FACE_ENROLL",
        status="SUCCESS",
        details=f"Enrolled biometric SFace template for {emp.full_name} (Quality: {quality})",
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Face successfully enrolled for {emp.full_name}!",
        "photo_url": emp.photo_path,
        "quality": quality,
    }


class ScanRequest(BaseModel):
    image: str
    direction: str = "CHECK_IN"


@app.post("/api/scan/recognize")
def recognize_face_api(req: ScanRequest, db: Session = Depends(get_db)):
    engine = get_face_engine()
    img = engine.decode_image(req.image)
    if img is None:
        return JSONResponse(status_code=400, content={"outcome": "ERROR", "message": "Invalid image format."})

    faces = engine.detect_faces(img)
    if not faces:
        return {"outcome": "NO_FACE", "message": "No face detected in scanner frame."}

    primary_box, primary_raw = max(faces, key=lambda f: f[0].width * f[0].height)
    query_emb = engine.extract_embedding(img, primary_raw)
    if query_emb is None:
        return {"outcome": "ERROR", "message": "Failed to extract face features.", "box": primary_box.to_dict()}

    all_embeddings = (
        db.query(FaceEmbedding.employee_id, FaceEmbedding.embedding_data)
        .join(Employee, Employee.id == FaceEmbedding.employee_id)
        .filter(Employee.status == "ACTIVE")
        .all()
    )

    import json
    gallery = []
    for emp_id, emb_str in all_embeddings:
        try:
            gallery.append((emp_id, json.loads(emb_str)))
        except Exception:
            continue

    matched_emp_id, sim_score = engine.match_against_gallery(query_emb, gallery)
    now = datetime.now()
    today = date.today()

    if matched_emp_id is None:
        scan_log = ScanLog(timestamp=now, outcome="UNKNOWN", similarity_score=sim_score, direction=req.direction)
        db.add(scan_log)
        db.commit()
        return {"outcome": "UNKNOWN", "message": "Unregistered face detected.", "similarity": sim_score, "box": primary_box.to_dict()}

    employee = db.query(Employee).options(joinedload(Employee.department)).filter_by(id=matched_emp_id).first()
    if not employee:
        return {"outcome": "ERROR", "message": "Employee not found."}

    recent_scan = (
        db.query(ScanLog)
        .filter(
            ScanLog.matched_employee_id == employee.id,
            ScanLog.timestamp >= now - timedelta(seconds=45),
            ScanLog.outcome == "MATCH",
        )
        .first()
    )
    already_scanned = recent_scan is not None

    att_record = db.query(AttendanceRecord).filter_by(employee_id=employee.id, attendance_date=today).first()
    direction = req.direction.upper()

    if not already_scanned:
        is_late = now.time() > time(9, 0)
        status_text = "LATE" if is_late else "PRESENT"

        if direction == "CHECK_IN":
            if not att_record:
                att_record = AttendanceRecord(
                    employee_id=employee.id,
                    attendance_date=today,
                    check_in_time=now,
                    status=status_text,
                    method="FACE_SCAN",
                    terminal_node="Terminal 04",
                    confidence=sim_score,
                    notes=f"Scanned at {now.strftime('%H:%M:%S')}",
                )
                db.add(att_record)
            elif not att_record.check_in_time:
                att_record.check_in_time = now
                att_record.status = status_text
        else:
            if not att_record:
                att_record = AttendanceRecord(
                    employee_id=employee.id,
                    attendance_date=today,
                    check_out_time=now,
                    status="PRESENT",
                    method="FACE_SCAN",
                    terminal_node="Terminal 04",
                    confidence=sim_score,
                )
                db.add(att_record)
            else:
                att_record.check_out_time = now

    # Save optical scan snapshot to disk
    snapshot_rel_path = None
    try:
        import cv2
        snap_name = f"scan_{int(now.timestamp())}_{employee.id}.jpg"
        snap_path = UPLOADS_DIR / snap_name
        cv2.imwrite(str(snap_path), img)
        snapshot_rel_path = f"/uploads/{snap_name}"
    except Exception:
        pass

    scan_log = ScanLog(
        timestamp=now,
        outcome="MATCH",
        matched_employee_id=employee.id,
        terminal_node="Terminal 04",
        similarity_score=sim_score,
        direction=direction,
        snapshot_path=snapshot_rel_path,
        notes=f"{direction} verified ({round(sim_score * 100, 1)}%)",
    )
    db.add(scan_log)

    audit = AuditLog(
        timestamp=now,
        operator="Optical Terminal #04",
        action_type="FACE_SCAN_MATCH",
        status="SUCCESS",
        details=f"{direction} verified for {employee.full_name} ({round(sim_score * 100, 1)}% Conf.)",
    )
    db.add(audit)
    db.commit()

    return {
        "outcome": "MATCH",
        "already_scanned": already_scanned,
        "message": f"Welcome, {employee.full_name}!" if direction == "CHECK_IN" else f"Goodbye, {employee.full_name}!",
        "employee": {
            "id": employee.id,
            "code": employee.employee_code,
            "name": employee.full_name,
            "position": employee.position or "Staff",
            "department": employee.department.name if employee.department else "Unassigned",
            "photo_path": employee.photo_path,
        },
        "direction": direction,
        "confidence": round(sim_score * 100, 1),
        "timestamp": now.strftime("%I:%M:%S %p"),
        "box": primary_box.to_dict(),
    }


@app.get("/api/attendance/export")
def export_attendance_csv(
    target_date: Optional[str] = None,
    dept_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(AttendanceRecord)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .options(joinedload(AttendanceRecord.employee).joinedload(Employee.department))
    )

    if target_date:
        try:
            d = datetime.strptime(target_date, "%Y-%m-%d").date()
            query = query.filter(AttendanceRecord.attendance_date == d)
        except ValueError:
            pass

    if dept_id:
        query = query.filter(Employee.department_id == dept_id)

    if status:
        query = query.filter(AttendanceRecord.status == status)

    records = query.order_by(desc(AttendanceRecord.attendance_date), desc(AttendanceRecord.check_in_time)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record ID",
        "Date",
        "Employee Code",
        "Employee Name",
        "Department",
        "Position",
        "Check In",
        "Check Out",
        "Status",
        "Terminal",
        "Confidence",
        "Notes",
    ])

    for r in records:
        writer.writerow([
            r.id,
            r.attendance_date.strftime("%Y-%m-%d"),
            r.employee.employee_code,
            r.employee.full_name,
            r.employee.department.name if r.employee.department else "Unassigned",
            r.employee.position or "-",
            r.check_in_time.strftime("%I:%M:%S %p") if r.check_in_time else "-",
            r.check_out_time.strftime("%I:%M:%S %p") if r.check_out_time else "-",
            r.status,
            r.terminal_node or "-",
            f"{round(r.confidence * 100, 1)}%" if r.confidence else "-",
            r.notes or "-",
        ])

    output.seek(0)
    filename = f"attendance_dossier_{target_date or date.today().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
