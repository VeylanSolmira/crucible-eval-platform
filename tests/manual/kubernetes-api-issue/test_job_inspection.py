#!/usr/bin/env python3
"""Inspect what actually gets created in Kubernetes"""

from kubernetes import client, config
import yaml
import json

# Load kubeconfig
config.load_kube_config()

# Create API clients
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

# Simple test code
test_code = '''import json
print(json.dumps({"test": "value"}))'''

# Create job using YAML approach
job_name = "test-inspect-job"
job_dict = {
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {
        "name": job_name,
        "namespace": "crucible"
    },
    "spec": {
        "template": {
            "spec": {
                "restartPolicy": "Never",
                "containers": [{
                    "name": "test",
                    "image": "python:3.11-slim",
                    "command": ["python", "-u", "-c", test_code]
                }]
            }
        }
    }
}

print("Creating job and inspecting what K8s actually stores...")

try:
    # Create the job
    created_job = batch_v1.create_namespaced_job(namespace="crucible", body=job_dict)
    
    # Get the job back from K8s to see what it looks like
    retrieved_job = batch_v1.read_namespaced_job(name=job_name, namespace="crucible")
    
    # Extract the command from the container spec
    container = retrieved_job.spec.template.spec.containers[0]
    print("\nContainer command from K8s:")
    print(f"Type: {type(container.command)}")
    print(f"Command: {container.command}")
    print(f"Command[3] (code): {repr(container.command[3])}")
    
    # Export as YAML to see exact format
    print("\nJob YAML as stored in K8s:")
    job_export = batch_v1.read_namespaced_job(
        name=job_name, 
        namespace="crucible",
        _preload_content=False
    )
    job_data = json.loads(job_export.data)
    print(yaml.dump(job_data['spec']['template']['spec']['containers'][0], default_flow_style=False))
    
    # Check if the issue is in how Python is invoked
    print("\nTesting direct command execution in pod...")
    
    # Create a pod that runs the command and also shows us what it received
    debug_pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "debug-command-pod",
            "namespace": "crucible"
        },
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "debug",
                "image": "python:3.11-slim",
                "command": ["/bin/sh", "-c", """
echo "=== Received command ==="
echo "$@"
echo "=== Python version ==="
python --version
echo "=== Running: python -u -c 'import json; print(json.dumps({\"test\": \"direct\"}))' ==="
python -u -c 'import json; print(json.dumps({"test": "direct"}))'
echo "=== Running via variable ==="
CODE='import json
print(json.dumps({"test": "variable"}))'
python -u -c "$CODE"
"""]
            }]
        }
    }
    
    core_v1.create_namespaced_pod(namespace="crucible", body=debug_pod)
    
    # Wait and get logs
    import time
    time.sleep(3)
    
    debug_logs = core_v1.read_namespaced_pod_log(
        name="debug-command-pod",
        namespace="crucible"
    )
    print("\nDebug pod output:")
    print(debug_logs)
    
    # Cleanup
    batch_v1.delete_namespaced_job(name=job_name, namespace="crucible")
    core_v1.delete_namespaced_pod(name="debug-command-pod", namespace="crucible")
    
except Exception as e:
    print(f"Error: {e}")
    # Cleanup
    try:
        batch_v1.delete_namespaced_job(name=job_name, namespace="crucible")
        core_v1.delete_namespaced_pod(name="debug-command-pod", namespace="crucible")
    except:
        pass