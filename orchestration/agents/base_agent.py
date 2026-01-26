"""
AI Agent Base Classes
Abstract classes and interfaces for AI agent implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.enums import AgentType, TaskCategory, AgentRole
from ..schemas.orchestration_schemas import (
    AgentContext, AgentRequest, AgentResponse,
    WorkItemResponse, SuggestionResponse
)


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the orchestration system.
    
    Each agent implementation should:
    1. Override the `process` method to handle requests
    2. Implement any domain-specific logic
    3. Use the LLM client for AI-powered decisions when needed
    """
    
    agent_type: AgentType = None
    
    def __init__(self, llm_client=None, config: Dict[str, Any] = None):
        """
        Initialize the agent.
        
        Args:
            llm_client: Optional LLM client for AI-powered decisions
            config: Optional configuration dictionary
        """
        self.llm_client = llm_client
        self.config = config or {}
    
    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process an agent request.
        
        Args:
            request: The agent request containing context and input data
            
        Returns:
            AgentResponse with the processing results
        """
        pass
    
    async def _call_llm(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        Call the LLM for AI-powered decisions.
        Override this method if you have a specific LLM implementation.
        """
        if self.llm_client is None:
            raise NotImplementedError("LLM client not configured")
        
        # This would be implemented based on your LLM client
        # Example: return await self.llm_client.complete(prompt, context)
        raise NotImplementedError("LLM call not implemented")
    
    def _create_success_response(self, **kwargs) -> AgentResponse:
        """Create a success response"""
        return AgentResponse(
            agent_type=self.agent_type,
            action=kwargs.get("action", "process"),
            success=True,
            **kwargs
        )
    
    def _create_error_response(self, error_message: str, **kwargs) -> AgentResponse:
        """Create an error response"""
        return AgentResponse(
            agent_type=self.agent_type,
            action=kwargs.get("action", "process"),
            success=False,
            error_message=error_message,
            **kwargs
        )


class SuggestionAgentBase(BaseAgent):
    """
    Base class for the Suggestion Agent.
    
    The Suggestion Agent is triggered when a user logs in and has no
    high-priority pending tasks. It evaluates suggestion rules and
    generates relevant task suggestions based on:
    - User's role and permissions
    - Current date/time conditions
    - Data thresholds and conditions
    - Historical patterns
    """
    
    agent_type = AgentType.SUGGESTION_AGENT
    
    @abstractmethod
    async def evaluate_suggestions(
        self,
        role: AgentRole,
        user_id: int,
        existing_tasks: List[str]
    ) -> List[SuggestionResponse]:
        """
        Evaluate suggestion rules and generate suggestions.
        
        Args:
            role: User's current role
            user_id: User's ID
            existing_tasks: List of template codes for existing pending tasks
            
        Returns:
            List of suggestions to display to the user
        """
        pass


class IntentClassifierAgentBase(BaseAgent):
    """
    Base class for the Intent Classifier Agent.
    
    The Intent Classifier analyzes user input or task requests and
    determines:
    - The intended action (what the user wants to do)
    - The task category (HR, Inventory, etc.)
    - The specific task type
    - Relevant entities extracted from the input
    """
    
    agent_type = AgentType.CLASSIFIER_AGENT
    
    @abstractmethod
    async def classify(
        self,
        input_text: str,
        context: AgentContext
    ) -> Dict[str, Any]:
        """
        Classify user input to determine intent.
        
        Args:
            input_text: The user's input text or request
            context: Current agent context
            
        Returns:
            Classification result with intent, category, confidence, and entities
        """
        pass


