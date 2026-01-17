"""Custom exceptions for the orchestration module"""
from typing import Optional, Dict, Any


class OrchestrationError(Exception):
    """Base exception for orchestration errors"""
    
    def __init__(
        self, 
        message: str, 
        code: str = "ORCHESTRATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class WorkflowNotFoundError(OrchestrationError):
    """Raised when a workflow instance is not found"""
    
    def __init__(self, workflow_id: str):
        super().__init__(
            message=f"Workflow not found: {workflow_id}",
            code="WORKFLOW_NOT_FOUND",
            details={"workflow_id": workflow_id}
        )


class SessionExpiredError(OrchestrationError):
    """Raised when a session has expired"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session expired: {session_id}",
            code="SESSION_EXPIRED",
            details={"session_id": session_id}
        )


class InvalidStateTransitionError(OrchestrationError):
    """Raised when an invalid state transition is attempted"""
    
    def __init__(self, from_state: str, to_state: str, reason: str = None):
        super().__init__(
            message=f"Invalid transition from {from_state} to {to_state}",
            code="INVALID_TRANSITION",
            details={
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason
            }
        )


class SagaCompensationError(OrchestrationError):
    """Raised when saga compensation fails"""
    
    def __init__(self, saga_id: str, step: str, original_error: str):
        super().__init__(
            message=f"Saga compensation failed at step {step}",
            code="SAGA_COMPENSATION_FAILED",
            details={
                "saga_id": saga_id,
                "step": step,
                "original_error": original_error
            }
        )


class ValidationError(OrchestrationError):
    """Raised when input validation fails"""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            message=f"Validation failed for {field}: {reason}",
            code="VALIDATION_ERROR",
            details={
                "field": field,
                "value": value,
                "reason": reason
            }
        )


class PermissionDeniedError(OrchestrationError):
    """Raised when user lacks required permissions"""
    
    def __init__(self, user_id: int, action: str, resource: str):
        super().__init__(
            message=f"Permission denied for action {action} on {resource}",
            code="PERMISSION_DENIED",
            details={
                "user_id": user_id,
                "action": action,
                "resource": resource
            }
        )