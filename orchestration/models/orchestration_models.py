"""
Orchestration Module Models
SQLAlchemy models for workflow templates, work items, and priority rules
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, JSON, Float, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

from .enums import (
    AgentRole, WorkItemStatus, WorkItemPriority, TaskCategory,
    TaskType, ExecutionMode, AgentType, WorkflowStepType, TriggerType
)


# ==================== WORKFLOW TEMPLATE MODELS ====================

class WorkflowTemplate(Base):
    """
    Defines reusable workflow templates with API endpoints, schemas, and business rules.
    Each template represents a complete workflow for a specific task type.
    """
    __tablename__ = "orchestration_workflow_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Template Identification
    name = Column(String(200), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)  # e.g., "HR_SALARY_GEN"
    description = Column(Text, nullable=True)
    version = Column(String(20), default="1.0.0")
    
    # Categorization
    category = Column(SQLEnum(TaskCategory), nullable=False, index=True)
    task_type = Column(SQLEnum(TaskType), nullable=False, index=True)
    
    # Execution Configuration
    execution_mode = Column(SQLEnum(ExecutionMode), default=ExecutionMode.SEMI_AUTOMATIC)
    default_priority = Column(SQLEnum(WorkItemPriority), default=WorkItemPriority.MEDIUM)
    
    # Target Agent
    target_agent = Column(SQLEnum(AgentType), nullable=False)
    
    # Allowed Roles (JSON array of AgentRole values)
    allowed_roles = Column(JSONB, default=[])
    
    # API Endpoint Configuration
    api_config = Column(JSON, nullable=False)
    # Structure: {
    #   "base_endpoint": "/api/v1/hr/salary",
    #   "method": "POST",
    #   "endpoints": [
    #       {"name": "generate", "path": "/generate/{employee_id}", "method": "POST"},
    #       {"name": "bulk_generate", "path": "/generate-bulk", "method": "POST"},
    #       {"name": "get_reports", "path": "/reports", "method": "GET"}
    #   ]
    # }
    
    # Input/Output Schema Definition
    input_schema = Column(JSON, nullable=False)
    # Structure: {
    #   "required_fields": ["employee_id", "salary_month"],
    #   "optional_fields": ["location_id", "department_id"],
    #   "field_definitions": {
    #       "employee_id": {"type": "integer", "description": "Employee ID"},
    #       "salary_month": {"type": "date", "format": "YYYY-MM-dd"}
    #   }
    # }
    
    output_schema = Column(JSON, nullable=True)
    # Structure: Similar to input_schema
    
    # Business Rules Configuration
    business_rules = Column(JSON, nullable=False, default=dict)
    # Structure: {
    #   "pre_conditions": [
    #       {"rule": "employee_must_be_active", "error_message": "Employee is not active"}
    #   ],
    #   "validations": [
    #       {"field": "salary_month", "rule": "not_future_date", "error_message": "Cannot generate future salary"}
    #   ],
    #   "post_actions": [
    #       {"action": "notify_employee", "condition": "on_success"}
    #   ]
    # }
    
    # Workflow Steps Definition
    workflow_steps = Column(JSON, nullable=False, default=list)
    # Structure: [
    #   {"step_id": 1, "type": "validation", "name": "Validate Input", "config": {...}},
    #   {"step_id": 2, "type": "api_call", "name": "Generate Salary", "config": {...}},
    #   {"step_id": 3, "type": "notification", "name": "Notify Employee", "config": {...}}
    # ]
    
    # Trigger Configuration
    triggers = Column(JSON, nullable=True)
    # Structure: {
    #   "scheduled": {"cron": "0 9 1 * *", "description": "First of every month at 9 AM"},
    #   "event_based": ["employee_month_complete"],
    #   "threshold": {"field": "pending_count", "operator": ">", "value": 10}
    # }
    
    # AI Agent Instructions
    agent_instructions = Column(Text, nullable=True)
    # Natural language instructions for the AI agent handling this workflow
    
    # Metadata
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System templates cannot be deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)
    
    # Relationships
    work_items = relationship("WorkItem", back_populates="workflow_template")
    priority_rules = relationship("PriorityRule", back_populates="workflow_template")
    suggestion_rules = relationship("SuggestionRule", back_populates="workflow_template")
    
    __table_args__ = (
        Index('idx_workflow_category_task', 'category', 'task_type'),
        Index('idx_workflow_active', 'is_active'),
    )


class WorkflowStep(Base):
    """
    Individual steps within a workflow template.
    Allows for more complex step definitions separate from the template.
    """
    __tablename__ = "orchestration_workflow_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("orchestration_workflow_templates.id"), nullable=False)
    
    # Step Configuration
    step_order = Column(Integer, nullable=False)
    step_type = Column(SQLEnum(WorkflowStepType), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Step-specific Configuration
    config = Column(JSON, nullable=False, default=dict)
    # For API_CALL: {"endpoint": "/api/v1/...", "method": "POST", "body_mapping": {...}}
    # For VALIDATION: {"rules": [...], "fail_action": "stop|skip|warn"}
    # For DECISION: {"condition": "...", "true_step": 3, "false_step": 4}
    # For USER_INPUT: {"fields": [...], "timeout_minutes": 30}
    
    # Conditional Execution
    condition = Column(JSON, nullable=True)
    # Structure: {"field": "previous_result.status", "operator": "==", "value": "success"}
    
    # Error Handling
    on_error = Column(String(50), default="stop")  # stop, skip, retry, escalate
    retry_count = Column(Integer, default=0)
    retry_delay_seconds = Column(Integer, default=60)
    
    # Timeout
    timeout_seconds = Column(Integer, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('template_id', 'step_order', name='uq_template_step_order'),
    )


# ==================== WORK ITEM (TASK) MODELS ====================

class WorkItem(Base):
    """
    Individual work items (tasks) created from workflow templates.
    Represents actual tasks that need to be executed.
    """
    __tablename__ = "orchestration_work_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference to Template
    template_id = Column(Integer, ForeignKey("orchestration_workflow_templates.id"), nullable=False)
    template_code = Column(String(50), nullable=False)  # Denormalized for quick access
    
    # Task Identification
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    reference_id = Column(String(100), nullable=True)  # External reference (e.g., employee_id:123)
    
    # Categorization (denormalized from template)
    category = Column(SQLEnum(TaskCategory), nullable=False, index=True)
    task_type = Column(SQLEnum(TaskType), nullable=False, index=True)
    
    # Assignment
    assigned_to_role = Column(SQLEnum(AgentRole), nullable=True, index=True)
    assigned_to_user_id = Column(Integer, nullable=True, index=True)
    assigned_agent = Column(SQLEnum(AgentType), nullable=True)
    
    # Status & Priority
    status = Column(SQLEnum(WorkItemStatus), default=WorkItemStatus.PENDING, index=True)
    priority = Column(SQLEnum(WorkItemPriority), default=WorkItemPriority.MEDIUM, index=True)
    priority_score = Column(Float, default=50.0, index=True)  # Calculated score for sorting
    
    # Input/Output Data
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=True)
    
    # Execution Context
    execution_mode = Column(SQLEnum(ExecutionMode), nullable=False)
    current_step = Column(Integer, default=0)
    step_results = Column(JSON, default=list)
    # Structure: [{"step_id": 1, "status": "completed", "result": {...}, "executed_at": "..."}]
    
    # AI Agent Context
    agent_context = Column(JSON, nullable=True)
    # Structure: {
    #   "conversation_history": [...],
    #   "user_preferences": {...},
    #   "suggested_actions": [...]
    # }
    
    # Timing
    due_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Error Handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Parent/Child Relationship (for sub-tasks)
    parent_id = Column(Integer, ForeignKey("orchestration_work_items.id"), nullable=True)
    
    # Trigger Information
    trigger_type = Column(SQLEnum(TriggerType), nullable=True)
    triggered_by = Column(String(100), nullable=True)  # user_id, schedule_name, event_name
    
    # Metadata
    is_suggestion = Column(Boolean, default=False)  # True if AI-suggested task
    is_automated = Column(Boolean, default=False)   # True if running automatically
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)
    
    # Relationships
    workflow_template = relationship("WorkflowTemplate", back_populates="work_items")
    children = relationship("WorkItem", backref="parent", remote_side=[id])
    execution_logs = relationship("WorkItemExecutionLog", back_populates="work_item")
    
    __table_args__ = (
        Index('idx_workitem_status_priority', 'status', 'priority_score'),
        Index('idx_workitem_role_status', 'assigned_to_role', 'status'),
        Index('idx_workitem_user_status', 'assigned_to_user_id', 'status'),
        Index('idx_workitem_due_date', 'due_date'),
    )


class WorkItemExecutionLog(Base):
    """
    Detailed execution logs for work items.
    Tracks every step, decision, and action taken during execution.
    """
    __tablename__ = "orchestration_work_item_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    work_item_id = Column(Integer, ForeignKey("orchestration_work_items.id"), nullable=False)
    
    # Log Entry
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    log_level = Column(String(20), default="INFO")  # DEBUG, INFO, WARNING, ERROR
    
    # What happened
    action = Column(String(100), nullable=False)  # step_executed, decision_made, error_occurred
    step_id = Column(Integer, nullable=True)
    agent_type = Column(SQLEnum(AgentType), nullable=True)
    
    # Details
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    
    # Result
    status = Column(String(50), nullable=True)  # success, failed, skipped
    duration_ms = Column(Integer, nullable=True)
    
    # User Interaction
    user_id = Column(Integer, nullable=True)
    user_action = Column(String(100), nullable=True)
    
    work_item = relationship("WorkItem", back_populates="execution_logs")
    
    __table_args__ = (
        Index('idx_log_workitem_timestamp', 'work_item_id', 'timestamp'),
    )


# ==================== PRIORITY RULE MODELS ====================

class PriorityRule(Base):
    """
    Defines rules for calculating work item priority.
    Uses weighted scoring to determine execution order.
    """
    __tablename__ = "orchestration_priority_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Rule Identification
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Scope
    template_id = Column(Integer, ForeignKey("orchestration_workflow_templates.id"), nullable=True)
    category = Column(SQLEnum(TaskCategory), nullable=True)  # If null, applies globally
    task_type = Column(SQLEnum(TaskType), nullable=True)
    
    # Rule Configuration
    rule_type = Column(String(50), nullable=False)
    # Types: "base_priority", "deadline_proximity", "user_role", "data_condition", "time_based", "dependency"
    
    # Weight Configuration
    base_weight = Column(Float, default=1.0)  # Multiplier for this rule
    max_score_contribution = Column(Float, default=100.0)  # Maximum score this rule can add
    
    # Condition
    condition = Column(JSON, nullable=False)
    # Examples:
    # For deadline_proximity: {"days_until_due": {"<": 1}, "score_formula": "100 - (days_until_due * 10)"}
    # For data_condition: {"field": "input_data.amount", "operator": ">", "value": 10000, "score": 25}
    # For user_role: {"role": "hr_manager", "base_boost": 10}
    # For time_based: {"time_range": {"start": "09:00", "end": "17:00"}, "boost": 5}
    
    # Score Calculation
    score_formula = Column(Text, nullable=True)
    # Python expression for complex calculations: "min(100, base_weight * (100 - days_until_due * 10))"
    
    # Priority Mapping (for base_priority type)
    priority_weights = Column(JSON, nullable=True)
    # Structure: {"critical": 100, "high": 75, "medium": 50, "low": 25, "background": 10}
    
    # Application Order
    evaluation_order = Column(Integer, default=100)  # Lower = evaluated first
    
    # Flags
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)
    is_additive = Column(Boolean, default=True)  # If true, adds to score; if false, multiplies
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)
    
    # Relationships
    workflow_template = relationship("WorkflowTemplate", back_populates="priority_rules")
    
    __table_args__ = (
        Index('idx_priority_rule_category', 'category', 'task_type'),
        Index('idx_priority_rule_order', 'evaluation_order'),
    )


class PriorityRuleApplication(Base):
    """
    Tracks which priority rules were applied to which work items.
    Useful for debugging and auditing priority calculations.
    """
    __tablename__ = "orchestration_priority_rule_applications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    work_item_id = Column(Integer, ForeignKey("orchestration_work_items.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("orchestration_priority_rules.id"), nullable=False)
    
    # Application Result
    score_contribution = Column(Float, nullable=False)
    rule_matched = Column(Boolean, default=True)
    evaluation_details = Column(JSON, nullable=True)  # What values were used in evaluation
    
    applied_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_rule_application_workitem', 'work_item_id'),
    )


# ==================== KNOWLEDGE GRAPH / DOMAIN EXPERTISE ====================

class DomainKnowledge(Base):
    """
    Stores domain expertise and knowledge for AI agents.
    This feeds into the Intent Classifier and Planning Agent.
    """
    __tablename__ = "orchestration_domain_knowledge"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Knowledge Identification
    category = Column(SQLEnum(TaskCategory), nullable=False, index=True)
    knowledge_type = Column(String(50), nullable=False)
    # Types: "intent_pattern", "business_rule", "domain_term", "procedure", "constraint"
    
    # Content
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    
    # For Intent Classification
    intent_patterns = Column(JSON, nullable=True)
    # Structure: ["generate salary", "create payroll", "process payment for employee"]
    
    # For Planning
    related_templates = Column(JSON, nullable=True)  # List of template_codes
    prerequisites = Column(JSON, nullable=True)  # List of required conditions
    
    # Metadata
    confidence_score = Column(Float, default=1.0)  # How reliable is this knowledge
    source = Column(String(200), nullable=True)  # Where did this knowledge come from
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_knowledge_category_type', 'category', 'knowledge_type'),
    )


# ==================== USER/ROLE CONTEXT ====================

class UserAgentContext(Base):
    """
    Stores user-specific context for AI agents.
    Tracks preferences, history, and personalization data.
    """
    __tablename__ = "orchestration_user_agent_context"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    
    # Role Information
    primary_role = Column(SQLEnum(AgentRole), nullable=False)
    additional_roles = Column(JSON, default=list)  # List of AgentRole values
    
    # Preferences
    preferences = Column(JSON, default=dict)
    # Structure: {
    #   "notification_level": "all|important|minimal",
    #   "auto_approve_threshold": 1000,
    #   "preferred_view": "list|kanban|calendar",
    #   "default_filters": {...}
    # }
    
    # Recent Activity (for suggestions)
    recent_tasks = Column(JSON, default=list)  # Last N task types executed
    frequent_actions = Column(JSON, default=dict)  # Action -> count mapping
    
    # AI Interaction History
    conversation_context = Column(JSON, nullable=True)  # Current conversation state
    
    # Metrics
    tasks_completed_today = Column(Integer, default=0)
    avg_task_completion_time = Column(Float, nullable=True)  # In minutes
    
    last_login_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== SUGGESTION CONFIGURATION ====================

class SuggestionRule(Base):
    """
    Defines rules for the Suggestion Agent to propose tasks.
    These are evaluated when a user logs in with a specific role.
    """
    __tablename__ = "orchestration_suggestion_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Rule Identification
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Targeting
    target_role = Column(SQLEnum(AgentRole), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("orchestration_workflow_templates.id"), nullable=False)
    
    # Condition for Suggestion
    condition = Column(JSON, nullable=False)
    # Examples:
    # {"type": "time_based", "day_of_month": 1, "description": "First of month - salary time"}
    # {"type": "data_threshold", "query": "pending_attendance_count", "operator": ">", "value": 0}
    # {"type": "event_based", "event": "month_end_approaching", "days_before": 3}
    # {"type": "periodic", "last_execution_days_ago": {">=": 7}}
    
    # Suggestion Content
    suggestion_title = Column(String(300), nullable=False)
    suggestion_message = Column(Text, nullable=False)
    suggestion_priority = Column(SQLEnum(WorkItemPriority), default=WorkItemPriority.MEDIUM)
    
    # Pre-filled Data
    default_input_data = Column(JSON, nullable=True)
    
    # Scheduling
    check_frequency_minutes = Column(Integer, default=60)  # How often to evaluate
    max_suggestions_per_day = Column(Integer, default=1)
    
    # Flags
    is_active = Column(Boolean, default=True)
    is_dismissible = Column(Boolean, default=True)  # Can user dismiss this suggestion
    auto_create_task = Column(Boolean, default=False)  # Automatically create work item
    
    # Metrics
    times_suggested = Column(Integer, default=0)
    times_accepted = Column(Integer, default=0)
    times_dismissed = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_suggestion_role_active', 'target_role', 'is_active'),
    )

    # Relationships
    workflow_template = relationship("WorkflowTemplate", back_populates="suggestion_rules")