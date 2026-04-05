"""Router for quoting endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.quoting import QuotingCreate, QuotingResponse
from backend.services.quoting import QuotingService

router = APIRouter()


@router.get("/", response_model=list[QuotingResponse])
async def list_quotings(
    page: int = 1,
    page_size: int = 20,
    service: QuotingService = Depends(),
) -> list[QuotingResponse]:
    """List all quotings with pagination."""
    return await service.list_all(page=page, page_size=page_size)


@router.post("/", response_model=QuotingResponse, status_code=status.HTTP_201_CREATED)
async def create_quoting(
    payload: QuotingCreate,
    service: QuotingService = Depends(),
) -> QuotingResponse:
    """Create a new quoting."""
    return await service.create(payload)


@router.get("/{item_id}", response_model=QuotingResponse)
async def get_quoting(
    item_id: UUID,
    service: QuotingService = Depends(),
) -> QuotingResponse:
    """Retrieve a quoting by ID."""
    result = await service.get_by_id(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Quoting not found")
    return result


@router.put("/{item_id}", response_model=QuotingResponse)
async def update_quoting(
    item_id: UUID,
    payload: QuotingCreate,
    service: QuotingService = Depends(),
) -> QuotingResponse:
    """Update an existing quoting."""
    result = await service.update(item_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Quoting not found")
    return result
