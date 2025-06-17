#!/usr/bin/env python3
"""
Execution Service - Dedicated microservice for code execution.

⚠️ STATUS: NOT YET IMPLEMENTED - FOR FUTURE USE
This file is part of the monolith but represents a future microservice.
Currently, execution happens directly in the main platform.

When we need to scale or separate Docker permissions, this service
will handle all Docker/gVisor execution, keeping the main platform 
free from needing Docker access.

To use: Set EXECUTION_MODE=remote environment variable
"""

from typing import Dict, Any
import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import queue

# Import our execution engines
from ..execution_engine.execution import DockerEngine, GVisorEngine, DisabledEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExecutionService:
    """Standalone execution service that can run in its own container."""
    
    def __init__(self, port: int = 8081):
        self.port = port
        self.engine = self._initialize_engine()
        self.execution_queue = queue.Queue()
        
    def _initialize_engine(self):
        """Initialize the best available execution engine."""
        import platform
        
        # Try gVisor on Linux
        if platform.system() == 'Linux':
            try:
                engine = GVisorEngine()
                logger.info("🛡️ Using gVisor execution engine")
                return engine
            except Exception as e:
                logger.warning(f"gVisor not available: {e}")
        
        # Try Docker
        try:
            engine = DockerEngine()
            logger.info("🐳 Using Docker execution engine")
            return engine
        except Exception as e:
            logger.error(f"Docker not available: {e}")
            logger.warning("⚠️ No execution engine available - service will reject all requests")
            return DisabledEngine("No execution engine available in executor service")
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        """Execute code using the configured engine."""
        return self.engine.execute(code, eval_id)
    
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint data."""
        return {
            'service': 'execution-service',
            'healthy': isinstance(self.engine, (DockerEngine, GVisorEngine)),
            'engine': self.engine.get_description(),
            'engine_health': self.engine.health_check()
        }


class ExecutionHandler(BaseHTTPRequestHandler):
    """HTTP handler for execution requests."""
    
    def do_POST(self):
        """Handle execution requests."""
        if self.path == '/execute':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                code = data.get('code', '')
                eval_id = data.get('eval_id', 'unknown')
                
                # Execute using the service
                result = self.server.execution_service.execute(code, eval_id)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                logger.error(f"Execution error: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': str(e),
                    'status': 'error'
                }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        """Handle health check."""
        if self.path == '/health':
            health = self.server.execution_service.health_check()
            
            self.send_response(200 if health['healthy'] else 503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use proper logging."""
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    """Run the execution service."""
    port = int(os.environ.get('EXECUTOR_PORT', '8081'))
    
    logger.info(f"🚀 Starting execution service on port {port}")
    
    # Create service
    service = ExecutionService(port)
    
    # Create HTTP server
    server = HTTPServer(('0.0.0.0', port), ExecutionHandler)
    server.execution_service = service
    
    logger.info(f"✅ Execution service ready on http://0.0.0.0:{port}")
    logger.info(f"   Engine: {service.engine.get_description()}")
    logger.info("   Health check: http://0.0.0.0:{}/health".format(port))
    logger.info("   Execute endpoint: http://0.0.0.0:{}/execute".format(port))
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down execution service")
        server.shutdown()


if __name__ == '__main__':
    main()