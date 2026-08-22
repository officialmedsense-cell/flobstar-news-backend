"""
API endpoints for story assignments
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.story_assignment import StoryAssignment

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_assignments(
    status: Optional[str] = None,
    assignment_type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all story assignments with optional filtering
    """
    query = select(StoryAssignment)

    if status:
        query = query.where(StoryAssignment.status == status)
    if assignment_type:
        query = query.where(StoryAssignment.assignment_type == assignment_type)
    if assigned_to:
        query = query.where(StoryAssignment.assigned_to == assigned_to)

    query = query.order_by(StoryAssignment.assigned_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    assignments = result.scalars().all()

    return [
        {
            "id": str(assignment.id),
            "story_id": str(assignment.story_id),
            "assigned_to": str(assignment.assigned_to),
            "assigned_by": str(assignment.assigned_by) if assignment.assigned_by else None,
            "assignment_type": assignment.assignment_type,
            "priority": assignment.priority,
            "status": assignment.status,
            "deadline": assignment.deadline.isoformat() if assignment.deadline else None,
            "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
            "accepted_at": assignment.accepted_at.isoformat() if assignment.accepted_at else None,
            "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
            "notes": assignment.notes,
        }
        for assignment in assignments
    ]


@router.get("/{assignment_id}", response_model=dict)
async def get_assignment(assignment_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific assignment by ID
    """
    query = select(StoryAssignment).where(StoryAssignment.id == assignment_id)
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    return {
        "id": str(assignment.id),
        "story_id": str(assignment.story_id),
        "assigned_to": str(assignment.assigned_to),
        "assigned_by": str(assignment.assigned_by) if assignment.assigned_by else None,
        "assignment_type": assignment.assignment_type,
        "priority": assignment.priority,
        "status": assignment.status,
        "deadline": assignment.deadline.isoformat() if assignment.deadline else None,
        "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
        "accepted_at": assignment.accepted_at.isoformat() if assignment.accepted_at else None,
        "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
        "notes": assignment.notes,
        "rejection_reason": assignment.rejection_reason,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
        "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None,
    }


@router.post("/", response_model=dict, status_code=201)
async def create_assignment(assignment_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Create a new story assignment
    """
    new_assignment = StoryAssignment(
        story_id=assignment_data.get("story_id"),
        assigned_to=assignment_data.get("assigned_to"),
        assigned_by=assignment_data.get("assigned_by"),
        assignment_type=assignment_data.get("assignment_type", "editorial"),
        priority=assignment_data.get("priority", "routine"),
        status=assignment_data.get("status", "assigned"),
        deadline=assignment_data.get("deadline"),
        notes=assignment_data.get("notes"),
    )

    db.add(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)

    return {
        "id": str(new_assignment.id),
        "story_id": str(new_assignment.story_id),
        "assigned_to": str(new_assignment.assigned_to),
        "status": new_assignment.status,
        "assigned_at": new_assignment.assigned_at.isoformat() if new_assignment.assigned_at else None,
    }


@router.put("/{assignment_id}", response_model=dict)
async def update_assignment(assignment_id: str, assignment_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Update an existing assignment
    """
    query = select(StoryAssignment).where(StoryAssignment.id == assignment_id)
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Update fields
    for field, value in assignment_data.items():
        if hasattr(assignment, field) and field not in ["id", "created_at", "assigned_at"]:
            setattr(assignment, field, value)

    await db.commit()
    await db.refresh(assignment)

    return {
        "id": str(assignment.id),
        "status": assignment.status,
        "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None,
    }


@router.patch("/{assignment_id}/accept", response_model=dict)
async def accept_assignment(assignment_id: str, db: AsyncSession = Depends(get_db)):
    """
    Accept a story assignment
    """
    query = select(StoryAssignment).where(StoryAssignment.id == assignment_id)
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.status != "assigned":
        raise HTTPException(status_code=400, detail="Assignment cannot be accepted in current status")

    assignment.status = "accepted"
    assignment.accepted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(assignment)

    return {
        "id": str(assignment.id),
        "status": assignment.status,
        "accepted_at": assignment.accepted_at.isoformat() if assignment.accepted_at else None,
    }


@router.patch("/{assignment_id}/complete", response_model=dict)
async def complete_assignment(assignment_id: str, completion_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Mark a story assignment as completed
    """
    query = select(StoryAssignment).where(StoryAssignment.id == assignment_id)
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.status != "accepted":
        raise HTTPException(status_code=400, detail="Assignment must be accepted before completion")

    assignment.status = "completed"
    assignment.completed_at = datetime.utcnow()
    if "notes" in completion_data:
        assignment.notes = completion_data["notes"]

    await db.commit()
    await db.refresh(assignment)

    return {
        "id": str(assignment.id),
        "status": assignment.status,
        "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
    }


@router.patch("/{assignment_id}/reject", response_model=dict)
async def reject_assignment(assignment_id: str, rejection_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Reject a story assignment
    """
    query = select(StoryAssignment).where(StoryAssignment.id == assignment_id)
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.status not in ["assigned", "accepted"]:
        raise HTTPException(status_code=400, detail="Assignment cannot be rejected in current status")

    assignment.status = "rejected"
    assignment.rejection_reason = rejection_data.get("reason", "No reason provided")

    await db.commit()
    await db.refresh(assignment)

    return {
        "id": str(assignment.id),
        "status": assignment.status,
        "rejection_reason": assignment.rejection_reason,
    }


@router.delete("/{assignment_id}", response_model=dict)
async def delete_assignment(assignment_id: str, db: AsyncSession = Depends(get_db)):
    """
    Cancel/delete a story assignment
    """
    query = select(StoryAssignment).where(StoryAssignment.id == assignment_id)
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Soft delete by cancelling
    assignment.status = "cancelled"
    await db.commit()

    return {
        "id": str(assignment.id),
        "status": "cancelled",
        "message": "Assignment cancelled successfully"
    }
