"""
Suggestion Service
Manages AI suggestions for users based on rules
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration_models import SuggestionRule, WorkflowTemplate, WorkItem
from ..models.enums import AgentRole, WorkItemStatus, WorkItemPriority, TaskCategory
from ..schemas.orchestration_schemas import SuggestionRuleCreate, SuggestionRuleResponse, SuggestionResponse

logger = logging.getLogger(__name__)


class SuggestionService:
    """Service for managing suggestions."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def generate_suggestions(
        self,
        role: AgentRole,
        user_id: int,
        existing_tasks: List[str],
        limit: int = 5
    ) -> List[SuggestionResponse]:
        """Generate suggestions for a user based on their role"""
        result = await self.session.execute(
            select(SuggestionRule).where(
                and_(
                    SuggestionRule.target_role == role,
                    SuggestionRule.is_active == True
                )
            )
        )
        rules = result.scalars().all()
        
        suggestions = []
        for rule in rules:
            # Get template
            template_result = await self.session.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.id == rule.template_id)
            )
            template = template_result.scalar_one_or_none()
            
            if not template or template.code in existing_tasks:
                continue
            
            # Evaluate condition
            if await self._evaluate_condition(rule, user_id):
                suggestions.append(SuggestionResponse(
                    suggestion_id=rule.id,
                    title=rule.suggestion_title,
                    message=rule.suggestion_message,
                    priority=rule.suggestion_priority,
                    template_code=template.code,
                    template_name=template.name,
                    category=template.category,
                    can_auto_create=rule.auto_create_task,
                    is_dismissible=rule.is_dismissible,
                    default_input_data=rule.default_input_data
                ))
                rule.times_suggested += 1
        
        await self.session.commit()
        
        # Sort by priority
        priority_order = {WorkItemPriority.CRITICAL: 0, WorkItemPriority.HIGH: 1,
                        WorkItemPriority.MEDIUM: 2, WorkItemPriority.LOW: 3, WorkItemPriority.BACKGROUND: 4}
        suggestions.sort(key=lambda x: priority_order.get(x.priority, 99))
        
        return suggestions[:limit]
    
    async def _evaluate_condition(self, rule: SuggestionRule, user_id: int) -> bool:
        """Evaluate if a suggestion rule condition is met"""
        condition = rule.condition
        condition_type = condition.get("type")
        now = datetime.utcnow()
        
        try:
            if condition_type == "time_based":
                if "day_of_month" in condition and now.day != condition["day_of_month"]:
                    return False
                if "day_of_week" in condition and now.weekday() != condition["day_of_week"]:
                    return False
                if "hour_range" in condition:
                    hr = condition["hour_range"]
                    if not (hr.get("start", 0) <= now.hour <= hr.get("end", 23)):
                        return False
                return True
            
            elif condition_type == "periodic":
                template_result = await self.session.execute(
                    select(WorkflowTemplate).where(WorkflowTemplate.id == rule.template_id)
                )
                template = template_result.scalar_one_or_none()
                if template:
                    last_result = await self.session.execute(
                        select(WorkItem).where(
                            and_(
                                WorkItem.template_code == template.code,
                                WorkItem.status == WorkItemStatus.COMPLETED
                            )
                        ).order_by(desc(WorkItem.completed_at)).limit(1)
                    )
                    last_item = last_result.scalar_one_or_none()
                    if last_item and last_item.completed_at:
                        days_since = (now - last_item.completed_at).days
                        threshold = condition.get("last_execution_days_ago", {})
                        for op, val in threshold.items():
                            if op == ">=" and days_since < val:
                                return False
                return True
            
            elif condition_type == "always":
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    async def accept_suggestion(self, suggestion_id: int) -> bool:
        """Mark a suggestion as accepted"""
        result = await self.session.execute(
            select(SuggestionRule).where(SuggestionRule.id == suggestion_id)
        )
        rule = result.scalar_one_or_none()
        if rule:
            rule.times_accepted += 1
            await self.session.commit()
            return True
        return False
    
    async def dismiss_suggestion(self, suggestion_id: int) -> bool:
        """Mark a suggestion as dismissed"""
        result = await self.session.execute(
            select(SuggestionRule).where(SuggestionRule.id == suggestion_id)
        )
        rule = result.scalar_one_or_none()
        if rule:
            if not rule.is_dismissible:
                raise ValueError("This suggestion cannot be dismissed")
            rule.times_dismissed += 1
            await self.session.commit()
            return True
        return False