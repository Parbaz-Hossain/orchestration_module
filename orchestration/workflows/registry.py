"""Workflow registry - factory for creating workflows"""
from typing import Dict, Any, Type, Optional

from .base import ConversationWorkflow
from .po_creation import POCreationWorkflow
from .stock_adjustment import StockAdjustmentWorkflow


class WorkflowRegistry:
    """Registry and factory for workflow types"""
    
    _workflows: Dict[str, Type[ConversationWorkflow]] = {
        "po_creation": POCreationWorkflow,
        "low_stock_reorder": POCreationWorkflow,  # Alias
        "stock_adjustment": StockAdjustmentWorkflow,
        "inventory_count": StockAdjustmentWorkflow  # Alias
    }
    
    @classmethod
    def register(cls, workflow_type: str, workflow_class: Type[ConversationWorkflow]) -> None:
        """Register a new workflow type"""
        cls._workflows[workflow_type] = workflow_class
    
    @classmethod
    def create(
        cls, 
        workflow_type: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ConversationWorkflow:
        """Create a workflow instance"""
        workflow_class = cls._workflows.get(workflow_type)
        
        if not workflow_class:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        return workflow_class(context=context)
    
    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available workflow types"""
        return list(cls._workflows.keys())