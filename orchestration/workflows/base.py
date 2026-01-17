"""Base workflow state machine"""
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from statemachine import StateMachine, State


@dataclass
class StateDefinition:
    """Defines what AI agent should do at each state"""
    instruction_type: str  # ASK, INFORM, CONFIRM, SELECT, FORM_FILL, DISPLAY
    prompt_template: str
    expected_input: Optional[str] = None
    validation: Optional[Dict] = None
    options: Optional[List] = None
    form_fields: Optional[List] = None
    display_data: Optional[Dict] = None
    auto_advance: bool = False


class ConversationWorkflow(StateMachine):
    """Base class for all conversation workflows"""
    
    workflow_type: str = "base"
    
    def __init__(self, context: Dict[str, Any] = None):
        self.workflow_id = uuid.uuid4()
        self.context = context or {}
        self.slot_values: Dict[str, Any] = {}
        self._progress_steps = 0
        self._total_steps = 0
        super().__init__()
    
    def get_current_instruction(self) -> Dict[str, Any]:
        """Generate instruction for AI agent based on current state"""
        state_def = self.current_state.value
        
        if not isinstance(state_def, StateDefinition):
            return {
                "instruction_type": "INFORM",
                "prompt": "Processing...",
                "current_state": self.current_state.id
            }
        
        # Interpolate template with collected data
        prompt = state_def.prompt_template.format(
            **self.context,
            **self.slot_values
        )
        
        return {
            "instruction_type": state_def.instruction_type,
            "prompt": prompt,
            "expected_input": state_def.expected_input,
            "validation": state_def.validation,
            "options": self._resolve_options(state_def.options),
            "form_fields": state_def.form_fields,
            "display_data": state_def.display_data,
            "current_state": self.current_state.id,
            "workflow_type": self.workflow_type
        }
    
    def process_input(self, user_input: Any, input_type: str = None) -> bool:
        """Process user input and validate"""
        state_def = self.current_state.value
        
        if isinstance(state_def, StateDefinition) and state_def.expected_input:
            # Validate input
            if state_def.validation:
                if not self._validate_input(user_input, state_def.validation):
                    return False
            
            # Store slot value
            self.slot_values[state_def.expected_input] = user_input
        
        self._progress_steps += 1
        return True
    
    def is_complete(self) -> bool:
        """Check if workflow has reached final state"""
        return self.current_state.final
    
    def get_result(self) -> Dict[str, Any]:
        """Get workflow result data"""
        return {
            "workflow_type": self.workflow_type,
            "slot_values": self.slot_values,
            "final_state": self.current_state.id
        }
    
    def get_completion_message(self) -> str:
        """Get message to show on completion"""
        return "Task completed successfully."
    
    def get_progress_percentage(self) -> int:
        """Calculate progress through workflow"""
        if self._total_steps == 0:
            return 0
        return min(100, int((self._progress_steps / self._total_steps) * 100))
    
    def _set_state(self, state_id: str) -> None:
        """Set current state by ID (for restoration)"""
        for state in self.states:
            if state.id == state_id:
                self._current_state = state
                return
    
    def _validate_input(self, value: Any, validation: Dict) -> bool:
        """Validate user input against rules"""
        val_type = validation.get("type")
        
        if val_type == "single_select":
            allowed = validation.get("allowed_values", [])
            return value in allowed or str(value).lower() in [str(v).lower() for v in allowed]
        
        elif val_type == "number":
            try:
                num = float(value)
                min_val = validation.get("min", float("-inf"))
                max_val = validation.get("max", float("inf"))
                return min_val <= num <= max_val
            except (ValueError, TypeError):
                return False
        
        elif val_type == "required":
            return bool(value)
        
        return True
    
    def _resolve_options(self, options: Optional[List]) -> Optional[List]:
        """Resolve dynamic options"""
        if options is None:
            return None
        
        # Options might be a callable or list
        if callable(options):
            return options(self.context, self.slot_values)
        
        return options