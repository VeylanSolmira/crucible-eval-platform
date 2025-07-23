#!/usr/bin/env python3
"""
Integration tests for executor import handling and ML library support.

These tests verify that:
1. Import errors are properly captured in stderr
2. ML libraries work correctly with the executor-ml image
"""

import pytest
import httpx
import time
import os

# API configuration
API_URL = os.environ.get("API_URL", "https://localhost")
VERIFY_SSL = False


@pytest.mark.whitebox
@pytest.mark.integration
@pytest.mark.executor
@pytest.mark.docker
@pytest.mark.skip(reason="We're not in a Kubernetes architecture and not using executor containers")
class TestExecutorImports:
    """Test executor handling of Python imports and ML libraries."""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Create API client with SSL verification disabled."""
        return httpx.Client(verify=VERIFY_SSL, follow_redirects=True)
    
    def submit_and_wait(self, client, code: str, timeout: int = 30) -> dict:
        """Submit code and wait for completion."""
        # Submit evaluation
        response = client.post(
            f"{API_URL}/api/eval",
            json={
                "code": code,
                "language": "python",
                "engine": "docker",
                "timeout": timeout
            }
        )
        response.raise_for_status()
        eval_id = response.json()["eval_id"]
        
        # Wait for completion
        start_time = time.time()
        while time.time() - start_time < timeout + 10:
            response = client.get(f"{API_URL}/api/eval/{eval_id}")
            if response.status_code == 200:
                result = response.json()
                if result["status"] in ["completed", "failed", "error"]:
                    return result
            time.sleep(1)
        
        raise TimeoutError(f"Evaluation {eval_id} did not complete in time")
    
    def test_import_error_captured(self, api_client):
        """Test that import errors are properly captured in stderr."""
        code = """
import sys

print("Starting import test...", file=sys.stdout)
print("This message goes to stdout", file=sys.stdout)

try:
    import torch
    print("Successfully imported torch!", file=sys.stdout)
    print(f"Torch version: {torch.__version__}", file=sys.stdout)
except ImportError as e:
    print(f"Import error (this should appear in stderr): {e}", file=sys.stderr)
    sys.exit(1)

print("This line should not be reached", file=sys.stdout)
"""
        
        result = self.submit_and_wait(api_client, code)
        
        # Verify the evaluation failed (exit code 1)
        assert result["status"] == "completed"
        assert result["exit_code"] == 1
        
        # Verify stdout contains expected messages
        assert "Starting import test..." in result["output"]
        assert "This message goes to stdout" in result["output"]
        
        # Verify stderr contains import error
        # Note: In current implementation, stdout and stderr are combined
        assert "Import error" in result["output"]
        assert "No module named 'torch'" in result["output"] or "torch" in result["output"]
        
        # Verify the last line was not reached
        assert "This line should not be reached" not in result["output"]
    
    @pytest.mark.skipif(
        os.environ.get("EXECUTOR_IMAGE", "").find("executor-ml") == -1,
        reason="Requires executor-ml image"
    )
    def test_ml_libraries_available(self, api_client):
        """Test that ML libraries are available in executor-ml image."""
        code = """
print("Testing ML library imports...")

try:
    import torch
    print(f"✓ PyTorch {torch.__version__} imported successfully")
    
    import transformers
    print(f"✓ Transformers {transformers.__version__} imported successfully")
    
    import numpy as np
    print(f"✓ NumPy {np.__version__} imported successfully")
    
    # Simple computation to verify it works
    x = torch.tensor([1.0, 2.0, 3.0])
    y = x * 2
    print(f"\\nTensor computation: {x} * 2 = {y}")
    
    print("\\n✅ All ML libraries are working correctly!")
    
except ImportError as e:
    print(f"\\n❌ Import error: {e}")
    print("Make sure the executor is using the executor-ml image")
    import sys
    sys.exit(1)
"""
        
        result = self.submit_and_wait(api_client, code)
        
        # Verify successful execution
        assert result["status"] == "completed"
        assert result["exit_code"] == 0
        
        # Verify all libraries imported
        assert "PyTorch" in result["output"]
        assert "imported successfully" in result["output"]
        assert "Transformers" in result["output"]
        assert "NumPy" in result["output"]
        
        # Verify computation worked
        assert "Tensor computation" in result["output"]
        assert "[2., 4., 6.]" in result["output"]
        
        # Verify success message
        assert "All ML libraries are working correctly!" in result["output"]
    
    def test_standard_library_imports(self, api_client):
        """Test that standard library imports work correctly."""
        code = """
import json
import datetime
import math

data = {"test": "value", "number": 42}
print(f"JSON: {json.dumps(data)}")

now = datetime.datetime.now()
print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

print(f"Pi: {math.pi}")
print("✅ Standard library imports working!")
"""
        
        result = self.submit_and_wait(api_client, code)
        
        assert result["status"] == "completed"
        assert result["exit_code"] == 0
        assert "JSON:" in result["output"]
        assert "Current time:" in result["output"]
        assert "Pi: 3.14" in result["output"]
        assert "Standard library imports working!" in result["output"]