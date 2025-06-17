"""
Remote execution engine that delegates to a separate execution service.

⚠️ STATUS: NOT YET ACTIVE - FOR FUTURE USE
This is part of the monolith but not currently used.
Activated when EXECUTION_MODE=remote is set.

This allows the main platform to run without Docker access while still
supporting code execution through a dedicated microservice.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any
import unittest
import os

from .execution import ExecutionEngine


class RemoteExecutionEngine(ExecutionEngine):
    """
    Execution engine that forwards requests to a remote execution service.
    
    This enables microservices architecture where the main platform
    doesn't need Docker access.
    """
    
    def __init__(self, service_url: str = None):
        """Initialize with the execution service URL."""
        self.service_url = service_url or os.environ.get(
            'EXECUTION_SERVICE_URL', 
            'http://crucible-executor:8081'
        )
        
        # Verify service is accessible
        try:
            self._health_check()
        except Exception as e:
            raise RuntimeError(f"Cannot connect to execution service at {self.service_url}: {e}")
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        """Execute code by sending to remote service."""
        url = f"{self.service_url}/execute"
        
        data = json.dumps({
            'code': code,
            'eval_id': eval_id
        }).encode('utf-8')
        
        request = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            response = urllib.request.urlopen(request, timeout=35)  # Slightly more than execution timeout
            result = json.loads(response.read().decode('utf-8'))
            return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_data = json.loads(error_body)
                return {
                    'id': eval_id,
                    'status': 'error',
                    'error': error_data.get('error', 'Remote execution failed')
                }
            except:
                return {
                    'id': eval_id,
                    'status': 'error',
                    'error': f'Remote execution failed: HTTP {e.code}'
                }
        except Exception as e:
            return {
                'id': eval_id,
                'status': 'error',
                'error': f'Remote execution failed: {str(e)}'
            }
    
    def get_description(self) -> str:
        """Describe the remote execution setup."""
        return f"Remote execution via {self.service_url}"
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of remote service."""
        try:
            return self._health_check()
        except Exception as e:
            return {
                'healthy': False,
                'engine_type': 'remote',
                'service_url': self.service_url,
                'error': str(e)
            }
    
    def _health_check(self) -> Dict[str, Any]:
        """Internal health check implementation."""
        url = f"{self.service_url}/health"
        
        try:
            response = urllib.request.urlopen(url, timeout=5)
            health_data = json.loads(response.read().decode('utf-8'))
            health_data['engine_type'] = 'remote'
            health_data['service_url'] = self.service_url
            return health_data
        except Exception as e:
            raise RuntimeError(f"Health check failed: {e}")
    
    def self_test(self) -> Dict[str, Any]:
        """Test the remote execution service."""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Service is reachable
        try:
            health = self._health_check()
            if health.get('healthy'):
                tests_passed.append('service_reachable')
            else:
                tests_failed.append(('service_unhealthy', health))
        except Exception as e:
            tests_failed.append(('service_unreachable', str(e)))
        
        # Test 2: Can execute simple code
        if not tests_failed:  # Only test execution if service is reachable
            try:
                result = self.execute("print('Hello from remote!')", "test-remote")
                if result.get('status') == 'completed':
                    tests_passed.append('remote_execution')
                else:
                    tests_failed.append(('remote_execution_failed', result))
            except Exception as e:
                tests_failed.append(('remote_execution_error', str(e)))
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': 'All remote execution tests passed' if not tests_failed else f"Failed {len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return test suite for remote execution."""
        class RemoteExecutionTests(unittest.TestCase):
            def setUp(self):
                self.engine = RemoteExecutionEngine()
            
            def test_service_health(self):
                """Test that remote service is healthy."""
                health = self.engine.health_check()
                self.assertTrue(health.get('healthy'), f"Service unhealthy: {health}")
            
            def test_remote_execution(self):
                """Test remote code execution."""
                result = self.engine.execute("print('test')", "test-1")
                self.assertEqual(result['status'], 'completed')
                self.assertIn('test', result.get('output', ''))
            
            def test_remote_error_handling(self):
                """Test remote error handling."""
                result = self.engine.execute("raise ValueError('test error')", "test-2")
                self.assertEqual(result['status'], 'failed')
                self.assertIn('ValueError', result.get('output', ''))
        
        return unittest.TestLoader().loadTestsFromTestCase(RemoteExecutionTests)