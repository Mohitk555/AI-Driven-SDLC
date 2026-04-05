"""Service layer for document business logic."""

from __future__ import annotations

from uuid import UUID

from backend.models.document import DocumentCreate, DocumentResponse


class DocumentService:
    """Handles document operations."""

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[DocumentResponse]:
        """Return paginated list of documents."""
        # TODO: replace with real DB query
        return []

    async def get_by_id(self, item_id: UUID) -> DocumentResponse | None:
        """Fetch a single document by primary key."""
        # TODO: replace with real DB query
        return None

    async def create(self, payload: DocumentCreate) -> DocumentResponse:
        """Persist a new document."""
        # TODO: replace with real DB insert
        raise NotImplementedError

    async def update(self, item_id: UUID, payload: DocumentCreate) -> DocumentResponse | None:
        """Update an existing document."""
        # TODO: replace with real DB update
        return None
