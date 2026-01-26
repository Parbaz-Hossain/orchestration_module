"""
Seed Data - Suggestion Rules
Predefined suggestion rules for AI suggestions
"""
from typing import List, Dict, Any


def get_default_suggestion_rules() -> List[Dict[str, Any]]:
    """Returns predefined suggestion rules"""
    return [
        {
            "name": "Monthly Salary Generation",
            "code": "SUGGEST_MONTHLY_SALARY",
            "description": "Suggest salary generation on 25th of month",
            "target_role": "hr_manager",
            "template_code": "HR_SALARY_GENERATE",
            "condition": {
                "type": "time_based",
                "day_of_month": 25,
                "description": "25th of every month"
            },
            "suggestion_title": "Generate Monthly Salaries",
            "suggestion_message": "It's the 25th of the month. Would you like to generate salaries for all employees?",
            "suggestion_priority": "high",
            "default_input_data": {},
            "check_frequency_minutes": 60,
            "max_suggestions_per_day": 1,
            "is_dismissible": True,
            "auto_create_task": False
        },
        {
            "name": "Daily Attendance Review",
            "code": "SUGGEST_DAILY_ATTENDANCE",
            "description": "Suggest attendance review each morning",
            "target_role": "hr_manager",
            "template_code": "HR_ATTENDANCE_REVIEW",
            "condition": {
                "type": "time_based",
                "hour_range": {"start": 9, "end": 11},
                "description": "Every morning between 9-11 AM"
            },
            "suggestion_title": "Review Yesterday's Attendance",
            "suggestion_message": "Would you like to review yesterday's attendance records?",
            "suggestion_priority": "medium",
            "default_input_data": {},
            "check_frequency_minutes": 120,
            "max_suggestions_per_day": 1,
            "is_dismissible": True,
            "auto_create_task": False
        },
        {
            "name": "Weekly Shift Review",
            "code": "SUGGEST_WEEKLY_SHIFT",
            "description": "Suggest shift review on Sundays",
            "target_role": "hr_manager",
            "template_code": "HR_SHIFT_ASSIGN",
            "condition": {
                "type": "time_based",
                "day_of_week": 6,
                "description": "Every Sunday"
            },
            "suggestion_title": "Review Weekly Shift Assignments",
            "suggestion_message": "Review and confirm shift assignments for the upcoming week.",
            "suggestion_priority": "medium",
            "default_input_data": {},
            "check_frequency_minutes": 240,
            "max_suggestions_per_day": 1,
            "is_dismissible": True,
            "auto_create_task": False
        },
        {
            "name": "End of Month Salary Reminder",
            "code": "SUGGEST_END_MONTH_SALARY",
            "description": "Remind about salary preparation at end of month",
            "target_role": "hr_manager",
            "template_code": "HR_SALARY_GENERATE",
            "condition": {
                "type": "time_based",
                "day_of_month": 24,
                "description": "24th of every month"
            },
            "suggestion_title": "Prepare for Salary Generation",
            "suggestion_message": "Month end is approaching. Review attendance and deductions before salary generation.",
            "suggestion_priority": "medium",
            "default_input_data": {},
            "check_frequency_minutes": 240,
            "max_suggestions_per_day": 1,
            "is_dismissible": True,
            "auto_create_task": False
        }
    ]