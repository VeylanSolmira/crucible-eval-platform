#!/usr/bin/env python3
"""Test different ways Python might be invoked in containers"""

from kubernetes import client, config
import time

config.load_kube_config()
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

test_configs = [
    {
        "name": "test-direct-python",
        "description": "Direct Python command (like K8s API)",
        "command": ["python", "-u", "-c", 'import json; print(json.dumps({"test": "direct"}))']
    },
    {
        "name": "test-shell-wrapper", 
        "description": "Shell wrapper (like kubectl apply)",
        "command": ["sh", "-c", 'python -u -c \'import json; print(json.dumps({"test": "shell"}))\'']
    },
    {
        "name": "test-exec-form",
        "description": "Exec form with explicit interpreter",
        "command": ["/usr/local/bin/python", "-u", "-c", 'import json; print(json.dumps({"test": "exec"}))']
    },
    {
        "name": "test-env-python",
        "description": "Using env to find python",
        "command": ["/usr/bin/env", "python", "-u", "-c", 'import json; print(json.dumps({"test": "env"}))']
    }
]

for config in test_configs:
    print(f"\n{'='*60}")
    print(f"Testing: {config['description']}")
    
    job_dict = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": config["name"],
            "namespace": "crucible"
        },
        "spec": {
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "test",
                        "image": "python:3.11-slim",
                        "command": config["command"]
                    }]
                }
            }
        }
    }
    
    try:
        batch_v1.create_namespaced_job(namespace="crucible", body=job_dict)
        time.sleep(2)
        
        pods = core_v1.list_namespaced_pod(
            namespace="crucible",
            label_selector=f"job-name={config['name']}"
        )
        
        if pods.items:
            logs = core_v1.read_namespaced_pod_log(
                name=pods.items[0].metadata.name,
                namespace="crucible"
            )
            print(f"Output: {repr(logs)}")
            
            if '"test"' in logs:
                print("✅ Produces proper JSON")
            elif "'test'" in logs:
                print("❌ Produces dict repr")
        
        batch_v1.delete_namespaced_job(name=config["name"], namespace="crucible")
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            batch_v1.delete_namespaced_job(name=config["name"], namespace="crucible")
        except:
            pass

# Now test if the issue is specific to json.dumps
print(f"\n{'='*60}")
print("Testing if issue is specific to json.dumps...")

test_job = {
    "apiVersion": "batch/v1",
    "kind": "Job", 
    "metadata": {
        "name": "test-json-behavior",
        "namespace": "crucible"
    },
    "spec": {
        "template": {
            "spec": {
                "restartPolicy": "Never",
                "containers": [{
                    "name": "test",
                    "image": "python:3.11-slim",
                    "command": ["python", "-u", "-c", """
import json
import sys

# Test different outputs
d = {"test": "value", "number": 123}

print("=== Direct dict print ===")
print(d)

print("\\n=== json.dumps output ===")
print(json.dumps(d))

print("\\n=== json.dumps to variable ===")
s = json.dumps(d)
print(s)

print("\\n=== Type of json.dumps ===")
print(type(json.dumps(d)))

print("\\n=== Repr of json.dumps ===") 
print(repr(json.dumps(d)))

print("\\n=== Write to stderr ===")
sys.stderr.write(json.dumps(d) + "\\n")
"""]
                }]
            }
        }
    }
}

try:
    batch_v1.create_namespaced_job(namespace="crucible", body=test_job)
    time.sleep(3)
    
    pods = core_v1.list_namespaced_pod(
        namespace="crucible",
        label_selector="job-name=test-json-behavior"
    )
    
    if pods.items:
        logs = core_v1.read_namespaced_pod_log(
            name=pods.items[0].metadata.name,
            namespace="crucible"
        )
        print("\nDetailed output:")
        print(logs)
    
    batch_v1.delete_namespaced_job(name="test-json-behavior", namespace="crucible")
    
except Exception as e:
    print(f"Error: {e}")
    try:
        batch_v1.delete_namespaced_job(name="test-json-behavior", namespace="crucible")
    except:
        pass