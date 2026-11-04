"""Database setup and rich enterprise data seeding using SQLAlchemy."""

import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_DB_FILE = DATA_DIR / "facetrack.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and seed default departments/employees/logs/users/shifts/leaves if empty."""
    from app.models import (
        AttendanceCorrection,
        AttendanceRecord,
        AuditLog,
        BiometricConsent,
        Department,
        Device,
        Employee,
        EmployeeShift,
        FaceEmbedding,
        Holiday,
        LeaveRequest,
        LeaveType,
        Notification,
        Permission,
        Role,
        RolePermission,
        ScanLog,
        Shift,
        SystemSetting,
        User,
    )
    from app.security import (
        hash_password,
        ROLE_ADMIN,
        ROLE_HR,
        ROLE_SECURITY,
        ROLE_EMPLOYEE,
    )

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # Seed Roles & Permissions
        if db.query(Role).count() == 0:
            roles = [
                Role(name=ROLE_ADMIN, description="Full administrative clearance across entire system"),
                Role(name=ROLE_HR, description="Human Resources & Employee Directory Manager"),
                Role(name=ROLE_SECURITY, description="Security Officer & Real-time Biometric Terminal Operator"),
                Role(name=ROLE_EMPLOYEE, description="General Staff Member with Personal Attendance Access"),
            ]
            db.add_all(roles)
            db.commit()

            # Seed basic permissions
            perms = [
                Permission(key="employees:read", description="View personnel directory", module="EMPLOYEES"),
                Permission(key="employees:write", description="Create and modify personnel records", module="EMPLOYEES"),
                Permission(key="attendance:read", description="View attendance logs", module="ATTENDANCE"),
                Permission(key="attendance:write", description="Record or correct attendance", module="ATTENDANCE"),
                Permission(key="shifts:manage", description="Configure work shifts and schedules", module="SHIFTS"),
                Permission(key="leave:manage", description="Review and approve leave requests", module="LEAVE"),
                Permission(key="devices:manage", description="Register and manage optical terminals", module="DEVICES"),
                Permission(key="audit:read", description="Inspect immutable audit logs", module="AUDIT"),
                Permission(key="system:settings", description="Modify system and security settings", module="SETTINGS"),
            ]
            db.add_all(perms)
            db.commit()

        # Seed Standard Shifts
        if db.query(Shift).count() == 0:
            shifts = [
                Shift(code="SHIFT-STD", name="Standard Office Shift", start_time="08:30", end_time="17:30", grace_period_minutes=15, is_overnight=False, description="Primary daylight operating shift"),
                Shift(code="SHIFT-MORN", name="Morning Terminal Shift", start_time="06:00", end_time="14:30", grace_period_minutes=10, is_overnight=False, description="Early optical gate coverage"),
                Shift(code="SHIFT-EVE", name="Evening Operations Shift", start_time="14:00", end_time="22:30", grace_period_minutes=10, is_overnight=False, description="Evening ingress & facility supervision"),
                Shift(code="SHIFT-NIGHT", name="Overnight Security Shift", start_time="22:00", end_time="06:30", grace_period_minutes=15, is_overnight=True, description="24/7 facility monitoring & nocturnal ingress"),
            ]
            db.add_all(shifts)
            db.commit()

        # Seed Leave Types
        if db.query(LeaveType).count() == 0:
            leaves = [
                LeaveType(code="ANNUAL", name="Annual Paid Leave", days_per_year=18, is_paid=True, description="Standard statutory annual paid leave allowance"),
                LeaveType(code="SICK", name="Medical / Sick Leave", days_per_year=14, is_paid=True, description="Paid sick leave with medical certificate"),
                LeaveType(code="SPECIAL", name="Special Family / Compassionate Leave", days_per_year=7, is_paid=True, description="Family emergencies, wedding, or bereavement"),
                LeaveType(code="UNPAID", name="Unpaid Leave", days_per_year=0, is_paid=False, description="Authorized unpaid absence approved by management"),
            ]
            db.add_all(leaves)
            db.commit()

        # Seed Optical Terminals / Devices
        if db.query(Device).count() == 0:
            devices = [
                Device(device_code="DEV-001", name="Front Entrance Optical Array #04", location="Building A Main Entrance", ip_address="192.168.1.104", device_type="OPTICAL_TERMINAL", status="ONLINE", last_seen_at=datetime.now(timezone.utc)),
                Device(device_code="DEV-002", name="Lobby Optical Turnstile #02", location="Ground Floor Lobby", ip_address="192.168.1.102", device_type="TURNSTILE", status="ONLINE", last_seen_at=datetime.now(timezone.utc)),
                Device(device_code="DEV-003", name="AI Research Lab Access Terminal #01", location="Building C Lab Entrance", ip_address="192.168.1.103", device_type="OPTICAL_TERMINAL", status="ONLINE", last_seen_at=datetime.now(timezone.utc)),
            ]
            db.add_all(devices)
            db.commit()

        # Seed Official Holidays
        if db.query(Holiday).count() == 0:
            year = date.today().year
            holidays = [
                Holiday(holiday_date=date(year, 1, 1), name="International New Year's Day", description="Global New Year holiday"),
                Holiday(holiday_date=date(year, 4, 13), name="Khmer New Year (Day 1)", description="Moha Sangkranta"),
                Holiday(holiday_date=date(year, 4, 14), name="Khmer New Year (Day 2)", description="Virak Wanabat"),
                Holiday(holiday_date=date(year, 4, 15), name="Khmer New Year (Day 3)", description="Virak Loeung Sak"),
                Holiday(holiday_date=date(year, 5, 1), name="International Labor Day", description="Statutory public holiday"),
                Holiday(holiday_date=date(year, 10, 1), name="Pchum Ben Day 1", description="Ancestors Day"),
                Holiday(holiday_date=date(year, 10, 2), name="Pchum Ben Day 2", description="Ancestors Day Festival"),
                Holiday(holiday_date=date(year, 11, 14), name="Water Festival (Day 1)", description="Bon Om Touk"),
                Holiday(holiday_date=date(year, 11, 15), name="Water Festival (Day 2)", description="Bon Om Touk"),
            ]
            db.add_all(holidays)
            db.commit()

    with SessionLocal() as db:
        # Seed Users & Roles if empty
        if db.query(User).count() == 0:
            demo_users = [
                User(
                    username="admin",
                    email="alex.chen@facetrack.ai",
                    full_name="Alex Chen",
                    hashed_password=hash_password("admin123"),
                    role=ROLE_ADMIN,
                    avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop&crop=faces",
                ),
                User(
                    username="hr",
                    email="chloe.zhang@facetrack.ai",
                    full_name="Chloe Zhang",
                    hashed_password=hash_password("hr123"),
                    role=ROLE_HR,
                    avatar_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop&crop=faces",
                ),
                User(
                    username="security",
                    email="kenji.sato@facetrack.ai",
                    full_name="Kenji Sato",
                    hashed_password=hash_password("security123"),
                    role=ROLE_SECURITY,
                    avatar_url="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=100&h=100&fit=crop&crop=faces",
                ),
                User(
                    username="staff",
                    email="david.vance@facetrack.ai",
                    full_name="David Vance",
                    hashed_password=hash_password("staff123"),
                    role=ROLE_EMPLOYEE,
                    avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=faces",
                ),
            ]
            db.add_all(demo_users)
            db.commit()
        # Seed Settings if empty
        if db.query(SystemSetting).count() == 0:
            settings = [
                SystemSetting(setting_key="auto_checkin", setting_value="true", description="Automatically record check-in upon face lock"),
                SystemSetting(setting_key="anti_spoofing", setting_value="active", description="3D liveness detection mode"),
                SystemSetting(setting_key="cosine_threshold", setting_value="0.38", description="SFace similarity threshold"),
                SystemSetting(setting_key="work_start_time", setting_value="09:00", description="Shift start time for punctuality"),
                SystemSetting(setting_key="camera_primary_node", setting_value="Front Entrance Terminal #04", description="Default entrance optical array"),
            ]
            db.add_all(settings)
            db.commit()

        # Seed Departments
        if db.query(Department).count() == 0:
            sample_depts = [
                Department(code="ENG", name="Engineering", description="Core AI, hardware integration, and software systems", head_name="David Vance", location="Building A - Floor 4"),
                Department(code="DES", name="Design & Product", description="Product UI/UX, hardware ergonomics, and aesthetics", head_name="Elena Rostova", location="Building B - Floor 2"),
                Department(code="FIN", name="Finance & Ops", description="Corporate accounting, payroll, and compliance", head_name="Marcus Sterling", location="Building A - Floor 1"),
                Department(code="HR", name="People & Culture", description="Talent acquisition, operations, and biometric governance", head_name="Chloe Zhang", location="Building A - Floor 2"),
                Department(code="INF", name="Infrastructure", description="Data centers, edge optical terminals, and networking", head_name="Kenji Sato", location="Server Complex C"),
                Department(code="RES", name="AI & Biometrics Lab", description="Deep learning computer vision and 3D liveness research", head_name="Sarah Jenkins", location="Building C - Floor 5"),
            ]
            db.add_all(sample_depts)
            db.commit()

        # Seed Personnel
        if db.query(Employee).count() == 0:
            eng = db.query(Department).filter_by(code="ENG").first()
            des = db.query(Department).filter_by(code="DES").first()
            fin = db.query(Department).filter_by(code="FIN").first()
            hr = db.query(Department).filter_by(code="HR").first()
            inf = db.query(Department).filter_by(code="INF").first()
            res = db.query(Department).filter_by(code="RES").first()

            employees = [
                Employee(employee_code="EMP-1001", first_name="David", last_name="Vance", email="david.vance@facetrack.ai", phone="+1 (555) 234-5678", position="Principal Engineer", department_id=eng.id if eng else None, status="ACTIVE"),
                Employee(employee_code="EMP-1002", first_name="Elena", last_name="Rostova", email="elena.rostova@facetrack.ai", phone="+1 (555) 345-6789", position="Lead Visual Designer", department_id=des.id if des else None, status="ACTIVE"),
                Employee(employee_code="EMP-1003", first_name="Marcus", last_name="Sterling", email="marcus.sterling@facetrack.ai", phone="+1 (555) 456-7890", position="Finance Controller", department_id=fin.id if fin else None, status="ACTIVE"),
                Employee(employee_code="EMP-1004", first_name="Chloe", last_name="Zhang", email="chloe.zhang@facetrack.ai", phone="+1 (555) 567-8901", position="VP People Operations", department_id=hr.id if hr else None, status="ACTIVE"),
                Employee(employee_code="EMP-1005", first_name="Kenji", last_name="Sato", email="kenji.sato@facetrack.ai", phone="+1 (555) 678-9012", position="Systems Architect", department_id=inf.id if inf else None, status="ACTIVE"),
                Employee(employee_code="EMP-1006", first_name="Sarah", last_name="Jenkins", email="sarah.jenkins@facetrack.ai", phone="+1 (555) 789-0123", position="Biometric Research Lead", department_id=res.id if res else None, status="ACTIVE"),
                Employee(employee_code="EMP-1007", first_name="Alex", last_name="Chen", email="alex.chen@facetrack.ai", phone="+1 (555) 890-1234", position="System Administrator", department_id=inf.id if inf else None, status="ACTIVE"),
                Employee(employee_code="EMP-1008", first_name="Meas", last_name="Nget", email="meas.nget@facetrack.ai", phone="+855 12 345 678", position="AI Platform Lead", department_id=eng.id if eng else None, status="ACTIVE"),
                Employee(employee_code="EMP-1009", first_name="Sophea", last_name="Chan", email="sophea.chan@facetrack.ai", phone="+855 12 876 543", position="HR Operations Manager", department_id=hr.id if hr else None, status="ACTIVE"),
                Employee(employee_code="EMP-1010", first_name="Dara", last_name="Sok", email="dara.sok@facetrack.ai", phone="+855 10 999 888", position="Field Deployment Specialist", department_id=inf.id if inf else None, status="ACTIVE"),
            ]
            db.add_all(employees)
            db.commit()

        # Seed Attendance & Scan Logs for Today and Past 7 Days if empty
        if db.query(AttendanceRecord).count() == 0:
            today = date.today()
            all_emps = db.query(Employee).all()

            for emp in all_emps[:6]:
                check_in_dt = datetime.combine(today, time(8, 40)) + timedelta(minutes=emp.id * 3)
                is_late = check_in_dt.time() > time(9, 0)
                status_str = "LATE" if is_late else "PRESENT"

                att = AttendanceRecord(
                    employee_id=emp.id,
                    attendance_date=today,
                    check_in_time=check_in_dt,
                    status=status_str,
                    method="FACE_SCAN",
                    terminal_node=f"Terminal 0{emp.id % 4 + 1}",
                    confidence=0.98 + (emp.id % 5) * 0.003,
                    notes=f"Ingress captured via Optical Array",
                )
                db.add(att)

                scan_log = ScanLog(
                    timestamp=check_in_dt,
                    outcome="MATCH",
                    matched_employee_id=emp.id,
                    terminal_node=f"Terminal 0{emp.id % 4 + 1}",
                    similarity_score=0.98 + (emp.id % 5) * 0.003,
                    direction="CHECK_IN",
                    notes=f"Verified Identity ({round((0.98 + (emp.id % 5) * 0.003) * 100, 1)}% Conf.)",
                )
                db.add(scan_log)

            # Historical weekly attendance
            for days_ago in range(1, 7):
                past_date = today - timedelta(days=days_ago)
                for emp in all_emps[:8]:
                    check_in_dt = datetime.combine(past_date, time(8, 45)) + timedelta(minutes=(emp.id + days_ago) * 2)
                    is_late = check_in_dt.time() > time(9, 0)
                    att = AttendanceRecord(
                        employee_id=emp.id,
                        attendance_date=past_date,
                        check_in_time=check_in_dt,
                        check_out_time=datetime.combine(past_date, time(17, 30)) + timedelta(minutes=emp.id * 5),
                        status="LATE" if is_late else "PRESENT",
                        method="FACE_SCAN",
                        terminal_node="Terminal 04",
                        confidence=0.985,
                        notes="Normal shift record",
                    )
                    db.add(att)

            db.commit()

        # Seed Audit Logs if empty
        if db.query(AuditLog).count() == 0:
            now = datetime.now()
            sample_audits = [
                AuditLog(timestamp=now - timedelta(minutes=4), operator="Optical Terminal #04", action_type="FACE_SCAN_MATCH", status="SUCCESS", details="Face verified for Sarah Jenkins (98.4% similarity)", ip_address="192.168.1.104"),
                AuditLog(timestamp=now - timedelta(minutes=9), operator="Optical Terminal #02", action_type="FACE_SCAN_MATCH", status="SUCCESS", details="Face verified for David Vance (98.8% similarity)", ip_address="192.168.1.102"),
                AuditLog(timestamp=now - timedelta(minutes=24), operator="Alex Chen (Admin)", action_type="EMPLOYEE_ENROLL", status="SUCCESS", details="Registered new personnel: Sarah Connor (EMP-1011)", ip_address="192.168.1.50"),
                AuditLog(timestamp=now - timedelta(minutes=38), operator="Gate 01 Scanner", action_type="LATE_INGRESS", status="WARN", details="Marcus Sterling arrived after shift cutoff (09:16 AM)", ip_address="192.168.1.101"),
                AuditLog(timestamp=now - timedelta(hours=2), operator="Alex Chen (Admin)", action_type="SETTINGS_UPDATE", status="SUCCESS", details="Adjusted SFace cosine distance threshold to 0.38", ip_address="192.168.1.50"),
                AuditLog(timestamp=now - timedelta(hours=5), operator="Lobby Turnstile #01", action_type="FACE_UNKNOWN", status="WARN", details="Unregistered visitor face detected in camera viewport", ip_address="192.168.1.101"),
            ]
            db.add_all(sample_audits)
            db.commit()
