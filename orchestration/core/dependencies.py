"""
FastAPI Dependencies for the Orchestration Module
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_async_session
from ..models.enums import AgentRole

# Security scheme
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Represents the current authenticated user"""
    def __init__(self, id: int, role: AgentRole, email: Optional[str] = None):
        self.id = id
        self.role = role
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Get the current authenticated user.
    
    Replace this implementation with your actual authentication logic.
    This is a placeholder that returns a default user for development.
    """
    # TODO: Replace with actual JWT validation or integrate with your auth system
    
    if credentials is None:
        # For development: return a default HR Manager user
        return CurrentUser(id=1, role=AgentRole.HR_MANAGER, email="dev@example.com")
    
    try:
        # Your JWT validation logic here
        # token = credentials.credentials
        # payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # user_id = payload.get("sub")
        # role = payload.get("role")
        
        # Placeholder
        return CurrentUser(id=1, role=AgentRole.HR_MANAGER, email="user@example.com")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    current_user: CurrentUser = Depends(get_current_user)
) -> int:
    """Get current user ID"""
    return current_user.id


async def get_current_user_role(
    current_user: CurrentUser = Depends(get_current_user)
) -> AgentRole:
    """Get current user role"""
    return current_user.role


def require_role(*allowed_roles: AgentRole):
    """
    Dependency factory to require specific roles.
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            _: None = Depends(require_role(AgentRole.SUPER_ADMIN))
        ):
            ...
    """
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker