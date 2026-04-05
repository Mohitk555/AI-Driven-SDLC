"""Service layer for quoting business logic."""

from __future__ import annotations

from uuid import UUID

from backend.models.quoting import QuotingCreate, QuotingResponse


class QuotingService:
    """Handles quoting operations."""

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[QuotingResponse]:
        """Return paginated list of quotings."""
        # TODO: replace with real DB query
        return []

    async def get_by_id(self, item_id: UUID) -> QuotingResponse | None:
        """Fetch a single quoting by primary key."""
        # TODO: replace with real DB query
        return None

    async def create(self, payload: QuotingCreate) -> QuotingResponse:
        """Persist a new quoting."""
        # TODO: replace with real DB insert
        raise NotImplementedError

    async def update(self, item_id: UUID, payload: QuotingCreate) -> QuotingResponse | None:
        """Update an existing quoting."""
        # TODO: replace with real DB update
        return None
