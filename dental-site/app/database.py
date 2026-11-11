"""SQLAlchemy 2.x database engine and transaction session dependencies for the dental site."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for isolated dental clinic tables."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Yield a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_dental_db() -> None:
    """Ensure tables exist when running in local dev; production uses Alembic migrations."""
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


@contextmanager
def db_transaction(db: Session) -> Generator[Session, None, None]:
    """Wrap related mutations in an explicit commit/rollback boundary."""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise

