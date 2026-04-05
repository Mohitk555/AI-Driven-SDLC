"""SQLAlchemy ORM models for the Claims Management system."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
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
