"""Router for policy endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.policy import PolicyCreate, PolicyResponse
from backend.services.policy import PolicyService

router = APIRouter()


@router.get("/", response_model=list[PolicyResponse])
async def list_policys(
    page: int = 1,
    page_size: int = 20,
    service: PolicyService = Depends(),
) -> list[PolicyResponse]:
    """List all policys with pagination."""
    return await service.list_all(page=page, page_size=page_size)


@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: PolicyCreate,
    service: PolicyService = Depends(),
) -> PolicyResponse:
    """Create a new policy."""
    return await service.create(payload)


@router.get("/{item_id}", response_model=PolicyResponse)
async def get_policy(
    item_id: UUID,
    service: PolicyService = Depends(),
) -> PolicyResponse:
    """Retrieve a policy by ID."""
    result = await service.get_by_id(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


@router.put("/{item_id}", response_model=PolicyResponse)
async def update_policy(
    item_id: UUID,
    payload: PolicyCreate,
    service: PolicyService = Depends(),
) -> PolicyResponse:
    """Update an existing policy."""
    result = await service.update(item_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result
