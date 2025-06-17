"""
API component for TRACE-AI architecture.
Provides business logic for handling evaluation requests, status queries, and queue operations.

This component is framework-agnostic and focuses purely on request processing logic,
delegating HTTP handling to the web_frontend component.
"""

from typing import Dict, Any, Optional, Callable, Tuple
import json
import uuid
import unittest
from unittest.mock import Mock
import threading
from dataclasses import dataclass
from enum import Enum

from ..shared.base import TestableComponent
from ..core.core import TestableEvaluationPlatform


class HTTPMethod(Enum):
    """HTTP methods supported by the API"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class APIRequest:
    """Abstraction for HTTP requests across frameworks"""
    method: HTTPMethod
    path: str
    headers: Dict[str, str]
    body: Optional[bytes] = None
    params: Dict[str, str] = None
    
    def json(self) -> Any:
        """Parse body as JSON"""
        if self.body:
            return json.loads(self.body.decode())
        return None


@dataclass
class APIResponse:
    """Abstraction for HTTP responses across frameworks"""
    status_code: int
    headers: Dict[str, str]
    body: bytes
    
    @staticmethod
    def json(data: Any, status: int = 200) -> 'APIResponse':
        """Create JSON response"""
        return APIResponse(
            status_code=status,
            headers={'Content-Type': 'application/json'},
            body=json.dumps(data).encode()
        )
    
    @staticmethod
    def text(text: str, status: int = 200) -> 'APIResponse':
        """Create text response"""
        return APIResponse(
            status_code=status,
            headers={'Content-Type': 'text/plain'},
            body=text.encode()
        )
    
    @staticmethod
    def html(html: str, status: int = 200) -> 'APIResponse':
        """Create HTML response"""
        return APIResponse(
            status_code=status,
            headers={'Content-Type': 'text/html'},
            body=html.encode()
        )


class APIService(TestableComponent):
    """
    Business logic service for handling API requests.
    Provides evaluation request processing, status queries, and queue operations
    without any HTTP-specific functionality.
    """
    
    def __init__(self, platform: Optional[TestableEvaluationPlatform] = None):
        self.platform = platform
        
    def process_evaluation(self, code: str) -> Dict[str, Any]:
        """
        Process a synchronous evaluation request.
        
        Args:
            code: The code to evaluate
            
        Returns:
            Evaluation result dictionary
        """
        if not code:
            raise ValueError("Missing code parameter")
            
        return self.platform.evaluate(code)
        
    def process_async_evaluation(self, code: str) -> Dict[str, Any]:
        """
        Process an asynchronous evaluation request.
        
        Args:
            code: The code to evaluate
            
        Returns:
            Dictionary with eval_id and status
        """
        if not code:
            raise ValueError("Missing code parameter")
            
        # Check if platform supports async
        if hasattr(self.platform, 'evaluate_async'):
            return self.platform.evaluate_async(code)
        else:
            # Fallback to sync with generated ID
            eval_id = str(uuid.uuid4())
            result = {
                'eval_id': eval_id,
                'status': 'queued',
                'message': 'Evaluation queued (sync mode)'
            }
            # Run sync evaluation in thread for demo
            def run_eval():
                self.platform.evaluate(code)
            threading.Thread(target=run_eval).start()
            return result
            
    def get_evaluation_status(self, eval_id: str) -> Dict[str, Any]:
        """
        Get the status of an evaluation.
        
        Args:
            eval_id: The evaluation ID
            
        Returns:
            Status dictionary
        """
        if hasattr(self.platform, 'get_evaluation_status'):
            return self.platform.get_evaluation_status(eval_id)
        else:
            # Fallback for platforms without status tracking
            return {
                'eval_id': eval_id,
                'status': 'unknown',
                'message': 'Status tracking not supported'
            }
            
    def get_platform_status(self) -> Dict[str, Any]:
        """
        Get platform health and status information.
        
        Returns:
            Platform status dictionary
        """
        status = {
            'healthy': True,
            'platform': self.platform.__class__.__name__,
            'version': getattr(self.platform, 'version', '1.0.0')
        }
        
        # Add platform-specific status if available
        if hasattr(self.platform, 'get_status'):
            try:
                platform_status = self.platform.get_status()
                if isinstance(platform_status, dict):
                    status.update(platform_status)
            except Exception as e:
                status['error'] = str(e)
        
        # Add component health checks
        if hasattr(self.platform, 'health_check'):
            status['health'] = self.platform.health_check()
            
        return status
        
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Queue status dictionary
        """
        if hasattr(self.platform, 'get_queue_status'):
            return self.platform.get_queue_status()
        else:
            # Default queue status for non-queued platforms
            return {
                'queue': {
                    'queued': 0,
                    'running': 0,
                    'completed': 0,
                    'failed': 0,
                    'workers': 1
                },
                'message': 'Queue not implemented'
            }
            
    def self_test(self) -> Dict[str, Any]:
        """Test the API service component"""
        results = {'passed': True, 'tests_passed': [], 'tests_failed': []}
        
        # Test evaluation processing
        try:
            # Test missing code parameter
            try:
                self.process_evaluation('')
                results['tests_failed'].append('Should have raised ValueError for empty code')
                results['passed'] = False
            except ValueError:
                results['tests_passed'].append('Empty code validation')
                
            # Test platform evaluation call
            if hasattr(self.platform, 'evaluate'):
                result = self.process_evaluation('print("test")')
                assert isinstance(result, dict)
                results['tests_passed'].append('Evaluation processing')
        except Exception as e:
            results['tests_failed'].append(f'Evaluation processing: {e}')
            results['passed'] = False
            
        # Test platform status
        try:
            status = self.get_platform_status()
            assert isinstance(status, dict)
            assert 'healthy' in status
            assert 'platform' in status
            results['tests_passed'].append('Platform status')
        except Exception as e:
            results['tests_failed'].append(f'Platform status: {e}')
            results['passed'] = False
            
        # Test queue status
        try:
            queue_status = self.get_queue_status()
            assert isinstance(queue_status, dict)
            results['tests_passed'].append('Queue status')
        except Exception as e:
            results['tests_failed'].append(f'Queue status: {e}')
            results['passed'] = False
            
        results['message'] = f"API tests: {len(results['tests_passed'])} passed, {len(results['tests_failed'])} failed"
        return results
        
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite for the API service component"""
        
        class APIServiceTests(unittest.TestCase):
            def setUp(self):
                self.mock_platform = Mock(spec=TestableEvaluationPlatform)
                # Set up mock attributes to avoid errors
                self.mock_platform.__class__.__name__ = 'MockPlatform'
                
                # Mock health_check to return a plain dict
                self.mock_platform.health_check.return_value = {
                    'healthy': True,
                    'component': 'MockPlatform',
                    'version': '1.0.0'
                }
                
                self.api = APIService(self.mock_platform)
                
            def test_evaluation_processing(self):
                """Test evaluation request processing"""
                # Test missing code
                with self.assertRaises(ValueError) as context:
                    self.api.process_evaluation('')
                self.assertIn('code', str(context.exception).lower())
                
            def test_sync_evaluation_success(self):
                """Test successful synchronous evaluation"""
                self.mock_platform.evaluate.return_value = {
                    'output': 'Hello, World!',
                    'error': None,
                    'success': True
                }
                
                result = self.api.process_evaluation('print("Hello, World!")')
                self.assertEqual(result['output'], 'Hello, World!')
                self.assertTrue(result['success'])
                
            def test_async_evaluation(self):
                """Test asynchronous evaluation processing"""
                self.mock_platform.evaluate_async = Mock(return_value={
                    'eval_id': 'test-123',
                    'status': 'queued'
                })
                
                result = self.api.process_async_evaluation('print("async")')
                self.assertEqual(result['eval_id'], 'test-123')
                self.assertEqual(result['status'], 'queued')
                
            def test_evaluation_status(self):
                """Test evaluation status retrieval"""
                self.mock_platform.get_evaluation_status = Mock(return_value={
                    'eval_id': 'test-123',
                    'status': 'completed',
                    'result': {'output': 'Done'}
                })
                
                status = self.api.get_evaluation_status('test-123')
                self.assertEqual(status['eval_id'], 'test-123')
                self.assertEqual(status['status'], 'completed')
                
            def test_platform_status_retrieval(self):
                """Test platform status retrieval"""
                # Mock get_status to return a plain dict
                def mock_get_status():
                    return {
                        'engine': 'subprocess',
                        'security': 'basic',
                        'components': {
                            'engine': {
                                'healthy': True,
                                'component': 'MockEngine',
                                'version': '1.0.0'
                            }
                        }
                    }
                
                self.mock_platform.get_status = mock_get_status
                
                status = self.api.get_platform_status()
                self.assertTrue(status['healthy'])
                self.assertEqual(status['platform'], 'MockPlatform')
                self.assertEqual(status['engine'], 'subprocess')
                
            def test_queue_status_retrieval(self):
                """Test queue status retrieval"""
                self.mock_platform.get_queue_status = Mock(return_value={
                    'queue': {
                        'queued': 5,
                        'running': 2,
                        'completed': 10,
                        'failed': 1,
                        'workers': 4
                    }
                })
                
                queue_status = self.api.get_queue_status()
                self.assertEqual(queue_status['queue']['queued'], 5)
                self.assertEqual(queue_status['queue']['workers'], 4)
                
            def test_error_handling(self):
                """Test error handling in API processing"""
                # Make platform.evaluate raise an exception
                self.mock_platform.evaluate.side_effect = RuntimeError("Test error")
                
                with self.assertRaises(RuntimeError):
                    self.api.process_evaluation('raise Exception()')
                    
            def test_async_evaluation_fallback(self):
                """Test async evaluation fallback for sync-only platforms"""
                # Remove evaluate_async to test fallback
                if hasattr(self.mock_platform, 'evaluate_async'):
                    delattr(self.mock_platform, 'evaluate_async')
                
                result = self.api.process_async_evaluation('print("test")')
                self.assertIn('eval_id', result)
                self.assertEqual(result['status'], 'queued')
                
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(APIServiceTests))
        return suite


class RESTfulAPIHandler:
    """
    Helper class for mapping HTTP routes to API service methods.
    Used by web_frontend to handle RESTful API requests.
    """
    
    def __init__(self, api_service: APIService):
        self.api = api_service
        self.routes: Dict[Tuple[HTTPMethod, str], Callable] = {}
        self._setup_routes()
        
    def _setup_routes(self):
        """Configure route mappings to API service methods"""
        
        def eval_sync(request: APIRequest) -> APIResponse:
            """Synchronous evaluation endpoint (DEPRECATED)"""
            # Return deprecation warning
            return APIResponse.json({
                'error': 'Synchronous evaluation is deprecated',
                'message': 'This endpoint is deprecated due to timeout issues with long-running evaluations. Please use POST /eval-async instead.',
                'alternative': {
                    'endpoint': '/eval-async',
                    'method': 'POST',
                    'description': 'Returns immediately with an eval_id to poll for results'
                }
            }, 410)  # 410 Gone - indicates deprecated/removed functionality
            
            # Original implementation (disabled):
            # data = request.json()
            # if not data or 'code' not in data:
            #     return APIResponse.json({'error': 'Missing code parameter'}, 400)
            # try:
            #     result = self.api.process_evaluation(data['code'])
            #     return APIResponse.json(result)
            # except...
                
        def eval_async(request: APIRequest) -> APIResponse:
            """Asynchronous evaluation endpoint"""
            data = request.json()
            if not data or 'code' not in data:
                return APIResponse.json({'error': 'Missing code parameter'}, 400)
                
            try:
                result = self.api.process_async_evaluation(data['code'])
                return APIResponse.json(result)
            except ValueError as e:
                return APIResponse.json({'error': str(e)}, 400)
            except Exception as e:
                return APIResponse.json({
                    'error': str(e),
                    'type': type(e).__name__
                }, 500)
                
        def eval_status(request: APIRequest) -> APIResponse:
            """Get evaluation status"""
            eval_id = request.params.get('eval_id')
            if not eval_id:
                return APIResponse.json({'error': 'Missing eval_id parameter'}, 400)
                
            try:
                status = self.api.get_evaluation_status(eval_id)
                return APIResponse.json(status)
            except Exception as e:
                return APIResponse.json({
                    'error': str(e),
                    'type': type(e).__name__
                }, 500)
                
        def platform_status(_request: APIRequest) -> APIResponse:
            """Platform health and status"""
            try:
                status = self.api.get_platform_status()
                return APIResponse.json(status)
            except Exception as e:
                return APIResponse.json({
                    'error': str(e),
                    'type': type(e).__name__
                }, 500)
                
        def queue_status(_request: APIRequest) -> APIResponse:
            """Queue statistics"""
            try:
                queue_info = self.api.get_queue_status()
                return APIResponse.json(queue_info)
            except Exception as e:
                return APIResponse.json({
                    'error': str(e),
                    'type': type(e).__name__
                }, 500)
                
        def openapi_spec(_request: APIRequest) -> APIResponse:
            """Serve OpenAPI specification"""
            import os
            from pathlib import Path
            
            # Look for OpenAPI spec file
            spec_paths = [
                Path("api/openapi.yaml"),
                Path("api/openapi.json"),
                Path(__file__).parent.parent.parent / "api" / "openapi.yaml"
            ]
            
            for spec_path in spec_paths:
                if spec_path.exists():
                    try:
                        with open(spec_path, 'r') as f:
                            content = f.read()
                            
                        # Determine content type based on file extension
                        if spec_path.suffix == '.yaml':
                            return APIResponse(
                                status_code=200,
                                body=content.encode(),
                                headers={'Content-Type': 'application/yaml'}
                            )
                        else:
                            return APIResponse(
                                status_code=200,
                                body=content.encode(),
                                headers={'Content-Type': 'application/json'}
                            )
                    except Exception as e:
                        return APIResponse.json({
                            'error': f'Failed to read OpenAPI spec: {str(e)}',
                            'type': type(e).__name__
                        }, 500)
                        
            return APIResponse.json({
                'error': 'OpenAPI specification not found',
                'paths_checked': [str(p) for p in spec_paths]
            }, 404)
                
        # Register routes
        self.routes[(HTTPMethod.POST, '/eval')] = eval_sync
        self.routes[(HTTPMethod.POST, '/eval-async')] = eval_async
        self.routes[(HTTPMethod.GET, '/eval-status/{eval_id}')] = eval_status
        self.routes[(HTTPMethod.GET, '/status')] = platform_status
        self.routes[(HTTPMethod.GET, '/queue-status')] = queue_status
        self.routes[(HTTPMethod.GET, '/openapi.yaml')] = openapi_spec
        self.routes[(HTTPMethod.GET, '/openapi.json')] = openapi_spec
        self.routes[(HTTPMethod.GET, '/spec')] = openapi_spec
        
    def handle_request(self, request: APIRequest) -> APIResponse:
        """
        Route HTTP request to appropriate handler.
        
        Args:
            request: The API request to handle
            
        Returns:
            APIResponse object
        """
        # Find matching route
        handler = None
        params = {}
        
        for (method, pattern), func in self.routes.items():
            if method == request.method:
                if self._match_path(pattern, request.path, params):
                    handler = func
                    request.params = params
                    break
                    
        if not handler:
            return APIResponse.json({'error': 'Not found'}, 404)
            
        try:
            return handler(request)
        except Exception as e:
            return APIResponse.json({
                'error': str(e),
                'type': type(e).__name__
            }, 500)
            
    def _match_path(self, pattern: str, path: str, params: Dict[str, str]) -> bool:
        """
        Match URL path against pattern, extracting parameters.
        Supports patterns like /eval-status/{eval_id}
        """
        pattern_parts = pattern.split('/')
        path_parts = path.split('/')
        
        if len(pattern_parts) != len(path_parts):
            return False
            
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                # Extract parameter
                param_name = pattern_part[1:-1]
                params[param_name] = path_part
            elif pattern_part != path_part:
                return False
                
        return True


class APIHandlerTests(unittest.TestCase):
    """Tests for RESTfulAPIHandler route handling"""
    
    def setUp(self):
        self.mock_platform = Mock(spec=TestableEvaluationPlatform)
        self.mock_platform.__class__.__name__ = 'MockPlatform'
        self.api_service = APIService(self.mock_platform)
        self.handler = RESTfulAPIHandler(self.api_service)
        
    def test_route_registration(self):
        """Test that routes are properly registered"""
        routes = [key[1] for key in self.handler.routes.keys()]
        self.assertIn('/eval', routes)
        self.assertIn('/eval-async', routes)
        self.assertIn('/status', routes)
        
    def test_path_matching(self):
        """Test URL path matching with parameters"""
        params = {}
        
        # Exact match
        self.assertTrue(self.handler._match_path('/eval', '/eval', params))
        self.assertEqual(params, {})
        
        # Parameter extraction
        params = {}
        self.assertTrue(self.handler._match_path(
            '/eval-status/{eval_id}', 
            '/eval-status/abc123', 
            params
        ))
        self.assertEqual(params, {'eval_id': 'abc123'})
        
    def test_request_routing(self):
        """Test request routing to correct handler"""
        self.mock_platform.evaluate.return_value = {
            'output': 'test',
            'success': True
        }
        
        request = APIRequest(
            method=HTTPMethod.POST,
            path='/eval',
            headers={},
            body=json.dumps({'code': 'print("test")'}).encode()
        )
        
        response = self.handler.handle_request(request)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.body)
        self.assertEqual(result['output'], 'test')


def create_api_service(platform: TestableEvaluationPlatform) -> APIService:
    """
    Factory function to create API service instance.
    
    Args:
        platform: The evaluation platform to expose via API
        
    Returns:
        APIService instance for handling business logic
    """
    return APIService(platform)


def create_api_handler(api_service: APIService) -> RESTfulAPIHandler:
    """
    Factory function to create RESTful API handler for route mapping.
    
    Args:
        api_service: The API service instance
        
    Returns:
        RESTfulAPIHandler for routing HTTP requests to API methods
    """
    return RESTfulAPIHandler(api_service)




# Example usage and integration
if __name__ == "__main__":
    # Example of using the API component
    from ..core.core import QueuedEvaluationPlatform
    from ..execution_engine.execution import SubprocessEngine
    from ..queue.queue import TaskQueue
    from ..monitoring.monitoring import AdvancedMonitor
    
    # Create platform
    engine = SubprocessEngine()
    queue = TaskQueue(max_workers=2)
    monitor = AdvancedMonitor()
    platform = QueuedEvaluationPlatform(engine, queue, monitor)
    
    # Create API service
    api_service = create_api_service(platform)
    
    # Run self-test
    test_results = api_service.self_test()
    print(f"API service self-test: {test_results['message']}")