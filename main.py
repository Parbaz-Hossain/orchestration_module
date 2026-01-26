"""
Main entry point for the Orchestration Module
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestration.api.routes import api_router
from orchestration.core.config import settings
from orchestration.core.database import engine, async_session_maker
from orchestration.models.orchestration_models import Base
from orchestration.seeds import seed_all_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("🚀 Starting Orchestration Module...")
    
    # Create tables if they don't exist (for development)
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created/verified")
    
    # Seed default data
    if settings.SEED_ON_STARTUP:
        try:
            async with async_session_maker() as session:
                result = await seed_all_data(session)
                print(f"✅ Seed data loaded: {result}")
        except Exception as e:
            print(f"⚠️ Seed data warning: {e}")
    
    print("✅ Orchestration Module ready!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Orchestration Module...")
    await engine.dispose()
    print("✅ Database connections closed")


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend Orchestration Module for AI Agentic Retail/Cafe Management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with prefix
# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Orchestration Module",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "orchestration-module",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )