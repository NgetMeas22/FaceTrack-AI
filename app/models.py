"""SQLAlchemy ORM models for Enterprise FaceTrack AI Workforce Intelligence System.

Fully normalized relational models supporting:
- Core: Users, Roles, Permissions, RolePermissions, AuditLogs, SystemSettings
- Organization: Departments, Employees, Shifts, EmployeeShifts
- Attendance: AttendanceRecords, AttendanceCorrections, ScanLogs, Devices
- Leave & Calendar: LeaveTypes, LeaveRequests, Holidays
- Biometrics & Privacy: FaceEmbeddings (BiometricTemplates), BiometricConsents
- Communication: In-App Notifications
"""

import json
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# 1. ACCESS CONTROL & IDENTITIES (Users, Roles, Permissions)
# ============================================================================

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    permissions: Mapped[List["RolePermission"]] = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users: Mapped[List["User"]] = relationship("User", back_populates="role_rel")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    module: Mapped[str] = mapped_column(String(50), default="SYSTEM")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    roles: Mapped[List["RolePermission"]] = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False)
    permission_id: Mapped[int] = mapped_column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), index=True, nullable=False)

    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    role: Mapped["Role"] = relationship("Role", back_populates="permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="roles")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="EMPLOYEE", index=True)  # ADMIN, HR_MANAGER, SECURITY_OFFICER, EMPLOYEE
    role_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    role_rel: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


# ============================================================================
# 2. ORGANIZATION STRUCTURE (Departments, Employees)
# ============================================================================

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    head_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE, ON_LEAVE
    photo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="employees")
    embeddings: Mapped[List["FaceEmbedding"]] = relationship(
        "FaceEmbedding", back_populates="employee", cascade="all, delete-orphan"
    )
    attendance_records: Mapped[List["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="employee", cascade="all, delete-orphan"
    )
    employee_shifts: Mapped[List["EmployeeShift"]] = relationship(
        "EmployeeShift", back_populates="employee", cascade="all, delete-orphan"
    )
    leave_requests: Mapped[List["LeaveRequest"]] = relationship(
        "LeaveRequest", back_populates="employee", cascade="all, delete-orphan"
    )
    biometric_consents: Mapped[List["BiometricConsent"]] = relationship(
        "BiometricConsent", back_populates="employee", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_emp_dept_status", "department_id", "status"),
        Index("idx_emp_name", "last_name", "first_name"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def has_face_registered(self) -> bool:
        return len(self.embeddings) > 0


# ============================================================================
# 3. SHIFTS & WORK SCHEDULES (Shifts, EmployeeShifts)
# ============================================================================

class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False, default="08:30")  # HH:MM format
    end_time: Mapped[str] = mapped_column(String(10), nullable=False, default="17:30")
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=15)
    is_overnight: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employee_shifts: Mapped[List["EmployeeShift"]] = relationship("EmployeeShift", back_populates="shift")


class EmployeeShift(Base):
    __tablename__ = "employee_shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    shift_id: Mapped[int] = mapped_column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), index=True, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="employee_shifts")
    shift: Mapped["Shift"] = relationship("Shift", back_populates="employee_shifts")


# ============================================================================
# 4. ATTENDANCE & CORRECTION AUDIT (AttendanceRecords, Corrections, Devices)
# ============================================================================

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), default="Main Entrance")
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    device_type: Mapped[str] = mapped_column(String(50), default="OPTICAL_TERMINAL")  # OPTICAL_TERMINAL, TURNSTILE, MOBILE_TABLET
    status: Mapped[str] = mapped_column(String(30), default="ONLINE", index=True)  # ONLINE, OFFLINE, MAINTENANCE
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    attendance_records: Mapped[List["AttendanceRecord"]] = relationship("AttendanceRecord", back_populates="device")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    check_in_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT")  # PRESENT, LATE, ABSENT, ON_LEAVE
    method: Mapped[str] = mapped_column(String(30), default="FACE_SCAN")  # FACE_SCAN, MANUAL, BADGE
    terminal_node: Mapped[str] = mapped_column(String(50), default="Front Terminal #04")
    device_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    shift_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_records")
    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="attendance_records")
    corrections: Mapped[List["AttendanceCorrection"]] = relationship("AttendanceCorrection", back_populates="attendance_record")

    __table_args__ = (
        Index("idx_att_date_emp", "attendance_date", "employee_id"),
        Index("idx_att_status_date", "status", "attendance_date"),
    )


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attendance_record_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("attendance_records.id", ondelete="SET NULL"), nullable=True
    )
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    requested_check_in: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    requested_check_out: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # PENDING, APPROVED, REJECTED
    requested_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employee: Mapped["Employee"] = relationship("Employee")
    attendance_record: Mapped[Optional["AttendanceRecord"]] = relationship("AttendanceRecord", back_populates="corrections")


