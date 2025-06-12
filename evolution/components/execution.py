"""
Execution engines for code evaluation.
These can evolve into full sandboxing services.
"""

import subprocess
import tempfile
import os
import platform
import uuid
from typing import Dict, Any
import unittest

from .base import TestableComponent


class ExecutionEngine(TestableComponent):
    """
    Abstract execution engine that MUST be testable.
    
    Future evolution:
    - Kubernetes Job API integration
    - GPU-aware scheduling
    - Multi-language support
    - Distributed execution
    """
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        """Execute code and return results"""
        raise NotImplementedError
    
    def get_description(self) -> str:
        """Get human-readable description of this engine"""
        raise NotImplementedError
    
    def self_test(self) -> Dict[str, Any]:
        """Default self-test for execution engines"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Can execute simple code
        try:
            result = self.execute("print('test')", "test-1")
            if 'test' in result.get('output', ''):
                tests_passed.append("Basic execution")
            else:
                tests_failed.append("Basic execution: no output")
        except Exception as e:
            tests_failed.append(f"Basic execution: {str(e)}")
        
        # Test 2: Handles timeout
        try:
            result = self.execute("import time; time.sleep(60)", "test-2")
            if result.get('status') in ['timeout', 'failed']:
                tests_passed.append("Timeout handling")
            else:
                tests_failed.append("Timeout handling: didn't timeout")
        except Exception as e:
            tests_failed.append(f"Timeout handling: {str(e)}")
        
        # Test 3: Handles errors
        try:
            result = self.execute("raise Exception('test error')", "test-3")
            if result.get('status') in ['error', 'failed', 'completed']:
                # For Docker, stderr might go to output with 'completed' status
                if 'Exception' in result.get('output', '') or result.get('status') in ['error', 'failed']:
                    tests_passed.append("Error handling")
                else:
                    tests_failed.append(f"Error handling: status={result.get('status')}, output={result.get('output', '')[:100]}")
            else:
                tests_failed.append(f"Error handling: unexpected status={result.get('status')}")
        except Exception as e:
            tests_failed.append(f"Error handling: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }


class SubprocessEngine(ExecutionEngine):
    """
    Unsafe subprocess engine with tests.
    This is for development only - NEVER use in production!
    """
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                'id': eval_id,
                'status': 'completed',
                'output': result.stdout or result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'id': eval_id, 'status': 'timeout', 'error': 'Timeout after 5 seconds'}
        except Exception as e:
            return {'id': eval_id, 'status': 'error', 'error': str(e)}
    
    def get_description(self) -> str:
        return "Subprocess (UNSAFE - Direct execution)"
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return specific tests for subprocess engine"""
        class SubprocessEngineTests(unittest.TestCase):
            def setUp(self):
                self.engine = SubprocessEngine()
            
            def test_basic_execution(self):
                result = self.engine.execute("print('hello')", "test-1")
                self.assertEqual(result['status'], 'completed')
                self.assertIn('hello', result['output'])
            
            def test_timeout(self):
                result = self.engine.execute("import time; time.sleep(10)", "test-2")
                self.assertEqual(result['status'], 'timeout')
            
            def test_file_access_works(self):
                # This SHOULD work in subprocess (that's the danger!)
                result = self.engine.execute("import os; print(os.getcwd())", "test-3")
                self.assertEqual(result['status'], 'completed')
                self.assertTrue(len(result['output']) > 0)
        
        return unittest.TestLoader().loadTestsFromTestCase(SubprocessEngineTests)


