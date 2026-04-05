"""Router for document endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.document import DocumentCreate, DocumentResponse
from backend.services.document import DocumentService

router = APIRouter()


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    service: DocumentService = Depends(),
) -> list[DocumentResponse]:
    """List all documents with pagination."""
    return await service.list_all(page=page, page_size=page_size)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    service: DocumentService = Depends(),
) -> DocumentResponse:
    """Create a new document."""
    return await service.create(payload)


@router.get("/{item_id}", response_model=DocumentResponse)
async def get_document(
    item_id: UUID,
    service: DocumentService = Depends(),
) -> DocumentResponse:
    """Retrieve a document by ID."""
    result = await service.get_by_id(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.put("/{item_id}", response_model=DocumentResponse)
async def update_document(
    item_id: UUID,
    payload: DocumentCreate,
    service: DocumentService = Depends(),
) -> DocumentResponse:
    """Update an existing document."""
    result = await service.update(item_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result
