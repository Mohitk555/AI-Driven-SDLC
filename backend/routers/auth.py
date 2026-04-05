"""Router for auth endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.auth import AuthCreate, AuthResponse
from backend.services.auth import AuthService

router = APIRouter()


@router.get("/", response_model=list[AuthResponse])
async def list_auths(
    page: int = 1,
    page_size: int = 20,
    service: AuthService = Depends(),
) -> list[AuthResponse]:
    """List all auths with pagination."""
    return await service.list_all(page=page, page_size=page_size)


@router.post("/", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def create_auth(
    payload: AuthCreate,
    service: AuthService = Depends(),
) -> AuthResponse:
    """Create a new auth."""
    return await service.create(payload)


@router.get("/{item_id}", response_model=AuthResponse)
async def get_auth(
    item_id: UUID,
    service: AuthService = Depends(),
) -> AuthResponse:
    """Retrieve a auth by ID."""
    result = await service.get_by_id(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Auth not found")
    return result


@router.put("/{item_id}", response_model=AuthResponse)
async def update_auth(
    item_id: UUID,
    payload: AuthCreate,
    service: AuthService = Depends(),
) -> AuthResponse:
    """Update an existing auth."""
    result = await service.update(item_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Auth not found")
    return result
