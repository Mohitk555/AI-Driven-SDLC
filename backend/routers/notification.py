"""Router for notification endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.notification import NotificationCreate, NotificationResponse
from backend.services.notification import NotificationService

router = APIRouter()


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    service: NotificationService = Depends(),
) -> list[NotificationResponse]:
    """List all notifications with pagination."""
    return await service.list_all(page=page, page_size=page_size)


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: NotificationCreate,
    service: NotificationService = Depends(),
) -> NotificationResponse:
    """Create a new notification."""
    return await service.create(payload)


@router.get("/{item_id}", response_model=NotificationResponse)
async def get_notification(
    item_id: UUID,
    service: NotificationService = Depends(),
) -> NotificationResponse:
    """Retrieve a notification by ID."""
    result = await service.get_by_id(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@router.put("/{item_id}", response_model=NotificationResponse)
async def update_notification(
    item_id: UUID,
    payload: NotificationCreate,
    service: NotificationService = Depends(),
) -> NotificationResponse:
    """Update an existing notification."""
    result = await service.update(item_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result
