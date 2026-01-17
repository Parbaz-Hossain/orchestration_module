"""Instruction schemas for Backend -> AI Agent communication"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field


class InstructionType(str, Enum):
    """Types of instructions the backend can send to AI agent"""
    ASK = "ASK"              # Ask user for specific information
    INFORM = "INFORM"        # Tell user something
    CONFIRM = "CONFIRM"      # Get user confirmation
    SELECT = "SELECT"        # Let user pick from options
    FORM_FILL = "FORM_FILL"  # Collect multiple fields
    DISPLAY = "DISPLAY"      # Show data/summary


class ValidationRule(BaseModel):
    """Validation rules for user input"""
    type: str  # single_select, multi_select, number, text, date, required
    allowed_values: Optional[List[str]] = None
    min: Optional[float] = None
    max: Optional[float] = None
    pattern: Optional[str] = None
    error_message: Optional[str] = None


class FormField(BaseModel):
    """Field definition for FORM_FILL instruction type"""
    name: str
    label: str
    field_type: str  # text, number, select, date, checkbox
    required: bool = True
    default_value: Optional[Any] = None
    validation: Optional[ValidationRule] = None
    options: Optional[List[Dict[str, Any]]] = None


class InstructionPayload(BaseModel):
    """Instruction pushed from Backend to AI Agent"""
    
    # Identifiers
    instruction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    workflow_id: str
    correlation_id: str
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence_number: int
    
    # Instruction content
    instruction_type: InstructionType
    priority: Literal["high", "normal", "low"] = "normal"
    
    # What to say/ask
    prompt: str
    prompt_ssml: Optional[str] = None  # For voice rendering
    
    # User response handling
    expected_response: Optional[str] = None  # Slot name to fill
    validation: Optional[ValidationRule] = None
    
    # Options for SELECT type
    options: Optional[List[Dict[str, Any]]] = None
    
    # Form fields for FORM_FILL type
    form_fields: Optional[List[FormField]] = None
    
    # Rich display data
    display_data: Optional[Dict[str, Any]] = None
    
    # Timeout handling
    timeout_seconds: int = 60
    timeout_action: Literal["repeat", "escalate", "cancel"] = "repeat"
    
    # Context for the agent
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # State info
    current_state: str
    workflow_type: str
    progress_percentage: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BackendToAgentMessage(BaseModel):
    """WebSocket message wrapper for backend to agent communication"""
    message_type: Literal["instruction", "state_update", "error", "heartbeat"]
    payload: Optional[InstructionPayload] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)