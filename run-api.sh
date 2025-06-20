#!/bin/bash
# Development server runner for FastAPI

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables
export FASTAPI_ENV=development
export PORT=${PORT:-8080}

echo "🚀 Starting FastAPI server on port $PORT with hot reloading..."
echo "📚 Interactive API docs: http://localhost:$PORT/docs"
echo "📝 Logs will appear below. Press Ctrl+C to stop."
echo ""

# Run FastAPI with Uvicorn
python -m src.api.servers.fastapi_server