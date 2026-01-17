"""Work item model for priority queue"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB

from orchestration.core.database import Base


class WorkItem(Base):
    """Pending work items with calculated priorities"""
    __tablename__ = "work_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type_id = Column(Integer, ForeignKey("task_types.id"))
    reference_id = Column(Integer, nullable=False)
    reference_table = Column(String(100), nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime)
    calculated_priority = Column(Integer)
    priority_level = Column(String(20))
    assigned_role_id = Column(Integer)
    meta_data = Column(JSONB)
    last_priority_calc = Column(DateTime)
    
    __table_args__ = (
        Index("idx_status_priority", "status", "calculated_priority"),
        Index("idx_role_pending", "assigned_role_id", "status", "calculated_priority"),
    )