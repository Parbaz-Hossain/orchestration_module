"""
Seed Runner
Execute seeding of all orchestration data
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.orchestration_models import WorkflowTemplate, PriorityRule, SuggestionRule
from ..models.enums import TaskCategory, TaskType, ExecutionMode, AgentType, WorkItemPriority, AgentRole
from .seed_templates import get_hr_workflow_templates
from .seed_priority_rules import get_default_priority_rules
from .seed_suggestion_rules import get_default_suggestion_rules

logger = logging.getLogger(__name__)


async def seed_all_data(session: AsyncSession, created_by: int = 1) -> dict:
    """
    Seed all orchestration data.
    
    Returns:
        dict with counts of created items
    """
    results = {
        "templates_created": 0,
        "templates_skipped": 0,
        "priority_rules_created": 0,
        "priority_rules_skipped": 0,
        "suggestion_rules_created": 0,
        "suggestion_rules_skipped": 0,
        "errors": []
    }
    
    # Seed priority rules first
    logger.info("Seeding priority rules...")
    for rule_data in get_default_priority_rules():
        try:
            existing = await session.execute(
                select(PriorityRule).where(PriorityRule.code == rule_data["code"])
            )
            if existing.scalar_one_or_none():
                results["priority_rules_skipped"] += 1
                continue
            
            # Handle category enum
            category = rule_data.pop("category", None)
            if category:
                category = TaskCategory(category) if isinstance(category, str) else category
            
            rule = PriorityRule(
                **rule_data,
                category=category,
                is_system=True,
                created_by=created_by
            )
            session.add(rule)
            results["priority_rules_created"] += 1
            logger.info(f"  Created priority rule: {rule_data['code']}")
        except Exception as e:
            results["errors"].append(f"Priority rule {rule_data.get('code')}: {str(e)}")
            logger.error(f"  Error creating priority rule: {e}")
    
    await session.flush()
    
    # Seed workflow templates
    logger.info("Seeding workflow templates...")
    template_map = {}  # code -> id mapping for suggestion rules
    
    for template_data in get_hr_workflow_templates():
        try:
            existing = await session.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.code == template_data["code"])
            )
            if existing.scalar_one_or_none():
                results["templates_skipped"] += 1
                # Still get the ID for suggestion rules
                result = await session.execute(
                    select(WorkflowTemplate.id).where(WorkflowTemplate.code == template_data["code"])
                )
                template_map[template_data["code"]] = result.scalar()
                continue
            
            template = WorkflowTemplate(
                name=template_data["name"],
                code=template_data["code"],
                description=template_data.get("description"),
                category=TaskCategory(template_data["category"]),
                task_type=TaskType(template_data["task_type"]),
                execution_mode=ExecutionMode(template_data["execution_mode"]),
                default_priority=WorkItemPriority(template_data["default_priority"]),
                target_agent=AgentType(template_data["target_agent"]),
                allowed_roles=template_data["allowed_roles"],
                api_config=template_data["api_config"],
                input_schema=template_data["input_schema"],
                business_rules=template_data.get("business_rules", {}),
                workflow_steps=template_data.get("workflow_steps", []),
                triggers=template_data.get("triggers"),
                agent_instructions=template_data.get("agent_instructions"),
                is_system=True,
                created_by=created_by
            )
            session.add(template)
            await session.flush()
            template_map[template_data["code"]] = template.id
            results["templates_created"] += 1
            logger.info(f"  Created template: {template_data['code']}")
        except Exception as e:
            results["errors"].append(f"Template {template_data.get('code')}: {str(e)}")
            logger.error(f"  Error creating template: {e}")
    
    await session.flush()
    
    # Seed suggestion rules
    logger.info("Seeding suggestion rules...")
    for rule_data in get_default_suggestion_rules():
        try:
            existing = await session.execute(
                select(SuggestionRule).where(SuggestionRule.code == rule_data["code"])
            )
            if existing.scalar_one_or_none():
                results["suggestion_rules_skipped"] += 1
                continue
            
            # Get template ID
            template_code = rule_data.pop("template_code")
            template_id = template_map.get(template_code)
            if not template_id:
                results["errors"].append(f"Suggestion rule {rule_data['code']}: Template {template_code} not found")
                continue
            
            rule = SuggestionRule(
                name=rule_data["name"],
                code=rule_data["code"],
                description=rule_data.get("description"),
                target_role=AgentRole(rule_data["target_role"]),
                template_id=template_id,
                condition=rule_data["condition"],
                suggestion_title=rule_data["suggestion_title"],
                suggestion_message=rule_data["suggestion_message"],
                suggestion_priority=WorkItemPriority(rule_data["suggestion_priority"]),
                default_input_data=rule_data.get("default_input_data"),
                check_frequency_minutes=rule_data.get("check_frequency_minutes", 60),
                max_suggestions_per_day=rule_data.get("max_suggestions_per_day", 1),
                is_dismissible=rule_data.get("is_dismissible", True),
                auto_create_task=rule_data.get("auto_create_task", False)
            )
            session.add(rule)
            results["suggestion_rules_created"] += 1
            logger.info(f"  Created suggestion rule: {rule_data['code']}")
        except Exception as e:
            results["errors"].append(f"Suggestion rule {rule_data.get('code')}: {str(e)}")
            logger.error(f"  Error creating suggestion rule: {e}")
    
    await session.commit()
    
    logger.info(f"Seeding complete: {results}")
    return results