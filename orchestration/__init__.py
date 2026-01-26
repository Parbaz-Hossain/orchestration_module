"""
AI Orchestration Module
========================

A comprehensive orchestration system for AI-powered cafe/retail management.

Components:
-----------
- Models: SQLAlchemy models for workflow templates, work items, and priority rules
- Schemas: Pydantic schemas for API validation and serialization
- Services: Business logic for orchestration, templates, work items, and priorities
- Agents: Base classes for AI agent implementations
- API: FastAPI endpoints for orchestration

Usage:
------
1. Include the API routes in your FastAPI app:
    ```python
    from orchestration_module.api.endpoints import orchestration_endpoints
    app.include_router(orchestration_endpoints.router)
    ```

2. Seed default data:
    ```python
    from orchestration_module.seed_data import seed_orchestration_data
    await seed_orchestration_data(session)
    ```

3. Start a session on user login:
    ```python
    from orchestration_module.services.orchestrator_service import OrchestratorService
    from orchestration_module.schemas.orchestration_schemas import OrchestratorSessionStart
    
    service = OrchestratorService(session)
    result = await service.start_session(OrchestratorSessionStart(
        user_id=user.id,
        role=user.role
    ))
    ```
"""

from .models.enums import (
    AgentRole,
    WorkItemStatus,
    WorkItemPriority,
    TaskCategory,
    TaskType,
    ExecutionMode,
    AgentType,
    WorkflowStepType,
    TriggerType
)

from .schemas.orchestration_schemas import (
    OrchestratorSessionStart,
    OrchestratorSessionResponse,
    WorkItemCreate,
    WorkItemUpdate,
    WorkItemResponse,
    WorkItemSummary,
    WorkflowTemplateCreate,
    WorkflowTemplateUpdate,
    WorkflowTemplateResponse,
    WorkflowTemplateSummary,
    PriorityRuleCreate,
    PriorityRuleUpdate,
    PriorityRuleResponse,
    SuggestionResponse,
    TaskExecutionRequest,
    TaskExecutionResponse,
    AgentContext,
    AgentRequest,
    AgentResponse
)

from .services.orchestrator_service import OrchestratorService
from .services.workflow_template_service import WorkflowTemplateService
from .services.work_item_service import WorkItemService
from .services.priority_rule_service import PriorityRuleService

from .agents.base_agent import (
    BaseAgent,
    SuggestionAgentBase,
    IntentClassifierAgentBase,
    PlanningAgentBase,
    DomainAgentBase,
    HRAgentBase,
    PurchaseAgentBase,
    InventoryAgentBase,
    ExecutionEngineBase,
    AgentRegistry
)

__version__ = "1.0.0"
__author__ = "Your Team"

__all__ = [
    # Enums
    "AgentRole",
    "WorkItemStatus",
    "WorkItemPriority",
    "TaskCategory",
    "TaskType",
    "ExecutionMode",
    "AgentType",
    "WorkflowStepType",
    "TriggerType",
    
    # Schemas
    "OrchestratorSessionStart",
    "OrchestratorSessionResponse",
    "WorkItemCreate",
    "WorkItemUpdate",
    "WorkItemResponse",
    "WorkItemSummary",
    "WorkflowTemplateCreate",
    "WorkflowTemplateUpdate",
    "WorkflowTemplateResponse",
    "WorkflowTemplateSummary",
    "PriorityRuleCreate",
    "PriorityRuleUpdate",
    "PriorityRuleResponse",
    "SuggestionResponse",
    "TaskExecutionRequest",
    "TaskExecutionResponse",
    "AgentContext",
    "AgentRequest",
    "AgentResponse",
    
    # Services
    "OrchestratorService",
    "WorkflowTemplateService",
    "WorkItemService",
    "PriorityRuleService",
    
    # Agents
    "BaseAgent",
    "SuggestionAgentBase",
    "IntentClassifierAgentBase",
    "PlanningAgentBase",
    "DomainAgentBase",
    "HRAgentBase",
    "PurchaseAgentBase",
    "InventoryAgentBase",
    "SalesAgentBase",
    "FinanceAgentBase",
    "FrontendAgentBase",
    "ExecutionEngineBase",
    "AgentRegistry"
]