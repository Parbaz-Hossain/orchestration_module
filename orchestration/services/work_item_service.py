"""
Work Item Service
Manages work items (tasks) created from workflow templates
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_, or_, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration_models import (
    WorkItem, WorkItemExecutionLog, WorkflowTemplate,
    PriorityRule, PriorityRuleApplication
)
from ..models.enums import (
    AgentRole, WorkItemStatus, WorkItemPriority, TaskCategory,
    TaskType, ExecutionMode, AgentType, TriggerType
)
from ..schemas.orchestration_schemas import (
    WorkItemCreate, WorkItemUpdate, WorkItemResponse, WorkItemSummary,
    WorkItemExecutionLogResponse
)

logger = logging.getLogger(__name__)


class WorkItemService:
    """
    Service for managing work items (tasks).
    Work items are instances created from workflow templates.
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
    
    async def create_work_item(
        self,
        data: WorkItemCreate,
        created_by: int
    ) -> WorkItemResponse:
        """Create a new work item from a template"""
        # Get template
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.code == data.template_code)
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template not found: {data.template_code}")
        
        if not template.is_active:
            raise ValueError(f"Template is not active: {data.template_code}")
        
        # Create work item
        work_item = WorkItem(
            template_id=template.id,
            template_code=template.code,
            title=data.title,
            description=data.description,
            reference_id=data.reference_id,
            category=template.category,
            task_type=template.task_type,
            assigned_to_role=data.assigned_to_role,
            assigned_to_user_id=data.assigned_to_user_id,
            assigned_agent=template.target_agent,
            status=WorkItemStatus.PENDING,
            priority=data.priority,
            input_data=data.input_data,
            execution_mode=template.execution_mode,
            due_date=data.due_date,
            trigger_type=data.trigger_type or TriggerType.MANUAL,
            is_suggestion=data.is_suggestion,
            created_by=created_by
        )
        
        # Set default role if not specified
        if not work_item.assigned_to_role and template.allowed_roles:
            work_item.assigned_to_role = template.allowed_roles[0]
        
        self.session.add(work_item)
        await self.session.flush()
        
        # Calculate priority score
        work_item.priority_score = await self._calculate_priority_score(work_item)
        
        # Log creation
        await self._create_log(
            work_item.id,
            "created",
            message=f"Work item created from template {template.code}",
            user_id=created_by
        )
        
        await self.session.commit()
        await self.session.refresh(work_item)
        
        return self._to_response(work_item)
    
    async def update_work_item(
        self,
        work_item_id: int,
        data: WorkItemUpdate,
        updated_by: int
    ) -> WorkItemResponse:
        """Update a work item"""
        result = await self.session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        work_item = result.scalar_one_or_none()
        
        if not work_item:
            raise ValueError(f"Work item not found: {work_item_id}")
        
        # Track changes for logging
        changes = []
        
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            old_value = getattr(work_item, field)
            if old_value != value:
                changes.append(f"{field}: {old_value} -> {value}")
                setattr(work_item, field, value)
        
        # Recalculate priority if priority changed
        if "priority" in update_data:
            work_item.priority_score = await self._calculate_priority_score(work_item)
        
        # Handle status transitions
        if "status" in update_data:
            if update_data["status"] == WorkItemStatus.IN_PROGRESS and not work_item.started_at:
                work_item.started_at = datetime.utcnow()
            elif update_data["status"] == WorkItemStatus.COMPLETED:
                work_item.completed_at = datetime.utcnow()
        
        work_item.updated_at = datetime.utcnow()
        
        # Log update
        if changes:
            await self._create_log(
                work_item_id,
                "updated",
                message=f"Updated: {', '.join(changes)}",
                user_id=updated_by
            )
        
        await self.session.commit()
        await self.session.refresh(work_item)
        
        return self._to_response(work_item)
    
    async def get_work_item(self, work_item_id: int) -> Optional[WorkItemResponse]:
        """Get a work item by ID"""
        result = await self.session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        work_item = result.scalar_one_or_none()
        
        if work_item:
            return self._to_response(work_item)
        return None
    
    async def get_work_items(
        self,
        page_index: int = 1,
        page_size: int = 50,
        role: Optional[AgentRole] = None,
        user_id: Optional[int] = None,
        category: Optional[TaskCategory] = None,
        task_type: Optional[TaskType] = None,
        status: Optional[WorkItemStatus] = None,
        priority: Optional[WorkItemPriority] = None,
        is_suggestion: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: str = "priority_score",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get work items with filtering and pagination"""
        query = select(WorkItem)
        count_query = select(func.count(WorkItem.id))
        
        conditions = []
        
        # Role/User filter
        if role or user_id:
            role_user_condition = []
            if role:
                role_user_condition.append(WorkItem.assigned_to_role == role)
            if user_id:
                role_user_condition.append(WorkItem.assigned_to_user_id == user_id)
            conditions.append(or_(*role_user_condition))
        
        if category:
            conditions.append(WorkItem.category == category)
        
        if task_type:
            conditions.append(WorkItem.task_type == task_type)
        
        if status:
            conditions.append(WorkItem.status == status)
        
        if priority:
            conditions.append(WorkItem.priority == priority)
        
        if is_suggestion is not None:
            conditions.append(WorkItem.is_suggestion == is_suggestion)
        
        if search:
            search_filter = or_(
                WorkItem.title.ilike(f"%{search}%"),
                WorkItem.description.ilike(f"%{search}%"),
                WorkItem.reference_id.ilike(f"%{search}%")
            )
            conditions.append(search_filter)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply sorting
        sort_column = getattr(WorkItem, sort_by, WorkItem.priority_score)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return {
            "items": [self._to_response(item) for item in items],
            "total_count": total_count,
            "page_index": page_index,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    async def get_pending_for_role(
        self,
        role: AgentRole,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[WorkItemSummary]:
        """Get pending work items for a role, sorted by priority"""
        conditions = [
            WorkItem.status.in_([
                WorkItemStatus.PENDING,
                WorkItemStatus.IN_PROGRESS,
                WorkItemStatus.AWAITING_INPUT
            ])
        ]
        
        if user_id:
            conditions.append(
                or_(
                    WorkItem.assigned_to_role == role,
                    WorkItem.assigned_to_user_id == user_id
                )
            )
        else:
            conditions.append(WorkItem.assigned_to_role == role)
        
        query = select(WorkItem).where(
            and_(*conditions)
        ).order_by(
            desc(WorkItem.priority_score),
            WorkItem.due_date.asc().nullslast(),
            WorkItem.created_at.asc()
        ).limit(limit)
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [self._to_summary(item) for item in items]
    
    async def update_status(
        self,
        work_item_id: int,
        new_status: WorkItemStatus,
        updated_by: int,
        error_message: Optional[str] = None
    ) -> WorkItemResponse:
        """Update work item status with proper transitions"""
        result = await self.session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        work_item = result.scalar_one_or_none()
        
        if not work_item:
            raise ValueError(f"Work item not found: {work_item_id}")
        
        old_status = work_item.status
        work_item.status = new_status
        
        # Handle timestamps
        if new_status == WorkItemStatus.IN_PROGRESS and not work_item.started_at:
            work_item.started_at = datetime.utcnow()
        elif new_status in [WorkItemStatus.COMPLETED, WorkItemStatus.FAILED, WorkItemStatus.CANCELLED]:
            work_item.completed_at = datetime.utcnow()
        
        if error_message:
            work_item.error_message = error_message
        
        work_item.updated_at = datetime.utcnow()
        
        # Log status change
        await self._create_log(
            work_item_id,
            "status_changed",
            message=f"Status changed: {old_status.value} -> {new_status.value}",
            details={"old_status": old_status.value, "new_status": new_status.value},
            user_id=updated_by
        )
        
        await self.session.commit()
        await self.session.refresh(work_item)
        
        return self._to_response(work_item)
    
    async def update_step_result(
        self,
        work_item_id: int,
        step_id: int,
        status: str,
        result_data: Dict[str, Any],
        duration_ms: Optional[int] = None
    ) -> WorkItemResponse:
        """Update the result of a workflow step"""
        db_result = await self.session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        work_item = db_result.scalar_one_or_none()
        
        if not work_item:
            raise ValueError(f"Work item not found: {work_item_id}")
        
        # Update step results
        step_results = work_item.step_results or []
        step_results.append({
            "step_id": step_id,
            "status": status,
            "result": result_data,
            "executed_at": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms
        })
        work_item.step_results = step_results
        work_item.current_step = step_id
        work_item.updated_at = datetime.utcnow()
        
        # Log step execution
        await self._create_log(
            work_item_id,
            "step_executed",
            step_id=step_id,
            message=f"Step {step_id} completed with status: {status}",
            details=result_data,
            status=status,
            duration_ms=duration_ms
        )
        
        await self.session.commit()
        await self.session.refresh(work_item)
        
        return self._to_response(work_item)
    
    async def get_execution_logs(
        self,
        work_item_id: int,
        limit: int = 100
    ) -> List[WorkItemExecutionLogResponse]:
        """Get execution logs for a work item"""
        result = await self.session.execute(
            select(WorkItemExecutionLog).where(
                WorkItemExecutionLog.work_item_id == work_item_id
            ).order_by(desc(WorkItemExecutionLog.timestamp)).limit(limit)
        )
        logs = result.scalars().all()
        
        return [
            WorkItemExecutionLogResponse(
                id=log.id,
                work_item_id=log.work_item_id,
                timestamp=log.timestamp,
                log_level=log.log_level,
                action=log.action,
                step_id=log.step_id,
                agent_type=log.agent_type,
                message=log.message,
                details=log.details,
                status=log.status,
                duration_ms=log.duration_ms
            )
            for log in logs
        ]
    
    async def _calculate_priority_score(self, work_item: WorkItem) -> float:
        """Calculate priority score using priority rules"""
        base_score = self._priority_weights.get(work_item.priority, 50)
        
        # Get applicable priority rules
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
                    )
                )
            ).order_by(PriorityRule.evaluation_order)
        )
        rules = result.scalars().all()
        
        total_additive = 0
        total_multiplier = 1.0
        
        for rule in rules:
            score = await self._evaluate_rule(rule, work_item)
            if score is not None:
                if rule.is_additive:
                    total_additive += min(score, rule.max_score_contribution)
                else:
                    total_multiplier *= (1 + score / 100)
        
        final_score = (base_score + total_additive) * total_multiplier
        return max(0, min(200, final_score))
    
    async def _evaluate_rule(
        self,
        rule: PriorityRule,
        work_item: WorkItem
    ) -> Optional[float]:
        """Evaluate a single priority rule"""
        try:
            if rule.rule_type == "deadline_proximity" and work_item.due_date:
                days_until_due = (work_item.due_date - datetime.utcnow()).days
                if days_until_due <= 1:
                    return rule.base_weight * 50
                elif days_until_due <= 3:
                    return rule.base_weight * 30
                elif days_until_due <= 7:
                    return rule.base_weight * 15
            
            elif rule.rule_type == "data_condition":
                condition = rule.condition
                field = condition.get("field", "").replace("input_data.", "")
                actual = work_item.input_data.get(field)
                expected = condition.get("value")
                operator = condition.get("operator", "==")
                
                if self._check_condition(actual, operator, expected):
                    return rule.base_weight * condition.get("score", 10)
            
            return None
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.code}: {e}")
            return None
    
    def _check_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Check a condition"""
        if actual is None:
            return False
        try:
            ops = {
                "==": lambda a, e: a == e,
                "!=": lambda a, e: a != e,
                ">": lambda a, e: a > e,
                "<": lambda a, e: a < e,
                ">=": lambda a, e: a >= e,
                "<=": lambda a, e: a <= e,
                "in": lambda a, e: a in e,
                "contains": lambda a, e: e in a,
            }
            return ops.get(operator, lambda a, e: False)(actual, expected)
        except:
            return False
    
    async def _create_log(
        self,
        work_item_id: int,
        action: str,
        step_id: Optional[int] = None,
        agent_type: Optional[AgentType] = None,
        message: Optional[str] = None,
        details: Optional[Dict] = None,
        status: str = "success",
        duration_ms: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        """Create an execution log entry"""
        log = WorkItemExecutionLog(
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
        self.session.add(log)
    
    def _to_response(self, work_item: WorkItem) -> WorkItemResponse:
        """Convert to response schema"""
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
    
    def _to_summary(self, work_item: WorkItem) -> WorkItemSummary:
        """Convert to summary schema"""
        return WorkItemSummary(
            id=work_item.id,
            title=work_item.title,
            template_code=work_item.template_code,
            category=work_item.category,
            task_type=work_item.task_type,
            status=work_item.status,
            priority=work_item.priority,
            priority_score=work_item.priority_score,
            assigned_to_role=work_item.assigned_to_role,
            due_date=work_item.due_date,
            is_suggestion=work_item.is_suggestion,
            created_at=work_item.created_at
        )