"""
Workflow Template API Endpoints
Endpoints for managing workflow templates
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from orchestration.models.enums import AgentRole, TaskCategory, TaskType
from orchestration.schemas.orchestration_schemas import (
    WorkflowTemplateCreate, WorkflowTemplateUpdate, 
    WorkflowTemplateResponse, WorkflowTemplateSummary
)
from orchestration.services.workflow_template_service import WorkflowTemplateService
from orchestration.core.dependencies import get_current_user
from orchestration.core.database import get_async_session

router = APIRouter(prefix="/orchestrator/templates", tags=["Workflow Templates"])


@router.post("/", response_model=WorkflowTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_template(
    data: WorkflowTemplateCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Create a new workflow template."""
    service = WorkflowTemplateService(session)
    return await service.create_template(
        data=data,
        created_by=current_user.id if current_user else 1
    )


@router.get("/", response_model=dict)
async def get_workflow_templates(
    page_index: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: Optional[TaskCategory] = Query(None),
    task_type: Optional[TaskType] = Query(None),
    role: Optional[AgentRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Get workflow templates with filtering and pagination."""
    service = WorkflowTemplateService(session)
    return await service.get_templates(
        page_index=page_index,
        page_size=page_size,
        category=category,
        task_type=task_type,
        role=role,
        is_active=is_active,
        search=search
    )


@router.get("/{template_id}", response_model=WorkflowTemplateResponse)
async def get_workflow_template(
    template_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Get a specific workflow template by ID"""
    service = WorkflowTemplateService(session)
    result = await service.get_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.put("/{template_id}", response_model=WorkflowTemplateResponse)
async def update_workflow_template(
    template_id: int,
    data: WorkflowTemplateUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
):
    """Update a workflow template."""
    try:
        service = WorkflowTemplateService(session)
        return await service.update_template(
            template_id=template_id,
            data=data,
            updated_by=current_user.id if current_user else 1
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}")
async def delete_workflow_template(
    template_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
):
    """Delete (deactivate) a workflow template."""
    try:
        service = WorkflowTemplateService(session)
        result = await service.delete_template(
            template_id=template_id,
            deleted_by=current_user.id if current_user else 1
        )
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"message": "Template deleted successfully", "success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))