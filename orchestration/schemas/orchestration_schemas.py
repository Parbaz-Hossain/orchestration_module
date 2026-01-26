"""
Orchestration Module Schemas
Pydantic schemas for API validation and serialization
"""
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.enums import (
    AgentRole, WorkItemStatus, WorkItemPriority, TaskCategory,
    TaskType, ExecutionMode, AgentType, WorkflowStepType, TriggerType
)


# ==================== BASE SCHEMAS ====================

class OrchestratorBase(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        use_enum_values = True


# ==================== WORKFLOW TEMPLATE SCHEMAS ====================

class APIEndpointConfig(BaseModel):
    """Configuration for a single API endpoint"""
    name: str = Field(..., description="Endpoint name for reference")
    path: str = Field(..., description="API path with optional parameters")
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE)")
    description: Optional[str] = None
    request_body_mapping: Optional[Dict[str, Any]] = None
    response_mapping: Optional[Dict[str, Any]] = None


class APIConfig(BaseModel):
    """Complete API configuration for a workflow template"""
    base_endpoint: str = Field(..., description="Base API endpoint path")
    method: str = Field(default="POST", description="Default HTTP method")
    endpoints: List[APIEndpointConfig] = Field(default_factory=list)
    headers: Optional[Dict[str, str]] = None
    auth_required: bool = True


class FieldDefinition(BaseModel):
    """Schema field definition"""
    type: str = Field(..., description="Data type: string, integer, float, date, datetime, boolean, array, object")
    description: Optional[str] = None
    format: Optional[str] = None  # e.g., "YYYY-MM-dd" for dates
    default: Optional[Any] = None
    enum_values: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern
    array_item_type: Optional[str] = None


class SchemaConfig(BaseModel):
    """Input/Output schema configuration"""
    required_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)
    field_definitions: Dict[str, FieldDefinition] = Field(default_factory=dict)


class BusinessRuleCondition(BaseModel):
    """A single business rule condition"""
    rule: str = Field(..., description="Rule identifier or expression")
    error_message: str
    severity: str = Field(default="error", description="error, warning, info")


class BusinessRulesConfig(BaseModel):
    """Business rules configuration"""
    pre_conditions: List[BusinessRuleCondition] = Field(default_factory=list)
    validations: List[Dict[str, Any]] = Field(default_factory=list)
    post_actions: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowStepConfig(BaseModel):
    """Configuration for a single workflow step"""
    step_id: int
    type: WorkflowStepType
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    condition: Optional[Dict[str, Any]] = None
    on_error: str = Field(default="stop")
    timeout_seconds: Optional[int] = None


class TriggerConfig(BaseModel):
    """Trigger configuration for workflows"""
    scheduled: Optional[Dict[str, Any]] = None  # {"cron": "...", "description": "..."}
    event_based: Optional[List[str]] = None
    threshold: Optional[Dict[str, Any]] = None


class WorkflowTemplateCreate(OrchestratorBase):
    """Schema for creating a new workflow template"""
    name: str = Field(..., min_length=3, max_length=200)
    code: str = Field(..., min_length=2, max_length=50, pattern="^[A-Z][A-Z0-9_]*$")
    description: Optional[str] = None
    version: str = Field(default="1.0.0")
    
    category: TaskCategory
    task_type: TaskType
    
    execution_mode: ExecutionMode = ExecutionMode.SEMI_AUTOMATIC
    default_priority: WorkItemPriority = WorkItemPriority.MEDIUM
    target_agent: AgentType
    allowed_roles: List[AgentRole]
    
    api_config: APIConfig
    input_schema: SchemaConfig
    output_schema: Optional[SchemaConfig] = None
    business_rules: BusinessRulesConfig = Field(default_factory=BusinessRulesConfig)
    workflow_steps: List[WorkflowStepConfig] = Field(default_factory=list)
    triggers: Optional[TriggerConfig] = None
    agent_instructions: Optional[str] = None


