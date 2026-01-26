"""
Workflow Template Service
Manages workflow templates with API endpoints, schemas, and business rules
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration_models import WorkflowTemplate
from ..models.enums import (
    AgentRole, TaskCategory, TaskType, ExecutionMode, 
    AgentType, WorkItemPriority
)
from ..schemas.orchestration_schemas import (
    WorkflowTemplateCreate, WorkflowTemplateUpdate, WorkflowTemplateResponse,
    WorkflowTemplateSummary
)

logger = logging.getLogger(__name__)


class WorkflowTemplateService:
    """
    Service for managing workflow templates.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_template(
        self, 
        data: WorkflowTemplateCreate, 
        created_by: int
    ) -> WorkflowTemplateResponse:
        """Create a new workflow template"""
        # Check for duplicate code
        existing = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Template with code '{data.code}' already exists")
        
        # Convert enums to values for JSON storage
        allowed_roles = [r.value if hasattr(r, 'value') else r for r in data.allowed_roles]
        
        template = WorkflowTemplate(
            name=data.name,
            code=data.code,
            description=data.description,
            version=data.version,
            category=data.category,
            task_type=data.task_type,
            execution_mode=data.execution_mode,
            default_priority=data.default_priority,
            target_agent=data.target_agent,
            allowed_roles=allowed_roles,
            api_config=data.api_config,
            input_schema=data.input_schema,
            output_schema=data.output_schema,
            business_rules=data.business_rules,
            workflow_steps=data.workflow_steps,
            triggers=data.triggers,
            agent_instructions=data.agent_instructions,
            created_by=created_by
        )
        
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        
        return self._to_response(template)
    
    async def update_template(
        self, 
        template_id: int, 
        data: WorkflowTemplateUpdate,
        updated_by: int
    ) -> WorkflowTemplateResponse:
        """Update an existing workflow template"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        if template.is_system:
            raise ValueError("System templates cannot be modified")
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "allowed_roles" and value:
                value = [r.value if hasattr(r, 'value') else r for r in value]
            setattr(template, field, value)
        
        template.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(template)
        
        return self._to_response(template)
    
    async def get_template(self, template_id: int) -> Optional[WorkflowTemplateResponse]:
        """Get a template by ID"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        
        if template:
            return self._to_response(template)
        return None
    
    async def get_template_by_code(self, code: str) -> Optional[WorkflowTemplateResponse]:
        """Get a template by code"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.code == code)
        )
        template = result.scalar_one_or_none()
        
        if template:
            return self._to_response(template)
        return None
    
    async def get_template_model_by_code(self, code: str) -> Optional[WorkflowTemplate]:
        """Get template model by code (for internal use)"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_templates(
        self,
        page_index: int = 1,
        page_size: int = 50,
        category: Optional[TaskCategory] = None,
        task_type: Optional[TaskType] = None,
        role: Optional[AgentRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get templates with filtering and pagination"""
        query = select(WorkflowTemplate)
        count_query = select(func.count(WorkflowTemplate.id))
        
        conditions = []
        
        if category:
            conditions.append(WorkflowTemplate.category == category)
        
        if task_type:
            conditions.append(WorkflowTemplate.task_type == task_type)
        
        if role:
            role_value = role.value if hasattr(role, 'value') else role
            # JSON contains check - this may vary by database
            conditions.append(WorkflowTemplate.allowed_roles.contains([role_value]))
        
        if is_active is not None:
            conditions.append(WorkflowTemplate.is_active == is_active)
        
        if search:
            search_filter = or_(
                WorkflowTemplate.name.ilike(f"%{search}%"),
                WorkflowTemplate.code.ilike(f"%{search}%"),
                WorkflowTemplate.description.ilike(f"%{search}%")
            )
            conditions.append(search_filter)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar() or 0
        
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(
            WorkflowTemplate.category, WorkflowTemplate.name
        )
        
        result = await self.session.execute(query)
        templates = result.scalars().all()
        
        return {
            "items": [self._to_response(t) for t in templates],
            "total_count": total_count,
            "page_index": page_index,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0
        }
    
    async def get_templates_for_role(self, role: AgentRole) -> List[WorkflowTemplateSummary]:
        """Get all templates available for a role"""
        role_value = role.value if hasattr(role, 'value') else role
        
        result = await self.session.execute(
            select(WorkflowTemplate).where(
                and_(
                    WorkflowTemplate.is_active == True,
                    WorkflowTemplate.allowed_roles.contains([role_value])
                )
            ).order_by(WorkflowTemplate.category, WorkflowTemplate.name)
        )
        templates = result.scalars().all()
        
        return [self._to_summary(t) for t in templates]
    
    async def delete_template(self, template_id: int, deleted_by: int) -> bool:
        """Soft delete a template (deactivate)"""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        
        if not template:
            return False
        
        if template.is_system:
            raise ValueError("System templates cannot be deleted")
        
        template.is_active = False
        template.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return True
    
    def _to_response(self, template: WorkflowTemplate) -> WorkflowTemplateResponse:
        """Convert model to response schema"""
        return WorkflowTemplateResponse(
            id=template.id,
            name=template.name,
            code=template.code,
            description=template.description,
            version=template.version,
            category=template.category,
            task_type=template.task_type,
            execution_mode=template.execution_mode,
            default_priority=template.default_priority,
            target_agent=template.target_agent,
            allowed_roles=template.allowed_roles or [],
            api_config=template.api_config or {},
            input_schema=template.input_schema or {},
            output_schema=template.output_schema,
            business_rules=template.business_rules or {},
            workflow_steps=template.workflow_steps or [],
            triggers=template.triggers,
            agent_instructions=template.agent_instructions,
            is_active=template.is_active,
            is_system=template.is_system,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
    
    def _to_summary(self, template: WorkflowTemplate) -> WorkflowTemplateSummary:
        """Convert model to summary schema"""
        return WorkflowTemplateSummary(
            id=template.id,
            name=template.name,
            code=template.code,
            category=template.category,
            task_type=template.task_type,
            execution_mode=template.execution_mode,
            default_priority=template.default_priority,
            is_active=template.is_active
        )