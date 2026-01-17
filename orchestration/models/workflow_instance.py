"""Workflow instance and state history models"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from orchestration.core.database import Base


class WorkflowInstance(Base):
    """Active workflow instances with full state"""
    __tablename__ = "workflow_instances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_type = Column(String(100), nullable=False)
    user_id = Column(Integer, nullable=False)
    session_id = Column(String(100), index=True)
    current_state = Column(String(50), nullable=False)
    state_data = Column(JSONB, nullable=False, default=dict)
    context_data = Column(JSONB, nullable=False, default=dict)
    task_stack = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    version = Column(Integer, default=1)
    
    # Relationships
    state_history = relationship("WorkflowStateHistory", back_populates="workflow_instance")
    saga_instances = relationship("SagaInstance", back_populates="workflow_instance")
    
    __table_args__ = (
        Index("idx_workflow_user", "user_id", "workflow_type", "current_state"),
        Index("idx_workflow_active", "current_state", "expires_at"),
    )


class WorkflowStateHistory(Base):
    """State transition history for audit and recovery"""
    __tablename__ = "workflow_state_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_instance_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("workflow_instances.id"),
        nullable=False
    )
    from_state = Column(String(50))
    to_state = Column(String(50), nullable=False)
    trigger_event = Column(String(50), nullable=False)
    event_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow_instance = relationship("WorkflowInstance", back_populates="state_history")