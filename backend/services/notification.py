"""Service layer for notification business logic."""

from __future__ import annotations

from uuid import UUID

from backend.models.notification import NotificationCreate, NotificationResponse


class NotificationService:
    """Handles notification operations."""

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[NotificationResponse]:
        """Return paginated list of notifications."""
        # TODO: replace with real DB query
        return []

    async def get_by_id(self, item_id: UUID) -> NotificationResponse | None:
        """Fetch a single notification by primary key."""
        # TODO: replace with real DB query
        return None

    async def create(self, payload: NotificationCreate) -> NotificationResponse:
        """Persist a new notification."""
        # TODO: replace with real DB insert
        raise NotImplementedError

    async def update(self, item_id: UUID, payload: NotificationCreate) -> NotificationResponse | None:
        """Update an existing notification."""
        # TODO: replace with real DB update
        return None
