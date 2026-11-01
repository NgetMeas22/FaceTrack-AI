"""Database setup and session management using SQLAlchemy."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database URL: defaults to SQLite file for zero-config run, or MySQL / Postgres via env
DEFAULT_DB_FILE = DATA_DIR / "facetrack.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE}")

# Connect arguments (SQLite needs check_same_thread=False for multi-threaded FastAPI)
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
    """Create all tables and seed default departments/employees if empty."""
    from app.models import Department, Employee, AttendanceRecord

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # Seed departments if none exist
        if db.query(Department).count() == 0:
            sample_depts = [
                Department(code="ENG", name="Engineering & IT", description="Software development, AI, and systems"),
                Department(code="HR", name="Human Resources", description="Talent acquisition and people operations"),
                Department(code="MKT", name="Marketing & Sales", description="Brand strategy, sales, and outreach"),
                Department(code="OPS", name="Operations", description="Logistics, facilities, and administration"),
                Department(code="FIN", name="Finance & Accounting", description="Payroll, budget, and compliance"),
            ]
            db.add_all(sample_depts)
            db.commit()

        # Seed sample employees if none exist
        if db.query(Employee).count() == 0:
            eng_dept = db.query(Department).filter_by(code="ENG").first()
            hr_dept = db.query(Department).filter_by(code="HR").first()
            mkt_dept = db.query(Department).filter_by(code="MKT").first()

            sample_employees = [
                Employee(
                    employee_code="EMP-1001",
                    first_name="Meas",
                    last_name="Nget",
                    email="meas.nget@company.com",
                    phone="+855 12 345 678",
                    position="Lead AI Engineer",
                    department_id=eng_dept.id if eng_dept else None,
                    status="ACTIVE",
                ),
                Employee(
                    employee_code="EMP-1002",
                    first_name="Sophea",
                    last_name="Chan",
                    email="sophea.chan@company.com",
                    phone="+855 12 876 543",
                    position="HR Manager",
                    department_id=hr_dept.id if hr_dept else None,
                    status="ACTIVE",
                ),
                Employee(
                    employee_code="EMP-1003",
                    first_name="Dara",
                    last_name="Sok",
                    email="dara.sok@company.com",
                    phone="+855 10 999 888",
                    position="Marketing Specialist",
                    department_id=mkt_dept.id if mkt_dept else None,
                    status="ACTIVE",
                ),
            ]
            db.add_all(sample_employees)
            db.commit()

