"""Health check server for Celery worker."""

import asyncio
import logging
from fastapi import FastAPI
import uvicorn
import redis

logger = logging.getLogger(__name__)


def create_health_app(broker_url: str) -> FastAPI:
    """Create FastAPI app for health checks."""
    app = FastAPI(title="Celery Worker Health")
    
    @app.get("/healthz")
    async def healthz():
        """Liveness probe - is the worker process alive?"""
        return {"status": "ok"}
        
    @app.get("/readyz")
    async def readyz():
        """Readiness probe - can the worker process tasks?"""
        try:
            # Just check Redis is accessible
            r = redis.from_url(broker_url)
            r.ping()
            return {"status": "ready"}
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            return {"status": "not ready", "error": str(e)}, 503
        
    return app


async def run_health_server(broker_url: str, port: int = 8088):
    """Run the health check server."""
    app = create_health_app(broker_url)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()