"""Shared FastAPI dependencies (DB session, current user, etc.)."""

from __future__ import annotations

from typing import AsyncGenerator


async def get_db() -> AsyncGenerator[None, None]:
    """Yield a database session.  Placeholder until SQLAlchemy is wired."""
    # TODO: wire up async SQLAlchemy session
    yield None
