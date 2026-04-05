"""Service layer for policy business logic."""

from __future__ import annotations

from uuid import UUID

from backend.models.policy import PolicyCreate, PolicyResponse


class PolicyService:
    """Handles policy operations."""

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[PolicyResponse]:
        """Return paginated list of policys."""
        # TODO: replace with real DB query
        return []

    async def get_by_id(self, item_id: UUID) -> PolicyResponse | None:
        """Fetch a single policy by primary key."""
        # TODO: replace with real DB query
        return None

    async def create(self, payload: PolicyCreate) -> PolicyResponse:
        """Persist a new policy."""
        # TODO: replace with real DB insert
        raise NotImplementedError

    async def update(self, item_id: UUID, payload: PolicyCreate) -> PolicyResponse | None:
        """Update an existing policy."""
        # TODO: replace with real DB update
        return None
