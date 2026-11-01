"""FastAPI Monolith Application Entry Point & Routes for FaceTrack AI."""

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
from app.models import AttendanceRecord, Department, Employee, FaceEmbedding, ScanLog

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# FastAPI App setup
app = FastAPI(
    title="FaceTrack AI — Face Recognition & Employee Attendance System",
    description="Clean, modern, pure Python face recognition & employee management system ready for Hostinger.",
    version="2.0.0",
)

# CORS Middleware (allows flexible multi-device and API access)
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

# Custom Jinja2 Filters
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


@app.on_event("startup")
def on_startup():
    """Initialize database schemas, seed records, and pre-load face models."""
    init_db()
    # Eagerly initialize face engine
    get_face_engine()


# ============================================================================
# WEB VIEW ROUTES (HTML)
# ============================================================================

@app.get("/", response_class=RedirectResponse)
def root_redirect():
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request, db: Session = Depends(get_db)):
    today = date.today()

    # Overview Metrics
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

    # Attendance rate
    attendance_rate = round((present_today / total_employees * 100), 1) if total_employees > 0 else 0.0

    # Recent Scans
    recent_scans = (
        db.query(ScanLog)
        .options(joinedload(ScanLog.matched_employee))
        .order_by(desc(ScanLog.timestamp))
        .limit(8)
        .all()
    )

    # Weekly Attendance Trend (Last 7 Days)
    week_days = []
    week_present_counts = []
    week_late_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%a (%m/%d)")
        p_count = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.attendance_date == day, AttendanceRecord.status == "PRESENT")
            .count()
        )
        l_count = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.attendance_date == day, AttendanceRecord.status == "LATE")
            .count()
        )
        week_days.append(day_str)
        week_present_counts.append(p_count)
        week_late_counts.append(l_count)

    # Department breakdown
    departments = db.query(Department).all()
    dept_stats = []
    for dept in departments:
        emp_count = db.query(Employee).filter(Employee.department_id == dept.id).count()
        dept_stats.append({"name": dept.name, "code": dept.code, "count": emp_count})

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "current_page": "dashboard",
            "stats": {
                "total_employees": total_employees,
                "present_today": present_today,
                "late_today": late_today,
                "pending_faces": pending_faces,
                "attendance_rate": attendance_rate,
            },
            "recent_scans": recent_scans,
            "week_days": week_days,
            "week_present": week_present_counts,
            "week_late": week_late_counts,
            "dept_stats": dept_stats,
        },
    )


@app.get("/employees", response_class=HTMLResponse)
def employees_view(
    request: Request,
    search: Optional[str] = Query(None),
    dept_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
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
            "current_page": "employees",
            "employees": employees,
            "departments": departments,
            "search": search or "",
            "selected_dept": dept_id,
            "selected_status": status or "",
        },
    )


@app.get("/scanner", response_class=HTMLResponse)
def scanner_view(request: Request, db: Session = Depends(get_db)):
    """Render the animated live face scanner page with glow effects."""
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
            "current_page": "scanner",
            "departments": departments,
            "total_enrolled": total_enrolled,
        },
    )


