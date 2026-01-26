"""
Seed Data - Workflow Templates
Predefined HR workflow templates
"""
from typing import List, Dict, Any


def get_hr_workflow_templates() -> List[Dict[str, Any]]:
    """Returns predefined HR workflow templates"""
    return [
        {
            "name": "Generate Employee Salary",
            "code": "HR_SALARY_GENERATE",
            "description": "Generate monthly salary for employees",
            "category": "hr",
            "task_type": "salary_generation",
            "execution_mode": "semi_automatic",
            "default_priority": "high",
            "target_agent": "hr_agent",
            "allowed_roles": ["hr_manager", "finance_manager"],
            "api_config": {
                "base_endpoint": "/api/v1/hr/salary",
                "method": "POST",
                "endpoints": [
                    {"name": "generate_single", "path": "/generate/{employee_id}", "method": "POST"},
                    {"name": "generate_bulk", "path": "/generate-bulk", "method": "POST"}
                ]
            },
            "input_schema": {
                "required_fields": ["employee_id", "salary_month"],
                "optional_fields": ["location_id", "department_id"],
                "field_definitions": {
                    "employee_id": {"type": "integer", "description": "Employee ID"},
                    "salary_month": {"type": "date", "format": "YYYY-MM-dd"}
                }
            },
            "business_rules": {
                "pre_conditions": [
                    {"rule": "employee_is_active", "error_message": "Employee must be active"}
                ],
                "validations": [
                    {"field": "salary_month", "rule": "not_future_date"}
                ],
                "post_actions": [
                    {"action": "notify_employee", "condition": "on_success"}
                ]
            },
            "workflow_steps": [
                {"step_id": 1, "type": "validation", "name": "Validate Input", "config": {}},
                {"step_id": 2, "type": "user_input", "name": "Review & Confirm", "config": {}},
                {"step_id": 3, "type": "api_call", "name": "Generate Salary", "config": {}},
                {"step_id": 4, "type": "notification", "name": "Notify", "config": {}}
            ],
            "triggers": {
                "scheduled": {"cron": "0 9 1 * *", "description": "First of month at 9 AM"}
            },
            "agent_instructions": "Help generate employee salary. Validate employee, get confirmation, then generate."
        },
        {
            "name": "Assign Employee Shift",
            "code": "HR_SHIFT_ASSIGN",
            "description": "Assign shift schedules to employees",
            "category": "hr",
            "task_type": "shift_assignment",
            "execution_mode": "semi_automatic",
            "default_priority": "medium",
            "target_agent": "hr_agent",
            "allowed_roles": ["hr_manager"],
            "api_config": {
                "base_endpoint": "/api/v1/hr/shift",
                "endpoints": [
                    {"name": "assign", "path": "/assign", "method": "POST"},
                    {"name": "bulk_assign", "path": "/assign/bulk", "method": "POST"}
                ]
            },
            "input_schema": {
                "required_fields": ["employee_ids", "shift_type_id","effective_date", "end_date"],
                "optional_fields": ["deduction_amount"],
                "field_definitions": {
                    "employee_ids": {"type": "array", "array_item_type": "integer"},
                    "shift_type_id": {"type": "integer"},
                    "effective_date": {"type": "date"},
                    "end_date": {"type": "date"}
                }
            },
            "business_rules": {
                "pre_conditions": [{"rule": "employees_exist", "error_message": "Employees not found"}],
                "validations": []
            },
            "workflow_steps": [
                {"step_id": 1, "type": "validation", "name": "Validate"},
                {"step_id": 2, "type": "api_call", "name": "Assign Shifts"}
            ],
            "agent_instructions": "Help assign shifts to employees."
        },
        {
            "name": "Mark Daily Attendance",
            "code": "HR_ATTENDANCE_MARK",
            "description": "Mark daily attendance for employees",
            "category": "hr",
            "task_type": "attendance_review",
            "execution_mode": "semi_automatic",
            "default_priority": "medium",
            "target_agent": "hr_agent",
            "allowed_roles": ["hr_manager"],
            "api_config": {
                "base_endpoint": "/api/v1/hr/attendance",
                "endpoints": [
                    {"name": "get", "path": "/", "method": "GET"},
                    {"name": "mark", "path": "/mark", "method": "POST"}
                ]
            },
            "input_schema": {
                "required_fields": ["employee_id","attendance_date"],
                "optional_fields": ["check_in_time", "check_out_time","remarks"],
                "field_definitions": {
                    "employee_id": {"type": "integer"},
                    "attendance_date": {"type": "date"}
                }
            },
            "business_rules": {
                "validations": [{"field": "attendance_date", "rule": "not_future_date"}]
            },
            "workflow_steps": [
                {"step_id": 1, "type": "api_call", "name": "Fetch Attendance"},
                {"step_id": 2, "type": "transformation", "name": "Identify Anomalies"},
                {"step_id": 3, "type": "user_input", "name": "Review"},
                {"step_id": 4, "type": "api_call", "name": "Process"}
            ],
            "triggers": {"scheduled": {"cron": "0 10 * * *", "description": "Daily at 10 AM"}},
            "agent_instructions": "Help review attendance. Flag anomalies."
        },
        {
            "name": "Process Employee Deduction",
            "code": "HR_DEDUCTION_PROCESS",
            "description": "Create and manage employee deductions",
            "category": "hr",
            "task_type": "deduction_processing",
            "execution_mode": "manual",
            "default_priority": "medium",
            "target_agent": "hr_agent",
            "allowed_roles": ["hr_manager", "finance_manager"],
            "api_config": {
                "base_endpoint": "/api/v1/hr/deduction",
                "endpoints": [
                    {"name": "create", "path": "/employee", "method": "POST"},
                    {"name": "forgive", "path": "/employee/{deduction_id}/forgive", "method": "PUT"}
                ]
            },
            "input_schema": {
                "required_fields": ["employee_id", "deduction_type_id", "total_amount","monthly_deduction_limit","effective_from","effective_to"],
                "optional_fields": ["description"],
                "field_definitions": {
                    "employee_id": {"type": "integer"},
                    "deduction_type_id": {"type": "integer"},
                    "total_amount": {"type": "float", "min_value": 0},
                    "monthly_deduction_limit": {"type": "float", "min_value": 0},
                    "effective_from": {"type": "date"},
                    "effective_to": {"type": "date"}
                }
            },
            "business_rules": {
                "pre_conditions": [{"rule": "employee_is_active", "error_message": "Employee must be active"}],
                "validations": [{"field": "total_amount", "rule": "positive_number"}]
            },
            "workflow_steps": [
                {"step_id": 1, "type": "validation", "name": "Validate"},
                {"step_id": 2, "type": "api_call", "name": "Create Deduction"},
                {"step_id": 3, "type": "notification", "name": "Notify Employee"}
            ],
            "agent_instructions": "Help process deductions."
        }
    ]