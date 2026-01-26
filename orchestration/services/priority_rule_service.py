"""
Priority Rule Service
Manages priority rules and calculates work item priority scores
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration_models import PriorityRule, PriorityRuleApplication, WorkItem
from ..models.enums import TaskCategory, TaskType, WorkItemPriority
from ..schemas.orchestration_schemas import (
    PriorityRuleCreate, PriorityRuleUpdate, PriorityRuleResponse
)

logger = logging.getLogger(__name__)


class PriorityRuleService:
    """
    Service for managing priority rules.
    Priority rules define how work items are scored for execution order.
    
    Rule Types:
    - base_priority: Maps WorkItemPriority enum to numeric scores
    - deadline_proximity: Increases score as due date approaches
    - data_condition: Adjusts score based on input data values
    - time_based: Adjusts score based on current time
    - user_role: Adjusts score based on assigned role
    - dependency: Adjusts score based on related work items
    """
    
    # Default priority weights
    DEFAULT_PRIORITY_WEIGHTS = {
        "critical": 100,
        "high": 75,
        "medium": 50,
        "low": 25,
        "background": 10
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_rule(
        self,
        data: PriorityRuleCreate,
        created_by: int
    ) -> PriorityRuleResponse:
        """Create a new priority rule"""
        # Check for duplicate code
        existing = await self.session.execute(
            select(PriorityRule).where(PriorityRule.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Priority rule with code '{data.code}' already exists")
        
        rule = PriorityRule(
            name=data.name,
            code=data.code,
            description=data.description,
            template_id=data.template_id,
            category=data.category,
            task_type=data.task_type,
            rule_type=data.rule_type,
            base_weight=data.base_weight,
            max_score_contribution=data.max_score_contribution,
            condition=data.condition,
            score_formula=data.score_formula,
            priority_weights=data.priority_weights or self.DEFAULT_PRIORITY_WEIGHTS,
            evaluation_order=data.evaluation_order,
            is_additive=data.is_additive,
            created_by=created_by
        )
        
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        
        return self._to_response(rule)
    
    async def update_rule(
        self,
        rule_id: int,
        data: PriorityRuleUpdate,
        updated_by: int
    ) -> PriorityRuleResponse:
        """Update a priority rule"""
        result = await self.session.execute(
            select(PriorityRule).where(PriorityRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise ValueError(f"Priority rule not found: {rule_id}")
        
        if rule.is_system:
            raise ValueError("System rules cannot be modified")
        
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        
        rule.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(rule)
        
        return self._to_response(rule)
    
    async def get_rule(self, rule_id: int) -> Optional[PriorityRuleResponse]:
        """Get a priority rule by ID"""
        result = await self.session.execute(
            select(PriorityRule).where(PriorityRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        
        if rule:
            return self._to_response(rule)
        return None
    
    async def get_rules(
        self,
        page_index: int = 1,
        page_size: int = 50,
        category: Optional[TaskCategory] = None,
        task_type: Optional[TaskType] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Get priority rules with filtering"""
        query = select(PriorityRule)
        count_query = select(func.count(PriorityRule.id))
        
        conditions = []
        
        if category:
            conditions.append(
                or_(
                    PriorityRule.category == category,
                    PriorityRule.category.is_(None)
                )
            )
        
        if task_type:
            conditions.append(
                or_(
                    PriorityRule.task_type == task_type,
                    PriorityRule.task_type.is_(None)
                )
            )
        
        if rule_type:
            conditions.append(PriorityRule.rule_type == rule_type)
        
        if is_active is not None:
            conditions.append(PriorityRule.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar()
        
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(PriorityRule.evaluation_order)
        
        result = await self.session.execute(query)
        rules = result.scalars().all()
        
        return {
            "items": [self._to_response(r) for r in rules],
            "total_count": total_count,
            "page_index": page_index,
            "page_size": page_size
        }
    
    async def delete_rule(self, rule_id: int, deleted_by: int) -> bool:
        """Soft delete a priority rule"""
        result = await self.session.execute(
            select(PriorityRule).where(PriorityRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        
        if not rule:
            return False
        
        if rule.is_system:
            raise ValueError("System rules cannot be deleted")
        
        rule.is_active = False
        rule.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return True
    
    async def calculate_priority_score(
        self,
        work_item: WorkItem
    ) -> float:
        """
        Calculate the priority score for a work item using all applicable rules.
        
        Returns a score between 0 and 200.
        Higher score = higher priority = processed first.
        """
        # Get base score from priority level
        base_score = self.DEFAULT_PRIORITY_WEIGHTS.get(
            work_item.priority.value if work_item.priority else "medium",
            50
        )
        
        # Get applicable rules
        rules = await self._get_applicable_rules(work_item)
        
        total_additive = 0.0
        total_multiplier = 1.0
        
        for rule in rules:
            try:
                score_contribution = self._evaluate_rule(rule, work_item)
                
                if score_contribution is not None:
                    # Record rule application
                    application = PriorityRuleApplication(
                        work_item_id=work_item.id,
                        rule_id=rule.id,
                        score_contribution=score_contribution,
                        rule_matched=True,
                        evaluation_details={
                            "rule_code": rule.code,
                            "rule_type": rule.rule_type,
                            "base_weight": rule.base_weight,
                            "is_additive": rule.is_additive
                        }
                    )
                    self.session.add(application)
                    
                    # Apply score
                    capped_score = min(score_contribution, rule.max_score_contribution)
                    
                    if rule.is_additive:
                        total_additive += capped_score
                    else:
                        total_multiplier *= (1 + capped_score / 100)
                        
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.code}: {e}")
        
        # Calculate final score
        final_score = (base_score + total_additive) * total_multiplier
        
        # Clamp to valid range
        return max(0.0, min(200.0, final_score))
    
    async def _get_applicable_rules(self, work_item: WorkItem) -> List[PriorityRule]:
        """Get all rules applicable to a work item"""
        result = await self.session.execute(
            select(PriorityRule).where(
                and_(
                    PriorityRule.is_active == True,
                    # Match template or global (null template_id)
                    or_(
                        PriorityRule.template_id == work_item.template_id,
                        PriorityRule.template_id.is_(None)
                    ),
                    # Match category or global
                    or_(
                        PriorityRule.category == work_item.category,
                        PriorityRule.category.is_(None)
                    ),
                    # Match task type or global
                    or_(
                        PriorityRule.task_type == work_item.task_type,
                        PriorityRule.task_type.is_(None)
                    )
                )
            ).order_by(PriorityRule.evaluation_order)
        )
        return result.scalars().all()
    
    def _evaluate_rule(
        self,
        rule: PriorityRule,
        work_item: WorkItem
    ) -> Optional[float]:
        """
        Evaluate a single priority rule against a work item.
        Returns the score contribution, or None if the rule doesn't apply.
        """
        condition = rule.condition
        
        if rule.rule_type == "base_priority":
            # This is the base score, already handled
            return None
        
        elif rule.rule_type == "deadline_proximity":
            return self._evaluate_deadline_rule(rule, work_item)
        
        elif rule.rule_type == "data_condition":
            return self._evaluate_data_condition_rule(rule, work_item)
        
        elif rule.rule_type == "time_based":
            return self._evaluate_time_based_rule(rule, work_item)
        
        elif rule.rule_type == "user_role":
            return self._evaluate_role_rule(rule, work_item)
        
        else:
            logger.warning(f"Unknown rule type: {rule.rule_type}")
            return None
    
    def _evaluate_deadline_rule(
        self,
        rule: PriorityRule,
        work_item: WorkItem
    ) -> Optional[float]:
        """Evaluate deadline proximity rule"""
        if not work_item.due_date:
            return None
        
        now = datetime.utcnow()
        time_until_due = work_item.due_date - now
        days_until_due = time_until_due.days + (time_until_due.seconds / 86400)
        
        condition = rule.condition
        
        # Check if condition is met
        if "days_until_due" in condition:
            threshold = condition["days_until_due"]
            if isinstance(threshold, dict):
                for op, val in threshold.items():
                    if op == "<" and not (days_until_due < val):
                        return None
                    if op == "<=" and not (days_until_due <= val):
                        return None
                    if op == ">" and not (days_until_due > val):
                        return None
                    if op == ">=" and not (days_until_due >= val):
                        return None
        
        # Calculate score
        if rule.score_formula:
            try:
                # Safe evaluation of formula
                local_vars = {
                    "days_until_due": days_until_due,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "base_weight": rule.base_weight
                }
                return eval(rule.score_formula, {"__builtins__": {}}, local_vars)
            except Exception as e:
                logger.error(f"Error evaluating score formula: {e}")
                return None
        else:
            # Default formula: closer deadline = higher score
            if days_until_due <= 0:
                return rule.base_weight * 100  # Overdue
            elif days_until_due <= 1:
                return rule.base_weight * 75
            elif days_until_due <= 3:
                return rule.base_weight * 50
            elif days_until_due <= 7:
                return rule.base_weight * 25
            else:
                return rule.base_weight * 10
    
    def _evaluate_data_condition_rule(
        self,
        rule: PriorityRule,
        work_item: WorkItem
    ) -> Optional[float]:
        """Evaluate data condition rule"""
        condition = rule.condition
        
        field_path = condition.get("field", "")
        operator = condition.get("operator", "==")
        expected_value = condition.get("value")
        score = condition.get("score", 10)
        
        # Get actual value from input_data
        actual_value = self._get_nested_value(work_item.input_data, field_path)
        
        if self._check_condition(actual_value, operator, expected_value):
            return rule.base_weight * score
        
        return None
    
    def _evaluate_time_based_rule(
        self,
        rule: PriorityRule,
        work_item: WorkItem
    ) -> Optional[float]:
        """Evaluate time-based rule"""
        condition = rule.condition
        now = datetime.utcnow()
        
        time_range = condition.get("time_range", {})
        
        if "start" in time_range and "end" in time_range:
            start_hour = int(time_range["start"].split(":")[0])
            end_hour = int(time_range["end"].split(":")[0])
            
            if start_hour <= now.hour <= end_hour:
                return rule.base_weight * condition.get("boost", 10)
        
        if "day_of_week" in condition:
            if now.weekday() == condition["day_of_week"]:
                return rule.base_weight * condition.get("boost", 10)
        
        if "day_of_month" in condition:
            if now.day == condition["day_of_month"]:
                return rule.base_weight * condition.get("boost", 10)
        
        return None
    
    def _evaluate_role_rule(
        self,
        rule: PriorityRule,
        work_item: WorkItem
    ) -> Optional[float]:
        """Evaluate user role rule"""
        condition = rule.condition
        target_role = condition.get("role")
        
        if work_item.assigned_to_role and work_item.assigned_to_role.value == target_role:
            return rule.base_weight * condition.get("base_boost", 10)
        
        return None
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get a nested value from a dictionary using dot notation"""
        if not data or not path:
            return None
        
        # Remove input_data. prefix if present
        path = path.replace("input_data.", "")
        
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    def _check_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Check if a condition is met"""
        if actual is None:
            return False
        
        try:
            operators = {
                "==": lambda a, e: a == e,
                "!=": lambda a, e: a != e,
                ">": lambda a, e: a > e,
                ">=": lambda a, e: a >= e,
                "<": lambda a, e: a < e,
                "<=": lambda a, e: a <= e,
                "in": lambda a, e: a in e,
                "not_in": lambda a, e: a not in e,
                "contains": lambda a, e: e in a,
                "starts_with": lambda a, e: str(a).startswith(str(e)),
                "ends_with": lambda a, e: str(a).endswith(str(e)),
            }
            
            return operators.get(operator, lambda a, e: False)(actual, expected)
        except Exception:
            return False
    
    def _to_response(self, rule: PriorityRule) -> PriorityRuleResponse:
        """Convert to response schema"""
        return PriorityRuleResponse(
            id=rule.id,
            name=rule.name,
            code=rule.code,
            description=rule.description,
            template_id=rule.template_id,
            category=rule.category,
            task_type=rule.task_type,
            rule_type=rule.rule_type,
            base_weight=rule.base_weight,
            max_score_contribution=rule.max_score_contribution,
            condition=rule.condition,
            score_formula=rule.score_formula,
            priority_weights=rule.priority_weights,
            evaluation_order=rule.evaluation_order,
            is_active=rule.is_active,
            is_system=rule.is_system,
            is_additive=rule.is_additive,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )


# ==================== PREDEFINED PRIORITY RULES ====================

def get_default_priority_rules() -> List[Dict[str, Any]]:
    """
    Returns predefined priority rules for system initialization.
    """
    return [
        {
            "name": "Base Priority Score",
            "code": "PRIORITY_BASE_SCORE",
            "description": "Maps priority levels to base scores",
            "rule_type": "base_priority",
            "base_weight": 1.0,
            "max_score_contribution": 100,
            "condition": {},
            "priority_weights": {
                "critical": 100,
                "high": 75,
                "medium": 50,
                "low": 25,
                "background": 10
            },
            "evaluation_order": 1,
            "is_system": True,
            "is_additive": True
        },
        {
            "name": "Urgent Deadline (24h)",
            "code": "PRIORITY_DEADLINE_24H",
            "description": "Boost priority for items due within 24 hours",
            "rule_type": "deadline_proximity",
            "base_weight": 1.5,
            "max_score_contribution": 75,
            "condition": {
                "days_until_due": {"<=": 1}
            },
            "score_formula": "base_weight * max(0, 75 - days_until_due * 25)",
            "evaluation_order": 10,
            "is_system": True,
            "is_additive": True
        },
        {
            "name": "Approaching Deadline (7 days)",
            "code": "PRIORITY_DEADLINE_7D",
            "description": "Moderate boost for items due within 7 days",
            "rule_type": "deadline_proximity",
            "base_weight": 1.0,
            "max_score_contribution": 30,
            "condition": {
                "days_until_due": {"<=": 7, ">": 1}
            },
            "score_formula": "base_weight * max(0, 30 - days_until_due * 3)",
            "evaluation_order": 11,
            "is_system": True,
            "is_additive": True
        },
        {
            "name": "Overdue Task",
            "code": "PRIORITY_OVERDUE",
            "description": "Maximum boost for overdue items",
            "rule_type": "deadline_proximity",
            "base_weight": 2.0,
            "max_score_contribution": 100,
            "condition": {
                "days_until_due": {"<": 0}
            },
            "score_formula": "base_weight * 100",
            "evaluation_order": 5,
            "is_system": True,
            "is_additive": True
        },
        {
            "name": "Business Hours Boost",
            "code": "PRIORITY_BUSINESS_HOURS",
            "description": "Slight boost during business hours (9 AM - 5 PM)",
            "rule_type": "time_based",
            "base_weight": 1.0,
            "max_score_contribution": 10,
            "condition": {
                "time_range": {"start": "09:00", "end": "17:00"},
                "boost": 10
            },
            "evaluation_order": 50,
            "is_system": False,
            "is_additive": True
        },
        {
            "name": "HR Manager Priority",
            "code": "PRIORITY_HR_MANAGER",
            "description": "Boost HR tasks assigned to HR managers",
            "category": "hr",
            "rule_type": "user_role",
            "base_weight": 1.0,
            "max_score_contribution": 15,
            "condition": {
                "role": "hr_manager",
                "base_boost": 15
            },
            "evaluation_order": 30,
            "is_system": False,
            "is_additive": True
        },
        {
            "name": "High Amount Transaction",
            "code": "PRIORITY_HIGH_AMOUNT",
            "description": "Boost priority for high-value transactions",
            "rule_type": "data_condition",
            "base_weight": 1.0,
            "max_score_contribution": 25,
            "condition": {
                "field": "input_data.amount",
                "operator": ">",
                "value": 10000,
                "score": 25
            },
            "evaluation_order": 40,
            "is_system": False,
            "is_additive": True
        }
    ]