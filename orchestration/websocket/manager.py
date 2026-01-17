"""WebSocket connection manager"""
from typing import Dict, Optional
from fastapi import WebSocket
import redis.asyncio as redis
import json

from orchestration.schemas.instructions import InstructionPayload, BackendToAgentMessage
from orchestration.core.config import settings


class WebSocketManager:
    """Manages WebSocket connections with Redis pub/sub for scaling"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.connections: Dict[str, WebSocket] = {}
    
    async def init_redis(self):
        """Initialize Redis connection"""
        self.redis = await redis.from_url(settings.REDIS_URL)
    
    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept WebSocket connection"""
        await websocket.accept()
        self.connections[session_id] = websocket
        
        # Subscribe to session channel for multi-instance support
        if self.redis:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(f"session:{session_id}")
    
    async def disconnect(self, session_id: str) -> None:
        """Handle disconnection"""
        if session_id in self.connections:
            del self.connections[session_id]
        
        if self.redis:
            await self.redis.publish(
                f"session:{session_id}",
                json.dumps({"type": "disconnected"})
            )
    
    async def push_instruction(
        self, 
        session_id: str, 
        instruction: InstructionPayload
    ) -> bool:
        """Push instruction to AI agent"""
        message = BackendToAgentMessage(
            message_type="instruction",
            payload=instruction
        )
        
        # Try direct connection first
        if session_id in self.connections:
            try:
                await self.connections[session_id].send_json(
                    message.model_dump(mode="json")
                )
                return True
            except Exception:
                del self.connections[session_id]
        
        # Fallback to Redis pub/sub for other instances
        if self.redis:
            await self.redis.publish(
                f"session:{session_id}",
                message.model_dump_json()
            )
            return True
        
        return False
    
    async def broadcast_to_role(self, role: str, message: dict) -> None:
        """Broadcast message to all users with a specific role"""
        if self.redis:
            await self.redis.publish(f"role:{role}", json.dumps(message))
    
    async def send_heartbeat(self, session_id: str) -> bool:
        """Send heartbeat to keep connection alive"""
        message = BackendToAgentMessage(message_type="heartbeat")
        
        if session_id in self.connections:
            try:
                await self.connections[session_id].send_json(
                    message.model_dump(mode="json")
                )
                return True
            except Exception:
                return False
        return False


# Global instance
ws_manager = WebSocketManager()