"""
Configuration settings for the Orchestration Module
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App settings
    APP_NAME: str = "Orchestration Module"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:pgadmin123@localhost:5432/orchestration_db"
    DATABASE_ECHO: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Seeding
    SEED_ON_STARTUP: bool = True
    
    # JWT/Auth (if needed for your integration)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI/LLM Settings (optional, for agent integration)
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4"
    LLM_BASE_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()