class PlanningAgentBase(BaseAgent):
    """
    Base class for the Planning Agent.
    
    The Planning Agent takes a classified intent and creates an
    execution plan by:
    - Selecting the appropriate workflow template
    - Validating input against the template schema
    - Creating a sequence of execution steps
    - Determining if approval is required
    """
    
    agent_type = AgentType.PLANNING_AGENT
    
    @abstractmethod
    async def create_plan(
        self,
        classification: Dict[str, Any],
        template_code: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an execution plan for a task.
        
        Args:
            classification: The classification result from Intent Classifier
            template_code: The workflow template code to use
            input_data: Input data for the task
            
        Returns:
            Execution plan with steps, estimates, and requirements
        """
        pass


class DomainAgentBase(BaseAgent):
    """
    Base class for Domain-specific Agents (HR, Purchase, Inventory, etc.)
    
    Domain agents handle the actual execution of workflow steps within
    their domain. They:
    - Execute API calls per the workflow template configuration
    - Make domain-specific decisions
    - Handle errors and retries
    - Return step results
    """
    
    category: TaskCategory = None
    
    @abstractmethod
    async def execute_step(
        self,
        work_item: WorkItemResponse,
        step_config: Dict[str, Any],
        template_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step.
        
        Args:
            work_item: The work item being processed
            step_config: Configuration for this specific step
            template_config: Overall template configuration
            
        Returns:
            Step execution result
        """
        pass
    
    async def make_api_call(
        self,
        endpoint: str,
        method: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make an API call as defined in the workflow template.
        Override this to integrate with your HTTP client.
        """
        raise NotImplementedError("API call not implemented")


class HRAgentBase(DomainAgentBase):
    """Base class for HR Agent"""
    agent_type = AgentType.HR_AGENT
    category = TaskCategory.HR


class PurchaseAgentBase(DomainAgentBase):
    """Base class for Purchase Agent"""
    agent_type = AgentType.PURCHASE_AGENT
    category = TaskCategory.PURCHASE


class InventoryAgentBase(DomainAgentBase):
    """Base class for Inventory Agent"""
    agent_type = AgentType.INVENTORY_AGENT
    category = TaskCategory.INVENTORY


# class SalesAgentBase(DomainAgentBase):
#     """Base class for Sales Agent"""
#     agent_type = AgentType.SALES_AGENT
#     category = TaskCategory.SALES


# class FinanceAgentBase(DomainAgentBase):
#     """Base class for Finance Agent"""
#     agent_type = AgentType.FINANCE_AGENT
#     category = TaskCategory.FINANCE


class ExecutionEngineBase(BaseAgent):
    """
    Base class for the Execution Engine.
    
    The Execution Engine orchestrates the execution of workflow steps:
    - Manages step sequencing
    - Routes to appropriate domain agents
    - Handles conditional logic
    - Manages retries and error handling
    """
    
    agent_type = AgentType.EXECUTION_AGENT
    
    def __init__(self, domain_agents: Dict[TaskCategory, DomainAgentBase] = None, **kwargs):
        super().__init__(**kwargs)
        self.domain_agents = domain_agents or {}
    
    @abstractmethod
    async def execute_workflow(
        self,
        work_item: WorkItemResponse,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow.
        
        Args:
            work_item: The work item to execute
            template: The workflow template
            
        Returns:
            Workflow execution result
        """
        pass
    
    def get_domain_agent(self, category: TaskCategory) -> Optional[DomainAgentBase]:
        """Get the domain agent for a category"""
        return self.domain_agents.get(category)
    
    def register_domain_agent(self, agent: DomainAgentBase):
        """Register a domain agent"""
        if agent.category:
            self.domain_agents[agent.category] = agent


# ==================== AGENT REGISTRY ====================

class AgentRegistry:
    """
    Registry for managing AI agent instances.
    
    Usage:
        registry = AgentRegistry()
        registry.register(my_hr_agent)
        hr_agent = registry.get(AgentType.HR_AGENT)
    """
    
    def __init__(self):
        self._agents: Dict[AgentType, BaseAgent] = {}
    
    def register(self, agent: BaseAgent):
        """Register an agent instance"""
        if agent.agent_type:
            self._agents[agent.agent_type] = agent
    
    def get(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent by type"""
        return self._agents.get(agent_type)
    
    def get_all(self) -> Dict[AgentType, BaseAgent]:
        """Get all registered agents"""
        return self._agents.copy()
    
    def unregister(self, agent_type: AgentType):
        """Unregister an agent"""
        if agent_type in self._agents:
            del self._agents[agent_type]