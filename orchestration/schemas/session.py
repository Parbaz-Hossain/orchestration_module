"""Session state schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PausedTask(BaseModel):
    """Representation of a paused task in the task stack"""
    workflow_id: str
    workflow_type: str
    state: str
    slot_values: Dict[str, Any]
    paused_at: datetime


class ConversationTurn(BaseModel):
    """Single turn in conversation history"""
    turn_number: int
    instruction_type: str
    prompt: str
    user_response: Optional[str] = None
    response_type: Optional[str] = None
    timestamp: datetime


class SessionState(BaseModel):
    """Full session state for recovery/handoff"""
    session_id: str
    user_id: int
    user_role: str
    channel: str  # web, voice, mobile
    device_id: Optional[str] = None
    
    # Workflow state
    active_workflow_id: Optional[str] = None
    workflow_type: Optional[str] = None
    current_state: Optional[str] = None
    slot_values: Dict[str, Any] = Field(default_factory=dict)
    
    # Task stack for switching
    paused_tasks: List[PausedTask] = Field(default_factory=list)
    
    # Conversation history
    turn_count: int = 0
    recent_turns: List[ConversationTurn] = Field(default_factory=list)
    conversation_summary: Optional[str] = None
    
    # User context
    user_name: str = ""
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Priority context
    pending_work_count: int = 0
    current_priority_items: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Timing
    session_start: datetime
    last_activity: datetime
    expires_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }