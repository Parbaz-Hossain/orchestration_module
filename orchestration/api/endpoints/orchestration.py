"""
Orchestration API Endpoints
Main endpoints for the orchestration module
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

# These imports would come from your existing app structure
from orchestration.core.dependencies import get_current_user
from orchestration.core.database import get_async_session

from orchestration.models.enums import AgentRole, TaskCategory, TaskType, WorkItemStatus, WorkItemPriority
from orchestration.schemas.orchestration_schemas import (
    OrchestratorSessionStart, OrchestratorSessionResponse,
    WorkItemCreate, WorkItemUpdate, WorkItemResponse, WorkItemSummary,
    TaskExecutionRequest, TaskExecutionResponse,
    SuggestionResponse
)
from orchestration.services.orchestrator_service import OrchestratorService
from orchestration.services.work_item_service import WorkItemService

router = APIRouter()


# ==================== SESSION ENDPOINTS ====================

@router.post("/session/start", response_model=OrchestratorSessionResponse)
async def start_orchestrator_session(
    request: OrchestratorSessionStart,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Start an orchestrator session when user logs in.
    
    This is the main entry point for the AI orchestration system.
    It:
    1. Checks for pending work items for the user's role
    2. If no pending tasks, generates AI suggestions
    3. Returns available workflow templates
    4. Provides dashboard metrics
    
    The frontend should call this endpoint after user authentication
    to initialize the AI assistant experience.
    """
    service = OrchestratorService(session)
    return await service.start_session(request)


