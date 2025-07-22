# Kubernetes Timeout and Grace Period Security Considerations

## Overview

When implementing timeout enforcement for code evaluation in Kubernetes, there's a critical security tradeoff between graceful shutdown and attack window duration. This document outlines best practices for secure timeout handling in high-risk evaluation scenarios.

## How Kubernetes Timeout Enforcement Works

When `activeDeadlineSeconds` is exceeded:
1. Kubernetes sends SIGTERM to all pod containers
2. Containers have `terminationGracePeriodSeconds` to shut down gracefully
3. After grace period expires, Kubernetes sends SIGKILL
4. Job is marked as failed with DeadlineExceeded

## Security Considerations for Forced Termination

### Risks of Too-Short Grace Period (1-2s)
```python
# Dangerous scenarios when abruptly killed:
1. File operations mid-write → corrupted files
2. Database transactions → inconsistent state  
3. Resource cleanup skipped → leaked secrets in /tmp
4. Audit logs incomplete → lost security events
5. Child processes orphaned → potential escape
```

### Risks of Too-Long Grace Period (30-60s)
```python
# Extended attack window allows:
- Exfiltrate data slowly to evade detection
- Establish persistent backdoors
- Fork bomb has more time to spawn
- Cryptocurrency mining continues
- Network scanning/lateral movement
```

## Recommended Approach: Defense in Depth

### 1. Handle Signals Properly (Primary Defense)
```python
import signal
import sys
import threading

class GracefulKiller:
    kill_now = False
    
    def __init__(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        self.kill_now = True
        # Trigger cleanup
        cleanup_thread = threading.Thread(target=self._emergency_cleanup)
        cleanup_thread.start()
    
    def _emergency_cleanup(self):
        # Kill subprocesses
        # Flush logs
        # Clean sensitive files
        # Close connections
        time.sleep(0.5)  # Quick cleanup
        sys.exit(1)
```

### 2. Implement Application-Level Timeouts
```python
import subprocess
import tempfile
from contextlib import contextmanager

@contextmanager
def secure_evaluation_context(timeout):
    temp_dir = tempfile.mkdtemp()
    proc = None
    
    try:
        # Start evaluation subprocess with timeout
        proc = subprocess.Popen(
            ["python", "untrusted_code.py"],
            cwd=temp_dir,
            preexec_fn=os.setsid,  # New process group
            timeout=timeout
        )
        yield proc
        
    finally:
        # Ensure cleanup even if killed
        if proc and proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(0.5)
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        
        # Secure cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
```

### 3. Risk-Based Grace Periods
```yaml
# Low risk evaluation (trusted source)
spec:
  terminationGracePeriodSeconds: 30

# High risk evaluation (untrusted code)
spec:
  terminationGracePeriodSeconds: 5
  
# Critical risk (known malicious patterns)
spec:
  terminationGracePeriodSeconds: 2
```

### 4. Progressive Termination Strategy
```python
class SecureExecutor:
    def __init__(self, risk_level="high"):
        self.risk_level = risk_level
        self.grace_periods = {
            "low": (10, 20),     # (soft_limit, hard_limit)
            "medium": (5, 10),
            "high": (2, 5),
            "critical": (1, 2)
        }
    
    def handle_timeout(self):
        soft, hard = self.grace_periods[self.risk_level]
        
        # Phase 1: Polite termination request
        logger.warning(f"Timeout reached, requesting termination")
        self.send_termination_signal()
        
        # Phase 2: Aggressive but clean
        time.sleep(soft)
        if self.is_running():
            logger.warning(f"Process didn't stop, escalating")
            self.kill_network_access()
            self.revoke_file_permissions()
            
        # Phase 3: Forced termination
        time.sleep(hard - soft)
        if self.is_running():
            logger.error(f"Force killing process")
            self.force_kill()
```

### 5. Runtime-Adaptive Grace Period
```python
def calculate_grace_period(evaluation_context):
    """Dynamically determine grace period based on behavior"""
    base_grace = 10
    
    # Reduce if suspicious behavior detected
    if evaluation_context.network_attempts > 0:
        base_grace -= 5
    if evaluation_context.subprocess_count > 2:
        base_grace -= 3
    if evaluation_context.memory_growth_rate > 100:  # MB/s
        base_grace -= 2
        
    return max(1, base_grace)  # Never less than 1 second
```

