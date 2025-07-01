#!/usr/bin/env python3
"""
Demo script to run both API and Frontend servers for development.
In production, these would be separate services.
"""

import sys
import time
import threading
import http.server

from components import (
    SubprocessEngine,
    DockerEngine,
    GVisorEngine,
    AdvancedMonitor,
    TaskQueue,
    QueuedEvaluationPlatform,
    FileStorage,
    create_api_service,
    create_api_handler,
    APIRequest,
    HTTPMethod,
    create_frontend,
    FrontendConfig,
    FrontendType,
    EventBus
)


class SimpleAPIServer:
    """Simple HTTP server wrapper for the API service"""
    def __init__(self, api_handler, port=8001):
        self.api_handler = api_handler
        self.port = port
        self.server = None
        
    def start(self):
        handler_instance = self.api_handler
        
        class APIRequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self._handle_request('GET')
                
            def do_POST(self):
                self._handle_request('POST')
                
            def _handle_request(self, method):
                # Create APIRequest
                body = None
                if method == 'POST':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)
                
                request = APIRequest(
                    method=HTTPMethod[method],
                    path=self.path,
                    headers=dict(self.headers),
                    body=body
                )
                
                # Handle with API handler
                response = handler_instance.handle_request(request)
                
                # Send response
                self.send_response(response.status_code)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.body)
                
            def log_message(self, format, *args):
                # Suppress logs
                pass
        
        self.server = http.server.HTTPServer(('', self.port), APIRequestHandler)
        thread = threading.Thread(target=self.server.serve_forever)
        thread.daemon = True
        thread.start()
        

def main():
    print("🚀 Crucible Demo - Starting API and Frontend servers")
    print()
    
    # Create execution engine
    try:
        engine = GVisorEngine()
        print("🛡️  Using gVisor")
    except:
        try:
            engine = DockerEngine()
            print("🐳 Using Docker")
        except:
            engine = SubprocessEngine()
            print("⚠️  Using subprocess")
    
    # Create components
    event_bus = EventBus()
    queue = TaskQueue(max_workers=4)
    monitor = AdvancedMonitor()
    storage = FileStorage("./demo_storage")
    
    # Create platform
    platform = QueuedEvaluationPlatform(
        engine=engine,
        queue=queue,
        monitor=monitor
    )
    
    # Create API service and handler
    api_service = create_api_service(platform)
    api_handler = create_api_handler(api_service)
    
    # Start API server on port 8001
    api_server = SimpleAPIServer(api_handler, port=8001)
    api_server.start()
    print("📡 API server running on http://localhost:8001")
    
    # Create and start frontend on port 8000
    frontend_config = FrontendConfig(
        port=8000,
        api_base_url="http://localhost:8001",
        enable_monitoring=True
    )
    
    frontend = create_frontend(
        frontend_type=FrontendType.SIMPLE_HTTP,
        config=frontend_config
    )
    
    frontend.start()
    print("🌐 Frontend running on http://localhost:8000")
    print()
    print("✅ Both servers running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if api_server.server:
            api_server.server.shutdown()
        frontend.stop()


if __name__ == "__main__":
    sys.exit(main())