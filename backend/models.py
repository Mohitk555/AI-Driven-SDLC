"""SQLAlchemy ORM models for the Claims Management system."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"


class ClaimType(str, enum.Enum):
    """Claim type enumeration."""
    AUTO = "auto"
    HEALTH = "health"
    PROPERTY = "property"
    LIFE = "life"


class ClaimStatus(str, enum.Enum):
    """Claim status enumeration."""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    INFO_REQUIRED = "info_required"


class CoverageType(str, enum.Enum):
    """Coverage type enumeration."""
    BASIC = "basic"
    FULL = "full"


class QuoteStatus(str, enum.Enum):
    """Quote status enumeration."""
    PENDING = "pending"
    PURCHASED = "purchased"
    EXPIRED = "expired"


class PolicyStatus(str, enum.Enum):
    """Policy status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REINSTATED = "reinstated"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    filed_claims: Mapped[list["Claim"]] = relationship(
        back_populates="filed_by_user", foreign_keys="Claim.filed_by"
    )
    assigned_claims: Mapped[list["Claim"]] = relationship(
        back_populates="assigned_to_user", foreign_keys="Claim.assigned_to"
    )
    documents: Mapped[list["Document"]] = relationship(back_populates="uploaded_by_user")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="user")
    policies: Mapped[list["Policy"]] = relationship(back_populates="user")


class Claim(Base):
    """Insurance claim model."""

    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    claim_type: Mapped[ClaimType] = mapped_column(Enum(ClaimType), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus), default=ClaimStatus.SUBMITTED, nullable=False
    )
    filed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    filed_by_user: Mapped["User"] = relationship(
        back_populates="filed_claims", foreign_keys=[filed_by]
    )
    assigned_to_user: Mapped["User | None"] = relationship(
        back_populates="assigned_claims", foreign_keys=[assigned_to]
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ClaimStatusHistory"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimStatusHistory.changed_at"
    )


class Document(Base):
    """Document attached to a claim."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    claim: Mapped["Claim"] = relationship(back_populates="documents")
    uploaded_by_user: Mapped["User"] = relationship(back_populates="documents")


class ClaimStatusHistory(Base):
    """Tracks status changes for audit trail."""

    __tablename__ = "claim_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    claim: Mapped["Claim"] = relationship(back_populates="status_history")
    changed_by_user: Mapped["User"] = relationship()


class Quote(Base):
    """Auto insurance quote model."""

    __tablename__ = "quotes"
    __table_args__ = (
        Index("idx_quotes_user_id", "user_id"),
        Index("idx_quotes_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_make: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_year: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_vin: Mapped[str] = mapped_column(String(17), nullable=False)
    vehicle_mileage: Mapped[int] = mapped_column(Integer, nullable=False)
    driver_first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    driver_last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    driver_date_of_birth: Mapped[datetime] = mapped_column(Date, nullable=False)
    driver_license_number: Mapped[str] = mapped_column(String(50), nullable=False)
    driver_address_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    driver_accident_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    driver_violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    driver_years_licensed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coverage_type: Mapped[CoverageType] = mapped_column(Enum(CoverageType), nullable=False)
    premium_amount: Mapped[float] = mapped_column(Float, nullable=False)
    premium_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[QuoteStatus] = mapped_column(
        Enum(QuoteStatus), default=QuoteStatus.PENDING, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="quotes")
    policy: Mapped["Policy | None"] = relationship(back_populates="quote", uselist=False)


class Policy(Base):
    """Auto insurance policy model."""

    __tablename__ = "policies"
    __table_args__ = (
        Index("idx_policies_user_id", "user_id"),
        Index("idx_policies_policy_number", "policy_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    quote_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotes.id"), nullable=False)
    coverage_type: Mapped[CoverageType] = mapped_column(Enum(CoverageType), nullable=False)
    premium_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus), default=PolicyStatus.ACTIVE, nullable=False
    )
    effective_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    renewed_from_policy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("policies.id"), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reinstatement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reinstatement_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    renewal_premium_breakdown_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="policies")
    quote: Mapped["Quote"] = relationship(back_populates="policy")
    renewed_from: Mapped["Policy | None"] = relationship(
        remote_side="Policy.id", foreign_keys=[renewed_from_policy_id]
    )


class AuditLog(Base):
    """Generic audit log for tracking entity changes."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class RiskRule(Base):
    """Configurable risk rule for premium calculation."""

    __tablename__ = "risk_rules"
    __table_args__ = (
        Index("idx_risk_rules_factor_name", "factor_name"),
        Index("idx_risk_rules_is_enabled", "is_enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    factor_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    brackets_json: Mapped[list] = mapped_column(JSON, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
