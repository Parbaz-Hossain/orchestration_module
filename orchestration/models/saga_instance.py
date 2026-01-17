"""Saga execution tracking models"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from orchestration.core.database import Base


class SagaInstance(Base):
    """Saga execution instance"""
    __tablename__ = "saga_instances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_instances.id"),
        nullable=True
    )
    saga_type = Column(String(100), nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, compensating, failed
    current_step = Column(Integer, default=0)
    completed_steps = Column(JSONB, default=list)
    context = Column(JSONB, nullable=False, default=dict)
    correlation_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflow_instance = relationship("WorkflowInstance", back_populates="saga_instances")
    step_results = relationship("SagaStepResult", back_populates="saga_instance")


class SagaStepResult(Base):
    """Individual saga step results for rollback"""
    __tablename__ = "saga_step_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    saga_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("saga_instances.id"),
        nullable=False
    )
    step_name = Column(String(100), nullable=False)
    step_sequence = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")  # pending, completed, failed, compensated
    result_data = Column(JSONB)
    compensation_data = Column(JSONB)
    executed_at = Column(DateTime)
    compensated_at = Column(DateTime)
    
    # Relationships
    saga_instance = relationship("SagaInstance", back_populates="step_results")