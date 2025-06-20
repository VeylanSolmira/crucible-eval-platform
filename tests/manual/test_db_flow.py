#!/usr/bin/env python3
"""Test the complete database storage flow with truncation verification.

This script tests:
1. Normal evaluation submission and retrieval
2. Large output evaluation to verify truncation
3. Storage persistence verification

Usage: python test_db_flow.py [--api-url http://localhost:8001]
"""

import requests
import time
import json
import sys
import argparse

def test_normal_evaluation(api_url):
    """Test 1: Submit a normal evaluation"""
    print("\n" + "="*60)
    print("Test 1: Normal evaluation")
    print("="*60)
    
    code = """
import sys
import os
print(f"Python: {sys.version}")
print(f"Working dir: {os.getcwd()}")
print("Database storage test successful!")
"""
    return submit_and_check_evaluation(api_url, code, "normal evaluation")

def test_large_output(api_url):
    """Test 2: Submit evaluation with large output to test truncation"""
    print("\n" + "="*60)
    print("Test 2: Large output (should trigger truncation)")
    print("="*60)
    
    # Create code that generates >1MB of output
    code = """
# Generate more than 1MB of output to test truncation
for i in range(50000):
    print(f"Line {i}: " + "x" * 100)
print("\\n=== END OF OUTPUT ===")
"""
    return submit_and_check_evaluation(api_url, code, "large output evaluation")

def submit_and_check_evaluation(api_url, code, test_name):
    """Submit evaluation and check results"""
    print(f"\nSubmitting {test_name}...")
    
    response = requests.post(f"{api_url}/api/eval", json={"code": code})
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        eval_id = response.json().get("eval_id")
        print(f"Evaluation ID: {eval_id}")
        
        # Poll for completion
        print("\nPolling for completion...")
        max_attempts = 30
        for i in range(max_attempts):
            status_response = requests.get(f"{api_url}/api/eval-status/{eval_id}")
            if status_response.status_code == 200:
                result = status_response.json()
                print(f"Attempt {i+1}: Status = {result.get('status')}")
                
                if result.get("status") in ["completed", "failed", "error"]:
                    print(f"\nFinal result:")
                    print(f"Status: {result.get('status')}")
                    
                    # Check output details
                    if 'output' in result:
                        output_len = len(result['output'])
                        print(f"Output length: {output_len} chars")
                        if output_len > 2000:
                            print(f"Output preview: {result['output'][:100]}...")
                            print(f"...{result['output'][-100:]}")
                        else:
                            print(f"Output: {result['output']}")
                    
                    # For large output test, check if truncation fields are present
                    if test_name == "large output evaluation":
                        print("\nChecking truncation fields:")
                        print(f"- output_truncated: {result.get('output_truncated', 'NOT PRESENT')}")
                        print(f"- output_size: {result.get('output_size', 'NOT PRESENT')}")
                        print(f"- output_location: {result.get('output_location', 'NOT PRESENT')}")
                    
                    return eval_id, result
            else:
                print(f"Error getting status: {status_response.status_code}")
                print(f"Response: {status_response.text}")
                return None, None
                
            time.sleep(1)
        
        print("Timeout waiting for completion")
        return eval_id, None
    else:
        print(f"Failed to submit evaluation: {response.status_code}")
        return None, None

def check_evaluation_in_list(api_url, eval_id):
    """Check if evaluation appears in the list"""
    print("\nChecking evaluation list...")
    list_response = requests.get(f"{api_url}/api/evaluations")
    if list_response.status_code == 200:
        evaluations = list_response.json()
        
        if isinstance(evaluations, list) and evaluations and isinstance(evaluations[0], str):
            print(f"Found {len(evaluations)} evaluation IDs")
            if eval_id in evaluations:
                print(f"✓ Found our evaluation ID {eval_id} in the list!")
                return True
            else:
                print(f"✗ Evaluation ID {eval_id} NOT found in list")
                return False
    else:
        print(f"Error listing evaluations: {list_response.status_code}")
        return False

# Run tests
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test database storage flow')
    parser.add_argument('--api-url', default='http://localhost:8001', 
                        help='API URL (default: http://localhost:8001)')
    args = parser.parse_args()
    
    print(f"Testing against API: {args.api_url}")
    
    # Test 1: Normal evaluation
    eval_id1, result1 = test_normal_evaluation(args.api_url)
    if eval_id1:
        check_evaluation_in_list(args.api_url, eval_id1)
    
    # Test 2: Large output evaluation
    eval_id2, result2 = test_large_output(args.api_url)
    if eval_id2:
        check_evaluation_in_list(args.api_url, eval_id2)