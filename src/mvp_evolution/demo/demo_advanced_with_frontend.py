#!/usr/bin/env python3
"""
Advanced platform demo with modular web frontend component.
Shows how the web frontend component integrates with the full platform.

Run with: python demo_advanced_with_frontend.py
Then open: http://localhost:8000
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys
from urllib.parse import urlparse

from components import (
    # Execution engines
    SubprocessEngine, DockerEngine, GVisorEngine,
    
    # Core components
    AdvancedMonitor, TaskQueue, QueuedEvaluationPlatform,
    
    # Web frontend
    FrontendType, FrontendConfig, create_frontend,
    
    # API
    RESTfulAPI
)


class AdvancedPlatformHandler(BaseHTTPRequestHandler):
    """HTTP handler that integrates all components"""
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        
        if path == '/':
            # Serve frontend HTML
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
            asset_path = path[8:]
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
                
        # API endpoints
        elif path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.server.platform.get_status()).encode())
            
        elif path == '/api/queue-status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.server.platform.get_queue_status()).encode())
            
        elif path.startswith('/api/eval-status/'):
            eval_id = path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.server.platform.get_evaluation_status(eval_id)).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        
        # Read request body
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        
        if path == '/api/eval':
            # Synchronous evaluation
            data = json.loads(body)
            result = self.server.platform.evaluate(data['code'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        elif path == '/api/eval-async':
            # Asynchronous evaluation
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
        """Suppress request logging"""
        pass


def create_advanced_platform():
    """Create platform with appropriate execution engine"""
    
    # Choose engine based on availability
    if '--unsafe' in sys.argv:
        print("⚠️  WARNING: Running with UNSAFE subprocess execution!")
        engine = SubprocessEngine()
    else:
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            
            # Check for gVisor
            docker_info = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            if 'runsc' in docker_info.stdout:
                print("✅ gVisor runtime detected - using production security")
                engine = GVisorEngine('runsc')
            else:
                print("ℹ️  Using Docker engine (install gVisor for enhanced security)")
                engine = DockerEngine()
        except:
            print("❌ Docker not available!")
            print("   Please install Docker or use --unsafe flag")
            sys.exit(1)
    
    # Create platform components
    monitor = AdvancedMonitor()
    queue = TaskQueue(max_workers=3)
    platform = QueuedEvaluationPlatform(engine, monitor, queue)
    
    return platform


def main():
    """Main entry point"""
    print("Advanced Platform with Modular Frontend")
    print("=" * 50)
    
    # Create platform
    platform = create_advanced_platform()
    
    # Show platform test results
    print("\nPlatform Component Tests:")
    for component, result in platform.test_results.items():
        if component != 'overall':
            status = "✅" if result['passed'] else "❌"
            print(f"  {status} {component.upper()}: {result['message']}")
    print("-" * 50)
    print(f"Overall: {platform.test_results['overall']['message']}")
    
    # Create frontend with full features
    frontend_config = FrontendConfig(
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
    
    # Let user choose frontend type
    if '--simple' in sys.argv:
        frontend_type = FrontendType.SIMPLE_HTML
        print("\n📄 Using Simple HTML Frontend")
    else:
        frontend_type = FrontendType.ADVANCED_HTML
        print("\n🚀 Using Advanced HTML Frontend")
    
    frontend = create_frontend(frontend_type, frontend_config)
    
    # Show frontend test results
    print("\nFrontend Component Tests:")
    frontend_results = frontend.self_test()
    for test in frontend_results['tests']:
        status = "✅" if test['passed'] else "❌"
        print(f"  {status} {test['name']}: {test['message']}")
    
    # Demonstrate customization
    if '--dark' in sys.argv:
        print("\n🌙 Applying dark theme...")
        frontend.customize({'theme': 'dark'})
    
    # Ensure platform is healthy before starting
    platform.start_if_healthy()
    
    # Create and configure server
    server = HTTPServer(('localhost', 8000), AdvancedPlatformHandler)
    server.platform = platform
    server.frontend = frontend
    
    print("\n" + "=" * 50)
    print(f"🌐 Platform running at http://localhost:8000")
    print(f"   Frontend: {frontend_type.value}")
    print(f"   Theme: {frontend.config.theme}")
    print(f"   Engine: {type(platform.engine).__name__}")
    print("\nOptions:")
    print("  --unsafe  : Use subprocess execution (no Docker required)")
    print("  --simple  : Use simple HTML frontend")
    print("  --dark    : Apply dark theme")
    print("\nPress Ctrl+C to shutdown")
    print("=" * 50)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        platform.shutdown()
        print("Shutdown complete.")


if __name__ == '__main__':
    main()