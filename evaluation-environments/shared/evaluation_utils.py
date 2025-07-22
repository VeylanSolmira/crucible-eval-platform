"""Utilities for evaluation code to ensure proper output formatting"""

import json
from typing import Any


def output_json(data: Any) -> None:
    """
    Output data as JSON in a way that works around Kubernetes API issues.
    
    When using Kubernetes Python API to create jobs, single-line json.dumps()
    output gets converted to Python dict representation. This function works
    around that issue by adding a suffix.
    
    Args:
        data: Python object to output as JSON
        
    Example:
        from evaluation_utils import output_json
        
        result = {"score": 42, "passed": True}
        output_json(result)  # Guaranteed to output proper JSON
    """
    print(json.dumps(data))
    print("# JSON_OUTPUT_COMPLETE")  # This suffix prevents dict repr conversion


def output_result(result: Any, metadata: dict = None) -> None:
    """
    Output evaluation result in a standardized format.
    
    Args:
        result: The main result data
        metadata: Optional metadata about the evaluation
        
    Example:
        from evaluation_utils import output_result
        
        output_result(
            {"score": 0.95, "passed": True},
            {"runtime_ms": 123, "model": "gpt-4"}
        )
    """
    output = {
        "result": result,
        "metadata": metadata or {}
    }
    output_json(output)


# For backwards compatibility
print_json = output_json