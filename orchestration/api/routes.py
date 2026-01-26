from fastapi import APIRouter
from orchestration.api.endpoints import orchestration
from orchestration.api.endpoints import priority_rule
from orchestration.api.endpoints import workflow_template

api_router = APIRouter()

# Authentication routes
api_router.include_router(orchestration.router, prefix="/orchestrator", tags=["Orchestrator"])
api_router.include_router(priority_rule.router, prefix="/orchestrator/priority-rules", tags=["Priority Rules"])
api_router.include_router(workflow_template.router, prefix="/orchestrator/templates", tags=["Workflow Templates"])
