"""Main orchestration engine - the brain of the system"""
import uuid
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from orchestration.schemas.instructions import InstructionPayload, InstructionType
from orchestration.schemas.responses import AgentToBackendMessage, UserResponseType
from orchestration.schemas.session import SessionState, PausedTask
from orchestration.core.exceptions import WorkflowNotFoundError, SessionExpiredError


class OrchestrationEngine:
    """Main orchestration coordinator - the 'brain' of the system"""
    
    def __init__(
        self,
        db: AsyncSession,
        work_detector: "WorkDetectionService",
        priority_calc: "PriorityCalculator",
        state_manager: "StateMachineManager",
        saga_orchestrator: "SagaOrchestrator",
        event_emitter: "EventEmitter",
        workflow_registry: "WorkflowRegistry"
    ):
        self.db = db
        self.work_detector = work_detector
        self.priority_calc = priority_calc
        self.state_manager = state_manager
        self.saga = saga_orchestrator
        self.events = event_emitter
        self.workflows = workflow_registry
    
    async def initialize_session(
        self, 
        user_id: int, 
        user_role: str,
        user_name: str,
        channel: str = "web"
    ) -> Tuple[SessionState, InstructionPayload]:
        """Initialize new session and determine first instruction"""
        
        # Create session
        session = await self.state_manager.create_session(
            user_id=user_id,
            user_role=user_role,
            user_name=user_name,
            channel=channel
        )
        
        # Detect prioritized work for this role
        pending_work = await self.work_detector.get_prioritized_work(user_id, user_role)
        
        # Update session with pending work info
        session.pending_work_count = len(pending_work)
        session.current_priority_items = pending_work[:5]  # Top 5
        
        # Generate greeting with priorities
        instruction = self._generate_greeting(session, pending_work)
        
        # Log session start
        await self.events.emit(
            event_type="session.started",
            data={
                "user_id": user_id,
                "role": user_role,
                "channel": channel,
                "pending_work_count": len(pending_work)
            },
            actor=str(user_id),
            correlation_id=session.session_id
        )
        
        return session, instruction
    
    async def process_user_response(
        self,
        session_id: str,
        response: AgentToBackendMessage
    ) -> InstructionPayload:
        """Process user response and generate next instruction"""
        
        # Load session state
        session = await self.state_manager.get_session(session_id)
        if not session:
            raise SessionExpiredError(session_id)
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        session.turn_count += 1
        
        # Handle special response types
        if response.response_type == UserResponseType.SWITCH_TASK:
            return await self._handle_task_switch(session, response)
        
        if response.response_type == UserResponseType.CANCEL:
            return await self._handle_cancellation(session)
        
        if response.response_type == UserResponseType.HELP:
            return await self._handle_help_request(session)
        
        if response.response_type == UserResponseType.BACK:
            return await self._handle_back_request(session)
        
        # Process workflow response
        if session.active_workflow_id:
            return await self._process_workflow_response(session, response)
        else:
            # No active workflow - user is selecting a task
            return await self._handle_task_selection(session, response)
    
    async def _process_workflow_response(
        self,
        session: SessionState,
        response: AgentToBackendMessage
    ) -> InstructionPayload:
        """Process response within active workflow"""
        
        # Get current workflow
        workflow = await self.state_manager.get_workflow(session.active_workflow_id)
        if not workflow:
            raise WorkflowNotFoundError(session.active_workflow_id)
        
        # Process input through state machine
        valid = workflow.process_input(response.extracted_value, response.response_type)
        
        if not valid:
            # Validation failed - reprompt with error
            return self._create_validation_error_instruction(session, workflow, response)
        
        # Attempt state transition
        transition_success = await self.state_manager.transition_workflow(workflow)
        
        # Persist updated state
        await self.state_manager.save_workflow(workflow)
        
        # Check if workflow is complete
        if workflow.is_complete():
            return await self._handle_workflow_complete(session, workflow)
        
        # Generate next instruction
        return self._generate_workflow_instruction(session, workflow)
    
    async def _handle_task_selection(
        self,
        session: SessionState,
        response: AgentToBackendMessage
    ) -> InstructionPayload:
        """Handle user selecting a task from priority list"""
        
        selected_task = response.extracted_value
        
        # Find matching task type
        task_info = next(
            (t for t in session.current_priority_items if t.get("task_type") == selected_task),
            None
        )
        
        if not task_info:
            # Task not found - reprompt
            return InstructionPayload(
                session_id=session.session_id,
                workflow_id="session",
                correlation_id=session.session_id,
                sequence_number=session.turn_count,
                instruction_type=InstructionType.SELECT,
                prompt="I didn't catch that. Which task would you like to work on?",
                options=[
                    {"value": t["task_type"], "label": t["title"]}
                    for t in session.current_priority_items
                ],
                current_state="task_selection",
                workflow_type="session"
            )
        
        # Create workflow for selected task
        workflow = self.workflows.create(
            workflow_type=task_info["task_type"],
            context={
                "reference_id": task_info.get("reference_id"),
                "user_id": session.user_id,
                "user_name": session.user_name,
                **task_info
            }
        )
        
        await self.state_manager.save_workflow(workflow)
        session.active_workflow_id = str(workflow.workflow_id)
        session.workflow_type = workflow.workflow_type
        await self.state_manager.save_session(session)
        
        return self._generate_workflow_instruction(session, workflow)
    
    async def _handle_task_switch(
        self, 
        session: SessionState, 
        response: AgentToBackendMessage
    ) -> InstructionPayload:
        """Pause current task and switch to new one"""
        
        if session.active_workflow_id:
            # Save current workflow to task stack
            current_workflow = await self.state_manager.get_workflow(session.active_workflow_id)
            if current_workflow:
                session.paused_tasks.append(PausedTask(
                    workflow_id=session.active_workflow_id,
                    workflow_type=current_workflow.workflow_type,
                    state=current_workflow.current_state.id,
                    slot_values=current_workflow.slot_values.copy(),
                    paused_at=datetime.utcnow()
                ))
        
        # Handle the switch
        return await self._handle_task_selection(session, response)
    
    async def _handle_cancellation(self, session: SessionState) -> InstructionPayload:
        """Handle user cancellation with saga rollback"""
        
        if session.active_workflow_id:
            # Trigger saga compensation if needed
            await self.saga.rollback(session.active_workflow_id)
            
            # Log cancellation
            await self.events.emit(
                event_type="workflow.cancelled",
                data={"workflow_id": session.active_workflow_id},
                actor=str(session.user_id),
                correlation_id=session.session_id
            )
            
            session.active_workflow_id = None
            session.workflow_type = None
        
        # Check for paused tasks
        if session.paused_tasks:
            return self._offer_resume_paused_task(session)
        
        return self._return_to_task_selection(session)
    
    async def _handle_workflow_complete(
        self,
        session: SessionState,
        workflow: Any
    ) -> InstructionPayload:
        """Handle workflow completion"""
        
        # Log completion
        await self.events.emit(
            event_type="workflow.completed",
            data={
                "workflow_id": str(workflow.workflow_id),
                "workflow_type": workflow.workflow_type,
                "result": workflow.get_result()
            },
            actor=str(session.user_id),
            correlation_id=session.session_id
        )
        
        # Clear active workflow
        session.active_workflow_id = None
        session.workflow_type = None
        
        # Refresh priority list
        pending_work = await self.work_detector.get_prioritized_work(
            session.user_id, 
            session.user_role
        )
        session.pending_work_count = len(pending_work)
        session.current_priority_items = pending_work[:5]
        
        await self.state_manager.save_session(session)
        
        # Generate completion message with next suggestions
        completion_msg = workflow.get_completion_message()
        
        if pending_work:
            next_item = pending_work[0]
            return InstructionPayload(
                session_id=session.session_id,
                workflow_id="session",
                correlation_id=session.session_id,
                sequence_number=session.turn_count,
                instruction_type=InstructionType.CONFIRM,
                prompt=f"{completion_msg}\n\nNext priority: {next_item['title']}. Would you like to handle that now?",
                expected_response="continue_next",
                options=[
                    {"value": "yes", "label": "Yes, continue"},
                    {"value": "no", "label": "No, show me all tasks"},
                    {"value": "done", "label": "I'm done for now"}
                ],
                current_state="workflow_complete",
                workflow_type="session"
            )
        
        return InstructionPayload(
            session_id=session.session_id,
            workflow_id="session",
            correlation_id=session.session_id,
            sequence_number=session.turn_count,
            instruction_type=InstructionType.INFORM,
            prompt=f"{completion_msg}\n\nGreat job! You're all caught up. Let me know if you need anything else.",
            current_state="all_complete",
            workflow_type="session"
        )
    
    def _generate_greeting(
        self, 
        session: SessionState, 
        pending_work: List[Dict]
    ) -> InstructionPayload:
        """Generate greeting instruction based on pending work"""
        
        if pending_work:
            # Format priority summary
            top_items = pending_work[:3]
            priority_lines = []
            for item in top_items:
                emoji = self._get_priority_emoji(item.get("priority_level"))
                priority_lines.append(f"{emoji} {item['title']}")
            
            priority_summary = "\n".join(priority_lines)
            
            return InstructionPayload(
                session_id=session.session_id,
                workflow_id="session_init",
                correlation_id=session.session_id,
                sequence_number=1,
                instruction_type=InstructionType.SELECT,
                prompt=f"Good morning, {session.user_name}! You have {len(pending_work)} pending items.\n\nMost urgent:\n{priority_summary}\n\nWhat would you like to tackle first?",
                options=[
                    {
                        "value": item["task_type"],
                        "label": item["title"],
                        "priority": item.get("priority_level"),
                        "reference_id": item.get("reference_id")
                    }
                    for item in top_items
                ],
                context={
                    "pending_count": len(pending_work),
                    "user_role": session.user_role
                },
                current_state="greeting",
                workflow_type="session"
            )
        
        return InstructionPayload(
            session_id=session.session_id,
            workflow_id="session_init",
            correlation_id=session.session_id,
            sequence_number=1,
            instruction_type=InstructionType.INFORM,
            prompt=f"Good morning, {session.user_name}! Everything looks caught up. How can I help you today?",
            current_state="greeting",
            workflow_type="session"
        )
    
    def _generate_workflow_instruction(
        self, 
        session: SessionState, 
        workflow: Any
    ) -> InstructionPayload:
        """Generate instruction from workflow state"""
        
        state_instruction = workflow.get_current_instruction()
        
        return InstructionPayload(
            session_id=session.session_id,
            workflow_id=str(workflow.workflow_id),
            correlation_id=session.session_id,
            sequence_number=session.turn_count,
            instruction_type=InstructionType(state_instruction["instruction_type"]),
            prompt=state_instruction["prompt"],
            expected_response=state_instruction.get("expected_input"),
            validation=state_instruction.get("validation"),
            options=state_instruction.get("options"),
            form_fields=state_instruction.get("form_fields"),
            display_data=state_instruction.get("display_data"),
            context=workflow.context,
            current_state=state_instruction["current_state"],
            workflow_type=workflow.workflow_type,
            progress_percentage=workflow.get_progress_percentage()
        )
    
    def _get_priority_emoji(self, level: str) -> str:
        """Get emoji for priority level"""
        return {
            "CRITICAL": "🔴",
            "URGENT": "🟠",
            "HIGH": "🟡",
            "MEDIUM": "🔵",
            "LOW": "⚪"
        }.get(level, "⚪")
    
    def _return_to_task_selection(self, session: SessionState) -> InstructionPayload:
        """Return user to task selection"""
        return InstructionPayload(
            session_id=session.session_id,
            workflow_id="session",
            correlation_id=session.session_id,
            sequence_number=session.turn_count,
            instruction_type=InstructionType.SELECT,
            prompt="What would you like to do next?",
            options=[
                {"value": t["task_type"], "label": t["title"]}
                for t in session.current_priority_items
            ],
            current_state="task_selection",
            workflow_type="session"
        )
    
    def _offer_resume_paused_task(self, session: SessionState) -> InstructionPayload:
        """Offer to resume a paused task"""
        paused = session.paused_tasks[-1]
        return InstructionPayload(
            session_id=session.session_id,
            workflow_id="session",
            correlation_id=session.session_id,
            sequence_number=session.turn_count,
            instruction_type=InstructionType.CONFIRM,
            prompt=f"Would you like to return to your previous task ({paused.workflow_type})?",
            expected_response="resume_paused",
            options=[
                {"value": "yes", "label": "Yes, resume"},
                {"value": "no", "label": "No, show other tasks"}
            ],
            current_state="offer_resume",
            workflow_type="session"
        )