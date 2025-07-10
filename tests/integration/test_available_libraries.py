#!/usr/bin/env python3
"""Integration tests for available Python libraries in containers"""

import pytest
import requests
import time
from tests.utils import submit_evaluation, wait_for_completion, get_evaluation_status

LIBRARY_TEST_CODE = '''
import json

libraries_to_test = [
    'numpy', 'pandas', 'requests', 'matplotlib', 
    'scipy', 'sklearn', 'tensorflow', 'torch',
    'json', 'hashlib', 'datetime', 'os', 'sys'
]

results = {"available": [], "unavailable": []}

for lib in libraries_to_test:
    try:
        __import__(lib)
        results["available"].append(lib)
    except ImportError:
        results["unavailable"].append(lib)

# Test that standard library works
import hashlib
import datetime

test_results = []
test_results.append(f"Hash test: {hashlib.sha256(b'test').hexdigest()[:10]}...")
test_results.append(f"Date test: {datetime.datetime.now().year}")

print(json.dumps({
    "available": results["available"],
    "unavailable": results["unavailable"],
    "tests": test_results
}, indent=2))
'''

@pytest.mark.integration
def test_available_libraries():
    """Test which Python libraries are available in containers"""
    # Submit the library test code
    eval_id = submit_evaluation(LIBRARY_TEST_CODE)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Wait for completion
    status = wait_for_completion(eval_id, timeout=30)
    assert status is not None, "Evaluation did not complete in time"
    
    # Get the full evaluation details
    eval_data = get_evaluation_status(eval_id)
    assert eval_data["status"] == "completed", f"Evaluation failed with status: {eval_data['status']}"
    
    # Parse the output
    output = eval_data.get("output", "")
    import json
    try:
        results = json.loads(output)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to parse output as JSON: {output}")
    
    # Check that standard library modules are available
    assert "json" in results["available"], "json module should be available"
    assert "hashlib" in results["available"], "hashlib module should be available"
    assert "datetime" in results["available"], "datetime module should be available"
    assert "os" in results["available"], "os module should be available"
    assert "sys" in results["available"], "sys module should be available"
    
    # Check that test results worked
    assert len(results["tests"]) == 2, "Should have two test results"
    assert "Hash test:" in results["tests"][0]
    assert "Date test:" in results["tests"][1]
    
    # Record what's available for documentation
    print(f"\nAvailable libraries: {', '.join(results['available'])}")
    print(f"Unavailable libraries: {', '.join(results['unavailable'])}")