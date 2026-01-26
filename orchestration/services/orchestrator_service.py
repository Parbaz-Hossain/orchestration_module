"""
Orchestrator Service
Core orchestration engine that coordinates all AI agents and workflows
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.orchestration_models import (
    WorkflowTemplate, WorkItem, WorkItemExecutionLog, PriorityRule,
    PriorityRuleApplication, DomainKnowledge, UserAgentContext, SuggestionRule
)
from ..models.enums import (
    AgentRole, WorkItemStatus, WorkItemPriority, TaskCategory,
    TaskType, ExecutionMode, AgentType, TriggerType
)
from ..schemas.orchestration_schemas import (
    OrchestratorSessionStart, OrchestratorSessionResponse,
    WorkItemCreate, WorkItemSummary, WorkItemResponse,
    SuggestionResponse, WorkflowTemplateSummary,
    AgentContext, AgentRequest, AgentResponse,
    TaskExecutionRequest, TaskExecutionResponse
)

logger = logging.getLogger(__name__)


class OrchestratorService:
    """
    Main orchestration service that coordinates:
    1. Session management (user login handling)
    2. Work item management
    3. Agent coordination
    4. Priority calculation
    5. Workflow execution
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._priority_weights = {
            WorkItemPriority.CRITICAL: 100,
            WorkItemPriority.HIGH: 75,
            WorkItemPriority.MEDIUM: 50,
            WorkItemPriority.LOW: 25,
            WorkItemPriority.BACKGROUND: 10
        }
    
    # ==================== SESSION MANAGEMENT ====================
    
    async def start_session(
        self, 
        request: OrchestratorSessionStart
    ) -> OrchestratorSessionResponse:
        """
        Initialize orchestrator session when user logs in.
        This is the main entry point for the orchestration flow.
        
        Flow:
        1. Update/create user agent context
        2. Fetch pending work items for user's role
        3. If no pending items, generate suggestions
        4. Return session with all relevant data
        """
        session_id = str(uuid.uuid4())
        
        # Update user context
        await self._update_user_context(request.user_id, request.role)
        
        # Get pending work items for this role
        pending_items = await self.get_pending_work_items(
            role=request.role,
            user_id=request.user_id,
            limit=50
        )
        
        # Get suggestions if no pending high-priority items
        suggestions = []
        high_priority_pending = [
            item for item in pending_items 
            if item.priority in [WorkItemPriority.CRITICAL, WorkItemPriority.HIGH]
        ]
        
        if len(high_priority_pending) < 3:
            suggestions = await self.generate_suggestions(
                role=request.role,
                user_id=request.user_id,
                existing_tasks=[item.template_code for item in pending_items]
            )
        
        # Get available templates for this role
        available_templates = await self.get_templates_for_role(request.role)
        
        # Calculate metrics
        metrics = await self._calculate_dashboard_metrics(
            role=request.role,
            user_id=request.user_id
        )
        
        return OrchestratorSessionResponse(
            session_id=session_id,
            user_id=request.user_id,
            role=request.role,
            pending_tasks=pending_items,
            pending_count=len(pending_items),
            suggestions=suggestions,
            available_templates=available_templates,
            metrics=metrics
        )
    
    async def _update_user_context(self, user_id: int, role: AgentRole) -> None:
        """Update or create user agent context"""
        result = await self.session.execute(
            select(UserAgentContext).where(UserAgentContext.user_id == user_id)
        )
        context = result.scalar_one_or_none()
        
        if context:
            context.primary_role = role
            context.last_login_at = datetime.utcnow()
            context.last_activity_at = datetime.utcnow()
        else:
            context = UserAgentContext(
                user_id=user_id,
                primary_role=role,
                last_login_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            self.session.add(context)
        
        await self.session.commit()
    
    async def _calculate_dashboard_metrics(
        self, 
        role: AgentRole, 
        user_id: int
    ) -> Dict[str, Any]:
        """Calculate dashboard metrics for the user"""
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        # Count tasks completed today
        completed_today = await self.session.execute(
            select(func.count(WorkItem.id)).where(
                and_(
                    or_(
                        WorkItem.assigned_to_role == role,
                        WorkItem.assigned_to_user_id == user_id
                    ),
                    WorkItem.status == WorkItemStatus.COMPLETED,
                    WorkItem.completed_at >= today_start
                )
            )
        )
        
        # Count pending tasks
        pending_count = await self.session.execute(
            select(func.count(WorkItem.id)).where(
                and_(
                    or_(
                        WorkItem.assigned_to_role == role,
                        WorkItem.assigned_to_user_id == user_id
                    ),
                    WorkItem.status.in_([
                        WorkItemStatus.PENDING, 
                        WorkItemStatus.IN_PROGRESS,
                        WorkItemStatus.AWAITING_INPUT
                    ])
                )
            )
        )
        
        # Count high priority
        high_priority = await self.session.execute(
            select(func.count(WorkItem.id)).where(
                and_(
                    or_(
                        WorkItem.assigned_to_role == role,
                        WorkItem.assigned_to_user_id == user_id
                    ),
                    WorkItem.status.in_([WorkItemStatus.PENDING, WorkItemStatus.IN_PROGRESS]),
                    WorkItem.priority.in_([WorkItemPriority.CRITICAL, WorkItemPriority.HIGH])
                )
            )
        )
        
        # Count overdue
        overdue = await self.session.execute(
            select(func.count(WorkItem.id)).where(
                and_(
                    or_(
                        WorkItem.assigned_to_role == role,
                        WorkItem.assigned_to_user_id == user_id
                    ),
                    WorkItem.status.in_([WorkItemStatus.PENDING, WorkItemStatus.IN_PROGRESS]),
                    WorkItem.due_date < datetime.utcnow()
                )
            )
        )
        
        return {
            "tasks_completed_today": completed_today.scalar() or 0,
            "tasks_pending": pending_count.scalar() or 0,
            "high_priority_count": high_priority.scalar() or 0,
            "overdue_count": overdue.scalar() or 0
        }
    
    # ==================== WORK ITEM MANAGEMENT ====================
    
    async def get_pending_work_items(
        self,
        role: AgentRole,
        user_id: int,
        limit: int = 50,
        category: Optional[TaskCategory] = None
    ) -> List[WorkItemSummary]:
        """Get pending work items for a role, sorted by priority score"""
        query = select(WorkItem).where(
            and_(
                or_(
                    WorkItem.assigned_to_role == role,
                    WorkItem.assigned_to_user_id == user_id
                ),
                WorkItem.status.in_([
                    WorkItemStatus.PENDING,
                    WorkItemStatus.IN_PROGRESS,
                    WorkItemStatus.AWAITING_INPUT
                ])
            )
        ).order_by(
            desc(WorkItem.priority_score),
            WorkItem.due_date.asc().nullslast(),
            WorkItem.created_at.asc()
        ).limit(limit)
        
        if category:
            query = query.where(WorkItem.category == category)
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [
            WorkItemSummary(
                id=item.id,
                title=item.title,
                template_code=item.template_code,
                category=item.category,
                task_type=item.task_type,
                status=item.status,
                priority=item.priority,
                priority_score=item.priority_score,
                assigned_to_role=item.assigned_to_role,
                due_date=item.due_date,
                is_suggestion=item.is_suggestion,
                created_at=item.created_at
            )
            for item in items
        ]
    
    async def create_work_item(
        self,
        data: WorkItemCreate,
        created_by: int
    ) -> WorkItemResponse:
        """Create a new work item from a template"""
        # Get template
        template = await self._get_template_by_code(data.template_code)
        if not template:
            raise ValueError(f"Template not found: {data.template_code}")
        
        # Create work item
        work_item = WorkItem(
            template_id=template.id,
            template_code=template.code,
            title=data.title,
            description=data.description,
            reference_id=data.reference_id,
            category=template.category,
            task_type=template.task_type,
            assigned_to_role=data.assigned_to_role or template.allowed_roles[0] if template.allowed_roles else None,
            assigned_to_user_id=data.assigned_to_user_id,
            assigned_agent=template.target_agent,
            status=WorkItemStatus.PENDING,
            priority=data.priority,
            input_data=data.input_data,
            execution_mode=template.execution_mode,
            due_date=data.due_date,
            trigger_type=data.trigger_type,
            is_suggestion=data.is_suggestion,
            created_by=created_by
        )
        
        self.session.add(work_item)
        await self.session.flush()
        
        # Calculate priority score
        work_item.priority_score = await self.calculate_priority_score(work_item)
        
        # Log creation
        await self._log_work_item_action(
            work_item.id,
            "work_item_created",
            None,
            None,
            f"Work item created from template {template.code}"
        )
        
        await self.session.commit()
        await self.session.refresh(work_item)
        
        return await self._work_item_to_response(work_item)
    
    async def get_work_item(self, work_item_id: int) -> Optional[WorkItemResponse]:
        """Get a work item by ID"""
        result = await self.session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        work_item = result.scalar_one_or_none()
        
        if work_item:
            return await self._work_item_to_response(work_item)
        return None
    
    async def _work_item_to_response(self, work_item: WorkItem) -> WorkItemResponse:
        """Convert WorkItem model to response schema"""
        return WorkItemResponse(
            id=work_item.id,
            template_id=work_item.template_id,
            template_code=work_item.template_code,
            title=work_item.title,
            description=work_item.description,
            reference_id=work_item.reference_id,
            category=work_item.category,
            task_type=work_item.task_type,
            assigned_to_role=work_item.assigned_to_role,
            assigned_to_user_id=work_item.assigned_to_user_id,
            assigned_agent=work_item.assigned_agent,
            status=work_item.status,
            priority=work_item.priority,
            priority_score=work_item.priority_score,
            input_data=work_item.input_data,
            output_data=work_item.output_data,
            execution_mode=work_item.execution_mode,
            current_step=work_item.current_step,
            step_results=work_item.step_results or [],
            due_date=work_item.due_date,
            started_at=work_item.started_at,
            completed_at=work_item.completed_at,
            error_message=work_item.error_message,
            retry_count=work_item.retry_count,
            trigger_type=work_item.trigger_type,
            is_suggestion=work_item.is_suggestion,
            is_automated=work_item.is_automated,
            created_at=work_item.created_at,
            updated_at=work_item.updated_at
        )
    
    # ==================== PRIORITY CALCULATION ====================
    
    async def calculate_priority_score(self, work_item: WorkItem) -> float:
        """
        Calculate priority score for a work item using priority rules.
        Higher score = higher priority.
        """
        base_score = self._priority_weights.get(work_item.priority, 50)
        
        # Get applicable rules
        rules = await self._get_applicable_priority_rules(work_item)
        
        total_additive_score = 0
        total_multiplier = 1.0
        
        for rule in rules:
            score_contribution = await self._evaluate_priority_rule(rule, work_item)
            
            if score_contribution is not None:
                # Log rule application
                application = PriorityRuleApplication(
                    work_item_id=work_item.id,
                    rule_id=rule.id,
                    score_contribution=score_contribution,
                    rule_matched=True,
                    evaluation_details={
                        "rule_code": rule.code,
                        "rule_type": rule.rule_type,
                        "is_additive": rule.is_additive
                    }
                )
                self.session.add(application)
                
                if rule.is_additive:
                    total_additive_score += min(score_contribution, rule.max_score_contribution)
                else:
                    total_multiplier *= (1 + score_contribution / 100)
        
        # Calculate final score
        final_score = (base_score + total_additive_score) * total_multiplier
        
        # Clamp to reasonable range
        return max(0, min(200, final_score))
    
    async def _get_applicable_priority_rules(self, work_item: WorkItem) -> List[PriorityRule]:
        """Get priority rules that apply to this work item"""
        result = await self.session.execute(
            select(PriorityRule).where(
                and_(
                    PriorityRule.is_active == True,
                    or_(
                        PriorityRule.template_id == work_item.template_id,
                        PriorityRule.template_id.is_(None)
                    ),
                    or_(
                        PriorityRule.category == work_item.category,
                        PriorityRule.category.is_(None)
                    ),
                    or_(
                        PriorityRule.task_type == work_item.task_type,
                        PriorityRule.task_type.is_(None)
                    )
                )
            ).order_by(PriorityRule.evaluation_order)
        )
        return result.scalars().all()
    
    async def _evaluate_priority_rule(
        self, 
        rule: PriorityRule, 
        work_item: WorkItem
    ) -> Optional[float]:
        """Evaluate a single priority rule and return score contribution"""
        try:
            condition = rule.condition
            
            if rule.rule_type == "deadline_proximity":
                if work_item.due_date:
                    days_until_due = (work_item.due_date - datetime.utcnow()).days
                    
                    # Check condition
                    if "days_until_due" in condition:
                        threshold = condition["days_until_due"]
                        if isinstance(threshold, dict):
                            for op, val in threshold.items():
                                if op == "<" and not (days_until_due < val):
                                    return None
                                if op == "<=" and not (days_until_due <= val):
                                    return None
                    
                    # Calculate score
                    if rule.score_formula:
                        return eval(rule.score_formula, {"days_until_due": days_until_due, "min": min, "max": max})
                    else:
                        # Default: closer deadline = higher score
                        return rule.base_weight * max(0, 100 - (days_until_due * 10))
                return None
            
            elif rule.rule_type == "data_condition":
                # Evaluate condition on input_data
                field_path = condition.get("field", "").replace("input_data.", "")
                operator = condition.get("operator", "==")
                expected_value = condition.get("value")
                score = condition.get("score", 10)
                
                # Get actual value
                actual_value = work_item.input_data.get(field_path)
                
                if self._evaluate_condition(actual_value, operator, expected_value):
                    return rule.base_weight * score
                return None
            
            elif rule.rule_type == "time_based":
                # Evaluate based on current time
                current_hour = datetime.utcnow().hour
                time_range = condition.get("time_range", {})
                start_hour = int(time_range.get("start", "00:00").split(":")[0])
                end_hour = int(time_range.get("end", "23:59").split(":")[0])
                
                if start_hour <= current_hour <= end_hour:
                    return rule.base_weight * condition.get("boost", 10)
                return None
            
            elif rule.rule_type == "base_priority":
                # This is handled by the base score
                return None
            
            else:
                logger.warning(f"Unknown rule type: {rule.rule_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error evaluating priority rule {rule.code}: {e}")
            return None
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a condition"""
        if actual is None:
            return False
        
        try:
            if operator == "==":
                return actual == expected
            elif operator == "!=":
                return actual != expected
            elif operator == ">":
                return actual > expected
            elif operator == "<":
                return actual < expected
            elif operator == ">=":
                return actual >= expected
            elif operator == "<=":
                return actual <= expected
            elif operator == "in":
                return actual in expected
            elif operator == "not_in":
                return actual not in expected
            elif operator == "contains":
                return expected in actual
            else:
                return False
        except:
            return False
    
    # ==================== SUGGESTION GENERATION ====================
    
    async def generate_suggestions(
        self,
        role: AgentRole,
        user_id: int,
        existing_tasks: List[str],
        limit: int = 5
    ) -> List[SuggestionResponse]:
        """Generate task suggestions for a user based on their role"""
        # Get active suggestion rules for this role
        result = await self.session.execute(
            select(SuggestionRule).where(
                and_(
                    SuggestionRule.target_role == role,
                    SuggestionRule.is_active == True
                )
            ).options(
                selectinload(SuggestionRule.workflow_template)
            )
        )
        rules = result.scalars().all()
        
        suggestions = []
        for rule in rules:
            # Skip if task already exists
            template = await self._get_template_by_id(rule.template_id)
            if template and template.code in existing_tasks:
                continue
            
            # Evaluate condition
            if await self._evaluate_suggestion_condition(rule, user_id):
                suggestions.append(SuggestionResponse(
                    suggestion_id=rule.id,
                    title=rule.suggestion_title,
                    message=rule.suggestion_message,
                    priority=rule.suggestion_priority,
                    template_code=template.code if template else "",
                    template_name=template.name if template else "",
                    category=template.category if template else TaskCategory.HR,
                    can_auto_create=rule.auto_create_task,
                    is_dismissible=rule.is_dismissible,
                    default_input_data=rule.default_input_data
                ))
                
                # Update suggestion count
                rule.times_suggested += 1
        
        await self.session.commit()
        
        # Sort by priority and return limited results
        suggestions.sort(
            key=lambda x: self._priority_weights.get(x.priority, 50), 
            reverse=True
        )
        
        return suggestions[:limit]
    
    async def _evaluate_suggestion_condition(
        self, 
        rule: SuggestionRule, 
        user_id: int
    ) -> bool:
        """Evaluate whether a suggestion rule condition is met"""
        condition = rule.condition
        condition_type = condition.get("type")
        
        try:
            if condition_type == "time_based":
                # Check day of month, day of week, etc.
                now = datetime.utcnow()
                
                if "day_of_month" in condition:
                    if now.day != condition["day_of_month"]:
                        return False
                
                if "day_of_week" in condition:
                    if now.weekday() != condition["day_of_week"]:
                        return False
                
                if "hour_range" in condition:
                    hr = condition["hour_range"]
                    if not (hr.get("start", 0) <= now.hour <= hr.get("end", 23)):
                        return False
                
                return True
            
            elif condition_type == "periodic":
                # Check last execution time
                last_execution = condition.get("last_execution_days_ago", {})
                
                # Get last completed work item of this type
                template = await self._get_template_by_id(rule.template_id)
                if template:
                    result = await self.session.execute(
                        select(WorkItem).where(
                            and_(
                                WorkItem.template_code == template.code,
                                WorkItem.status == WorkItemStatus.COMPLETED
                            )
                        ).order_by(desc(WorkItem.completed_at)).limit(1)
                    )
                    last_item = result.scalar_one_or_none()
                    
                    if last_item and last_item.completed_at:
                        days_since = (datetime.utcnow() - last_item.completed_at).days
                        
                        for op, val in last_execution.items():
                            if op == ">=" and not (days_since >= val):
                                return False
                            if op == ">" and not (days_since > val):
                                return False
                
                return True
            
            elif condition_type == "data_threshold":
                # This would require querying actual data
                # For now, return True to show the suggestion
                return True
            
            elif condition_type == "always":
                return True
            
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating suggestion condition: {e}")
            return False
    
    # ==================== TEMPLATE MANAGEMENT ====================
    
    async def get_templates_for_role(self, role: AgentRole) -> List[WorkflowTemplateSummary]:
        """Get workflow templates available for a role"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(
                and_(
                    WorkflowTemplate.is_active == True,
                    WorkflowTemplate.allowed_roles.contains([role])
                )
            ).order_by(WorkflowTemplate.category, WorkflowTemplate.name)
        )
        templates = result.scalars().all()
        
        return [
            WorkflowTemplateSummary(
                id=t.id,
                name=t.name,
                code=t.code,
                category=t.category,
                task_type=t.task_type,
                execution_mode=t.execution_mode,
                default_priority=t.default_priority,
                is_active=t.is_active
            )
            for t in templates
        ]
    
    async def _get_template_by_code(self, code: str) -> Optional[WorkflowTemplate]:
        """Get template by code"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.code == code)
        )
        return result.scalar_one_or_none()
    
    async def _get_template_by_id(self, template_id: int) -> Optional[WorkflowTemplate]:
        """Get template by ID"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    # ==================== LOGGING ====================
    
    async def _log_work_item_action(
        self,
        work_item_id: int,
        action: str,
        step_id: Optional[int],
        agent_type: Optional[AgentType],
        message: str,
        details: Optional[Dict] = None,
        status: str = "success",
        duration_ms: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        """Log a work item action"""
        log_entry = WorkItemExecutionLog(
            work_item_id=work_item_id,
            action=action,
            step_id=step_id,
            agent_type=agent_type,
            message=message,
            details=details,
            status=status,
            duration_ms=duration_ms,
            user_id=user_id
        )
        self.session.add(log_entry)