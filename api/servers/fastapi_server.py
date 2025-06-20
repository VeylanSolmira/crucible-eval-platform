"""
FastAPI server for Crucible Evaluation Platform.
Demonstrates async capabilities and WebSocket support.
"""

from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import os
import logging
from typing import Dict, Any
import json

from api.api import APIRequest, APIResponse, HTTPMethod, create_api_service, create_api_handler
from api.favicon import get_favicon_bytes, get_svg_favicon
from src.core.core import QueuedEvaluationPlatform
from src.execution_engine.execution import DockerEngine, GVisorEngine
from src.queue.queue import TaskQueue
from src.monitoring.monitoring import AdvancedMonitor
from src.event_bus.events import EventBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Crucible Evaluation Platform API",
    description="FastAPI implementation with async support and WebSockets",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    """Handle HTTP exceptions with custom format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with custom format"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "path": request.url.path
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle internal server errors"""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": request.url.path
        }
    )

# Initialize platform components (will be done in create_app)
api_handler = None


async def create_app():
    """Factory function to create and configure the FastAPI app"""
    global api_handler
    
    # Create event bus
    event_bus = EventBus()
    
    # Create execution engine
    if os.path.exists('/usr/bin/runsc'):
        engine = GVisorEngine()
        logger.info("Using gVisor engine for enhanced security")
    else:
        engine = DockerEngine()
        logger.info("Using Docker engine")
    
    # Create other components
    queue = TaskQueue(max_workers=4)
    monitor = AdvancedMonitor()
    
    # Create platform
    platform = QueuedEvaluationPlatform(
        engine=engine,
        queue=queue,
        monitor=monitor
    )
    
    # Create API service and handler
    api_service = create_api_service(platform)
    api_handler = create_api_handler(api_service)
    
    logger.info("FastAPI server initialized")
    return app


# Route definitions
@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page with async interface"""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Crucible Platform - FastAPI Edition</title>
    <style>
        body { font-family: Arial; max-width: 900px; margin: 50px auto; }
        .container { padding: 20px; }
        textarea { width: 100%; height: 150px; font-family: monospace; }
        button { background: #17a2b8; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .feature-badge { background: #6c757d; color: white; padding: 5px 10px; margin: 2px; border-radius: 3px; display: inline-block; }
        .ws-status { padding: 10px; background: #f8f9fa; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Crucible Platform - FastAPI Edition</h1>
        <div>
            <span class="feature-badge">Async Support</span>
            <span class="feature-badge">WebSocket Ready</span>
            <span class="feature-badge">Auto API Docs</span>
        </div>
        <p>Visit <a href="/docs">/docs</a> for interactive API documentation</p>
        <div class="ws-status" id="ws-status">WebSocket: Not Connected</div>
        <textarea id="code" placeholder="Enter Python code...">print('FastAPI async edition!')</textarea>
        <br><br>
        <button onclick="submitCode()">Evaluate (Async)</button>
        <div id="result"></div>
    </div>
    <script>
        // WebSocket connection
        const wsUrl = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsUrl}//${window.location.host}/ws`);
        
        ws.onopen = () => {
            document.getElementById('ws-status').innerHTML = 'WebSocket: Connected ✅';
        };
        
        ws.onerror = () => {
            document.getElementById('ws-status').innerHTML = 'WebSocket: Not Available';
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'evaluation_update') {
                document.getElementById('result').innerHTML += `<p>${data.message}</p>`;
            }
        };
        
        async function submitCode() {
            const code = document.getElementById('code').value;
            const response = await fetch('/api/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            const result = await response.json();
            document.getElementById('result').innerHTML = `<pre>${JSON.stringify(result, null, 2)}</pre>`;
        }
    </script>
</body>
</html>
"""


@app.post("/api/eval")
async def eval_endpoint(request: Dict[str, Any]):
    """Main evaluation endpoint (async)"""
    if not api_handler:
        return JSONResponse(
            {"error": "Server not initialized"}, 
            status_code=503
        )
    
    api_request = APIRequest(
        method=HTTPMethod.POST,
        path='/eval',
        headers={},
        body=json.dumps(request).encode()
    )
    api_response = api_handler.handle_request(api_request)
    
    response_data = json.loads(api_response.body.decode())
    return JSONResponse(
        response_data,
        status_code=api_response.status_code
    )


@app.get("/api/eval-status/{eval_id}")
async def eval_status_endpoint(eval_id: str):
    """Get evaluation status (async)"""
    if not api_handler:
        return JSONResponse(
            {"error": "Server not initialized"}, 
            status_code=503
        )
    
    api_request = APIRequest(
        method=HTTPMethod.GET,
        path=f'/eval-status/{eval_id}',
        headers={},
        body=None,
        params={'eval_id': eval_id}
    )
    api_response = api_handler.handle_request(api_request)
    
    response_data = json.loads(api_response.body.decode())
    return JSONResponse(
        response_data,
        status_code=api_response.status_code
    )


@app.get("/api/status")
async def platform_status_endpoint():
    """Platform health and status"""
    if not api_handler:
        return JSONResponse(
            {"error": "Server not initialized"}, 
            status_code=503
        )
    
    api_request = APIRequest(
        method=HTTPMethod.GET,
        path='/status',
        headers={},
        body=None
    )
    api_response = api_handler.handle_request(api_request)
    
    response_data = json.loads(api_response.body.decode())
    return JSONResponse(
        response_data,
        status_code=api_response.status_code
    )


@app.get("/api/queue-status")
async def queue_status_endpoint():
    """Queue statistics"""
    if not api_handler:
        return JSONResponse(
            {"error": "Server not initialized"}, 
            status_code=503
        )
    
    api_request = APIRequest(
        method=HTTPMethod.GET,
        path='/queue-status',
        headers={},
        body=None
    )
    api_response = api_handler.handle_request(api_request)
    
    response_data = json.loads(api_response.body.decode())
    return JSONResponse(
        response_data,
        status_code=api_response.status_code
    )


@app.get("/api/evaluations")
async def evaluations_endpoint(limit: int = 100, offset: int = 0):
    """Get evaluation history"""
    if not api_handler:
        return JSONResponse(
            {"error": "Server not initialized"}, 
            status_code=503
        )
    
    api_request = APIRequest(
        method=HTTPMethod.GET,
        path='/evaluations',
        headers={},
        body=None,
        params={'limit': str(limit), 'offset': str(offset)}
    )
    api_response = api_handler.handle_request(api_request)
    
    response_data = json.loads(api_response.body.decode())
    return JSONResponse(
        response_data,
        status_code=api_response.status_code
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to Crucible Platform WebSocket"
        })
        
        # In a real implementation, this would subscribe to evaluation events
        # and forward them to the client
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            # Echo back for now
            await websocket.send_json({
                "type": "echo",
                "message": f"Received: {data}"
            })
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


@app.on_event("startup")
async def startup_event():
    """Initialize the app on startup"""
    # Only create app if api_handler is not already set (e.g., by app.py)
    if api_handler is None:
        await create_app()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "service": "crucible-api",
        "framework": "fastapi",
        "async": True
    }


# OpenAPI spec endpoints
@app.get("/api/openapi.yaml")
@app.get("/api/openapi.json") 
@app.get("/api/spec")
async def openapi_spec_endpoint():
    """Serve OpenAPI specification"""
    if not api_handler:
        return JSONResponse(
            {"error": "Server not initialized"}, 
            status_code=503
        )
    
    api_request = APIRequest(
        method=HTTPMethod.GET,
        path='/spec',
        headers={},
        body=None
    )
    api_response = api_handler.handle_request(api_request)
    
    # Determine content type from response
    if api_response.headers.get('Content-Type') == 'application/yaml':
        return Response(
            content=api_response.body,
            media_type="application/yaml"
        )
    else:
        response_data = json.loads(api_response.body.decode())
        return JSONResponse(
            response_data,
            status_code=api_response.status_code
        )


# Favicon routes
@app.get("/favicon.ico")
async def favicon_ico():
    """Serve favicon.ico"""
    favicon_bytes = get_favicon_bytes()
    return Response(
        content=favicon_bytes,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=31536000"}  # Cache for 1 year
    )


@app.get("/favicon.svg")
async def favicon_svg():
    """Serve favicon.svg"""
    svg_content = get_svg_favicon()
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=31536000"}  # Cache for 1 year
    )


# CLI entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Starting FastAPI server on port {port}")
    uvicorn.run(
        "api.servers.fastapi_server:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get('FASTAPI_ENV') == 'development'
    )