"""
API endpoints for notifications
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.news_notification import NewsNotification

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_notifications(
    recipient_id: str,
    notification_type: Optional[str] = None,
    read_status: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List notifications for a specific user
    """
    query = select(NewsNotification).where(NewsNotification.recipient_id == recipient_id)

    if notification_type:
        query = query.where(NewsNotification.notification_type == notification_type)
    if read_status is not None:
        query = query.where(NewsNotification.read_status == read_status)

    query = query.order_by(NewsNotification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        {
            "id": str(notification.id),
            "recipient_id": str(notification.recipient_id),
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority,
            "story_id": str(notification.story_id) if notification.story_id else None,
            "assignment_id": str(notification.assignment_id) if notification.assignment_id else None,
            "source_id": str(notification.source_id) if notification.source_id else None,
            "action_url": notification.action_url,
            "action_label": notification.action_label,
            "channels": notification.channels,
            "delivery_status": notification.delivery_status,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "read_status": notification.read_status,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        }
        for notification in notifications
    ]


@router.get("/{notification_id}", response_model=dict)
async def get_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific notification by ID
    """
    query = select(NewsNotification).where(NewsNotification.id == notification_id)
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {
        "id": str(notification.id),
        "recipient_id": str(notification.recipient_id),
        "notification_type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "priority": notification.priority,
        "story_id": str(notification.story_id) if notification.story_id else None,
        "assignment_id": str(notification.assignment_id) if notification.assignment_id else None,
        "source_id": str(notification.source_id) if notification.source_id else None,
        "action_url": notification.action_url,
        "action_label": notification.action_label,
        "channels": notification.channels,
        "delivery_status": notification.delivery_status,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "read_status": notification.read_status,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "updated_at": notification.updated_at.isoformat() if notification.updated_at else None,
    }


@router.post("/", response_model=dict, status_code=201)
async def create_notification(notification_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Create a new notification
    """
    new_notification = NewsNotification(
        recipient_id=notification_data.get("recipient_id"),
        notification_type=notification_data.get("notification_type"),
        title=notification_data.get("title"),
        message=notification_data.get("message"),
        priority=notification_data.get("priority", "normal"),
        story_id=notification_data.get("story_id"),
        assignment_id=notification_data.get("assignment_id"),
        source_id=notification_data.get("source_id"),
        action_url=notification_data.get("action_url"),
        action_label=notification_data.get("action_label"),
        channels=notification_data.get("channels", ["in_app"]),
        delivery_status=notification_data.get("delivery_status", "pending"),
    )

    db.add(new_notification)
    await db.commit()
    await db.refresh(new_notification)

    return {
        "id": str(new_notification.id),
        "recipient_id": str(new_notification.recipient_id),
        "notification_type": new_notification.notification_type,
        "title": new_notification.title,
        "created_at": new_notification.created_at.isoformat() if new_notification.created_at else None,
    }


@router.patch("/{notification_id}/read", response_model=dict)
async def mark_notification_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    """
    Mark a notification as read
    """
    query = select(NewsNotification).where(NewsNotification.id == notification_id)
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read_status = True
    notification.read_at = datetime.utcnow()

    await db.commit()
    await db.refresh(notification)

    return {
        "id": str(notification.id),
        "read_status": notification.read_status,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
    }


@router.patch("/recipient/{recipient_id}/read-all", response_model=dict)
async def mark_all_notifications_read(recipient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Mark all notifications for a user as read
    """
    query = select(NewsNotification).where(
        and_(
            NewsNotification.recipient_id == recipient_id,
            NewsNotification.read_status == False
        )
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    for notification in notifications:
        notification.read_status = True
        notification.read_at = datetime.utcnow()

    await db.commit()

    return {
        "recipient_id": recipient_id,
        "marked_as_read": len(notifications),
        "message": f"Marked {len(notifications)} notifications as read"
    }


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a notification
    """
    query = select(NewsNotification).where(NewsNotification.id == notification_id)
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()

    return {
        "id": str(notification_id),
        "message": "Notification deleted successfully"
    }


@router.get("/recipient/{recipient_id}/unread-count", response_model=dict)
async def get_unread_count(recipient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get the count of unread notifications for a user
    """
    query = select(func.count(NewsNotification.id)).where(
        and_(
            NewsNotification.recipient_id == recipient_id,
            NewsNotification.read_status == False
        )
    )
    result = await db.execute(query)
    count = result.scalar()

    return {
        "recipient_id": recipient_id,
        "unread_count": count,
    }
