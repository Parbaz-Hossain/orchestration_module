"""Response schemas for AI Agent -> Backend communication"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class UserResponseType(str, Enum):
    """Types of responses from user via AI agent"""
    TEXT = "text"
    SELECTION = "selection"
    CONFIRMATION = "confirmation"
    FORM_DATA = "form_data"
    CANCEL = "cancel"
    SWITCH_TASK = "switch_task"
    HELP = "help"
    BACK = "back"


class ExtractedEntity(BaseModel):
    """Entity extracted from user input"""
    entity_type: str
    value: Any
    confidence: float = 1.0
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None


class AgentToBackendMessage(BaseModel):
    """Response from AI Agent to Backend"""
    
    # Identifiers
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    in_response_to: str  # instruction_id being responded to
    session_id: str
    workflow_id: str
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Response content
    response_type: UserResponseType
    
    # Raw user input
    raw_input: str
    
    # Extracted/parsed value
    extracted_value: Any
    extraction_confidence: float = 1.0
    
    # For entity extraction
    entities: Optional[List[ExtractedEntity]] = None
    
    # User intent (if detected)
    detected_intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    
    # For task switching
    switch_to_task: Optional[str] = None
    
    # For form data
    form_data: Optional[Dict[str, Any]] = None
    
    # Error info
    extraction_error: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }