"""
Web Frontend component for TRACE-AI architecture.
Provides a complete frontend service including HTTP server, HTML generation, and API integration.

This component owns the entire web layer, from HTTP server to HTML/JS generation.
It demonstrates evolution from simple Python http.server to full microservices.

Evolution path:
1. SimpleHTTPFrontend: Python's http.server + basic HTML
2. AdvancedHTMLFrontend: Advanced HTML/JS, no framework dependency
3. FlaskFrontend: Flask app with templates and better routing
4. FastAPIFrontend: FastAPI with async support and WebSockets
5. ReactFrontend: Separate React SPA + nginx (full microservice)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Callable
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from enum import Enum
import os
import mimetypes
import threading
import http.server
import socketserver
from http import HTTPStatus
import time
import asyncio

# Import API types
from ..api.api import APIRequest, APIResponse, HTTPMethod
from urllib.parse import urlparse, parse_qs

from ..shared.base import TestableComponent
from .favicon import get_favicon_bytes, get_svg_favicon


class FrontendType(Enum):
    """Types of frontend implementations"""
    SIMPLE_HTTP = "simple_http"      # Python http.server
    ADVANCED_HTTP = "advanced_http"  # Advanced HTML/JS, no framework
    FLASK = "flask"                  # Flask framework
    FASTAPI = "fastapi"              # FastAPI with async
    REACT = "react"                  # React + nginx
    API_ONLY = "api_only"            # API only, no HTML (for separate frontend)


@dataclass
class FrontendConfig:
    """Configuration for frontend services"""
    # Server configuration
    host: str = os.environ.get('BIND_HOST', 'localhost')  # Configurable bind address
    port: int = 8080
    
    # API integration
    api_base_url: str = "/api"
    platform_host: str = os.environ.get('PLATFORM_HOST', 'localhost')
    platform_port: int = 8000
    
    # Frontend features
    websocket_url: Optional[str] = None
    enable_monitoring: bool = True
    enable_queue: bool = True
    theme: str = "default"
    features: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {
                'async_execution': True,
                'real_time_updates': True,
                'batch_submission': True,
                'event_streaming': True,
                'security_warnings': True
            }
    
    def to_json(self) -> str:
        """Convert config to JSON for frontend consumption"""
        return json.dumps({
            'apiBaseUrl': self.api_base_url,
            'websocketUrl': self.websocket_url,
            'enableMonitoring': self.enable_monitoring,
            'enableQueue': self.enable_queue,
            'theme': self.theme,
            'features': self.features
        })


class WebFrontendService(TestableComponent, ABC):
    """
    Abstract base class for web frontend services.
    Includes HTTP server capabilities and platform integration.
    """
    
    def __init__(self, config: Optional[FrontendConfig] = None, api_service=None, api_handler=None):
        self.config = config or FrontendConfig()
        self.api_service = api_service  # Optional API service for integrated deployments
        self.api_handler = api_handler  # Optional API handler for routing requests
        self.assets: Dict[str, bytes] = {}
        self.server = None
        self.server_thread = None
        self.is_running = False
        self._load_assets()
        
    @abstractmethod
    def start(self) -> None:
        """Start the HTTP server"""
        pass
        
    @abstractmethod
    def stop(self) -> None:
        """Stop the HTTP server"""
        pass
        
    @abstractmethod
    def get_index_html(self) -> str:
        """Return the main HTML page"""
        pass
        
    @abstractmethod
    def get_asset(self, path: str) -> Optional[Tuple[bytes, str]]:
        """
        Return static asset content and content type.
        Returns None if asset not found.
        """
        pass
        
    @abstractmethod
    def handle_api_request(self, method: str, path: str, body: Optional[str] = None) -> Dict[str, Any]:
        """Handle API requests by forwarding to platform"""
        pass
        
    def get_config(self) -> str:
        """Return frontend configuration as JSON"""
        return self.config.to_json()
        
    def customize(self, options: Dict[str, Any]) -> None:
        """Apply runtime customization options"""
        if 'theme' in options:
            self.config.theme = options['theme']
        if 'features' in options:
            self.config.features.update(options['features'])
        if 'api_base_url' in options:
            self.config.api_base_url = options['api_base_url']
            
    @abstractmethod
    def _load_assets(self) -> None:
        """Load static assets into memory"""
        pass
        
    def self_test(self) -> Dict[str, Any]:
        """Test the frontend service including server functionality"""
        tests = []
        
        # Test HTML generation
        try:
            html = self.get_index_html()
            tests.append({
                'name': 'html_generation',
                'passed': len(html) > 0 and '<!DOCTYPE html>' in html,
                'message': 'HTML generation works'
            })
        except Exception as e:
            tests.append({
                'name': 'html_generation',
                'passed': False,
                'message': f'HTML generation failed: {e}'
            })
            
        # Test configuration
        try:
            config = self.get_config()
            config_data = json.loads(config)
            tests.append({
                'name': 'configuration',
                'passed': 'apiBaseUrl' in config_data,
                'message': 'Configuration is valid JSON'
            })
        except Exception as e:
            tests.append({
                'name': 'configuration',
                'passed': False,
                'message': f'Configuration invalid: {e}'
            })
            
        # Test customization
        try:
            original_theme = self.config.theme
            self.customize({'theme': 'dark'})
            tests.append({
                'name': 'customization',
                'passed': self.config.theme == 'dark',
                'message': 'Customization works'
            })
            self.config.theme = original_theme
        except Exception as e:
            tests.append({
                'name': 'customization',
                'passed': False,
                'message': f'Customization failed: {e}'
            })
            
        # Test server start/stop
        try:
            self.start()
            time.sleep(0.5)  # Let server start
            tests.append({
                'name': 'server_start',
                'passed': self.is_running,
                'message': 'Server starts successfully'
            })
            self.stop()
            tests.append({
                'name': 'server_stop',
                'passed': not self.is_running,
                'message': 'Server stops successfully'
            })
        except Exception as e:
            tests.append({
                'name': 'server_lifecycle',
                'passed': False,
                'message': f'Server lifecycle failed: {e}'
            })
            
        passed = all(t['passed'] for t in tests)
        return {
            'passed': passed,
            'tests': tests,
            'message': 'All tests passed' if passed else 'Some tests failed'
        }
        
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite for this component"""
        
        class FrontendServiceTests(unittest.TestCase):
            def setUp(self):
                self.service = self.__class__.service_class()
                
            def test_html_generation(self):
                html = self.service.get_index_html()
                self.assertIsInstance(html, str)
                self.assertIn('<!DOCTYPE html>', html)
                
            def test_configuration(self):
                config_json = self.service.get_config()
                config = json.loads(config_json)
                self.assertIn('apiBaseUrl', config)
                self.assertIn('features', config)
                
            def test_customization(self):
                self.service.customize({'theme': 'custom'})
                self.assertEqual(self.service.config.theme, 'custom')
                
            def test_asset_serving(self):
                # Test CSS asset
                result = self.service.get_asset('styles.css')
                if result:
                    content, content_type = result
                    self.assertEqual(content_type, 'text/css')
                    
            def test_server_lifecycle(self):
                self.service.start()
                self.assertTrue(self.service.is_running)
                self.service.stop()
                self.assertFalse(self.service.is_running)
                
            def test_api_request_handling(self):
                # Mock API service if not provided
                if not self.service.api_service:
                    self.service.api_service = Mock()
                    self.service.api_service.process_evaluation.return_value = {
                        'output': 'Test output',
                        'error': None
                    }
                
                result = self.service.handle_api_request(
                    'POST', '/api/eval', 
                    json.dumps({'code': 'print("test")'})
                )
                self.assertIn('output', result)
                
        # Store reference to actual class for tests
        FrontendServiceTests.service_class = type(self)
        
        suite = unittest.TestSuite()
        suite.addTest(FrontendServiceTests('test_html_generation'))
        suite.addTest(FrontendServiceTests('test_configuration'))
        suite.addTest(FrontendServiceTests('test_customization'))
        suite.addTest(FrontendServiceTests('test_asset_serving'))
        suite.addTest(FrontendServiceTests('test_server_lifecycle'))
        suite.addTest(FrontendServiceTests('test_api_request_handling'))
        
        return suite


class SimpleHTTPFrontend(WebFrontendService):
    """
    Simple HTTP frontend using Python's built-in http.server.
    This is the most basic implementation showing direct HTTP handling.
    """
    
    def start(self) -> None:
        """Start the HTTP server"""
        if self.is_running:
            return
            
        # Create custom request handler
        parent = self
        
        class RequestHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                try:
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html')
                        self.end_headers()
                        self.wfile.write(parent.get_index_html().encode())
                    elif self.path == '/favicon.ico':
                        self.send_response(200)
                        self.send_header('Content-Type', 'image/x-icon')
                        self.send_header('Cache-Control', 'public, max-age=31536000')  # Cache for 1 year
                        self.end_headers()
                        self.wfile.write(get_favicon_bytes())
                    elif self.path == '/favicon.svg':
                        self.send_response(200)
                        self.send_header('Content-Type', 'image/svg+xml')
                        self.send_header('Cache-Control', 'public, max-age=31536000')
                        self.end_headers()
                        self.wfile.write(get_svg_favicon().encode())
                    elif self.path == '/config.json':
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(parent.get_config().encode())
                    elif self.path.startswith('/assets/'):
                        asset_path = self.path[8:]  # Remove /assets/
                        result = parent.get_asset(asset_path)
                        if result:
                            content, content_type = result
                            self.send_response(200)
                            self.send_header('Content-Type', content_type)
                            self.end_headers()
                            self.wfile.write(content)
                        else:
                            self.send_error(404)
                    elif self.path.startswith('/api/'):
                        # Handle API requests using api_handler if available
                        if parent.api_handler:
                            request = APIRequest(
                                method=HTTPMethod.GET,
                                path=self.path[4:],  # Remove /api prefix
                                headers=dict(self.headers),
                                body=None
                            )
                            response = parent.api_handler.handle_request(request)
                            
                            self.send_response(response.status_code)
                            for key, value in response.headers.items():
                                self.send_header(key, value)
                            self.end_headers()
                            self.wfile.write(response.body)
                        else:
                            # No API handler configured
                            self.send_response(501)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                'error': 'API handler not configured',
                                'message': 'In production, configure your frontend to call the API service directly'
                            }).encode())
                    else:
                        self.send_error(404)
                except (BrokenPipeError, ConnectionResetError):
                    # Client disconnected, ignore
                    pass
                except Exception as e:
                    try:
                        self.send_error(500, str(e))
                    except:
                        pass
                    
            def do_POST(self):
                try:
                    if self.path.startswith('/api/'):
                        # Handle API requests using api_handler if available
                        if parent.api_handler:
                            content_length = int(self.headers.get('Content-Length', 0))
                            body = self.rfile.read(content_length) if content_length > 0 else None
                            
                            request = APIRequest(
                                method=HTTPMethod.POST,
                                path=self.path[4:],  # Remove /api prefix
                                headers=dict(self.headers),
                                body=body
                            )
                            response = parent.api_handler.handle_request(request)
                            
                            self.send_response(response.status_code)
                            for key, value in response.headers.items():
                                self.send_header(key, value)
                            self.end_headers()
                            self.wfile.write(response.body)
                        else:
                            # No API handler configured
                            self.send_response(501)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                'error': 'API handler not configured',
                                'message': 'In production, configure your frontend to call the API service directly'
                            }).encode())
                    else:
                        self.send_error(404)
                except (BrokenPipeError, ConnectionResetError):
                    # Client disconnected, ignore
                    pass
                except Exception as e:
                    try:
                        self.send_error(500, str(e))
                    except:
                        pass
                    
            def log_message(self, format, *args):
                # Suppress logs in test mode
                if not parent.config.features.get('suppress_logs', False):
                    super().log_message(format, *args)
        
        # Use ThreadingTCPServer for concurrent requests
        self.server = socketserver.ThreadingTCPServer(
            (self.config.host, self.config.port),
            RequestHandler
        )
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.is_running = True
        
    def stop(self) -> None:
        """Stop the HTTP server"""
        if self.server and self.is_running:
            self.server.shutdown()
            self.server_thread.join(timeout=5)
            self.is_running = False
    
    def handle_api_request(self, method: str, path: str, body: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle API requests by forwarding to API service.
        In a real deployment, API requests would go directly to the API service,
        but for the integrated demo, we forward them.
        """
        # This is a placeholder - in production, the frontend wouldn't handle API requests
        # API requests would go directly to the API service endpoint
        return {'error': 'API forwarding not configured', 'status': 501}
    
    def get_index_html(self) -> str:
        """Return simple HTML interface"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Crucible Platform - Simple Edition</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="shortcut icon" href="/favicon.ico">
    <style>
        body {{ font-family: Arial; max-width: 600px; margin: 50px auto; }}
        textarea {{ width: 100%; height: 150px; font-family: monospace; }}
        button {{ background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }}
        pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
        .warning {{ background: #ff0000; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Crucible Evaluation Platform</h1>
    
    {"<div class='warning'><h2>⚠️ SAFETY WARNING ⚠️</h2><p>This platform executes Python code. Use with caution.</p></div>" if self.config.features.get('security_warnings', True) else ""}
    
    <p>Submit Python code for evaluation:</p>
    
    <textarea id="code" placeholder="print('Hello, Crucible!')">print('Hello, Crucible!')</textarea>
    <br><br>
    <button onclick="runEval()">Run Evaluation</button>
    
    <div id="result"></div>
    
    <script>
        const config = {json.dumps(self.config.__dict__)};
        
        async function runEval() {{
            const code = document.getElementById('code').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '<p>Submitting evaluation...</p>';
            
            try {{
                const response = await fetch('/api/eval', {{
                    method: 'POST',
                    body: JSON.stringify({{code}}),
                    headers: {{'Content-Type': 'application/json'}}
                }});
                
                const result = await response.json();
                
                if (response.ok) {{
                    resultDiv.innerHTML = `
                        <h3>Result:</h3>
                        <pre>${{result.output || result.error || JSON.stringify(result, null, 2)}}</pre>
                    `;
                }} else {{
                    resultDiv.innerHTML = `
                        <h3>Error:</h3>
                        <pre>${{result.error || 'Unknown error'}}</pre>
                    `;
                }}
            }} catch (e) {{
                resultDiv.innerHTML = `
                    <h3>Error:</h3>
                    <pre>${{e.message}}</pre>
                `;
            }}
        }}
    </script>
</body>
</html>
"""
    
    def get_asset(self, path: str) -> Optional[Tuple[bytes, str]]:
        """Simple frontend has no additional assets"""
        return None
        
    def _load_assets(self) -> None:
        """No assets to load for simple frontend"""
        pass


class FlaskFrontend(WebFrontendService):
    """
    Flask-based frontend showing evolution to a proper web framework.
    Demonstrates templates, better routing, and session management.
    """
    
    def __init__(self, config: Optional[FrontendConfig] = None, platform=None, api_handler=None):
        super().__init__(config, platform, api_handler)
        self.flask_app = None
        self._setup_flask()
        
    def _setup_flask(self):
        """Setup Flask application"""
        try:
            from flask import Flask, render_template_string, request, jsonify
            
            self.flask_app = Flask(__name__)
            parent = self
            
            @self.flask_app.route('/')
            def index():
                return parent.get_index_html()
                
            @self.flask_app.route('/api/eval', methods=['POST'])
            def eval_endpoint():
                result = parent.handle_api_request(
                    'POST', '/api/eval', 
                    request.get_data(as_text=True)
                )
                return jsonify(result), result.get('status', 200)
                
            @self.flask_app.route('/api/status')
            def status_endpoint():
                result = parent.handle_api_request('GET', '/api/status')
                return jsonify(result)
                
        except ImportError:
            # Flask not available, fallback to simple implementation
            self.flask_app = None
    
    def start(self) -> None:
        """Start Flask server"""
        if self.is_running:
            return
            
        if self.flask_app:
            # Run Flask in thread
            from werkzeug.serving import make_server
            
            self.server = make_server(
                self.config.host, 
                self.config.port,
                self.flask_app,
                threaded=True
            )
            
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.is_running = True
        else:
            # Fallback to simple HTTP server
            super().start()
            
    def stop(self) -> None:
        """Stop Flask server"""
        if self.server and self.is_running:
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join(timeout=5)
            self.is_running = False
            
    def handle_api_request(self, method: str, path: str, body: Optional[str] = None) -> Dict[str, Any]:
        """Handle API requests"""
        # Same as SimpleHTTPFrontend
        if not self.platform:
            return {'error': 'No platform connected', 'status': 503}
            
        try:
            if path == '/api/eval' and method == 'POST':
                data = json.loads(body) if body else {}
                return self.platform.handle_evaluation(data.get('code', ''))
            elif path == '/api/status':
                return self.platform.get_status()
            else:
                return {'error': 'Unknown endpoint', 'status': 404}
        except Exception as e:
            return {'error': str(e), 'status': 500}
    
    def get_index_html(self) -> str:
        """Return Flask-style HTML interface"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Crucible Platform - Flask Edition</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="shortcut icon" href="/favicon.ico">
    <style>
        body {{ font-family: Arial; max-width: 800px; margin: 50px auto; }}
        .container {{ padding: 20px; }}
        textarea {{ width: 100%; height: 150px; font-family: monospace; }}
        button {{ background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; }}
        .flash-message {{ background: #ffc107; padding: 10px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌟 Crucible Platform - Flask Edition</h1>
        <div class="flash-message">
            Flask framework features: Templates, Sessions, Better routing
        </div>
        <textarea id="code" placeholder="Enter Python code...">print('Flask edition!')</textarea>
        <br><br>
        <button onclick="submitCode()">Evaluate</button>
        <div id="result"></div>
    </div>
    <script>
        async function submitCode() {{
            const code = document.getElementById('code').value;
            const response = await fetch('/api/eval', {{
                method: 'POST',
                body: JSON.stringify({{code}}),
                headers: {{'Content-Type': 'application/json'}}
            }});
            const result = await response.json();
            document.getElementById('result').innerHTML = `<pre>${{JSON.stringify(result, null, 2)}}</pre>`;
        }}
    </script>
</body>
</html>
"""
            

class AdvancedHTMLFrontend(SimpleHTTPFrontend):
    """
    Advanced HTML frontend with full features but no Flask dependency.
    Shows progression from basic HTML to sophisticated JavaScript without
    requiring a web framework.
    """
    
    def get_index_html(self) -> str:
        """Return advanced HTML interface with queue, monitoring, etc."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Crucible Platform - Advanced Edition</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="shortcut icon" href="/favicon.ico">
    <style>
        {self._get_styles()}
    </style>
</head>
<body>
    <h1>🚀 Crucible Platform - Advanced Edition</h1>
    
    <div class="info">
        <h3>Advanced Features Active</h3>
        <ul>
            {self._get_feature_list()}
        </ul>
    </div>
    
    <div class="container">
        <div class="left-panel">
            <h3>Submit Evaluation</h3>
            <textarea id="code" placeholder="Enter Python code to evaluate...">{self._get_default_code()}</textarea>
            <br><br>
            <button onclick="submitEvaluation()">Submit to Queue</button>
            {self._get_batch_button()}
            <button onclick="getQueueStatus()">Queue Status</button>
            
            <div id="submission-result"></div>
            
            <h3>Active Evaluations</h3>
            <div id="evaluations"></div>
        </div>
        
        <div class="right-panel">
            {self._get_monitoring_panel()}
        </div>
    </div>
    
    <script>
        const config = {self.config.to_json()};
        {self._get_javascript()}
    </script>
</body>
</html>
"""
    
    def _get_styles(self) -> str:
        """Return CSS styles"""
        return """
        body { font-family: Arial; max-width: 1000px; margin: 50px auto; }
        .container { display: flex; gap: 20px; }
        .left-panel { flex: 1; }
        .right-panel { flex: 1; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; }
        button:hover { background: #218838; }
        .status { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .events { background: #f5f5f5; padding: 10px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; }
        .event { margin: 2px 0; }
        .event-info { color: #17a2b8; }
        .event-complete { color: #28a745; }
        .event-error { color: #dc3545; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .info { background: #d1ecf1; color: #0c5460; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .queue-status { background: #e7f3ff; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .eval-status { padding: 10px; margin: 5px 0; border: 1px solid #dee2e6; border-radius: 5px; }
        .eval-status.queued { background: #fff3cd; }
        .eval-status.running { background: #cfe2ff; }
        .eval-status.completed { background: #d1e7dd; }
        .eval-status.failed { background: #f8d7da; }
        """
        
    def _get_feature_list(self) -> str:
        """Generate feature list HTML"""
        features = []
        if self.config.enable_queue:
            features.append("✅ <strong>Queue-based execution</strong> - Non-blocking, concurrent evaluations")
        if self.config.enable_monitoring:
            features.append("✅ <strong>Real-time monitoring</strong> - Live event streaming")
        if self.config.features.get('async_execution'):
            features.append("✅ <strong>Asynchronous processing</strong> - Handle multiple evaluations")
        features.append("✅ <strong>Security isolation</strong> - Docker/gVisor sandboxing")
        
        return '\n'.join(f'<li>{feature}</li>' for feature in features)
        
    def _get_default_code(self) -> str:
        """Return default code example"""
        return """import time
import random

print("Advanced evaluation starting...")
time.sleep(random.uniform(1, 3))  # Simulate variable work

# Generate some results
result = sum(range(100))
print(f"Calculation result: {result}")

# Test isolation
try:
    import requests
    print("❌ Network access allowed!")
except:
    print("✅ Network properly isolated")

print("Evaluation complete!")"""
    
    def _get_batch_button(self) -> str:
        """Return batch submission button if enabled"""
        if self.config.features.get('batch_submission', True):
            return '<button onclick="submitMultiple()">Submit 5 Evaluations</button>'
        return ''
        
    def _get_monitoring_panel(self) -> str:
        """Return monitoring panel HTML"""
        if not self.config.enable_monitoring:
            return '<div class="status">Monitoring disabled</div>'
            
        return """
            <h3>Queue Status</h3>
            <div id="queue-status" class="queue-status">Loading...</div>
            
            <h3>Real-time Event Stream</h3>
            <div id="events" class="events">
                <div class="event event-info">Waiting for events...</div>
            </div>
            
            <h3>Platform Status</h3>
            <div id="platform-status" class="status">Loading...</div>
        """
        
    def _get_javascript(self) -> str:
        """Return JavaScript code"""
        return """
        let activeEvaluations = new Map();
        let eventSources = new Map();
        
        // Clear any stale evaluations on page load
        activeEvaluations.clear();
        eventSources.clear();
        
        // Poll for updates if monitoring enabled
        if (config.enableMonitoring) {
            setInterval(updateStatus, 2000);
            updateStatus();
        }
        
        async function submitEvaluation() {
            const code = document.getElementById('code').value;
            
            const endpoint = config.features.async_execution ? '/api/eval-async' : '/api/eval';
            const response = await fetch(endpoint, {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const result = await response.json();
            
            if (config.features.async_execution) {
                document.getElementById('submission-result').innerHTML = `
                    <div class="status">
                        <strong>Submitted!</strong><br>
                        Evaluation ID: ${result.eval_id}<br>
                        Status: ${result.status}
                    </div>
                `;
                
                // Track evaluation
                activeEvaluations.set(result.eval_id, result);
                updateEvaluationsList();
                
                // Subscribe to events if enabled
                if (config.features.event_streaming) {
                    subscribeToEvents(result.eval_id);
                }
            } else {
                document.getElementById('submission-result').innerHTML = `
                    <div class="status">
                        <strong>Completed!</strong><br>
                        <pre>${result.output || result.error}</pre>
                    </div>
                `;
            }
        }
        
        async function submitMultiple() {
            for (let i = 0; i < 5; i++) {
                const code = `
import time
print(f"Batch evaluation ${i} starting...")
time.sleep(${1 + i * 0.5})  # Variable duration
result = ${i} * 100
print(f"Result: {result}")
print("Done!")
                `;
                
                const response = await fetch('/api/eval-async', {
                    method: 'POST',
                    body: JSON.stringify({code}),
                    headers: {'Content-Type': 'application/json'}
                });
                
                const result = await response.json();
                activeEvaluations.set(result.eval_id, result);
                if (config.features.event_streaming) {
                    subscribeToEvents(result.eval_id);
                }
            }
            
            updateEvaluationsList();
            document.getElementById('submission-result').innerHTML = `
                <div class="status">
                    <strong>Submitted 5 evaluations!</strong>
                </div>
            `;
        }
        
        function subscribeToEvents(evalId) {
            if (!eventSources.has(evalId)) {
                eventSources.set(evalId, {lastIndex: 0});
            }
        }
        
        async function updateStatus() {
            // Update queue status
            if (config.enableQueue) {
                try {
                    const queueResp = await fetch('/api/queue-status');
                    const queueStatus = await queueResp.json();
                    
                    document.getElementById('queue-status').innerHTML = `
                        <strong>Queue:</strong> ${queueStatus.queue.queued} queued<br>
                        <strong>Workers:</strong> ${queueStatus.queue.workers} active<br>
                        <strong>Completed:</strong> ${queueStatus.queue.completed}<br>
                        <strong>Failed:</strong> ${queueStatus.queue.failed}
                    `;
                } catch (e) {}
            }
            
            // Update platform status
            try {
                const statusResp = await fetch('/api/status');
                const status = await statusResp.json();
                
                let componentHtml = '<strong>Components:</strong><br>';
                if (status.components) {
                    for (const [name, comp] of Object.entries(status.components)) {
                        const health = comp.healthy ? '✅' : '❌';
                        componentHtml += `${health} ${name}: ${comp.component || comp.toString() || 'Unknown'}<br>`;
                    }
                }
                
                let engineInfo = '';
                if (status.engine) {
                    engineInfo = `<strong>Engine:</strong> ${status.engine}<br>`;
                }
                
                document.getElementById('platform-status').innerHTML = `
                    ${engineInfo}
                    ${componentHtml}
                    <strong>Platform:</strong> ${status.platform || 'Unknown'}<br>
                    <strong>Healthy:</strong> ${status.healthy ? '✅ Yes' : '❌ No'}
                `;
            } catch (e) {}
            
            // Update evaluation statuses
            for (const [evalId, evalData] of activeEvaluations.entries()) {
                // Skip if already completed or failed
                if (evalData.status === 'completed' || evalData.status === 'failed' || evalData.status === 'error') {
                    continue;
                }
                
                try {
                    const resp = await fetch(`/api/eval-status/${evalId}`);
                    const evalStatus = await resp.json();
                    
                    activeEvaluations.set(evalId, evalStatus);
                    
                    // Update events
                    if (evalStatus.events && eventSources.has(evalId)) {
                        const source = eventSources.get(evalId);
                        const newEvents = evalStatus.events.slice(source.lastIndex);
                        
                        for (const event of newEvents) {
                            addEvent(evalId, event);
                        }
                        
                        source.lastIndex = evalStatus.events.length;
                    }
                    
                    // Remove from active tracking if completed
                    if (evalStatus.status === 'completed' || evalStatus.status === 'failed' || evalStatus.status === 'error') {
                        // Keep in list for display but stop polling
                        setTimeout(() => {
                            // Remove after 30 seconds
                            activeEvaluations.delete(evalId);
                            eventSources.delete(evalId);
                            updateEvaluationsList();
                        }, 30000);
                    }
                } catch (e) {
                    // Remove if we can't get status (eval might not exist)
                    activeEvaluations.delete(evalId);
                }
            }
            
            updateEvaluationsList();
        }
        
        function updateEvaluationsList() {
            let html = '';
            
            for (const [evalId, evalData] of activeEvaluations) {
                html += `
                    <div class="eval-status ${evalData.status}">
                        <strong>${evalId}</strong>: ${evalData.status}
                        ${evalData.result ? `<br>Output: <pre>${evalData.result.output}</pre>` : ''}
                    </div>
                `;
            }
            
            document.getElementById('evaluations').innerHTML = html || '<em>No active evaluations</em>';
        }
        
        function addEvent(evalId, event) {
            const eventsDiv = document.getElementById('events');
            const eventClass = event.type === 'error' ? 'event-error' : 
                               event.type === 'complete' ? 'event-complete' : 
                               'event-info';
            
            const eventHtml = `
                <div class="event ${eventClass}">
                    [${evalId.substring(0, 8)}] ${event.type}: ${event.message}
                </div>
            `;
            
            eventsDiv.innerHTML = eventHtml + eventsDiv.innerHTML;
            
            // Keep only last 50 events
            while (eventsDiv.children.length > 50) {
                eventsDiv.removeChild(eventsDiv.lastChild);
            }
        }
        
        async function getQueueStatus() {
            await updateStatus();
        }
        """
        
    def get_asset(self, path: str) -> Optional[Tuple[bytes, str]]:
        """Return static assets"""
        if path in self.assets:
            content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            return (self.assets[path], content_type)
        return None
        
    def _load_assets(self) -> None:
        """Load any static assets (future: CSS/JS files)"""
        # For now, everything is inline
        # In future, we'd load external CSS/JS files here
        pass


class FastAPIFrontend(WebFrontendService):
    """
    FastAPI-based frontend showing async capabilities and WebSocket support.
    Demonstrates modern async Python web development.
    """
    
    def __init__(self, config: Optional[FrontendConfig] = None, platform=None):
        super().__init__(config, platform)
        self.fastapi_app = None
        self._setup_fastapi()
        
    def _setup_fastapi(self):
        """Setup FastAPI application"""
        try:
            from fastapi import FastAPI, WebSocket
            from fastapi.responses import HTMLResponse, JSONResponse
            import uvicorn
            
            self.fastapi_app = FastAPI()
            parent = self
            
            @self.fastapi_app.get('/', response_class=HTMLResponse)
            async def index():
                return parent.get_index_html()
                
            @self.fastapi_app.post('/api/eval')
            async def eval_endpoint(request: dict):
                result = parent.handle_api_request(
                    'POST', '/api/eval',
                    json.dumps(request)
                )
                return JSONResponse(result, status_code=result.get('status', 200))
                
            @self.fastapi_app.get('/api/status')
            async def status_endpoint():
                return parent.handle_api_request('GET', '/api/status')
                
            @self.fastapi_app.websocket('/ws')
            async def websocket_endpoint(websocket: WebSocket):
                await websocket.accept()
                # WebSocket handling for real-time updates
                await websocket.close()
                
        except ImportError:
            self.fastapi_app = None
            
    def start(self) -> None:
        """Start FastAPI server"""
        if self.is_running:
            return
            
        if self.fastapi_app:
            import uvicorn
            
            # Run in thread
            config = uvicorn.Config(
                self.fastapi_app,
                host=self.config.host,
                port=self.config.port,
                log_level="warning"
            )
            self.server = uvicorn.Server(config)
            
            self.server_thread = threading.Thread(target=self.server.run)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.is_running = True
        else:
            # Fallback
            super().start()
            
    def stop(self) -> None:
        """Stop FastAPI server"""
        if self.server and self.is_running:
            self.server.should_exit = True
            if self.server_thread:
                self.server_thread.join(timeout=5)
            self.is_running = False
            
    def handle_api_request(self, method: str, path: str, body: Optional[str] = None) -> Dict[str, Any]:
        """Handle API requests with async support"""
        # Same implementation as base
        if not self.platform:
            return {'error': 'No platform connected', 'status': 503}
            
        try:
            if path == '/api/eval' and method == 'POST':
                data = json.loads(body) if body else {}
                return self.platform.handle_evaluation(data.get('code', ''))
            elif path == '/api/status':
                return self.platform.get_status()
            else:
                return {'error': 'Unknown endpoint', 'status': 404}
        except Exception as e:
            return {'error': str(e), 'status': 500}
    
    def get_index_html(self) -> str:
        """Return FastAPI HTML interface with async features"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Crucible Platform - FastAPI Edition</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="shortcut icon" href="/favicon.ico">
    <style>
        body {{ font-family: Arial; max-width: 900px; margin: 50px auto; }}
        .container {{ padding: 20px; }}
        textarea {{ width: 100%; height: 150px; font-family: monospace; }}
        button {{ background: #17a2b8; color: white; padding: 10px 20px; border: none; cursor: pointer; }}
        .feature-badge {{ background: #6c757d; color: white; padding: 5px 10px; margin: 2px; border-radius: 3px; display: inline-block; }}
        .ws-status {{ padding: 10px; background: #f8f9fa; margin: 10px 0; border-radius: 5px; }}
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
        <div class="ws-status" id="ws-status">WebSocket: Not Connected</div>
        <textarea id="code" placeholder="Enter Python code...">print('FastAPI async edition!')</textarea>
        <br><br>
        <button onclick="submitCode()">Evaluate (Async)</button>
        <div id="result"></div>
    </div>
    <script>
        // WebSocket connection stub
        const wsUrl = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${{wsUrl}}//${{window.location.host}}/ws`);
        
        ws.onopen = () => {{
            document.getElementById('ws-status').innerHTML = 'WebSocket: Connected ✅';
        }};
        
        ws.onerror = () => {{
            document.getElementById('ws-status').innerHTML = 'WebSocket: Not Available';
        }};
        
        async function submitCode() {{
            const code = document.getElementById('code').value;
            const response = await fetch('/api/eval', {{
                method: 'POST',
                body: JSON.stringify({{code}}),
                headers: {{'Content-Type': 'application/json'}}
            }});
            const result = await response.json();
            document.getElementById('result').innerHTML = `<pre>${{JSON.stringify(result, null, 2)}}</pre>`;
        }}
    </script>
</body>
</html>
"""


class ReactFrontend(WebFrontendService):
    """
    React-based frontend representing full microservice architecture.
    In production, this would be:
    - React SPA built with webpack
    - Served by nginx
    - Communicating with backend API
    """
    
    def start(self) -> None:
        """Start nginx to serve React app"""
        # In production, this would start nginx container
        # For demo, we'll use simple server
        super().start()
        
    def stop(self) -> None:
        """Stop nginx"""
        super().stop()
        
    def handle_api_request(self, method: str, path: str, body: Optional[str] = None) -> Dict[str, Any]:
        """
        In production React setup, API requests go directly to backend service.
        This is here for compatibility with the component interface.
        """
        # React app would make direct calls to API backend
        # This is just for testing
        return super().handle_api_request(method, path, body)
    
    def get_index_html(self) -> str:
        """Return React app HTML"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - React Edition</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Production React SPA with nginx">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="shortcut icon" href="/favicon.ico">
</head>
<body>
    <div id="root"></div>
    <script>
        // In production, config would be fetched from API
        window.CRUCIBLE_CONFIG = {self.config.to_json()};
        // Production note: React app makes direct API calls to backend service
        // Not through the frontend server
    </script>
    <script src="/assets/react.production.min.js"></script>
    <script src="/assets/react-dom.production.min.js"></script>
    <script src="/assets/app.bundle.js"></script>
</body>
</html>
"""
    
    def get_asset(self, path: str) -> Optional[Tuple[bytes, str]]:
        """Serve React build artifacts"""
        # In a real implementation, this would serve the webpack bundle
        # and other React build outputs
        return None
        
    def _load_assets(self) -> None:
        """Load React build artifacts"""
        # Would load from build directory in real implementation
        pass


class APIOnlyFrontend(SimpleHTTPFrontend):
    """
    API-only frontend for use with separate frontend services.
    Provides CORS headers and JSON responses only - no HTML.
    """
    
    def start(self) -> None:
        """Start HTTP server with CORS-enabled handler"""
        if self.is_running:
            return
        
        parent = self
        
        class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
            def do_OPTIONS(self):
                """Handle preflight requests"""
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Max-Age', '3600')
                self.end_headers()
            
            def end_headers(self):
                """Add CORS headers to all responses"""
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                super().end_headers()
            
            def do_GET(self):
                """Handle GET with CORS"""
                try:
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        response = {
                            'name': f'{parent.config.features.get("app_name", "Platform")} API',
                            'version': parent.config.features.get('api_version', '1.0.0'),
                            'endpoints': {
                                'evaluate': '/api/eval',
                                'status': '/api/status',
                                'queue': '/api/queue-status'
                            }
                        }
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path.startswith('/api/') and parent.api_handler:
                        # Forward to API handler
                        api_request = APIRequest(
                            method=HTTPMethod.GET,
                            path=self.path,
                            headers=dict(self.headers),
                            body=None
                        )
                        response = parent.api_handler(api_request)
                        self.send_response(response.status_code)
                        for key, value in response.headers.items():
                            self.send_header(key, value)
                        self.end_headers()
                        self.wfile.write(response.body)
                    else:
                        self.send_response(404)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': 'Not found'}).encode())
                except Exception as e:
                    self.send_error(500, str(e))
                    
            def do_POST(self):
                """Handle POST with CORS"""
                try:
                    if self.path.startswith('/api/') and parent.api_handler:
                        content_length = int(self.headers.get('Content-Length', 0))
                        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else None
                        
                        api_request = APIRequest(
                            method=HTTPMethod.POST,
                            path=self.path,
                            headers=dict(self.headers),
                            body=body
                        )
                        response = parent.api_handler(api_request)
                        self.send_response(response.status_code)
                        for key, value in response.headers.items():
                            self.send_header(key, value)
                        self.end_headers()
                        self.wfile.write(response.body)
                    else:
                        self.send_response(404)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': 'Not found'}).encode())
                except Exception as e:
                    self.send_error(500, str(e))
            
            def log_message(self, format, *args):
                # Suppress logs in test mode
                if not parent.config.features.get('suppress_logs', False):
                    super().log_message(format, *args)
        
        # Use ThreadingTCPServer for concurrent requests
        self.server = socketserver.ThreadingTCPServer(
            (self.config.host, self.config.port),
            CORSRequestHandler
        )
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.is_running = True


# Export frontend factory
def create_frontend(
    frontend_type: FrontendType = FrontendType.SIMPLE_HTTP,
    config: Optional[FrontendConfig] = None,
    api_service=None,
    api_handler=None
) -> WebFrontendService:
    """
    Factory function to create frontend instances.
    
    Evolution path:
    1. SIMPLE_HTTP: Basic Python http.server
    2. FLASK: Proper web framework with templates
    3. FASTAPI: Modern async framework with WebSockets
    4. REACT: Full microservice with separate frontend
    
    Args:
        frontend_type: Type of frontend to create
        config: Frontend configuration
        api_service: Optional API service for integrated deployments
        api_handler: Optional API handler for routing requests
        
    Returns:
        WebFrontendService instance
    """
    frontend_classes = {
        FrontendType.SIMPLE_HTTP: SimpleHTTPFrontend,
        FrontendType.ADVANCED_HTTP: AdvancedHTMLFrontend,
        FrontendType.FLASK: FlaskFrontend,
        FrontendType.FASTAPI: FastAPIFrontend,
        FrontendType.REACT: ReactFrontend,
        FrontendType.API_ONLY: APIOnlyFrontend,
    }
    
    frontend_class = frontend_classes.get(frontend_type)
    if not frontend_class:
        raise ValueError(f"Unknown frontend type: {frontend_type}")
        
    return frontend_class(config, api_service, api_handler)


# Example usage showing evolution
class FrontendEvolutionDemo:
    """
    Demonstrates the evolution of frontend architecture.
    """
    
    @staticmethod
    def show_evolution():
        """Show how frontend evolves from simple to complex"""
        
        # Stage 1: Simple HTTP server
        print("Stage 1: Python http.server")
        simple_frontend = create_frontend(
            FrontendType.SIMPLE_HTTP,
            FrontendConfig(port=8080)
        )
        simple_frontend.start()
        print(f"  - Serving on http://localhost:8080")
        print("  - Basic HTML, inline JS/CSS")
        print("  - Direct HTTP handling")
        simple_frontend.stop()
        
        # Stage 2: Flask framework
        print("\nStage 2: Flask web framework")
        flask_frontend = create_frontend(
            FrontendType.FLASK,
            FrontendConfig(port=8081)
        )
        print("  - Template engine support")
        print("  - Better routing")
        print("  - Session management")
        
        # Stage 3: FastAPI with async
        print("\nStage 3: FastAPI async framework")
        fastapi_frontend = create_frontend(
            FrontendType.FASTAPI,
            FrontendConfig(port=8082)
        )
        print("  - Async request handling")
        print("  - WebSocket support")
        print("  - Auto-generated API docs")
        
        # Stage 4: React microservice
        print("\nStage 4: React + nginx microservice")
        react_frontend = create_frontend(
            FrontendType.REACT,
            FrontendConfig(port=80)
        )
        print("  - Separate frontend service")
        print("  - nginx serving static assets")
        print("  - Direct API communication")
        print("  - Full production architecture")
        
        return {
            'simple': simple_frontend,
            'flask': flask_frontend,
            'fastapi': fastapi_frontend,
            'react': react_frontend
        }