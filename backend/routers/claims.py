"""Router for claims endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.claims import ClaimsCreate, ClaimsResponse
from backend.services.claims import ClaimsService

router = APIRouter()


@router.get("/", response_model=list[ClaimsResponse])
async def list_claimss(
    page: int = 1,
    page_size: int = 20,
    service: ClaimsService = Depends(),
) -> list[ClaimsResponse]:
    """List all claimss with pagination."""
    return await service.list_all(page=page, page_size=page_size)


@router.post("/", response_model=ClaimsResponse, status_code=status.HTTP_201_CREATED)
async def create_claims(
    payload: ClaimsCreate,
    service: ClaimsService = Depends(),
) -> ClaimsResponse:
    """Create a new claims."""
    return await service.create(payload)


@router.get("/{item_id}", response_model=ClaimsResponse)
async def get_claims(
    item_id: UUID,
    service: ClaimsService = Depends(),
) -> ClaimsResponse:
    """Retrieve a claims by ID."""
    result = await service.get_by_id(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Claims not found")
    return result


@router.put("/{item_id}", response_model=ClaimsResponse)
async def update_claims(
    item_id: UUID,
    payload: ClaimsCreate,
    service: ClaimsService = Depends(),
) -> ClaimsResponse:
    """Update an existing claims."""
    result = await service.update(item_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Claims not found")
    return result
