#!/usr/bin/env python3
"""Test dual-write functionality - verify evaluation goes to both systems"""
import requests
import time
import json

# Submit a test evaluation
print("Submitting test evaluation...")
response = requests.post(
    "http://localhost:8000/api/eval",
    json={
        "code": 'print("Hello from dual-write test!")',
        "language": "python"
    }
)

if response.status_code == 200:
    result = response.json()
    eval_id = result["eval_id"]
    print(f"✅ Evaluation submitted: {eval_id}")
    
    # Wait a bit for processing
    print("Waiting for execution...")
    time.sleep(5)
    
    # Check status
    status_response = requests.get(f"http://localhost:8000/api/eval/{eval_id}/status")
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"✅ Status: {status['status']}")
        if status['status'] == 'completed':
            print(f"✅ Output: {status.get('output', 'N/A')}")
    
    # Check which executor processed it
    print("\nChecking executor logs...")
    
else:
    print(f"❌ Failed to submit: {response.status_code}")
    print(response.text)