class WorkflowTemplateUpdate(OrchestratorBase):
    """Schema for updating a workflow template"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    version: Optional[str] = None
    
    execution_mode: Optional[ExecutionMode] = None
    default_priority: Optional[WorkItemPriority] = None
    allowed_roles: Optional[List[AgentRole]] = None
    
    api_config: Optional[APIConfig] = None
    input_schema: Optional[SchemaConfig] = None
    output_schema: Optional[SchemaConfig] = None
    business_rules: Optional[BusinessRulesConfig] = None
    workflow_steps: Optional[List[WorkflowStepConfig]] = None
    triggers: Optional[TriggerConfig] = None
    agent_instructions: Optional[str] = None
    
    is_active: Optional[bool] = None


class WorkflowTemplateResponse(OrchestratorBase):
    """Schema for workflow template response"""
    id: int
    name: str
    code: str
    description: Optional[str]
    version: str
    
    category: TaskCategory
    task_type: TaskType
    
    execution_mode: ExecutionMode
    default_priority: WorkItemPriority
    target_agent: AgentType
    allowed_roles: List[str]
    
    api_config: Dict[str, Any]
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]
    business_rules: Dict[str, Any]
    workflow_steps: List[Dict[str, Any]]
    triggers: Optional[Dict[str, Any]]
    agent_instructions: Optional[str]
    
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateSummary(OrchestratorBase):
    """Lightweight summary of a workflow template"""
    id: int
    name: str
    code: str
    category: TaskCategory
    task_type: TaskType
    execution_mode: ExecutionMode
    default_priority: WorkItemPriority
    is_active: bool


# ==================== WORK ITEM SCHEMAS ====================

class WorkItemCreate(OrchestratorBase):
    """Schema for creating a new work item"""
    template_code: str = Field(..., description="Code of the workflow template")
    title: str = Field(..., min_length=3, max_length=300)
    description: Optional[str] = None
    reference_id: Optional[str] = None
    
    assigned_to_role: Optional[AgentRole] = None
    assigned_to_user_id: Optional[int] = None
    
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    input_data: Dict[str, Any] = Field(default_factory=dict)
    
    due_date: Optional[datetime] = None
    trigger_type: Optional[TriggerType] = TriggerType.MANUAL
    
    is_suggestion: bool = False


class WorkItemUpdate(OrchestratorBase):
    """Schema for updating a work item"""
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    description: Optional[str] = None
    
    assigned_to_role: Optional[AgentRole] = None
    assigned_to_user_id: Optional[int] = None
    
    status: Optional[WorkItemStatus] = None
    priority: Optional[WorkItemPriority] = None
    
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    
    due_date: Optional[datetime] = None
    error_message: Optional[str] = None


class WorkItemResponse(OrchestratorBase):
    """Schema for work item response"""
    id: int
    template_id: int
    template_code: str
    
    title: str
    description: Optional[str]
    reference_id: Optional[str]
    
    category: TaskCategory
    task_type: TaskType
    
    assigned_to_role: Optional[AgentRole]
    assigned_to_user_id: Optional[int]
    assigned_agent: Optional[AgentType]
    
    status: WorkItemStatus
    priority: WorkItemPriority
    priority_score: float
    
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    
    execution_mode: ExecutionMode
    current_step: int
    step_results: List[Dict[str, Any]]
    
    due_date: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    error_message: Optional[str]
    retry_count: int
    
    trigger_type: Optional[TriggerType]
    is_suggestion: bool
    is_automated: bool
    
    created_at: datetime
    updated_at: datetime


class WorkItemSummary(OrchestratorBase):
    """Lightweight summary of a work item"""
    id: int
    title: str
    template_code: str
    category: TaskCategory
    task_type: TaskType
    status: WorkItemStatus
    priority: WorkItemPriority
    priority_score: float
    assigned_to_role: Optional[AgentRole]
    due_date: Optional[datetime]
    is_suggestion: bool
    created_at: datetime


class WorkItemExecutionLogResponse(OrchestratorBase):
    """Schema for execution log response"""
    id: int
    work_item_id: int
    timestamp: datetime
    log_level: str
    action: str
    step_id: Optional[int]
    agent_type: Optional[AgentType]
    message: Optional[str]
    details: Optional[Dict[str, Any]]
    status: Optional[str]
    duration_ms: Optional[int]


# ==================== PRIORITY RULE SCHEMAS ====================

class PriorityCondition(BaseModel):
    """Condition for priority rule evaluation"""
    field: Optional[str] = None  # Field to evaluate
    operator: Optional[str] = None  # ==, !=, >, <, >=, <=, in, not_in, contains
    value: Optional[Any] = None
    score_formula: Optional[str] = None  # Python expression for score calculation


class PriorityRuleCreate(OrchestratorBase):
    """Schema for creating a priority rule"""
    name: str = Field(..., min_length=3, max_length=200)
    code: str = Field(..., min_length=2, max_length=50, pattern="^[A-Z][A-Z0-9_]*$")
    description: Optional[str] = None
    
    template_id: Optional[int] = None  # Specific template or null for global
    category: Optional[TaskCategory] = None
    task_type: Optional[TaskType] = None
    
    rule_type: str = Field(..., description="base_priority, deadline_proximity, user_role, data_condition, time_based")
    base_weight: float = Field(default=1.0, ge=0, le=10)
    max_score_contribution: float = Field(default=100.0, ge=0)
    
    condition: Dict[str, Any]
    score_formula: Optional[str] = None
    priority_weights: Optional[Dict[str, float]] = None  # For base_priority type
    
    evaluation_order: int = Field(default=100, ge=0)
    is_additive: bool = True


class PriorityRuleUpdate(OrchestratorBase):
    """Schema for updating a priority rule"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    
    base_weight: Optional[float] = Field(None, ge=0, le=10)
    max_score_contribution: Optional[float] = Field(None, ge=0)
    
    condition: Optional[Dict[str, Any]] = None
    score_formula: Optional[str] = None
    priority_weights: Optional[Dict[str, float]] = None
    
    evaluation_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_additive: Optional[bool] = None


