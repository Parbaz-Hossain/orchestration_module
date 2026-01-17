"""
Main entry point for the Orchestration Module
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestration.api.routes import router as api_router
from orchestration.api.websocket_routes import router as ws_router
from orchestration.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend Orchestration Module for AI Agentic Retail/Cafe Management",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestration-module"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )