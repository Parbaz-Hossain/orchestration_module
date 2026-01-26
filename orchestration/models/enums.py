"""
Orchestration Module Enums
Defines all enumeration types for the orchestration system
"""
from enum import Enum


class AgentRole(str, Enum):
    """User roles that map to specific AI agents"""
    HR_MANAGER = "hr_manager"
    PURCHASE_MANAGER = "purchase_manager"
    INVENTORY_MANAGER = "inventory_manager"
    SALES_MANAGER = "sales_manager"
    FINANCE_MANAGER = "finance_manager"
    OPERATIONS_MANAGER = "operations_manager"
    GENERAL_MANAGER = "general_manager"
    SUPER_ADMIN = "super_admin"


class WorkItemStatus(str, Enum):
    """Status of work items in the system"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class WorkItemPriority(str, Enum):
    """Priority levels for work items"""
    CRITICAL = "critical"      # Weight: 100
    HIGH = "high"              # Weight: 75
    MEDIUM = "medium"          # Weight: 50
    LOW = "low"                # Weight: 25
    BACKGROUND = "background"  # Weight: 10


class TaskCategory(str, Enum):
    """Categories of tasks mapped to domain modules"""
    HR = "hr"
    INVENTORY = "inventory"
    PURCHASE = "purchase"
    LOGISTICS = "logistics"
    REPORTING = "reporting"
    APPROVAL = "approval"


class TaskType(str, Enum):
    """Specific task types within categories"""
    # HR Tasks
    ATTENDANCE_REVIEW = "attendance_review"
    SALARY_GENERATION = "salary_generation"
    LEAVE_APPROVAL = "leave_approval"
    SHIFT_ASSIGNMENT = "shift_assignment"
    EMPLOYEE_ONBOARDING = "employee_onboarding"
    DEDUCTION_PROCESSING = "deduction_processing"
    TICKET_RESOLUTION = "ticket_resolution"
    
    # Inventory Tasks
    STOCK_CHECK = "stock_check"
    REORDER_ALERT = "reorder_alert"
    INVENTORY_AUDIT = "inventory_audit"
    WASTAGE_REPORT = "wastage_report"
    
    # Purchase Tasks
    PURCHASE_ORDER_CREATE = "purchase_order_create"
    SUPPLIER_EVALUATION = "supplier_evaluation"
    PRICE_COMPARISON = "price_comparison"
    DELIVERY_TRACKING = "delivery_tracking"
    
    # General Tasks
    DAILY_SUMMARY = "daily_summary"
    CUSTOM_REPORT = "custom_report"
    DATA_EXPORT = "data_export"


class ExecutionMode(str, Enum):
    """How a task should be executed"""
    AUTOMATIC = "automatic"         # AI executes without user input
    SEMI_AUTOMATIC = "semi_automatic"  # AI prepares, user confirms
    MANUAL = "manual"               # AI guides, user executes
    APPROVAL_REQUIRED = "approval_required"  # Needs manager approval


class AgentType(str, Enum):
    """Types of AI agents in the system"""
    SUGGESTION_AGENT = "suggestion_agent"
    CLASSIFIER_AGENT = "classifier_agent"
    PLANNING_AGENT = "planning_agent"
    HR_AGENT = "hr_agent"
    INVENTORY_AGENT = "inventory_agent"
    PURCHASE_AGENT = "purchase_agent"
    LOGISTICS_AGENT = "logistics_agent"
    REPORTING_AGENT = "reporting_agent"
    EXECUTION_AGENT = "execution_agent"


class WorkflowStepType(str, Enum):
    """Types of steps in a workflow"""
    API_CALL = "api_call"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    DECISION = "decision"
    USER_INPUT = "user_input"
    NOTIFICATION = "notification"
    APPROVAL = "approval"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class TriggerType(str, Enum):
    """What triggers a workflow or task"""
    USER_LOGIN = "user_login"
    SCHEDULED = "scheduled"
    EVENT_BASED = "event_based"
    MANUAL = "manual"
    THRESHOLD = "threshold"
    API_CALL = "api_call"
    APPROVAL_RESULT = "approval_result"