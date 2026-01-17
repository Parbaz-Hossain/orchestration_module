# Backend Orchestration Module

AI Agentic Retail/Cafe Management System - Backend Orchestration Module

## Overview

This module serves as the "brain" of the AI Agentic system, controlling:
- Dynamic work priority calculation based on real-time system state
- Push-based instruction delivery to AI agents
- Full conversation state management
- Multi-step workflow orchestration with saga pattern

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start the server
python main.py
```

## Architecture

```
orchestration/
├── core/           # Configuration and dependencies
├── models/         # SQLAlchemy ORM models
├── schemas/        # Pydantic validation models
├── services/       # Business logic services
├── workflows/      # State machine workflow definitions
├── websocket/      # WebSocket connection management
├── api/            # HTTP and WebSocket endpoints
└── tasks/          # Background Celery tasks
```

## API Documentation

After starting the server, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## WebSocket Endpoint

Connect to `ws://localhost:8000/ws/orchestrator/{session_id}` for real-time communication.