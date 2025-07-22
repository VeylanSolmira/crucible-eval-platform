#!/usr/bin/env python3
"""Test creating a job via Kubernetes Python API to isolate the issue"""

from kubernetes import client, config
import time

# Load kubeconfig
config.load_kube_config()

# Create API clients
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

# Test different command formats
test_configs = [
    {
        "name": "test-api-job-1",
        "description": "Original format (like dispatcher)",
        "command": ["python", "-u", "-c", "import json\ndata = {'test': 'api', 'numbers': [1, 2, 3]}\nprint(json.dumps(data))"]
    },
    {
        "name": "test-api-job-2",
        "description": "Using /bin/sh -c",
        "command": ["/bin/sh", "-c", "python -c \"import json; data = {'test': 'api', 'numbers': [1, 2, 3]}; print(json.dumps(data))\""]
    },
    {
        "name": "test-api-job-3",
        "description": "Simple hello test",
        "command": ["python", "-c", "print('hello')"]
    },
    {
        "name": "test-api-job-4",
        "description": "Direct JSON without intermediate variable",
        "command": ["python", "-c", "import json; print(json.dumps({'test': 'direct', 'nums': [4, 5, 6]}))"]
    },
    {
        "name": "test-api-job-5",
        "description": "Write to file to bypass stdout",
        "command": ["python", "-c", "import json; open('/tmp/out.json','w').write(json.dumps({'test': 'file'})); print(open('/tmp/out.json').read())"]
    }
]

for config in test_configs:
    print(f"\n{'='*60}")
    print(f"Testing: {config['description']}")
    print(f"Command: {config['command']}")
    
    # Create job using API
    job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name=config["name"],
            namespace="crucible"
        ),
        spec=client.V1JobSpec(
            template=client.V1PodTemplateSpec(
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="test",
                            image="python:3.11-slim",
                            command=config["command"]
                        )
                    ]
                )
            )
        )
    )

    try:
        batch_v1.create_namespaced_job(namespace="crucible", body=job)
        
        # Wait for completion
        time.sleep(3)
        
        # Get logs
        pods = core_v1.list_namespaced_pod(
            namespace="crucible",
            label_selector=f"job-name={config['name']}"
        )
        
        if pods.items:
            pod_name = pods.items[0].metadata.name
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace="crucible"
            )
            print(f"\nOutput type: {type(logs)}")
            print(f"Output repr: {repr(logs)}")
            print(f"Output raw: {logs}")
            
            # Check if it's dict repr
            if logs.strip().startswith("{") and "'" in logs[:20]:
                print("⚠️  DICT REPR DETECTED (single quotes)")
            elif logs.strip().startswith("{") and '"' in logs[:20]:
                print("✅ PROPER JSON (double quotes)")
        else:
            print("No pods found")
        
        # Cleanup
        batch_v1.delete_namespaced_job(name=config["name"], namespace="crucible")
        
    except Exception as e:
        print(f"Error: {e}")
        # Try cleanup anyway
        try:
            batch_v1.delete_namespaced_job(name=config["name"], namespace="crucible")
        except:
            pass