@router.get("/session/refresh", response_model=OrchestratorSessionResponse)
async def refresh_session(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Refresh the current session data.
    
    Call this to get updated pending tasks, suggestions, and metrics
    without creating a new session.
    """
    # Get user's role from their profile or token
    role = AgentRole.HR_MANAGER  # This would come from current_user
    
    request = OrchestratorSessionStart(
        user_id=current_user.id if current_user else 1,
        role=role
    )
    
    service = OrchestratorService(session)
    return await service.start_session(request)


# ==================== WORK ITEM ENDPOINTS ====================

@router.post("/work-items", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED)
async def create_work_item(
    data: WorkItemCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Create a new work item from a workflow template.
    
    This creates a task instance that will be processed by the
    orchestration engine and relevant AI agents.
    """
    service = WorkItemService(session)
    return await service.create_work_item(
        data=data,
        created_by=current_user.id if current_user else 1
    )


@router.get("/work-items", response_model=dict)
async def get_work_items(
    page_index: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: Optional[TaskCategory] = Query(None),
    task_type: Optional[TaskType] = Query(None),
    status: Optional[WorkItemStatus] = Query(None),
    priority: Optional[WorkItemPriority] = Query(None),
    is_suggestion: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("priority_score"),
    sort_order: str = Query("desc"),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Get work items with filtering and pagination.
    
    By default, returns items sorted by priority_score descending
    (highest priority first).
    """
    role = AgentRole.HR_MANAGER  # From current_user
    
    service = WorkItemService(session)
    return await service.get_work_items(
        page_index=page_index,
        page_size=page_size,
        role=role,
        user_id=current_user.id if current_user else None,
        category=category,
        task_type=task_type,
        status=status,
        priority=priority,
        is_suggestion=is_suggestion,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/work-items/pending", response_model=List[WorkItemSummary])
async def get_pending_work_items(
    limit: int = Query(50, ge=1, le=100),
    category: Optional[TaskCategory] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Get pending work items for the current user's role.
    
    Returns items that are PENDING, IN_PROGRESS, or AWAITING_INPUT,
    sorted by priority score (highest first).
    """
    role = AgentRole.HR_MANAGER  # From current_user
    
    service = WorkItemService(session)
    return await service.get_pending_for_role(
        role=role,
        user_id=current_user.id if current_user else None,
        limit=limit
    )


@router.get("/work-items/{work_item_id}", response_model=WorkItemResponse)
async def get_work_item(
    work_item_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Get a specific work item by ID"""
    service = WorkItemService(session)
    result = await service.get_work_item(work_item_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Work item not found")
    
    return result


@router.put("/work-items/{work_item_id}", response_model=WorkItemResponse)
async def update_work_item(
    work_item_id: int,
    data: WorkItemUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Update a work item"""
    service = WorkItemService(session)
    return await service.update_work_item(
        work_item_id=work_item_id,
        data=data,
        updated_by=current_user.id if current_user else 1
    )


@router.post("/work-items/{work_item_id}/status/{new_status}", response_model=WorkItemResponse)
async def update_work_item_status(
    work_item_id: int,
    new_status: WorkItemStatus,
    error_message: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Update work item status.
    
    Status transitions:
    - PENDING -> IN_PROGRESS (when work starts)
    - IN_PROGRESS -> AWAITING_INPUT (when user input needed)
    - IN_PROGRESS -> COMPLETED (when finished successfully)
    - IN_PROGRESS -> FAILED (when error occurs)
    - Any -> CANCELLED (when user cancels)
    """
    service = WorkItemService(session)
    return await service.update_status(
        work_item_id=work_item_id,
        new_status=new_status,
        updated_by=current_user.id if current_user else 1,
        error_message=error_message
    )


@router.get("/work-items/{work_item_id}/logs")
async def get_work_item_logs(
    work_item_id: int,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Get execution logs for a work item"""
    service = WorkItemService(session)
    return await service.get_execution_logs(work_item_id, limit)


# ==================== SUGGESTION ENDPOINTS ====================

@router.get("/suggestions", response_model=List[SuggestionResponse])
async def get_suggestions(
    limit: int = Query(5, ge=1, le=20),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Get AI-generated task suggestions for the current user.
    
    Suggestions are based on:
    - User's role and permissions
    - Current time (e.g., salary generation on 1st of month)
    - Pending data conditions (e.g., unprocessed attendance)
    - Historical patterns
    """
    role = AgentRole.HR_MANAGER  # From current_user
    
    service = OrchestratorService(session)
    
    # Get current pending tasks to avoid duplicate suggestions
    work_item_service = WorkItemService(session)
    pending = await work_item_service.get_pending_for_role(role, current_user.id if current_user else None)
    existing_codes = [item.template_code for item in pending]
    
    return await service.generate_suggestions(
        role=role,
        user_id=current_user.id if current_user else 1,
        existing_tasks=existing_codes,
        limit=limit
    )


@router.post("/suggestions/{suggestion_id}/accept", response_model=WorkItemResponse)
async def accept_suggestion(
    suggestion_id: int,
    input_data: Optional[dict] = None,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Accept a suggestion and create a work item from it.
    
    This creates a new work item based on the suggestion's template
    and optional input data provided.
    """
    # Get suggestion rule to find template
    from ..models.orchestration_models import SuggestionRule
    from sqlalchemy import select
    
    result = await session.execute(
        select(SuggestionRule).where(SuggestionRule.id == suggestion_id)
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    # Get template
    from orchestration.models.orchestration_models import WorkflowTemplate
    template_result = await session.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == rule.template_id)
    )
    template = template_result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Update suggestion metrics
    rule.times_accepted += 1
    
    # Create work item
    work_item_data = WorkItemCreate(
        template_code=template.code,
        title=rule.suggestion_title,
        description=rule.suggestion_message,
        priority=rule.suggestion_priority,
        input_data=input_data or rule.default_input_data or {},
        is_suggestion=True
    )
    
    service = WorkItemService(session)
    return await service.create_work_item(
        data=work_item_data,
        created_by=current_user.id if current_user else 1
    )


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    suggestion_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Dismiss a suggestion.
    
    The suggestion won't be shown again for the configured time period.
    """
    from orchestration.models.orchestration_models import SuggestionRule
    from sqlalchemy import select
    
    result = await session.execute(
        select(SuggestionRule).where(SuggestionRule.id == suggestion_id)
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if not rule.is_dismissible:
        raise HTTPException(status_code=400, detail="This suggestion cannot be dismissed")
    
    rule.times_dismissed += 1
    await session.commit()
    
    return {"message": "Suggestion dismissed", "success": True}


# ==================== TASK EXECUTION ENDPOINTS ====================

@router.post("/execute", response_model=TaskExecutionResponse)
async def execute_task(
    request: TaskExecutionRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Execute a task through the orchestration engine.
    
    This is the main endpoint for running workflows.
    It can:
    1. Execute an existing work item (by work_item_id)
    2. Create and execute a new work item (by template_code)
    
    The execution engine will:
    - Validate input against the workflow template schema
    - Run business rules validation
    - Execute workflow steps in order
    - Call appropriate AI agents for decision-making
    - Return results or request additional input
    """
    # This would be implemented by the Execution Engine service
    # For now, return a placeholder response
    
    work_item_id = request.work_item_id
    
    if not work_item_id and request.template_code:
        # Create new work item
        service = WorkItemService(session)
        work_item = await service.create_work_item(
            data=WorkItemCreate(
                template_code=request.template_code,
                title=f"Task from {request.template_code}",
                input_data=request.input_data
            ),
            created_by=current_user.id if current_user else 1
        )
        work_item_id = work_item.id
    
    if not work_item_id:
        raise HTTPException(
            status_code=400, 
            detail="Either work_item_id or template_code must be provided"
        )
    
    # Get work item
    service = WorkItemService(session)
    work_item = await service.get_work_item(work_item_id)
    
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")
    
    # Return execution response
    # In a full implementation, this would run the actual workflow
    return TaskExecutionResponse(
        work_item_id=work_item_id,
        status=work_item.status,
        current_step=work_item.current_step,
        total_steps=len(work_item.step_results) + 1,
        step_name="Validation",
        requires_input=False,
        requires_confirmation=work_item.execution_mode.value == "semi_automatic",
        confirmation_message="Ready to execute. Please confirm to proceed.",
        message="Task ready for execution",
        next_action="confirm" if work_item.execution_mode.value == "semi_automatic" else "execute"
    )


@router.post("/execute/{work_item_id}/confirm", response_model=TaskExecutionResponse)
async def confirm_execution(
    work_item_id: int,
    confirmed: bool = True,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Confirm execution for semi-automatic tasks.
    
    When a task is in SEMI_AUTOMATIC mode, the AI prepares everything
    but waits for user confirmation before executing.
    """
    if not confirmed:
        # Update status to cancelled
        service = WorkItemService(session)
        return await service.update_status(
            work_item_id=work_item_id,
            new_status=WorkItemStatus.CANCELLED,
            updated_by=current_user.id if current_user else 1
        )
    
    # Proceed with execution
    # This would trigger the actual workflow execution
    service = WorkItemService(session)
    work_item = await service.update_status(
        work_item_id=work_item_id,
        new_status=WorkItemStatus.IN_PROGRESS,
        updated_by=current_user.id if current_user else 1
    )
    
    return TaskExecutionResponse(
        work_item_id=work_item_id,
        status=work_item.status,
        current_step=1,
        total_steps=3,  # This would come from the template
        step_name="Executing",
        requires_input=False,
        requires_confirmation=False,
        message="Execution started",
        next_action="monitor"
    )


@router.post("/execute/{work_item_id}/input", response_model=TaskExecutionResponse)
async def provide_input(
    work_item_id: int,
    input_data: dict,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Provide additional input for a task that's awaiting input.
    
    When a workflow step requires user input (USER_INPUT step type),
    the task enters AWAITING_INPUT status. This endpoint allows
    the user to provide the required data.
    """
    service = WorkItemService(session)
    work_item = await service.get_work_item(work_item_id)
    
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")
    
    if work_item.status != WorkItemStatus.AWAITING_INPUT:
        raise HTTPException(
            status_code=400, 
            detail=f"Work item is not awaiting input. Current status: {work_item.status}"
        )
    
    # Merge input data
    current_input = work_item.input_data or {}
    current_input.update(input_data)
    
    # Update work item
    updated = await service.update_work_item(
        work_item_id=work_item_id,
        data=WorkItemUpdate(
            input_data=current_input,
            status=WorkItemStatus.IN_PROGRESS
        ),
        updated_by=current_user.id if current_user else 1
    )
    
    return TaskExecutionResponse(
        work_item_id=work_item_id,
        status=updated.status,
        current_step=updated.current_step + 1,
        total_steps=3,
        step_name="Processing Input",
        requires_input=False,
        requires_confirmation=False,
        message="Input received, continuing execution",
        next_action="monitor"
    )