# ============================================================================
# 5. LEAVE MANAGEMENT & HOLIDAYS (LeaveTypes, LeaveRequests, Holidays)
# ============================================================================

class LeaveType(Base):
    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    days_per_year: Mapped[int] = mapped_column(Integer, default=18)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    leave_requests: Mapped[List["LeaveRequest"]] = relationship("LeaveRequest", back_populates="leave_type")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    leave_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leave_types.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    days_count: Mapped[float] = mapped_column(Float, default=1.0)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # PENDING, APPROVED, REJECTED
    approved_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="leave_requests")
    leave_type: Mapped["LeaveType"] = relationship("LeaveType", back_populates="leave_requests")


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    holiday_date: Mapped[date] = mapped_column(Date, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


# ============================================================================
# 6. BIOMETRICS & PRIVACY GOVERNANCE (FaceEmbedding/Templates, Consents)
# ============================================================================

class FaceEmbedding(Base):
    """Stores 128-d canonical facial embeddings extracted via OpenCV SFace."""
    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    embedding_data: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(30), default="WEBCAM")  # WEBCAM, UPLOAD
    model_version: Mapped[str] = mapped_column(String(50), default="sface_2021dec")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="embeddings")

    def get_vector(self) -> list[float]:
        try:
            return json.loads(self.embedding_data)
        except Exception:
            return []

    def set_vector(self, vec: list[float]) -> None:
        self.embedding_data = json.dumps(vec)


# BiometricTemplate alias as per Section 5 of AGENT_GUIDE_updated.md
BiometricTemplate = FaceEmbedding


class BiometricConsent(Base):
    """Explicit privacy consent and withdrawal records adhering to Biometric Data Governance."""
    __tablename__ = "biometric_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(100), default="ATTENDANCE_VERIFICATION")
    notice_version: Mapped[str] = mapped_column(String(20), default="v1.0")
    is_granted: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    consented_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="biometric_consents")


# ============================================================================
# 7. LOGS, TELEMETRY & NOTIFICATIONS (ScanLogs, Audits, Settings, Notifications)
# ============================================================================

class ScanLog(Base):
    __tablename__ = "scan_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    outcome: Mapped[str] = mapped_column(String(30), index=True)  # MATCH, UNKNOWN, NO_FACE, ERROR
    matched_employee_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    terminal_node: Mapped[str] = mapped_column(String(50), default="Terminal 04")
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    direction: Mapped[str] = mapped_column(String(20), default="CHECK_IN")  # CHECK_IN, CHECK_OUT
    snapshot_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    matched_employee: Mapped[Optional["Employee"]] = relationship("Employee")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    setting_value: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    operator: Mapped[str] = mapped_column(String(100), default="System Engine")
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")  # SUCCESS, WARN, FAILED
    details: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), default="127.0.0.1")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(50), default="SYSTEM", index=True)  # ATTENDANCE, CORRECTION, LEAVE, SECURITY, SYSTEM
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="notifications")
