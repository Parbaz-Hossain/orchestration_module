"""Application configuration using pydantic-settings"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Orchestration Module"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/retail_cafe_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_CONNECTION_TIMEOUT: int = 300
    
    # Priority Calculation
    PRIORITY_REFRESH_INTERVAL_MINUTES: int = 5
    
    # Workflow Settings
    WORKFLOW_SESSION_TIMEOUT_MINUTES: int = 30
    MAX_PAUSED_TASKS: int = 5
    
    # Priority Weights
    PRIORITY_WEIGHT_URGENCY: float = 0.30
    PRIORITY_WEIGHT_IMPACT: float = 0.25
    PRIORITY_WEIGHT_DEPENDENCY: float = 0.20
    PRIORITY_WEIGHT_FINANCIAL: float = 0.15
    PRIORITY_WEIGHT_AGING: float = 0.10
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()