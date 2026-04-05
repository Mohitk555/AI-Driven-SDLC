"""Router for user endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.user import UserCreate, UserResponse
from backend.services.user import UserService

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    service: UserService = Depends(),
) -> list[UserResponse]:
    """List all users with pagination."""
    return await service.list_all(page=page, page_size=page_size)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(),
) -> UserResponse:
    """Create a new user."""
    return await service.create(payload)


@router.get("/{item_id}", response_model=UserResponse)
async def get_user(
    item_id: UUID,
    service: UserService = Depends(),
) -> UserResponse:
    """Retrieve a user by ID."""
    result = await service.get_by_id(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put("/{item_id}", response_model=UserResponse)
async def update_user(
    item_id: UUID,
    payload: UserCreate,
    service: UserService = Depends(),
) -> UserResponse:
    """Update an existing user."""
    result = await service.update(item_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result