class PriorityRuleResponse(OrchestratorBase):
    """Schema for priority rule response"""
    id: int
    name: str
    code: str
    description: Optional[str]
    
    template_id: Optional[int]
    category: Optional[TaskCategory]
    task_type: Optional[TaskType]
    
    rule_type: str
    base_weight: float
    max_score_contribution: float
    
    condition: Dict[str, Any]
    score_formula: Optional[str]
    priority_weights: Optional[Dict[str, float]]
    
    evaluation_order: int
    is_active: bool
    is_system: bool
    is_additive: bool
    
    created_at: datetime
    updated_at: datetime


# ==================== SUGGESTION SCHEMAS ====================

class SuggestionRuleCreate(OrchestratorBase):
    """Schema for creating a suggestion rule"""
    name: str = Field(..., min_length=3, max_length=200)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    
    target_role: AgentRole
    template_id: int
    
    condition: Dict[str, Any]
    suggestion_title: str = Field(..., max_length=300)
    suggestion_message: str
    suggestion_priority: WorkItemPriority = WorkItemPriority.MEDIUM
    
    default_input_data: Optional[Dict[str, Any]] = None
    check_frequency_minutes: int = Field(default=60, ge=1)
    max_suggestions_per_day: int = Field(default=1, ge=1)
    
    is_dismissible: bool = True
    auto_create_task: bool = False


class SuggestionRuleResponse(OrchestratorBase):
    """Schema for suggestion rule response"""
    id: int
    name: str
    code: str
    description: Optional[str]
    
    target_role: AgentRole
    template_id: int
    
    condition: Dict[str, Any]
    suggestion_title: str
    suggestion_message: str
    suggestion_priority: WorkItemPriority
    
    default_input_data: Optional[Dict[str, Any]]
    check_frequency_minutes: int
    max_suggestions_per_day: int
    
    is_active: bool
    is_dismissible: bool
    auto_create_task: bool
    
    times_suggested: int
    times_accepted: int
    times_dismissed: int
    
    created_at: datetime


class SuggestionResponse(OrchestratorBase):
    """Schema for a suggestion to display to user"""
    suggestion_id: int  # Rule ID
    title: str
    message: str
    priority: WorkItemPriority
    template_code: str
    template_name: str
    category: TaskCategory
    
    can_auto_create: bool
    is_dismissible: bool
    default_input_data: Optional[Dict[str, Any]]
    
    # Pre-computed information
    estimated_duration_minutes: Optional[int] = None
    affected_records_count: Optional[int] = None


# ==================== AGENT INTERACTION SCHEMAS ====================

