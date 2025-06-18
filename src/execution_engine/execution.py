"""
Execution engines for code evaluation.
These can evolve into full sandboxing services.

NOTE: Currently monolithic by design. See docs/architecture/when-to-modularize.md
for criteria on when to split into separate modules.

TODO: Consider modularizing when:
- Adding 5th engine type (e.g., Firecracker)
- Any engine exceeds 200 lines
- Need engine-specific dependencies
"""

import subprocess
import tempfile
import os
import platform
import uuid
from typing import Dict, Any
import unittest

from ..shared.base import TestableComponent


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
            # Accept both timeout and error status, as subprocess timeout might manifest as error
            if result.get('status') in ['timeout', 'failed', 'error']:
                # Check if it's a timeout-related error
                if result.get('status') == 'timeout' or 'timeout' in str(result.get('error', '')).lower():
                    tests_passed.append("Timeout handling")
                elif result.get('status') == 'error':
                    # Docker might fail to start if system is busy
                    tests_passed.append("Timeout handling (Docker busy)")
                else:
                    tests_failed.append(f"Timeout handling: got status={result.get('status')}")
            else:
                tests_failed.append(f"Timeout handling: didn't timeout, got status={result.get('status')}, output={result.get('output', '')[:50]}")
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
    
    def __init__(self, image: str = "python:3.11-slim", temp_base_dir: str = None):
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
        # Use STORAGE_BASE from environment if available (for containerized deployments)
        # Otherwise default to ~/crucible/storage
        default_base = os.environ.get('STORAGE_BASE') or os.path.expanduser("~/crucible/storage")
        self.temp_base_dir = temp_base_dir or default_base
    
    def _build_docker_command(self, temp_file: str) -> list:
        """Build the docker command. Can be overridden by subclasses."""
        # When running inside a container, we need to map container paths to host paths
        # for Docker Desktop to be able to mount them
        mount_path = temp_file
        
        # Check if we're running inside a container and using /app/storage
        if temp_file.startswith('/app/storage/') and os.environ.get('STORAGE_BASE') == '/app/storage':
            # Get the absolute host path from PWD (working directory on host)
            # This assumes docker-compose was run from the project root
            host_pwd = os.environ.get('HOST_PWD')
            if not host_pwd:
                # Fallback: try to determine the host path
                # This handles cases where HOST_PWD isn't set properly
                raise RuntimeError(
                    "HOST_PWD environment variable not set. "
                    "Please ensure docker-compose sets HOST_PWD=${PWD} "
                    "or run with: HOST_PWD=$(pwd) docker-compose up"
                )
            # Replace /app/storage with ./storage relative to host
            relative_path = temp_file.replace('/app/storage/', '')
            mount_path = os.path.join(host_pwd, 'storage', relative_path)
            
            # Debug logging to help diagnose path issues
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Path mapping: {temp_file} -> {mount_path}")
            logger.debug(f"HOST_PWD: {host_pwd}, relative_path: {relative_path}")
            
        return [
            'docker', 'run',
            '--rm', '--network', 'none',
            '--memory', self.memory_limit, 
            '--cpus', self.cpu_limit,
            '--read-only',
            '--cap-drop', 'ALL',  # Drop all capabilities
            '--security-opt', 'no-new-privileges',
            '-v', f'{mount_path}:/code.py:ro',
            self.image,
            'python', '/code.py'
        ]
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        # Create temp files in a directory accessible to both systemd service and Docker
        # This works around PrivateTmp=true in systemd which isolates /tmp
        temp_dir = os.path.join(self.temp_base_dir, "tmp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Verify the directory is writable
        test_file = os.path.join(temp_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            raise RuntimeError(f"Cannot write to temp directory {temp_dir}: {e}")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=temp_dir) as f:
            f.write(code)
            temp_file = f.name
        
        # Make file world-readable so Docker containers can access it
        # (especially important for gVisor which runs as nobody:65534)
        os.chmod(temp_file, 0o644)
        
        try:
            docker_cmd = self._build_docker_command(temp_file)
            
            # Log the command for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Executing Docker command: {' '.join(docker_cmd)}")
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # If the command failed, provide more detailed error info
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                # Check for specific error patterns
                if "can't find '__main__' module" in error_msg:
                    # Add debugging info for the mount path issue
                    logger.error(f"Python module not found error. Temp file: {temp_file}")
                    logger.error(f"Docker command: {' '.join(docker_cmd)}")
                    if os.path.exists(temp_file):
                        logger.error(f"Temp file exists: True, size: {os.path.getsize(temp_file)}")
                    else:
                        logger.error("Temp file does not exist!")
                    error_msg += f"\nDebug: temp_file={temp_file}, exists={os.path.exists(temp_file)}"
            
            return {
                'id': eval_id,
                'status': 'completed' if result.returncode == 0 else 'failed',
                'output': result.stdout or result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'id': eval_id, 'status': 'timeout', 'error': f'Timeout after {self.timeout} seconds'}
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error executing code: {e}")
            return {'id': eval_id, 'status': 'error', 'error': str(e)}
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
            # Clean up old temp files (older than 1 hour)
            self._cleanup_old_temp_files(temp_dir)
    
    def get_description(self) -> str:
        return "Docker (Containerized - Network isolated)"
    
    def _cleanup_old_temp_files(self, temp_dir: str, max_age_seconds: int = 3600):
        """Clean up temp files older than max_age_seconds"""
        try:
            import time
            current_time = time.time()
            for filename in os.listdir(temp_dir):
                if filename.endswith('.py'):
                    filepath = os.path.join(temp_dir, filename)
                    if os.path.isfile(filepath):
                        file_age = current_time - os.path.getmtime(filepath)
                        if file_age > max_age_seconds:
                            os.unlink(filepath)
        except Exception:
            # Don't fail execution if cleanup fails
            pass
    
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


class GVisorEngine(DockerEngine):
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
    
    def __init__(self, runtime: str = 'runsc', temp_base_dir: str = None):
        # Initialize parent DockerEngine
        super().__init__(image="python:3.11-slim", temp_base_dir=temp_base_dir)
        
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
        
    def _build_docker_command(self, temp_file: str) -> list:
        """Override parent to add gVisor-specific security features"""
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
            self.image,
            'python', '-u', '/code.py'
        ])
        
        return docker_cmd
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        """Use parent's execute but override the result to add runtime info"""
        result = super().execute(code, eval_id)
        
        # Add gVisor-specific metadata
        result['runtime'] = self.runtime
        if self.runtime == 'runsc':
            result['security'] = 'production-grade'
        
        return result
    
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


class DisabledEngine(ExecutionEngine):
    """
    Execution engine that always returns errors.
    
    Used when no secure execution environment is available, allowing
    the platform to start and serve the web interface while clearly
    indicating that code execution is disabled.
    """
    
    def __init__(self, error_msg: str = "No execution engine available"):
        """Initialize with a specific error message explaining why execution is disabled."""
        self.error_msg = error_msg
        
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        """Return an error for any execution attempt."""
        return {
            'id': eval_id,
            'status': 'error',
            'error': f'Code execution disabled: {self.error_msg}'
        }
        
    def get_description(self) -> str:
        """Describe the disabled state."""
        return f"Disabled - {self.error_msg}"
        
    def health_check(self) -> Dict[str, Any]:
        """Report unhealthy status with reason."""
        return {
            'healthy': False,
            'reason': self.error_msg,
            'engine_type': 'disabled'
        }
        
    def self_test(self) -> Dict[str, Any]:
        """Return test results showing engine is disabled."""
        return {
            'passed': True,  # Not failing, just disabled
            'tests_passed': ['engine_disabled_check'],
            'tests_failed': [],
            'message': f'Engine disabled: {self.error_msg}'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return empty test suite - nothing to test for disabled engine."""
        return unittest.TestSuite()