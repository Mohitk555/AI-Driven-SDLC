"""Service layer for auth business logic."""

from __future__ import annotations

from uuid import UUID

from backend.models.auth import AuthCreate, AuthResponse


class AuthService:
    """Handles auth operations."""

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[AuthResponse]:
        """Return paginated list of auths."""
        # TODO: replace with real DB query
        return []

    async def get_by_id(self, item_id: UUID) -> AuthResponse | None:
        """Fetch a single auth by primary key."""
        # TODO: replace with real DB query
        return None

    async def create(self, payload: AuthCreate) -> AuthResponse:
        """Persist a new auth."""
        # TODO: replace with real DB insert
        raise NotImplementedError

    async def update(self, item_id: UUID, payload: AuthCreate) -> AuthResponse | None:
        """Update an existing auth."""
        # TODO: replace with real DB update
        return None
