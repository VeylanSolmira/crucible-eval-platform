#!/usr/bin/env python3
"""
Test to understand kubectl logs behavior when pods complete.

This test helps us understand:
1. When kubectl logs -f terminates relative to pod completion
2. Whether we're missing output due to early termination
3. How to properly wait for all logs before considering a job complete
"""

import subprocess
import threading
import time
import queue

def test_log_timing():
    """Test log collection timing with a simple job."""
    
    # Create a test job that outputs then sleeps briefly
    job_manifest = """
apiVersion: batch/v1
kind: Job
metadata:
  name: log-timing-test
spec:
  backoffLimit: 0
  template:
    spec:
      containers:
      - name: test
        image: busybox
        command: 
        - sh
        - -c
        - |
          echo "START OF OUTPUT"
          for i in 1 2 3 4 5; do
            echo "Line $i"
            sleep 0.5
          done
          echo "FINAL LINE - PYTEST SUMMARY WOULD BE HERE"
          echo "===== 5 passed in 2.5s ====="
          sleep 1
          echo "POST-SUMMARY OUTPUT"
      restartPolicy: Never
"""
    
    # Apply the job
    print("Creating test job...")
    result = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=job_manifest,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Failed to create job: {result.stderr}")
        return
    
    # Now monitor it like coordinator.py does
    log_queue = queue.Queue()
    captured_logs = []
    log_process = None
    log_streaming_complete = threading.Event()
    
    def stream_logs():
        nonlocal log_process
        try:
            time.sleep(2)  # Wait for pod to start
            
            log_process = subprocess.Popen(
                ["kubectl", "logs", "-f", "job/log-timing-test"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in iter(log_process.stdout.readline, ''):
                if line:
                    line_stripped = line.rstrip()
                    log_queue.put(f"[{time.time():.3f}] {line_stripped}")
                    captured_logs.append(line_stripped)
            
            log_process.wait()
        except Exception as e:
            log_queue.put(f"[Log error: {e}]")
        finally:
            log_streaming_complete.set()
    
    log_thread = threading.Thread(target=stream_logs, daemon=False)
    log_thread.start()
    
    # Monitor job status
    print("\nMonitoring job...")
    start_time = time.time()
    
    while True:
        # Print any logs
        try:
            while True:
                line = log_queue.get_nowait()
                print(f"LOG: {line}")
        except queue.Empty:
            pass
        
        # Check job status
        result = subprocess.run(
            ["kubectl", "get", "job", "log-timing-test", "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            import json
            job_data = json.loads(result.stdout)
            status = job_data.get("status", {})
            
            print(f"[{time.time() - start_time:.3f}s] Status: active={status.get('active', 0)}, "
                  f"succeeded={status.get('succeeded', 0)}, failed={status.get('failed', 0)}")
            
            # This is the condition coordinator.py uses
            if status.get("active", 0) == 0 and (status.get("succeeded", 0) > 0 or status.get("failed", 0) > 0):
                print(f"\n[{time.time() - start_time:.3f}s] Job complete per K8s API")
                
                # This is what coordinator.py does - terminate logs immediately
                if log_process and log_process.poll() is None:
                    print("TERMINATING LOG PROCESS")
                    log_process.terminate()
                
                # Wait for streaming to complete
                if not log_streaming_complete.wait(timeout=10):
                    print("WARNING: Log streaming did not complete")
                
                break
        
        time.sleep(0.5)
    
    # Print what we captured
    print("\n=== CAPTURED LOGS ===")
    for log in captured_logs:
        print(log)
    
    print(f"\nTotal lines captured: {len(captured_logs)}")
    print(f"Found 'FINAL LINE': {'FINAL LINE' in ' '.join(captured_logs)}")
    print(f"Found pytest summary: {'===== 5 passed' in ' '.join(captured_logs)}")
    
    # Cleanup
    print("\nCleaning up...")
    subprocess.run(["kubectl", "delete", "job", "log-timing-test", "--wait=false"])

if __name__ == "__main__":
    test_log_timing()