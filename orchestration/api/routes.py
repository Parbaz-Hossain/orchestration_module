"""HTTP API routes"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from orchestration.core.dependencies import get_orchestrator, DbSession
from orchestration.services.orchestrator import OrchestrationEngine
from orchestration.schemas.session import SessionState
from orchestration.schemas.instructions import InstructionPayload


router = APIRouter(tags=["Orchestration"])


class SessionInitRequest(BaseModel):
    """Request to initialize a session"""
    user_id: int
    user_role: str
    user_name: str
    channel: str = "web"


class SessionInitResponse(BaseModel):
    """Response with session and first instruction"""
    session: SessionState
    instruction: InstructionPayload


@router.post("/sessions/init", response_model=SessionInitResponse)
async def initialize_session(
    request: SessionInitRequest,
    orchestrator: Annotated[OrchestrationEngine, Depends(get_orchestrator)]
):
    """Initialize a new user session"""
    session, instruction = await orchestrator.initialize_session(
        user_id=request.user_id,
        user_role=request.user_role,
        user_name=request.user_name,
        channel=request.channel
    )
    
    return SessionInitResponse(session=session, instruction=instruction)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    orchestrator: Annotated[OrchestrationEngine, Depends(get_orchestrator)]
):
    """Get current session state"""
    session = await orchestrator.state_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session


@router.get("/work/{user_id}/{role}")
async def get_pending_work(
    user_id: int,
    role: str,
    orchestrator: Annotated[OrchestrationEngine, Depends(get_orchestrator)]
):
    """Get prioritized pending work for a user"""
    work_items = await orchestrator.work_detector.get_prioritized_work(user_id, role)
    return {"items": work_items, "count": len(work_items)}


@router.get("/workflows/types")
async def get_workflow_types():
    """Get available workflow types"""
    from orchestration.workflows.registry import WorkflowRegistry
    return {"types": WorkflowRegistry.get_available_types()}