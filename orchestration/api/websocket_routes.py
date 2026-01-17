"""WebSocket API routes"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Annotated

from orchestration.websocket.manager import ws_manager
from orchestration.websocket.handlers import MessageHandler
from orchestration.core.dependencies import get_orchestrator
from orchestration.services.orchestrator import OrchestrationEngine


router = APIRouter()


@router.websocket("/orchestrator/{session_id}")
async def orchestrator_websocket(
    websocket: WebSocket,
    session_id: str
):
    """Main WebSocket endpoint for orchestration"""
    
    # Initialize Redis if not done
    if not ws_manager.redis:
        await ws_manager.init_redis()
    
    await ws_manager.connect(websocket, session_id)
    
    # Get orchestrator instance
    # Note: In production, inject properly via middleware
    from orchestration.core.database import async_session_maker
    
    try:
        async with async_session_maker() as db:
            from orchestration.services.work_detection import WorkDetectionService
            from orchestration.services.priority_calculator import PriorityCalculator
            from orchestration.services.state_machine_manager import StateMachineManager
            from orchestration.services.saga_orchestrator import SagaOrchestrator
            from orchestration.services.event_emitter import EventEmitter
            from orchestration.workflows.registry import WorkflowRegistry
            
            orchestrator = OrchestrationEngine(
                db=db,
                work_detector=WorkDetectionService(db, PriorityCalculator()),
                priority_calc=PriorityCalculator(),
                state_manager=StateMachineManager(db),
                saga_orchestrator=SagaOrchestrator(db),
                event_emitter=EventEmitter(db),
                workflow_registry=WorkflowRegistry()
            )
            
            handler = MessageHandler(orchestrator)
            
            while True:
                # Receive message from AI agent
                data = await websocket.receive_text()
                
                # Process and get next instruction
                instruction = await handler.handle_message(session_id, data)
                
                # Push instruction back to agent
                await ws_manager.push_instruction(session_id, instruction)
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id)
    except Exception as e:
        await ws_manager.disconnect(session_id)
        raise