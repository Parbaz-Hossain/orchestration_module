"""Saga pattern orchestrator for multi-step transactions"""
import uuid
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from orchestration.models.saga_instance import SagaInstance, SagaStepResult
from orchestration.core.exceptions import SagaCompensationError


@dataclass
class SagaStep:
    """Definition of a single saga step"""
    name: str
    action: Callable
    compensation: Callable
    sequence: int = 0


class SagaOrchestrator:
    """Manages saga execution with compensation"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.steps: List[SagaStep] = []
    
    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Callable
    ) -> "SagaOrchestrator":
        """Add a step to the saga"""
        self.steps.append(SagaStep(
            name=name,
            action=action,
            compensation=compensation,
            sequence=len(self.steps)
        ))
        return self
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all saga steps with rollback on failure"""
        
        saga_id = uuid.uuid4()
        correlation_id = context.get("correlation_id", uuid.uuid4())
        
        # Create saga instance
        saga_instance = SagaInstance(
            id=saga_id,
            saga_type=context.get("saga_type", "unknown"),
            status="in_progress",
            context=context,
            correlation_id=correlation_id
        )
        self.db.add(saga_instance)
        await self.db.flush()
        
        completed_steps: List[SagaStepResult] = []
        
        try:
            for step in self.steps:
                # Execute step
                step_result = SagaStepResult(
                    saga_instance_id=saga_id,
                    step_name=step.name,
                    step_sequence=step.sequence,
                    status="pending"
                )
                self.db.add(step_result)
                
                result = await step.action(context)
                
                # Store result
                step_result.status = "completed"
                step_result.result_data = result if isinstance(result, dict) else {"value": result}
                step_result.executed_at = datetime.utcnow()
                
                # Store result in context for next steps
                context[f"{step.name}_result"] = result
                
                completed_steps.append(step_result)
                saga_instance.current_step = step.sequence + 1
                saga_instance.completed_steps = [s.step_name for s in completed_steps]
                
                await self.db.flush()
            
            # All steps completed
            saga_instance.status = "completed"
            await self.db.flush()
            
            return {
                "saga_id": str(saga_id),
                "status": "completed",
                "context": context
            }
            
        except Exception as e:
            # Rollback - execute compensations in reverse
            saga_instance.status = "compensating"
            await self.db.flush()
            
            await self._compensate(completed_steps, context)
            
            saga_instance.status = "failed"
            await self.db.flush()
            
            raise
    
    async def rollback(self, workflow_id: str) -> None:
        """Rollback saga associated with workflow"""
        result = await self.db.execute(
            select(SagaInstance).where(
                SagaInstance.workflow_instance_id == uuid.UUID(workflow_id)
            )
        )
        saga = result.scalar_one_or_none()
        
        if saga and saga.status == "in_progress":
            # Get completed steps
            steps_result = await self.db.execute(
                select(SagaStepResult)
                .where(SagaStepResult.saga_instance_id == saga.id)
                .where(SagaStepResult.status == "completed")
                .order_by(SagaStepResult.step_sequence.desc())
            )
            completed_steps = steps_result.scalars().all()
            
            saga.status = "compensating"
            await self._compensate(completed_steps, saga.context)
            saga.status = "rolled_back"
            await self.db.flush()
    
    async def _compensate(
        self, 
        completed_steps: List[SagaStepResult],
        context: Dict[str, Any]
    ) -> None:
        """Execute compensations in reverse order"""
        for step_result in reversed(completed_steps):
            try:
                # Find matching step definition
                step_def = next(
                    (s for s in self.steps if s.name == step_result.step_name),
                    None
                )
                
                if step_def and step_def.compensation:
                    await step_def.compensation(context)
                    step_result.status = "compensated"
                    step_result.compensated_at = datetime.utcnow()
                    
            except Exception as e:
                raise SagaCompensationError(
                    saga_id=str(step_result.saga_instance_id),
                    step=step_result.step_name,
                    original_error=str(e)
                )