"""Service layer for claims business logic."""

from __future__ import annotations

from uuid import UUID

from backend.models.claims import ClaimsCreate, ClaimsResponse


class ClaimsService:
    """Handles claims operations."""

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[ClaimsResponse]:
        """Return paginated list of claimss."""
        # TODO: replace with real DB query
        return []

    async def get_by_id(self, item_id: UUID) -> ClaimsResponse | None:
        """Fetch a single claims by primary key."""
        # TODO: replace with real DB query
        return None

    async def create(self, payload: ClaimsCreate) -> ClaimsResponse:
        """Persist a new claims."""
        # TODO: replace with real DB insert
        raise NotImplementedError

    async def update(self, item_id: UUID, payload: ClaimsCreate) -> ClaimsResponse | None:
        """Update an existing claims."""
        # TODO: replace with real DB update
        return None