@app.get("/attendance", response_class=HTMLResponse)
def attendance_view(
    request: Request,
    target_date: Optional[str] = Query(None),
    dept_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
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

    # Metrics for filtered view
    total_present = sum(1 for r in records if r.status in ["PRESENT", "LATE"])
    total_late = sum(1 for r in records if r.status == "LATE")

    return templates.TemplateResponse(
        request=request,
        name="attendance.html",
        context={
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


# ============================================================================
# API ENDPOINTS (Face Scanning, Employee CRUD, Face Enrollment, Export)
# ============================================================================

class ScanRequest(BaseModel):
    image: str  # Base64 data URL
    direction: str = "CHECK_IN"  # "CHECK_IN" or "CHECK_OUT"


@app.post("/api/scan/recognize")
def recognize_face_api(req: ScanRequest, db: Session = Depends(get_db)):
    """
    Process video frame from webcam, detect faces, match against employee gallery,
    and log attendance automatically with anti-bounce protection.
    """
    engine = get_face_engine()
    img = engine.decode_image(req.image)
    if img is None:
        return JSONResponse(
            status_code=400,
            content={"outcome": "ERROR", "message": "Invalid image data format."},
        )

    # 1. Detect faces in frame
    faces = engine.detect_faces(img)
    if not faces:
        return {
            "outcome": "NO_FACE",
            "message": "No face detected in scanner frame.",
            "faces_count": 0,
        }

    # Focus on the most prominent / largest face in frame
    primary_box, primary_raw = max(faces, key=lambda f: f[0].width * f[0].height)

    # Assess quality
    quality_score, quality_msg = engine.assess_quality(img, primary_box)

    # Extract 128-d feature embedding
    query_emb = engine.extract_embedding(img, primary_raw)
    if query_emb is None:
        return {
            "outcome": "ERROR",
            "message": "Failed to extract face features. Please look directly at camera.",
            "box": primary_box.to_dict(),
        }

    # 2. Load Gallery of Registered Employees
    all_embeddings = (
        db.query(FaceEmbedding.employee_id, FaceEmbedding.embedding_data)
        .join(Employee, Employee.id == FaceEmbedding.employee_id)
        .filter(Employee.status == "ACTIVE")
        .all()
    )

    gallery = []
    for emp_id, emb_str in all_embeddings:
        try:
            import json
            gallery.append((emp_id, json.loads(emb_str)))
        except Exception:
            continue

    # 3. Match against gallery
    matched_emp_id, sim_score = engine.match_against_gallery(query_emb, gallery)

    now = datetime.now()
    today = date.today()

    if matched_emp_id is None:
        # Unknown Face
        scan_log = ScanLog(
            timestamp=now,
            outcome="UNKNOWN",
            similarity_score=sim_score,
            direction=req.direction,
            notes="Unrecognized face in scanner",
        )
        db.add(scan_log)
        db.commit()

        return {
            "outcome": "UNKNOWN",
            "message": "Unknown face. Please register face in Employee Directory.",
            "similarity": sim_score,
            "box": primary_box.to_dict(),
        }

    # 4. Known Employee Matched!
    employee = db.query(Employee).options(joinedload(Employee.department)).filter_by(id=matched_emp_id).first()
    if not employee:
        return {"outcome": "ERROR", "message": "Employee record not found."}

    # Anti-bounce / Debounce Check (prevent repeat scans within 45 seconds for same person)
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

    # Attendance Logic:
    # Check if attendance record exists for today
    att_record = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id == employee.id,
            AttendanceRecord.attendance_date == today,
        )
        .first()
    )

    direction = req.direction.upper()
    status_text = "PRESENT"
    # Company policy: Late if check-in after 09:00 AM
    work_start_time = time(9, 0, 0)

    if not already_scanned:
        if direction == "CHECK_IN":
            is_late = now.time() > work_start_time
            status_text = "LATE" if is_late else "PRESENT"

            if not att_record:
                att_record = AttendanceRecord(
                    employee_id=employee.id,
                    attendance_date=today,
                    check_in_time=now,
                    status=status_text,
                    method="FACE_SCAN",
                    confidence=sim_score,
                    notes=f"Scanned at {now.strftime('%H:%M:%S')}",
                )
                db.add(att_record)
            else:
                # If already checked in earlier, update check-in note or maintain time
                if not att_record.check_in_time:
                    att_record.check_in_time = now
                    att_record.status = status_text
        else:
            # CHECK_OUT
            if not att_record:
                att_record = AttendanceRecord(
                    employee_id=employee.id,
                    attendance_date=today,
                    check_out_time=now,
                    status="PRESENT",
                    method="FACE_SCAN",
                    confidence=sim_score,
                    notes=f"Check-out only at {now.strftime('%H:%M:%S')}",
                )
                db.add(att_record)
            else:
                att_record.check_out_time = now

    # Record Scan Log
    scan_log = ScanLog(
        timestamp=now,
        outcome="MATCH",
        matched_employee_id=employee.id,
        similarity_score=sim_score,
        direction=direction,
        notes=f"{direction} verified ({round(sim_score * 100, 1)}%)",
    )
    db.add(scan_log)
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


@app.post("/api/employees")
def create_employee_api(
    employee_code: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    department_id: Optional[int] = Form(None),
    status: str = Form("ACTIVE"),
    db: Session = Depends(get_db),
):
    # Check duplicate code
    existing = db.query(Employee).filter_by(employee_code=employee_code.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee Code already exists.")

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
    db.commit()
    db.refresh(emp)

    return RedirectResponse(url="/employees?success=created", status_code=303)


@app.post("/api/employees/{emp_id}/update")
def update_employee_api(
    emp_id: int,
    employee_code: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    department_id: Optional[int] = Form(None),
    status: str = Form("ACTIVE"),
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

    db.commit()
    return RedirectResponse(url="/employees?success=updated", status_code=303)


@app.post("/api/employees/{emp_id}/delete")
def delete_employee_api(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter_by(id=emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    db.delete(emp)
    db.commit()
    return RedirectResponse(url="/employees?success=deleted", status_code=303)


class FaceEnrollRequest(BaseModel):
    image: str  # Base64 string from webcam or file picker


@app.post("/api/employees/{emp_id}/register-face")
def register_face_api(emp_id: int, req: FaceEnrollRequest, db: Session = Depends(get_db)):
    """Register face sample for an employee from webcam snapshot or file."""
    emp = db.query(Employee).filter_by(id=emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    engine = get_face_engine()
    img = engine.decode_image(req.image)
    if img is None:
        return JSONResponse(status_code=400, content={"success": False, "message": "Failed to decode image data."})

    faces = engine.detect_faces(img)
    if not faces:
        return JSONResponse(status_code=400, content={"success": False, "message": "No face found in image. Please center your face."})

    if len(faces) > 1:
        return JSONResponse(status_code=400, content={"success": False, "message": "Multiple faces detected. Please ensure only one person is in frame."})

    box, raw_yunet = faces[0]
    quality, quality_msg = engine.assess_quality(img, box)
    if quality < 0.4:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Face quality too low: {quality_msg}."})

    emb = engine.extract_embedding(img, raw_yunet)
    if not emb:
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to compute face embedding."})

    # Save photo crop for employee avatar
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

    # Remove previous embeddings or append
    db.query(FaceEmbedding).filter_by(employee_id=emp.id).delete()

    face_rec = FaceEmbedding(
        employee_id=emp.id,
        embedding_data=json.dumps(emb),
        quality_score=quality,
        source="WEBCAM",
    )
    db.add(face_rec)
    db.commit()

    return {
        "success": True,
        "message": f"Face successfully enrolled for {emp.full_name}!",
        "photo_url": emp.photo_path,
        "quality": quality,
    }


@app.get("/api/attendance/export")
def export_attendance_csv(
    target_date: Optional[str] = None,
    dept_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export attendance data to a clean CSV file."""
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
        "Method",
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
            r.method,
            f"{round(r.confidence * 100, 1)}%" if r.confidence else "-",
            r.notes or "-",
        ])

    output.seek(0)
    filename = f"attendance_export_{target_date or date.today().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
