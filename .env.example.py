# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/retail_cafe_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
APP_NAME=Orchestration Module
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# WebSocket
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=300

# Priority Calculation
PRIORITY_REFRESH_INTERVAL_MINUTES=5

# Workflow Settings
WORKFLOW_SESSION_TIMEOUT_MINUTES=30
MAX_PAUSED_TASKS=5