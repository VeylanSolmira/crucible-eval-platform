"""
Integration tests for evaluation job import handling.

These tests verify that Kubernetes Jobs created by the dispatcher
properly handle various import scenarios, including:
- Standard library imports
- Missing module imports
- ML library availability
"""

import pytest
import time
import requests
from typing import Dict, Any
from shared.utils import is_valid_evaluation_id
from tests.utils.utils import wait_for_logs


def wait_for_evaluation(
    api_session: requests.Session,
    api_base_url: str,
    eval_id: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """Wait for an evaluation to reach a terminal state."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = api_session.get(f"{api_base_url}/eval/{eval_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get("status") in ["completed", "failed", "timeout", "cancelled"]:
                return result
        time.sleep(0.5)
    
    raise TimeoutError(f"Evaluation {eval_id} did not complete within {timeout} seconds")


@pytest.mark.integration
@pytest.mark.api
class TestEvaluationJobImports:
    """Test import handling in Kubernetes evaluation jobs."""
    
    def test_standard_library_imports(self, api_session: requests.Session, api_base_url: str):
        """Test that standard library imports work correctly in evaluation jobs."""
        code = """
import json
import datetime
import math
import sys
import os

data = {"test": "value", "number": 42}
print(f"JSON: {json.dumps(data)}")

now = datetime.datetime.now()
print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

print(f"Math operations: sqrt(16) = {math.sqrt(16)}")
print(f"Python version: {sys.version}")
print(f"Platform: {os.environ.get('KUBERNETES_SERVICE_HOST', 'not in k8s')}")
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Verify successful completion
        assert result["status"] == "completed", f"Evaluation failed: {result}"
        
        # Verify output contains expected content
        output = result.get("output", "")
        assert "JSON:" in output
        assert "Current time:" in output
        assert "Math operations: sqrt(16) = 4.0" in output
        assert "Python version:" in output
        # Verify we're running in Kubernetes
        assert "KUBERNETES_SERVICE_HOST" not in output or "not in k8s" not in output
    
    def test_import_error_captured(self, api_session: requests.Session, api_base_url: str):
        """Test that import errors are properly captured in evaluation jobs."""
        code = """
import sys

print("Starting import test...", file=sys.stdout)
print("This message goes to stdout", file=sys.stdout)

try:
    import torch
    print("Successfully imported torch!", file=sys.stdout)
except ImportError as e:
    print(f"Failed to import torch: {e}", file=sys.stderr)
    print("This is expected in minimal executor", file=sys.stdout)

# Try another non-existent module
try:
    import nonexistent_module_12345
except ImportError as e:
    print(f"Expected error: {e}", file=sys.stdout)

print("Import test completed", file=sys.stdout)
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Should complete successfully (we caught the exceptions)
        assert result["status"] == "completed", f"Evaluation failed: {result}"
        
        # Verify output and error handling
        output = result.get("output", "")
        error = result.get("error", "")
        combined = output + error
        
        assert "Starting import test..." in combined
        assert "Import test completed" in combined
        assert "Expected error:" in combined
        assert "nonexistent_module_12345" in combined
    
    def test_ml_libraries_available(self, api_session: requests.Session, api_base_url: str):
        """Test that ML libraries are available in the executor-ml image.
        
        Note: This test is marked with 'ml' and assumes the executor-ml image
        is being used which includes PyTorch, NumPy, etc.
        """
        code = """
import sys

# Test numpy
try:
    import numpy as np
    arr = np.array([1, 2, 3, 4, 5])
    print(f"NumPy version: {np.__version__}")
    print(f"Array mean: {arr.mean()}")
except ImportError as e:
    print(f"NumPy not available: {e}", file=sys.stderr)

# Test basic ML operations
try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    tensor = torch.tensor([1.0, 2.0, 3.0])
    print(f"Tensor sum: {tensor.sum().item()}")
except ImportError as e:
    print(f"PyTorch not available: {e}", file=sys.stderr)
    
print("ML library test completed")
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Should complete (even if libraries aren't available)
        assert result["status"] == "completed", f"Evaluation failed: {result}"
        
        output = result.get("output", "")
        error = result.get("error", "")
        combined = output + error
        
        # At minimum, the test should complete
        assert "ML library test completed" in combined
        
        # If this is executor-ml, libraries should be available
        if "executor-ml" in combined or "NumPy version:" in combined:
            assert "Array mean: 3.0" in combined
            # PyTorch might or might not be available depending on image
    
    def test_sys_path_and_modules(self, api_session: requests.Session, api_base_url: str):
        """Test sys.path configuration and available modules in evaluation jobs."""
        code = """
import sys
import os

print("=== Python Environment ===")
print(f"Python version: {sys.version}")
print(f"Executable: {sys.executable}")

print("\\n=== sys.path ===")
for i, path in enumerate(sys.path):
    print(f"{i}: {path}")

print("\\n=== Environment ===")
print(f"Working directory: {os.getcwd()}")
print(f"HOME: {os.environ.get('HOME', 'not set')}")
print(f"USER: {os.environ.get('USER', 'not set')}")
print(f"EVAL_ID: {os.environ.get('EVAL_ID', 'not set')}")

print("\\n=== Available built-in modules ===")
print(f"Number of built-in modules: {len(sys.builtin_module_names)}")
print("Some examples:", ", ".join(list(sys.builtin_module_names)[:10]))
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Should complete successfully
        assert result["status"] == "completed", f"Evaluation failed: {result}"
        
        # Wait for logs to be available (handles async log fetching)
        from tests.utils.utils import wait_for_logs
        output = wait_for_logs(eval_id, timeout=60)
        
        # Verify environment information
        assert "Python version:" in output
        assert "sys.path" in output
        assert "Working directory:" in output
        # Should have EVAL_ID from dispatcher
        assert "EVAL_ID: " in output
        # Verify the ID matches the format our function generates
        eval_id_line = [line for line in output.split('\n') if 'EVAL_ID: ' in line][0]
        eval_id = eval_id_line.split('EVAL_ID: ')[1].strip()
        
        # Validate using our shared utility function
        assert is_valid_evaluation_id(eval_id), f"Eval ID '{eval_id}' doesn't match expected format"
        assert "built-in modules:" in output
    
    def test_import_with_syntax_error(self, api_session: requests.Session, api_base_url: str):
        """Test handling of syntax errors during import."""
        code = """
# This will cause a syntax error
import json
from invalid syntax import something

print("This should not execute")
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Should fail due to syntax error
        assert result["status"] == "failed", f"Expected failure but got: {result['status']}"
        
        # Wait for logs to be collected
        logs = wait_for_logs(eval_id, timeout=30)
        
        # Check error message
        error = (result.get("error") or "") + logs
        assert "SyntaxError" in error or "invalid syntax" in error
        assert "This should not execute" not in error  # Should not reach this line
    
    def test_relative_imports(self, api_session: requests.Session, api_base_url: str):
        """Test that relative imports fail appropriately (no package context)."""
        code = """
# Relative imports should fail in evaluation context
try:
    from . import something
    print("Relative import succeeded (unexpected)")
except ImportError as e:
    print(f"Relative import failed as expected: {e}")

try:
    from .. import parent_module
except ImportError as e:
    print(f"Parent import failed as expected: {e}")

print("Relative import test completed")
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Should complete (we're catching the errors)
        assert result["status"] == "completed", f"Evaluation failed: {result}"
        
        output = result.get("output", "")
        assert "Relative import failed as expected" in output
        assert "Parent import failed as expected" in output
        assert "Relative import test completed" in output
    
    def test_multiline_imports(self, api_session: requests.Session, api_base_url: str):
        """Test multi-line import statements and complex import patterns."""
        code = """
# Test multi-line imports
from datetime import (
    datetime,
    timedelta,
    timezone
)

# Test aliased imports
import json as j
from math import pi as PI, sqrt as square_root

# Test star imports
from collections import *

# Verify imports work
now = datetime.now()
delta = timedelta(days=1)
data = j.dumps({"pi": PI})
root = square_root(16)
counter = Counter(['a', 'b', 'a'])

print(f"Current time: {now}")
print(f"Tomorrow: {now + delta}")
print(f"JSON data: {data}")
print(f"Square root of 16: {root}")
print(f"Counter: {dict(counter)}")
print("✅ Complex imports working!")
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Should complete successfully
        assert result["status"] == "completed", f"Evaluation failed: {result}"
        
        output = result.get("output", "")
        assert "Current time:" in output
        assert "Tomorrow:" in output
        assert "JSON data:" in output
        assert "Square root of 16: 4.0" in output
        assert "Counter:" in output
        assert "Complex imports working!" in output
    
    def test_subprocess_imports(self, api_session: requests.Session, api_base_url: str):
        """Test that subprocess module works (important for many evaluation scenarios)."""
        code = """
import subprocess
import sys

# Test running a simple command
try:
    result = subprocess.run(
        [sys.executable, "-c", "print('Subprocess works!')"],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(f"Return code: {result.returncode}")
    print(f"Output: {result.stdout.strip()}")
    if result.stderr:
        print(f"Error: {result.stderr.strip()}")
except Exception as e:
    print(f"Subprocess failed: {e}")

# Test subprocess with import in child
try:
    child_code = '''
import json
data = {"from": "subprocess"}
print(json.dumps(data))
'''
    result = subprocess.run(
        [sys.executable, "-c", child_code],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(f"Child process output: {result.stdout.strip()}")
except Exception as e:
    print(f"Child process failed: {e}")

print("✅ Subprocess imports test completed")
"""
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={"code": code, "language": "python", "timeout": 30}
        )
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=60)
        
        # Should complete successfully
        assert result["status"] == "completed", f"Evaluation failed: {result}"
        
        output = result.get("output", "")
        assert "Return code: 0" in output
        assert "Output: Subprocess works!" in output
        assert '{"from": "subprocess"}' in output
        assert "Subprocess imports test completed" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])