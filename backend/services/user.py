"""Service layer for user business logic."""

from __future__ import annotations

from uuid import UUID

from backend.models.user import UserCreate, UserResponse


class UserService:
    """Handles user operations."""

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[UserResponse]:
        """Return paginated list of users."""
        # TODO: replace with real DB query
        return []

    async def get_by_id(self, item_id: UUID) -> UserResponse | None:
        """Fetch a single user by primary key."""
        # TODO: replace with real DB query
        return None

    async def create(self, payload: UserCreate) -> UserResponse:
        """Persist a new user."""
        # TODO: replace with real DB insert
        raise NotImplementedError

    async def update(self, item_id: UUID, payload: UserCreate) -> UserResponse | None:
        """Update an existing user."""
        # TODO: replace with real DB update
        return None