## Security Monitoring During Grace Period

```python
class GracePeriodMonitor:
    def __init__(self, pid):
        self.pid = pid
        self.start_termination = time.time()
        
    def monitor_termination(self):
        """Watch for malicious behavior during shutdown"""
        while process_exists(self.pid):
            # Check for suspicious activity
            if self.detect_data_exfiltration():
                self.immediate_kill("Data exfiltration attempted during shutdown")
                
            if self.detect_fork_bomb():
                self.immediate_kill("Fork bomb detected during shutdown")
                
            if time.time() - self.start_termination > 2:
                # Log what the process is doing
                self.audit_log_activity()
                
            time.sleep(0.1)
    
    def detect_data_exfiltration(self):
        # Monitor network traffic
        bytes_sent = get_network_bytes(self.pid)
        return bytes_sent > 1_000_000  # 1MB threshold
```

## Security Audit Logging

```python
import logging
import json
from datetime import datetime

class SecurityAuditLogger:
    def __init__(self, job_id):
        self.job_id = job_id
        self.start_time = datetime.utcnow()
        
    def log_termination(self, reason):
        audit_entry = {
            "event": "evaluation_terminated",
            "job_id": self.job_id,
            "reason": reason,
            "duration": (datetime.utcnow() - self.start_time).seconds,
            "cleanup_status": "attempted"
        }
        # Ensure this gets written even during shutdown
        with open('/var/log/security-audit.json', 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
            f.flush()
            os.fsync(f.fileno())
```

## Best Practice: Context-Aware Termination

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: high-risk-evaluation
  labels:
    risk-level: high
spec:
  activeDeadlineSeconds: 60
  template:
    metadata:
      labels:
        risk-level: high
    spec:
      # Short grace for high-risk
      terminationGracePeriodSeconds: 3
      
      # Network policies to limit damage
      # Resource limits to prevent fork bombs
      # Security contexts to limit capabilities
      
      initContainers:
      - name: setup-monitoring
        # Pre-configure aggressive monitoring
        
      containers:
      - name: executor
        env:
        - name: INTERNAL_TIMEOUT
          value: "55"  # 5s before K8s deadline
        - name: SHUTDOWN_MONITORING
          value: "aggressive"
```

## Recommended Configuration by Risk Level

### High-Risk Evaluations
- **Application timeout**: 90 seconds
- **Kubernetes deadline**: 120 seconds  
- **Grace period**: 3-5 seconds
- **Signal handling**: Required
- **Audit logging**: Comprehensive

### Medium-Risk Evaluations
- **Application timeout**: 180 seconds
- **Kubernetes deadline**: 200 seconds
- **Grace period**: 10 seconds
- **Signal handling**: Recommended
- **Audit logging**: Standard

### Low-Risk Evaluations
- **Application timeout**: 300 seconds
- **Kubernetes deadline**: 330 seconds
- **Grace period**: 30 seconds
- **Signal handling**: Optional
- **Audit logging**: Basic

## Nuclear Option for Active Attacks

In extreme cases where an active attack is detected:
```bash
# Force immediate termination with no grace period
kubectl delete pod $POD --grace-period=0 --force
```

## Key Insights

1. **Grace period is part of your security posture** - Too long creates attack windows, too short risks incomplete cleanup
2. **Use defense in depth** - Don't rely solely on Kubernetes timeouts
3. **Monitor during shutdown** - Malicious code may attempt to exploit the grace period
4. **Adapt to risk level** - High-risk evaluations need shorter grace periods
5. **Log everything** - Audit trails are critical for security analysis

## Current Implementation Status

As of July 16, 2025:
- ✅ Kubernetes activeDeadlineSeconds is properly configured
- ✅ terminationGracePeriodSeconds reduced to 1 second for evaluations
- ❌ Python signal handling not yet implemented
- ❌ Risk-based grace periods not yet implemented
- ❌ Grace period monitoring not yet implemented

## References

- [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Python Signal Handling](https://docs.python.org/3/library/signal.html)
- [Container Security Best Practices](https://kubernetes.io/docs/concepts/security/)