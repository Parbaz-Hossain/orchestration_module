"""
Priority Rule API Endpoints
Endpoints for managing priority rules
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from orchestration.models.enums import TaskCategory, TaskType
from orchestration.schemas.orchestration_schemas import (
    PriorityRuleCreate, PriorityRuleUpdate, PriorityRuleResponse
)
from orchestration.services.priority_rule_service import PriorityRuleService
from orchestration.core.dependencies import get_current_user
from orchestration.core.database import get_async_session

router = APIRouter()


@router.post("/", response_model=PriorityRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_priority_rule(
    data: PriorityRuleCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Create a new priority rule.
    
    Rule types:
    - base_priority: Maps priority levels to scores
    - deadline_proximity: Increases score as due date approaches
    - data_condition: Adjusts score based on input data
    - time_based: Adjusts score based on current time
    - user_role: Adjusts score based on assigned role
    """
    service = PriorityRuleService(session)
    return await service.create_rule(
        data=data,
        created_by=current_user.id if current_user else 1
    )


@router.get("/", response_model=dict)
async def get_priority_rules(
    page_index: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: Optional[TaskCategory] = Query(None),
    task_type: Optional[TaskType] = Query(None),
    rule_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Get priority rules with filtering."""
    service = PriorityRuleService(session)
    return await service.get_rules(
        page_index=page_index,
        page_size=page_size,
        category=category,
        task_type=task_type,
        rule_type=rule_type,
        is_active=is_active
    )


@router.get("/{rule_id}", response_model=PriorityRuleResponse)
async def get_priority_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Get a specific priority rule by ID"""
    service = PriorityRuleService(session)
    result = await service.get_rule(rule_id)
    if not result:
        raise HTTPException(status_code=404, detail="Priority rule not found")
    return result


@router.put("/{rule_id}", response_model=PriorityRuleResponse)
async def update_priority_rule(
    rule_id: int,
    data: PriorityRuleUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Update a priority rule."""
    try:
        service = PriorityRuleService(session)
        return await service.update_rule(
            rule_id=rule_id,
            data=data,
            updated_by=current_user.id if current_user else 1
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{rule_id}")
async def delete_priority_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Delete (deactivate) a priority rule."""
    try:
        service = PriorityRuleService(session)
        result = await service.delete_rule(
            rule_id=rule_id,
            deleted_by=current_user.id if current_user else 1
        )
        if not result:
            raise HTTPException(status_code=404, detail="Priority rule not found")
        return {"message": "Priority rule deleted successfully", "success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))