class DockerEngine(ExecutionEngine):
    """
    Docker-based execution engine with safety features.
    
    Future evolution:
    - gVisor/Firecracker integration
    - Custom security policies
    - Resource accounting
    - Multi-container workflows
    """
    
    def __init__(self, image: str = "python:3.11-slim"):
        # Verify Docker is available
        try:
            result = subprocess.run(['docker', 'version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Docker not available: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError("Docker command not found. Please install Docker.")
        except Exception as e:
            raise RuntimeError(f"Docker initialization failed: {e}")
        
        # Check if image exists, pull if not
        self.image = image
        try:
            result = subprocess.run(['docker', 'image', 'inspect', image], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"   Docker image '{image}' not found locally")
                print(f"   Downloading image (this may take a minute on first run)...")
                # Run docker pull without capturing output so user sees progress
                pull_result = subprocess.run(['docker', 'pull', image])
                if pull_result.returncode != 0:
                    raise RuntimeError(f"Failed to pull image {image}")
                print(f"   ✓ Docker image ready!")
        except Exception as e:
            print(f"   Warning: Could not verify Docker image: {e}")
            
        self.memory_limit = "100m"
        self.cpu_limit = "0.5"
        self.timeout = 30
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            docker_cmd = [
                'docker', 'run',
                '--rm', '--network', 'none',
                '--memory', self.memory_limit, 
                '--cpus', self.cpu_limit,
                '--read-only',
                '-v', f'{temp_file}:/code.py:ro',
                self.image,
                'python', '/code.py'
            ]
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            return {
                'id': eval_id,
                'status': 'completed' if result.returncode == 0 else 'failed',
                'output': result.stdout or result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'id': eval_id, 'status': 'timeout', 'error': f'Timeout after {self.timeout} seconds'}
        except Exception as e:
            return {'id': eval_id, 'status': 'error', 'error': str(e)}
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def get_description(self) -> str:
        return "Docker (Containerized - Network isolated)"
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Docker-specific safety tests"""
        class DockerEngineTests(unittest.TestCase):
            def setUp(self):
                self.engine = DockerEngine()
            
            def test_network_isolation(self):
                result = self.engine.execute(
                    "import urllib.request; urllib.request.urlopen('http://google.com')",
                    "test-net"
                )
                self.assertIn('failed', result['status'])
                self.assertIn('Network is unreachable', result['output'])
            
            def test_filesystem_readonly(self):
                result = self.engine.execute(
                    "open('/tmp/test.txt', 'w').write('test')",
                    "test-fs"
                )
                self.assertIn('failed', result['status'])
                self.assertIn('Read-only file system', result['output'])
            
            def test_resource_limits(self):
                # Try to allocate more than 100MB
                result = self.engine.execute(
                    "data = 'x' * (200 * 1024 * 1024)",  # 200MB
                    "test-mem"
                )
                # Should be killed by memory limit
                self.assertIn(result['status'], ['failed', 'error'])
        
        return unittest.TestLoader().loadTestsFromTestCase(DockerEngineTests)


class GVisorEngine(ExecutionEngine):
    """
    Production-grade Docker execution with gVisor runtime.
    
    Security layers (matching Google Cloud Run):
    1. Docker container isolation
    2. gVisor (runsc) - userspace kernel for syscall interception
    3. Network completely disabled
    4. Non-root user (65534:65534)
    5. Read-only filesystem
    6. Resource limits (CPU/memory)
    
    This provides defense-in-depth against:
    - Container escape attempts
    - Kernel exploits (gVisor handles syscalls)
    - Network exfiltration (no network)
    - Privilege escalation (non-root)
    - Filesystem persistence (read-only)
    - Resource exhaustion (limits enforced)
    """
    
    def __init__(self, runtime: str = 'runsc'):
        # Check if gVisor is actually available
        if runtime == 'runsc' and platform.system() != 'Linux':
            raise RuntimeError("gVisor (runsc) is only available on Linux")
        
        # Verify runsc is installed if requested
        if runtime == 'runsc':
            try:
                subprocess.run(['docker', 'info'], capture_output=True, text=True, check=True)
                # Check if runsc runtime is configured in Docker
                result = subprocess.run(['docker', 'system', 'info'], capture_output=True, text=True)
                if 'runsc' not in result.stdout:
                    raise RuntimeError("runsc runtime not configured in Docker")
            except:
                raise RuntimeError("gVisor runtime not available")
        
        self.runtime = runtime  # 'runsc' for gVisor, 'runc' for standard
        self.memory_limit = "100m"
        self.cpu_limit = "0.5"
        self.timeout = 30
        
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Build Docker command with production safety features
            docker_cmd = [
                'docker', 'run',
                '--rm',                      # Remove container after exit
            ]
            
            # Only add runtime flag if it's runsc (not default runc)
            if self.runtime == 'runsc':
                docker_cmd.extend(['--runtime', self.runtime])
            
            docker_cmd.extend([
                '--user', '65534:65534',     # Non-root user (nobody:nogroup)
                '--network', 'none',         # No network access
                '--memory', self.memory_limit,          # Memory limit
                '--cpus', self.cpu_limit,            # CPU limit
                '--read-only',              # Read-only root filesystem
                '--tmpfs', '/tmp:size=10M',  # Small writable /tmp
                '--security-opt', 'no-new-privileges',  # Prevent privilege escalation
                '-v', f'{temp_file}:/code.py:ro',  # Mount code read-only
                'python:3.11-slim',
                'python', '-u', '/code.py'
            ])
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            return {
                'id': eval_id,
                'status': 'completed' if result.returncode == 0 else 'failed',
                'output': result.stdout or result.stderr,
                'runtime': self.runtime,
                'security': 'production-grade' if self.runtime == 'runsc' else 'standard'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'id': eval_id, 
                'status': 'timeout', 
                'error': f'Timeout after {self.timeout} seconds',
                'runtime': self.runtime
            }
        except Exception as e:
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'runtime': self.runtime
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def get_description(self) -> str:
        if self.runtime == 'runsc':
            return "gVisor (Production security - kernel isolation)"
        else:
            return f"Docker with {self.runtime} runtime"
    
    def get_test_suite(self) -> unittest.TestSuite:
        """gVisor-specific safety tests"""
        class GVisorEngineTests(unittest.TestCase):
            def setUp(self):
                # Try gVisor first, fall back to runc
                try:
                    subprocess.run(['docker', 'info'], capture_output=True, text=True)
                    result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
                    if 'runsc' in result.stdout:
                        self.engine = GVisorEngine('runsc')
                    else:
                        self.engine = GVisorEngine('runc')
                        print("Warning: gVisor not available, using standard runtime")
                except:
                    self.skipTest("Docker not available")
            
            def test_network_isolation(self):
                result = self.engine.execute(
                    "import urllib.request; urllib.request.urlopen('http://google.com')",
                    "test-net"
                )
                self.assertEqual(result['status'], 'failed')
                self.assertIn('Network is unreachable', result['output'])
            
            def test_filesystem_readonly(self):
                result = self.engine.execute(
                    "open('/etc/test.txt', 'w').write('test')",
                    "test-fs"
                )
                self.assertEqual(result['status'], 'failed')
                self.assertIn('Read-only file system', result['output'])
            
            def test_non_root_user(self):
                result = self.engine.execute(
                    "import os; print(f'UID: {os.getuid()}, GID: {os.getgid()}')",
                    "test-user"
                )
                self.assertEqual(result['status'], 'completed')
                self.assertIn('UID: 65534', result['output'])  # nobody user
            
            def test_no_privilege_escalation(self):
                result = self.engine.execute(
                    "import os; os.setuid(0)",  # Try to become root
                    "test-priv"
                )
                self.assertEqual(result['status'], 'failed')
                self.assertIn('Operation not permitted', result['output'])
        
        return unittest.TestLoader().loadTestsFromTestCase(GVisorEngineTests)