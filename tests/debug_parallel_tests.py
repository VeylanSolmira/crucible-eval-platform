#!/usr/bin/env python3
"""
Comprehensive debugging script for parallel test failures.

This script monitors and logs detailed information during parallel test runs to identify
why e2e tests fail in parallel but succeed individually.
"""

import subprocess
import json
import time
import threading
import sys
import os
from datetime import datetime
from collections import defaultdict
import argparse

class ParallelTestDebugger:
    def __init__(self, namespace="dev", output_dir="debug_output"):
        self.namespace = namespace
        self.output_dir = output_dir
        self.start_time = time.time()
        self.running = True
        self.evaluation_tracking = defaultdict(dict)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Open log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_files = {
            "main": open(f"{output_dir}/debug_main_{timestamp}.log", "w"),
            "evaluations": open(f"{output_dir}/debug_evaluations_{timestamp}.log", "w"),
            "pods": open(f"{output_dir}/debug_pods_{timestamp}.log", "w"),
            "jobs": open(f"{output_dir}/debug_jobs_{timestamp}.log", "w"),
            "dispatcher": open(f"{output_dir}/debug_dispatcher_{timestamp}.log", "w"),
            "api": open(f"{output_dir}/debug_api_{timestamp}.log", "w"),
            "events": open(f"{output_dir}/debug_events_{timestamp}.log", "w"),
        }
        
    def log(self, message, file="main"):
        """Log a timestamped message to the specified file."""
        timestamp = f"[{time.time() - self.start_time:.1f}s]"
        log_line = f"{timestamp} {message}\n"
        self.log_files[file].write(log_line)
        self.log_files[file].flush()
        print(log_line.strip())
        
    def get_evaluation_jobs(self):
        """Get all evaluation jobs in the namespace."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "jobs", "-n", self.namespace, 
                 "-l", "app=evaluation", "-o", "json"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return json.loads(result.stdout).get("items", [])
        except Exception as e:
            self.log(f"Error getting evaluation jobs: {e}", "jobs")
        return []
        
    def get_evaluation_pods(self):
        """Get all evaluation pods in the namespace."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace,
                 "-l", "app=evaluation", "-o", "json"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return json.loads(result.stdout).get("items", [])
        except Exception as e:
            self.log(f"Error getting evaluation pods: {e}", "pods")
        return []
        
    def get_api_evaluation_status(self, eval_id):
        """Get evaluation status from the API."""
        try:
            result = subprocess.run(
                ["kubectl", "exec", "-n", self.namespace,
                 "deployment/api", "--", "curl", "-s",
                 f"http://localhost:8080/api/eval/{eval_id}"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            self.log(f"Error getting API status for {eval_id}: {e}", "api")
        return None
        
    def get_dispatcher_logs(self, since_seconds=10):
        """Get recent dispatcher logs."""
        try:
            result = subprocess.run(
                ["kubectl", "logs", "-n", self.namespace,
                 "deployment/dispatcher", f"--since={since_seconds}s"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            self.log(f"Error getting dispatcher logs: {e}", "dispatcher")
        return ""
        
    def get_events(self, since_seconds=60):
        """Get recent Kubernetes events."""
        try:
            # Get events for evaluation pods/jobs
            result = subprocess.run(
                ["kubectl", "get", "events", "-n", self.namespace,
                 "--field-selector", "involvedObject.kind=Job",
                 "-o", "json"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                events = json.loads(result.stdout).get("items", [])
                # Filter recent events
                recent_events = []
                current_time = time.time()
                for event in events:
                    # Check if event is recent
                    if event.get("involvedObject", {}).get("name", "").startswith("evaluation-"):
                        recent_events.append(event)
                return recent_events
        except Exception as e:
            self.log(f"Error getting events: {e}", "events")
        return []
        
    def monitor_evaluation_lifecycle(self):
        """Monitor the complete lifecycle of evaluations."""
        while self.running:
            # Get current state
            jobs = self.get_evaluation_jobs()
            pods = self.get_evaluation_pods()
            
            # Track jobs by eval ID
            jobs_by_eval = {}
            for job in jobs:
                job_name = job["metadata"]["name"]
                # Extract eval ID from job name (format: evaluation-<eval_id>-job-<suffix>)
                if job_name.startswith("evaluation-") and "-job-" in job_name:
                    eval_id = job_name.split("-job-")[0].replace("evaluation-", "")
                    jobs_by_eval[eval_id] = job
                    
            # Track pods by eval ID
            pods_by_eval = {}
            for pod in pods:
                pod_name = pod["metadata"]["name"]
                # Extract eval ID from pod name
                if pod_name.startswith("evaluation-") and "-job-" in pod_name:
                    eval_id = pod_name.split("-job-")[0].replace("evaluation-", "")
                    pods_by_eval[eval_id] = pod
                    
            # Check each evaluation we're tracking
            for eval_id in list(self.evaluation_tracking.keys()):
                tracking = self.evaluation_tracking[eval_id]
                
                # Check if job exists
                if eval_id in jobs_by_eval:
                    if "job_created" not in tracking:
                        tracking["job_created"] = time.time() - self.start_time
                        self.log(f"EVAL {eval_id}: Job created", "evaluations")
                        
                    job = jobs_by_eval[eval_id]
                    job_status = job.get("status", {})
                    if job_status.get("failed", 0) > 0 and "job_failed" not in tracking:
                        tracking["job_failed"] = time.time() - self.start_time
                        self.log(f"EVAL {eval_id}: Job failed", "evaluations")
                        
                # Check if pod exists
                if eval_id in pods_by_eval:
                    if "pod_created" not in tracking:
                        tracking["pod_created"] = time.time() - self.start_time
                        self.log(f"EVAL {eval_id}: Pod created", "evaluations")
                        
                    pod = pods_by_eval[eval_id]
                    pod_phase = pod["status"]["phase"]
                    if pod_phase != tracking.get("last_pod_phase"):
                        tracking["last_pod_phase"] = pod_phase
                        self.log(f"EVAL {eval_id}: Pod phase changed to {pod_phase}", "evaluations")
                        
                # Check API status
                api_status = self.get_api_evaluation_status(eval_id)
                if api_status:
                    api_state = api_status.get("status", "unknown")
                    if api_state != tracking.get("last_api_state"):
                        tracking["last_api_state"] = api_state
                        self.log(f"EVAL {eval_id}: API state changed to {api_state}", "evaluations")
                        
                        # Check for missing job/pod
                        if api_state in ["provisioning", "running"] and eval_id not in jobs_by_eval:
                            self.log(f"WARNING: EVAL {eval_id} is {api_state} but has no job!", "evaluations")
                            
            time.sleep(2)
            
    def monitor_dispatcher(self):
        """Monitor dispatcher logs for issues."""
        last_check = 0
        while self.running:
            # Get dispatcher logs every 5 seconds
            logs = self.get_dispatcher_logs(since_seconds=5)
            
            # Look for interesting patterns
            for line in logs.split('\n'):
                if any(pattern in line for pattern in ["ERROR", "Failed", "Exception", "provisioning"]):
                    self.log(f"DISPATCHER: {line}", "dispatcher")
                    
                # Track evaluation submissions
                if "Creating job for evaluation" in line:
                    # Extract eval ID
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "evaluation" and i + 1 < len(parts):
                            eval_id = parts[i + 1]
                            if eval_id not in self.evaluation_tracking:
                                self.evaluation_tracking[eval_id] = {
                                    "submitted": time.time() - self.start_time
                                }
                                self.log(f"EVAL {eval_id}: Submitted to dispatcher", "evaluations")
                                
            time.sleep(5)
            
    def monitor_events(self):
        """Monitor Kubernetes events for issues."""
        while self.running:
            events = self.get_events(since_seconds=30)
            
            for event in events:
                event_type = event.get("type", "")
                reason = event.get("reason", "")
                message = event.get("message", "")
                obj_name = event.get("involvedObject", {}).get("name", "")
                
                if event_type == "Warning" or reason in ["FailedCreate", "FailedScheduling"]:
                    self.log(f"K8S EVENT: {obj_name} - {reason}: {message}", "events")
                    
            time.sleep(10)
            
    def generate_summary(self):
        """Generate a summary of findings."""
        self.log("\n=== DEBUGGING SUMMARY ===", "main")
        
        # Analyze evaluation tracking
        total_evals = len(self.evaluation_tracking)
        no_job_count = 0
        no_pod_count = 0
        failed_count = 0
        
        for eval_id, tracking in self.evaluation_tracking.items():
            if "job_created" not in tracking:
                no_job_count += 1
                self.log(f"EVAL {eval_id}: Never got a job created", "main")
            elif "pod_created" not in tracking:
                no_pod_count += 1
                self.log(f"EVAL {eval_id}: Job created but no pod", "main")
            if "job_failed" in tracking:
                failed_count += 1
                
        self.log(f"\nTotal evaluations tracked: {total_evals}", "main")
        self.log(f"Evaluations without jobs: {no_job_count}", "main")
        self.log(f"Evaluations without pods: {no_pod_count}", "main")
        self.log(f"Failed evaluations: {failed_count}", "main")
        
    def run(self, duration=180):
        """Run the debugger for the specified duration."""
        self.log(f"Starting parallel test debugger for {duration} seconds", "main")
        self.log(f"Namespace: {self.namespace}", "main")
        
        # Start monitoring threads
        threads = [
            threading.Thread(target=self.monitor_evaluation_lifecycle, daemon=True),
            threading.Thread(target=self.monitor_dispatcher, daemon=True),
            threading.Thread(target=self.monitor_events, daemon=True),
        ]
        
        for thread in threads:
            thread.start()
            
        # Wait for specified duration
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            self.log("Interrupted by user", "main")
            
        # Stop monitoring
        self.running = False
        
        # Generate summary
        self.generate_summary()
        
        # Close log files
        for f in self.log_files.values():
            f.close()
            
        self.log(f"\nDebug logs saved to {self.output_dir}/", "main")


def main():
    parser = argparse.ArgumentParser(description="Debug parallel test failures")
    parser.add_argument("--duration", type=int, default=180,
                       help="Duration to monitor in seconds (default: 180)")
    parser.add_argument("--namespace", default="dev",
                       help="Kubernetes namespace (default: dev)")
    parser.add_argument("--output-dir", default="debug_output",
                       help="Output directory for logs (default: debug_output)")
    
    args = parser.parse_args()
    
    debugger = ParallelTestDebugger(
        namespace=args.namespace,
        output_dir=args.output_dir
    )
    
    print("Start the parallel tests in another terminal:")
    print(f"  python tests/test_orchestrator.py integration e2e --parallel --show-cluster-resources")
    print("\nPress Enter when ready to start monitoring...")
    input()
    
    debugger.run(duration=args.duration)


if __name__ == "__main__":
    main()