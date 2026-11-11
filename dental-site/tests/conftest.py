"""Shared pytest fixtures using an isolated temporary SQLite database per test run."""

import os
import sys
import tempfile
from pathlib import Path

DENTAL_ROOT = Path(__file__).resolve().parent.parent
_TEMP_DIR = tempfile.TemporaryDirectory(prefix="dental_test_", ignore_cleanup_errors=True)
os.environ["DENTAL_DATABASE_URL"] = f"sqlite:///{Path(_TEMP_DIR.name).as_posix()}/test_dental.db"
os.environ["APP_ENV"] = "development"
os.environ["DENTAL_SECRET_KEY"] = "test-secret-key-for-automated-tests-only"

sys.path.insert(0, str(DENTAL_ROOT))

import pytest

from app.database import engine, init_dental_db
from app.security import form_rate_limiter


@pytest.fixture(scope="session", autouse=True)
def dispose_engine_on_exit():
    """Dispose SQLAlchemy connection pool before TemporaryDirectory cleanup on Windows."""
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_test_state():
    """Ensure DB tables exist and rate limiter buckets start clean for every test."""
    init_dental_db()
    form_rate_limiter.reset()
    yield
    form_rate_limiter.reset()
