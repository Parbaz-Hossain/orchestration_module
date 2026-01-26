"""
Seed Data - Priority Rules
Predefined priority rules for work item scoring
"""
from typing import List, Dict, Any


def get_default_priority_rules() -> List[Dict[str, Any]]:
    """Returns predefined priority rules"""
    return [
        {
            "name": "Base Priority Score",
            "code": "PRIORITY_BASE",
            "description": "Maps priority levels to base scores",
            "rule_type": "base_priority",
            "base_weight": 1.0,
            "max_score_contribution": 100,
            "condition": {},
            "priority_weights": {"critical": 100, "high": 75, "medium": 50, "low": 25, "background": 10},
            "evaluation_order": 1,
            "is_additive": True
        },
        {
            "name": "Overdue Task Boost",
            "code": "PRIORITY_OVERDUE",
            "description": "Maximum boost for overdue items",
            "rule_type": "deadline_proximity",
            "base_weight": 2.0,
            "max_score_contribution": 100,
            "condition": {"days_until_due": {"<": 0}},
            "score_formula": "base_weight * 100",
            "evaluation_order": 5,
            "is_additive": True
        },
        {
            "name": "Urgent Deadline (24h)",
            "code": "PRIORITY_URGENT_24H",
            "description": "High boost for tasks due within 24 hours",
            "rule_type": "deadline_proximity",
            "base_weight": 1.5,
            "max_score_contribution": 75,
            "condition": {"days_until_due": {"<=": 1, ">": 0}},
            "score_formula": "base_weight * 75",
            "evaluation_order": 10,
            "is_additive": True
        },
        {
            "name": "Approaching Deadline (3 days)",
            "code": "PRIORITY_APPROACHING_3D",
            "description": "Moderate boost for tasks due within 3 days",
            "rule_type": "deadline_proximity",
            "base_weight": 1.2,
            "max_score_contribution": 50,
            "condition": {"days_until_due": {"<=": 3, ">": 1}},
            "score_formula": "base_weight * 50",
            "evaluation_order": 11,
            "is_additive": True
        },
        {
            "name": "Week Deadline",
            "code": "PRIORITY_WEEK",
            "description": "Small boost for tasks due within a week",
            "rule_type": "deadline_proximity",
            "base_weight": 1.0,
            "max_score_contribution": 20,
            "condition": {"days_until_due": {"<=": 7, ">": 3}},
            "score_formula": "base_weight * 20",
            "evaluation_order": 12,
            "is_additive": True
        },
        {
            "name": "Business Hours Boost",
            "code": "PRIORITY_BUSINESS_HOURS",
            "description": "Slight boost during business hours",
            "rule_type": "time_based",
            "base_weight": 1.0,
            "max_score_contribution": 10,
            "condition": {"time_range": {"start": "09:00", "end": "18:00"}, "boost": 10},
            "evaluation_order": 50,
            "is_additive": True
        },
        {
            "name": "First of Month HR Tasks",
            "code": "PRIORITY_MONTH_START_HR",
            "description": "Boost HR tasks on first 5 days of month",
            "category": "hr",
            "rule_type": "time_based",
            "base_weight": 1.5,
            "max_score_contribution": 25,
            "condition": {"day_of_month_range": {"start": 1, "end": 5}, "boost": 25},
            "evaluation_order": 30,
            "is_additive": True
        },
        {
            "name": "High Value Transaction",
            "code": "PRIORITY_HIGH_VALUE",
            "description": "Boost for high-value transactions (> 10,000)",
            "rule_type": "data_condition",
            "base_weight": 1.0,
            "max_score_contribution": 25,
            "condition": {"field": "input_data.amount", "operator": ">", "value": 10000, "score": 25},
            "evaluation_order": 40,
            "is_additive": True
        }
    ]