class AgentContext(OrchestratorBase):
    """Context passed to/from AI agents"""
    user_id: int
    user_role: AgentRole
    session_id: str
    
    current_work_item_id: Optional[int] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    available_templates: List[WorkflowTemplateSummary] = Field(default_factory=list)
    pending_work_items: List[WorkItemSummary] = Field(default_factory=list)
    suggestions: List[SuggestionResponse] = Field(default_factory=list)
    
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    recent_actions: List[str] = Field(default_factory=list)


class AgentRequest(OrchestratorBase):
    """Request to an AI agent"""
    agent_type: AgentType
    action: str  # classify, plan, suggest, execute, respond
    
    context: AgentContext
    input_data: Dict[str, Any] = Field(default_factory=dict)
    
    work_item_id: Optional[int] = None
    template_code: Optional[str] = None
    
    user_message: Optional[str] = None  # For conversational agents


class AgentResponse(OrchestratorBase):
    """Response from an AI agent"""
    agent_type: AgentType
    action: str
    success: bool
    
    # Classification results
    classified_intent: Optional[str] = None
    classified_category: Optional[TaskCategory] = None
    confidence_score: Optional[float] = None
    
    # Planning results
    recommended_template: Optional[str] = None
    execution_plan: Optional[List[Dict[str, Any]]] = None
    
    # Execution results
    work_item_id: Optional[int] = None
    execution_status: Optional[str] = None
    step_results: Optional[List[Dict[str, Any]]] = None
    
    # For frontend
    ui_actions: Optional[List[Dict[str, Any]]] = None
    response_message: Optional[str] = None
    
    # Errors
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


# ==================== ORCHESTRATOR SESSION SCHEMAS ====================

class OrchestratorSessionStart(OrchestratorBase):
    """Request to start an orchestrator session (on user login)"""
    user_id: int
    role: AgentRole
    location_id: Optional[int] = None
    department_id: Optional[int] = None


class OrchestratorSessionResponse(OrchestratorBase):
    """Response for orchestrator session"""
    session_id: str
    user_id: int
    role: AgentRole
    
    # Pending work
    pending_tasks: List[WorkItemSummary]
    pending_count: int
    
    # Suggestions
    suggestions: List[SuggestionResponse]
    
    # Available actions
    available_templates: List[WorkflowTemplateSummary]
    
    # Dashboard metrics
    metrics: Dict[str, Any] = Field(default_factory=dict)
    # Structure: {
    #   "tasks_completed_today": 5,
    #   "tasks_pending": 12,
    #   "high_priority_count": 3,
    #   "overdue_count": 1
    # }


class TaskExecutionRequest(OrchestratorBase):
    """Request to execute a task through the orchestrator"""
    work_item_id: Optional[int] = None  # Existing work item
    template_code: Optional[str] = None  # To create new work item
    
    input_data: Dict[str, Any] = Field(default_factory=dict)
    user_confirmation: Optional[bool] = None  # For semi-automatic tasks
    
    # For conversational flow
    user_message: Optional[str] = None


class TaskExecutionResponse(OrchestratorBase):
    """Response from task execution"""
    work_item_id: int
    status: WorkItemStatus
    
    # Current state
    current_step: int
    total_steps: int
    step_name: Optional[str] = None
    
    # What's needed
    requires_input: bool = False
    required_fields: Optional[List[str]] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    
    # Results
    partial_results: Optional[Dict[str, Any]] = None
    final_results: Optional[Dict[str, Any]] = None
    
    # For frontend
    ui_update: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None
    
    # Messages
    message: str
    details: Optional[str] = None


# ==================== DOMAIN KNOWLEDGE SCHEMAS ====================

class DomainKnowledgeCreate(OrchestratorBase):
    """Schema for creating domain knowledge"""
    category: TaskCategory
    knowledge_type: str
    title: str = Field(..., max_length=300)
    content: str
    
    intent_patterns: Optional[List[str]] = None
    related_templates: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    
    confidence_score: float = Field(default=1.0, ge=0, le=1)
    source: Optional[str] = None


class DomainKnowledgeResponse(OrchestratorBase):
    """Schema for domain knowledge response"""
    id: int
    category: TaskCategory
    knowledge_type: str
    title: str
    content: str
    
    intent_patterns: Optional[List[str]]
    related_templates: Optional[List[str]]
    prerequisites: Optional[List[str]]
    
    confidence_score: float
    source: Optional[str]
    is_active: bool
    created_at: datetime