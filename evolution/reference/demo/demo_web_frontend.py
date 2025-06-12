#!/usr/bin/env python3
"""
Demo script for the web frontend component.
Shows how to use different frontend implementations with the API component.

Run with: python demo_web_frontend.py
Then open: http://localhost:8001 for simple, http://localhost:8002 for advanced
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from urllib.parse import urlparse

from components import (
    # Frontend components
    FrontendType, FrontendConfig, create_frontend,
    
    # API components
    RESTfulAPI,
    
    # Platform components
    SubprocessEngine, InMemoryMonitor, TaskQueue,
    QueuedEvaluationPlatform
)


class FrontendHandler(BaseHTTPRequestHandler):
    """HTTP handler that integrates frontend with API"""
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            # Serve main HTML
            html = self.server.frontend.get_index_html()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
            
        elif path == '/config.json':
            # Serve frontend configuration
            config = self.server.frontend.get_config()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(config.encode())
            
        elif path.startswith('/assets/'):
            # Serve static assets
            asset_path = path[8:]  # Remove /assets/
            result = self.server.frontend.get_asset(asset_path)
            
            if result:
                content, content_type = result
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
                
        elif path.startswith('/api/'):
            # Forward to API service
            api_path = path[4:]  # Remove /api
            
            if hasattr(self.server, 'api_handler'):
                self.server.api_handler(self, 'GET', api_path)
            else:
                self.send_response(404)
                self.end_headers()
                
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith('/api/'):
            # Forward to API service
            api_path = path[4:]  # Remove /api
            
            # Read body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            
            # Simple API handling for demo
            if api_path == '/eval':
                data = json.loads(body)
                result = self.server.platform.evaluate(data['code'])
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            elif api_path == '/eval-async':
                data = json.loads(body)
                result = self.server.platform.evaluate_async(data['code'])
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            else:
                self.send_response(404)
                self.end_headers()
                
    def log_message(self, format, *args):
        # Suppress request logging
        pass


def run_frontend_demo(frontend_type: FrontendType, port: int, config: FrontendConfig):
    """Run a frontend demo server"""
    
    # Create platform components
    engine = SubprocessEngine()
    monitor = InMemoryMonitor()
    queue = TaskQueue(max_workers=2)
    platform = QueuedEvaluationPlatform(engine, monitor, queue)
    
    # Create frontend
    frontend = create_frontend(frontend_type, config)
    
    # Test frontend
    print(f"\n{frontend_type.value.upper()} Frontend Tests:")
    test_results = frontend.self_test()
    for test in test_results['tests']:
        status = "✅" if test['passed'] else "❌"
        print(f"  {status} {test['name']}: {test['message']}")
    
    # Create server
    server = HTTPServer(('localhost', port), FrontendHandler)
    server.frontend = frontend
    server.platform = platform
    
    print(f"\n🚀 {frontend_type.value.upper()} Frontend running at http://localhost:{port}")
    
    # Run in thread
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    return server, platform


if __name__ == '__main__':
    print("Web Frontend Component Demo")
    print("=" * 50)
    
    # Demo 1: Simple HTML Frontend
    simple_config = FrontendConfig(
        api_base_url="/api",
        enable_monitoring=False,
        enable_queue=False,
        features={
            'async_execution': False,
            'real_time_updates': False,
            'batch_submission': False,
            'event_streaming': False,
            'security_warnings': True
        }
    )
    
    simple_server, simple_platform = run_frontend_demo(
        FrontendType.SIMPLE_HTML, 
        8001,
        simple_config
    )
    
    # Demo 2: Advanced HTML Frontend
    advanced_config = FrontendConfig(
        api_base_url="/api",
        enable_monitoring=True,
        enable_queue=True,
        theme="default",
        features={
            'async_execution': True,
            'real_time_updates': True,
            'batch_submission': True,
            'event_streaming': True,
            'security_warnings': True
        }
    )
    
    advanced_server, advanced_platform = run_frontend_demo(
        FrontendType.ADVANCED_HTML,
        8002,
        advanced_config
    )
    
    # Demo 3: Customization example
    print("\nDemonstrating runtime customization...")
    
    # Create a dark theme frontend
    dark_frontend = create_frontend(FrontendType.ADVANCED_HTML)
    dark_frontend.customize({
        'theme': 'dark',
        'features': {
            'security_warnings': False,
            'batch_submission': False
        }
    })
    
    print("  - Created dark theme frontend")
    print(f"  - Theme: {dark_frontend.config.theme}")
    print(f"  - Security warnings: {dark_frontend.config.features['security_warnings']}")
    
    # Demo 4: Future frontend types (placeholders)
    print("\nFuture frontend types (ready for implementation):")
    print("  - React Frontend: Component-based UI with state management")
    print("  - WebSocket Frontend: Real-time bidirectional communication")
    
    print("\n" + "=" * 50)
    print("Frontend servers running:")
    print(f"  Simple HTML:   http://localhost:8001")
    print(f"  Advanced HTML: http://localhost:8002")
    print("\nPress Ctrl+C to stop all servers")
    
    try:
        # Keep main thread alive
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        simple_server.shutdown()
        advanced_server.shutdown()
        simple_platform.shutdown()
        advanced_platform.shutdown()
        print("Shutdown complete.")