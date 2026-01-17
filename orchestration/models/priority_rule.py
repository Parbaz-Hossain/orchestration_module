"""Priority rules and task type configuration models"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from orchestration.core.database import Base


class TaskType(Base):
    """Task type definitions with base priorities"""
    __tablename__ = "task_types"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    base_priority = Column(Integer, default=50)
    default_sla_hours = Column(Integer)
    workflow_definition = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    priority_rules = relationship("PriorityRule", back_populates="task_type")
    role_assignments = relationship("RoleTaskAssignment", back_populates="task_type")


class RoleTaskAssignment(Base):
    """Role-to-task visibility and priority adjustments"""
    __tablename__ = "role_task_assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, nullable=False)
    task_type_id = Column(Integer, ForeignKey("task_types.id"))
    can_view = Column(Boolean, default=True)
    can_action = Column(Boolean, default=True)
    priority_boost = Column(Integer, default=0)
    
    # Relationships
    task_type = relationship("TaskType", back_populates="role_assignments")
    
    __table_args__ = (
        UniqueConstraint("role_id", "task_type_id", name="uq_role_task"),
    )


class PriorityRule(Base):
    """Configurable priority calculation rules"""
    __tablename__ = "priority_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type_id = Column(Integer, ForeignKey("task_types.id"))
    rule_name = Column(String(100), nullable=False)
    condition_field = Column(String(100))
    condition_operator = Column(String(20))  # lt, lte, gt, gte, between, eq
    condition_value = Column(JSONB)
    priority_score = Column(Integer)
    priority_level = Column(String(20))  # CRITICAL, URGENT, HIGH, MEDIUM, LOW
    is_active = Column(Boolean, default=True)
    evaluation_order = Column(Integer, default=0)
    
    # Relationships
    task_type = relationship("TaskType", back_populates="priority_rules")