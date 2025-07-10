#!/usr/bin/env python3
"""
Automated demo runner for Crucible Platform
Submits a series of demo evaluations to showcase platform capabilities

This follows the "Tagged Evaluation System" approach described in 
/docs/planning/demo-philosophy.md - each evaluation can be filtered
in the frontend to facilitate story-driven demonstrations.

Future versions could add metadata/tags to evaluations for better
organization and filtering in the UI.
"""
import time
import json
import sys
import os
from typing import List, Dict, Optional
import requests
from datetime import datetime

# Default to production URL
DEFAULT_API_URL = "https://crucible.veylan.dev/api/eval"

class DemoRunner:
    def __init__(self, api_url: str, delay: float = 2.0):
        self.api_url = api_url
        self.delay = delay
        self.results = []
        
    def submit_code(self, code: str, description: str) -> Optional[Dict]:
        """Submit code and return the evaluation ID"""
        print(f"\n{'='*60}")
        print(f"Demo: {description}")
        print(f"{'='*60}")
        print(f"Submitting code...")
        
        try:
            response = requests.post(
                self.api_url,
                json={"code": code},
                headers={"Content-Type": "application/json"},
                verify=False  # For self-signed certs in dev
            )
            response.raise_for_status()
            
            result = response.json()
            eval_id = result.get("eval_id", "unknown")
            
            print(f"✓ Submitted successfully!")
            print(f"  Evaluation ID: {eval_id}")
            print(f"  Status: {result.get('status', 'unknown')}")
            
            self.results.append({
                "description": description,
                "eval_id": eval_id,
                "status": "submitted",
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to submit: {e}")
            self.results.append({
                "description": description,
                "eval_id": None,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return None
    
    def run_demo_suite(self):
        """Run the complete demo suite"""
        print(f"Starting Crucible Platform Demo Suite")
        print(f"Target: {self.api_url}")
        print(f"Delay between submissions: {self.delay}s")
        
        # Define demo files to run
        demos = [
            # Basic functionality demos
            {
                "description": "Hello World - Basic Success",
                "file": "../frontend/lib/templates/hello-world.py"
            },
            
            # Error handling demos
            {
                "description": "Syntax Error - Clear Error Reporting",
                "file": "templates/syntax-error.py"
            },
            {
                "description": "Runtime Error - Division by Zero",
                "file": "templates/runtime-error.py"
            },
            
            # Resource limit demos
            {
                "description": "Timeout Demo - 30 Second Limit",
                "file": "templates/timeout-demo.py"
            },
            {
                "description": "CPU Exhaustion - Throttling Test",
                "file": "templates/cpu-exhaustion.py"
            },
            {
                "description": "Memory Exhaustion - OOM Kill",
                "file": "templates/memory-exhaustion.py"
            },
            
            # Platform capability demos
            {
                "description": "Large Output - Output Handling",
                "file": "templates/large-output.py"
            },
            
            # Load test demo (submit multiple times for concurrent testing)
            {
                "description": "Stress Test - Variable Workload",
                "file": "templates/stress-test.py"
            }
        ]
        
        # Load code from files where specified
        demo_dir = os.path.dirname(os.path.abspath(__file__))
        for demo in demos:
            if "file" in demo:
                file_path = os.path.join(demo_dir, demo["file"])
                try:
                    with open(file_path, 'r') as f:
                        demo["code"] = f.read()
                except FileNotFoundError:
                    print(f"Warning: Could not find {file_path}")
                    continue
        
        # Submit all demos
        for i, demo in enumerate(demos):
            if "code" in demo:
                self.submit_code(demo["code"], demo["description"])
                
                # Delay between submissions (except for the last one)
                if i < len(demos) - 1:
                    print(f"\nWaiting {self.delay}s before next submission...")
                    time.sleep(self.delay)
        
        # Summary
        print(f"\n{'='*60}")
        print("DEMO SUITE COMPLETE")
        print(f"{'='*60}")
        print(f"Total demos: {len(self.results)}")
        print(f"Successful: {sum(1 for r in self.results if r['status'] == 'submitted')}")
        print(f"Failed: {sum(1 for r in self.results if r['status'] == 'failed')}")
        
        print("\nSubmitted evaluations:")
        for result in self.results:
            if result["status"] == "submitted":
                print(f"  - {result['eval_id']}: {result['description']}")
        
        print(f"\nView results at: {self.api_url.replace('/api/eval', '')}")

def main():
    # Parse command line arguments
    api_url = DEFAULT_API_URL
    delay = 2.0
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("Usage: python run-demo-suite.py [api_url] [delay_seconds]")
            print(f"  api_url: API endpoint (default: {DEFAULT_API_URL})")
            print(f"  delay_seconds: Delay between submissions (default: 2.0)")
            sys.exit(0)
        api_url = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            delay = float(sys.argv[2])
        except ValueError:
            print(f"Invalid delay value: {sys.argv[2]}")
            sys.exit(1)
    
    # Suppress SSL warnings for development
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Run the demo suite
    runner = DemoRunner(api_url, delay)
    runner.run_demo_suite()

if __name__ == "__main__":
    main()