"""FastAPI dependency injection"""
from typing import AsyncGenerator, Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_orchestrator(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Orchestration engine dependency"""
    from orchestration.services.orchestrator import OrchestrationEngine
    from orchestration.services.work_detection import WorkDetectionService
    from orchestration.services.priority_calculator import PriorityCalculator
    from orchestration.services.state_machine_manager import StateMachineManager
    from orchestration.services.saga_orchestrator import SagaOrchestrator
    from orchestration.services.event_emitter import EventEmitter
    from orchestration.workflows.registry import WorkflowRegistry
    
    priority_calc = PriorityCalculator()
    work_detector = WorkDetectionService(db, priority_calc)
    state_manager = StateMachineManager(db)
    saga_orchestrator = SagaOrchestrator(db)
    event_emitter = EventEmitter(db)
    workflow_registry = WorkflowRegistry()
    
    return OrchestrationEngine(
        db=db,
        work_detector=work_detector,
        priority_calc=priority_calc,
        state_manager=state_manager,
        saga_orchestrator=saga_orchestrator,
        event_emitter=event_emitter,
        workflow_registry=workflow_registry
    )


# Type alias for cleaner annotations
DbSession = Annotated[AsyncSession, Depends(get_db)]