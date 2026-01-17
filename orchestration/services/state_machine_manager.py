"""State machine management service"""
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from orchestration.models.workflow_instance import WorkflowInstance, WorkflowStateHistory
from orchestration.schemas.session import SessionState
from orchestration.core.config import settings
from orchestration.core.exceptions import WorkflowNotFoundError, SessionExpiredError


class StateMachineManager:
    """Manages workflow state machines and sessions"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_session(
        self,
        user_id: int,
        user_role: str,
        user_name: str,
        channel: str
    ) -> SessionState:
        """Create a new user session"""
        now = datetime.utcnow()
        
        session = SessionState(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            user_role=user_role,
            user_name=user_name,
            channel=channel,
            session_start=now,
            last_activity=now,
            expires_at=now + timedelta(minutes=settings.WORKFLOW_SESSION_TIMEOUT_MINUTES)
        )
        
        # Store in Redis or database
        await self._store_session(session)
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session by ID"""
        # Implement Redis or database lookup
        session = await self._load_session(session_id)
        
        if session and session.expires_at < datetime.utcnow():
            raise SessionExpiredError(session_id)
        
        return session
    
    async def save_session(self, session: SessionState) -> None:
        """Persist session state"""
        session.last_activity = datetime.utcnow()
        await self._store_session(session)
    
    async def get_workflow(self, workflow_id: str) -> Optional[Any]:
        """Load workflow instance"""
        result = await self.db.execute(
            select(WorkflowInstance).where(WorkflowInstance.id == uuid.UUID(workflow_id))
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            return None
        
        # Reconstruct workflow state machine
        from orchestration.workflows.registry import WorkflowRegistry
        registry = WorkflowRegistry()
        
        workflow = registry.create(
            workflow_type=instance.workflow_type,
            context=instance.context_data
        )
        workflow.workflow_id = instance.id
        workflow.slot_values = instance.state_data
        workflow._set_state(instance.current_state)
        
        return workflow
    
    async def save_workflow(self, workflow: Any) -> None:
        """Persist workflow state"""
        instance = await self.db.execute(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow.workflow_id)
        )
        instance = instance.scalar_one_or_none()
        
        if instance:
            instance.current_state = workflow.current_state.id
            instance.state_data = workflow.slot_values
            instance.context_data = workflow.context
            instance.updated_at = datetime.utcnow()
            instance.version += 1
        else:
            instance = WorkflowInstance(
                id=workflow.workflow_id,
                workflow_type=workflow.workflow_type,
                user_id=workflow.context.get("user_id"),
                current_state=workflow.current_state.id,
                state_data=workflow.slot_values,
                context_data=workflow.context,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            self.db.add(instance)
        
        await self.db.flush()
    
    async def transition_workflow(self, workflow: Any) -> bool:
        """Attempt state transition and log history"""
        from_state = workflow.current_state.id
        
        try:
            workflow.send("next")
            to_state = workflow.current_state.id
            
            # Log transition
            history = WorkflowStateHistory(
                workflow_instance_id=workflow.workflow_id,
                from_state=from_state,
                to_state=to_state,
                trigger_event="next",
                event_data={"slot_values": workflow.slot_values}
            )
            self.db.add(history)
            
            return True
        except Exception:
            return False
    
    async def _store_session(self, session: SessionState) -> None:
        """Store session in cache/database"""
        # Implement Redis storage
        pass
    
    async def _load_session(self, session_id: str) -> Optional[SessionState]:
        """Load session from cache/database"""
        # Implement Redis lookup
        pass