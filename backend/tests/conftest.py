"""Shared pytest fixtures for the auto-insurance test suites."""

from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.database as _db_module
import backend.main as _main_module
from backend.auth import get_current_user
from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    CoverageType,
    Quote,
    QuoteStatus,
    User,
    UserRole,
)


# ── Test database ────────────────────────────────────────────────────────────

SQLALCHEMY_TEST_URL = "sqlite://"  # in-memory

test_engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch the module-level engine in both database.py and main.py so the
# on_startup handler (Base.metadata.create_all(bind=engine)) uses the test
# SQLite engine instead of the production database.
_db_module.engine = test_engine
_main_module.engine = test_engine


@pytest.fixture(autouse=True)
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database for every test, yield a session, then tear down."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def _override_get_db(session: Session):
    """Return a FastAPI dependency override bound to the given session."""
    def _inner():
        try:
            yield session
        finally:
            pass  # session lifecycle managed by fixture
    return _inner


# ── Test users ───────────────────────────────────────────────────────────────

_TEST_USER_DEFAULTS = dict(
    email="testuser@example.com",
    full_name="Test User",
    hashed_password="fakehash",
    role=UserRole.USER,
    is_active=True,
)


@pytest.fixture()
def test_user(db_session: Session) -> User:
    """Insert and return a default test user."""
    user = User(**_TEST_USER_DEFAULTS)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def other_user(db_session: Session) -> User:
    """Insert and return a second user (for ownership tests)."""
    user = User(
        email="other@example.com",
        full_name="Other User",
        hashed_password="fakehash",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Authenticated test client ────────────────────────────────────────────────


@pytest.fixture()
def client(db_session: Session, test_user: User) -> Generator[TestClient, None, None]:
    """Yield a TestClient with auth and db overrides injecting `test_user`."""
    app.dependency_overrides[get_db] = _override_get_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthed_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Yield a TestClient with db override but NO auth override."""
    app.dependency_overrides[get_db] = _override_get_db(db_session)
    # Do NOT override get_current_user -- real auth path runs
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def other_client(
    db_session: Session, other_user: User
) -> Generator[TestClient, None, None]:
    """Yield a TestClient authenticated as `other_user`."""
    app.dependency_overrides[get_db] = _override_get_db(db_session)
    app.dependency_overrides[get_current_user] = lambda: other_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Quote data helpers ───────────────────────────────────────────────────────


def _valid_quote_payload(
    coverage_type: str = "basic",
    vehicle_year: int | None = None,
    driver_dob: str | None = None,
    violation_count: int = 0,
    accident_count: int = 0,
    mileage: int = 15000,
) -> dict:
    """Return a valid QuoteCreateRequest payload (camelCase keys)."""
    if vehicle_year is None:
        vehicle_year = date.today().year - 2
    if driver_dob is None:
        driver_dob = str(date.today().replace(year=date.today().year - 35))
    return {
        "vehicle": {
            "make": "Toyota",
            "model": "Camry",
            "year": vehicle_year,
            "vin": "1HGBH41JXMN109186",
            "mileage": mileage,
        },
        "driver": {
            "firstName": "Jane",
            "lastName": "Doe",
            "dateOfBirth": driver_dob,
            "licenseNumber": "DL-12345678",
            "address": {
                "street": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "zipCode": "78701",
            },
            "drivingHistory": {
                "accidentCount": accident_count,
                "violationCount": violation_count,
                "yearsLicensed": 10,
            },
        },
        "coverageType": coverage_type,
    }


@pytest.fixture()
def valid_quote_payload() -> dict:
    """Fixture returning a valid quote creation payload."""
    return _valid_quote_payload()


@pytest.fixture()
def sample_quote(db_session: Session, test_user: User) -> Quote:
    """Insert and return a pending, non-expired quote owned by test_user."""
    quote = Quote(
        user_id=test_user.id,
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_year=date.today().year - 2,
        vehicle_vin="1HGBH41JXMN109186",
        vehicle_mileage=15000,
        driver_first_name="Jane",
        driver_last_name="Doe",
        driver_date_of_birth=date(1990, 6, 15),
        driver_license_number="DL-12345678",
        driver_address_json={
            "street": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
        },
        driver_accident_count=0,
        driver_violation_count=0,
        driver_years_licensed=10,
        coverage_type=CoverageType.BASIC,
        premium_amount=700.0,
        premium_breakdown_json=[
            {"factor": "base_rate", "value": "basic", "impact": 800.0},
            {"factor": "driver_age", "value": "35 (25-65)", "impact": -50.0},
            {"factor": "violations", "value": "0", "impact": 0.0},
            {"factor": "accidents", "value": "0", "impact": 0.0},
            {"factor": "vehicle_age", "value": "2yr (<3)", "impact": 100.0},
            {"factor": "mileage", "value": "15000 (10k-30k)", "impact": 0.0},
        ],
        status=QuoteStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)
    return quote
