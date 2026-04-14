"""Shared test fixtures for the InsureOS backend test suite."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.auth import get_current_user, require_admin
from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    CoverageType,
    Policy,
    PolicyStatus,
    Quote,
    QuoteStatus,
    User,
    UserRole,
)

TEST_DB_URL = "sqlite:///./test_insure.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session() -> Session:
    """Provide a clean DB session."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_user(db_session: Session) -> User:
    """Create and return an admin user."""
    user = User(
        email="admin@test.com",
        full_name="Admin User",
        hashed_password="fakehash_not_used_auth_is_overridden",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def regular_user(db_session: Session) -> User:
    """Create and return a regular user."""
    user = User(
        email="user@test.com",
        full_name="John Doe",
        hashed_password="fakehash_not_used_auth_is_overridden",
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def sample_quote(db_session: Session, regular_user: User) -> Quote:
    """Create a sample quote for testing."""
    from datetime import datetime, timedelta, timezone

    quote = Quote(
        user_id=regular_user.id,
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_year=2024,
        vehicle_vin="1HGBH41JXMN109186",
        vehicle_mileage=15000,
        driver_first_name="John",
        driver_last_name="Doe",
        driver_date_of_birth=datetime(1990, 5, 15),
        driver_license_number="DL123456",
        driver_address_json={"street": "123 Main St", "city": "Austin", "state": "TX", "zipCode": "78701"},
        driver_accident_count=0,
        driver_violation_count=0,
        driver_years_licensed=10,
        coverage_type=CoverageType.BASIC,
        premium_amount=850.00,
        premium_breakdown_json=[{"factor": "base_rate", "value": "basic", "impact": 800.0}],
        status=QuoteStatus.PURCHASED,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)
    return quote


@pytest.fixture()
def active_policy(db_session: Session, regular_user: User, sample_quote: Quote) -> Policy:
    """Create an active policy."""
    from datetime import date, timedelta

    policy = Policy(
        policy_number="POL-20260406-ABCDE",
        user_id=regular_user.id,
        quote_id=sample_quote.id,
        coverage_type=CoverageType.BASIC,
        premium_amount=850.00,
        status=PolicyStatus.ACTIVE,
        effective_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture()
def admin_client(admin_user: User) -> TestClient:
    """Test client authenticated as admin."""
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_admin] = lambda: admin_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def user_client(regular_user: User) -> TestClient:
    """Test client authenticated as regular user."""
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: regular_user

    def _deny_admin():
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    app.dependency_overrides[require_admin] = _deny_admin
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def unauth_client() -> TestClient:
    """Test client with no auth."""
    app.dependency_overrides[get_db] = _override_get_db
    # Don't override auth — will use real dependency which requires token
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
