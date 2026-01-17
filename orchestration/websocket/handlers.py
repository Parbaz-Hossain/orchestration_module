"""WebSocket message handlers"""
from typing import Dict, Any
import json

from orchestration.schemas.responses import AgentToBackendMessage
from orchestration.schemas.instructions import InstructionPayload


class MessageHandler:
    """Handles incoming WebSocket messages"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
    
    async def handle_message(
        self, 
        session_id: str, 
        raw_message: str
    ) -> InstructionPayload:
        """Process incoming message and return next instruction"""
        try:
            data = json.loads(raw_message)
            response = AgentToBackendMessage(**data)
            
            return await self.orchestrator.process_user_response(
                session_id=session_id,
                response=response
            )
        except json.JSONDecodeError:
            # Handle invalid JSON
            raise ValueError("Invalid message format")
        except Exception as e:
            # Log and re-raise
            raise
    
    async def handle_disconnect(self, session_id: str) -> None:
        """Handle client disconnection"""
        # Save session state for recovery
        pass
    
    async def handle_reconnect(self, session_id: str) -> InstructionPayload:
        """Handle client reconnection"""
        # Restore session and return current instruction
        pass