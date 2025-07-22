#!/usr/bin/env python3
"""Test specific cases to isolate the dict repr issue"""

from kubernetes import client, config
import time

# Load kubeconfig
config.load_kube_config()

# Create API clients
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

# Test different Python code formats
test_configs = [
    {
        "name": "test-dict-literal",
        "description": "Dict literal in code",
        "command": ["python", "-c", "d = {'test': 'value'}; print(d)"]
    },
    {
        "name": "test-json-from-dict",
        "description": "JSON from dict literal",
        "command": ["python", "-c", "import json; d = {'test': 'value'}; print(json.dumps(d))"]
    },
    {
        "name": "test-json-from-dict-constructor",
        "description": "JSON from dict() constructor",
        "command": ["python", "-c", "import json; d = dict(test='value'); print(json.dumps(d))"]
    },
    {
        "name": "test-escaped-quotes",
        "description": "Escaped double quotes in dict",
        "command": ["python", "-c", 'import json; d = {"test": "value"}; print(json.dumps(d))']
    },
    {
        "name": "test-print-literal-json",
        "description": "Print literal JSON string",
        "command": ["python", "-c", 'print(\'{"test": "value"}\')']
    },
    {
        "name": "test-json-loads-dumps",
        "description": "Parse then dump JSON",
        "command": ["python", "-c", "import json; s = '{\"test\": \"value\"}'; d = json.loads(s); print(json.dumps(d))"]
    }
]

for config_item in test_configs:
    print(f"\n{'='*60}")
    print(f"Testing: {config_item['description']}")
    print(f"Command: {config_item['command']}")
    
    # Create job
    job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name=config_item["name"],
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
                            command=config_item["command"]
                        )
                    ]
                )
            )
        )
    )
    
    try:
        batch_v1.create_namespaced_job(namespace="crucible", body=job)
        
        # Wait for completion
        time.sleep(2)
        
        # Get logs
        pods = core_v1.list_namespaced_pod(
            namespace="crucible",
            label_selector=f"job-name={config_item['name']}"
        )
        
        if pods.items:
            pod_name = pods.items[0].metadata.name
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace="crucible"
            )
            print(f"Output: {repr(logs)}")
            
            # Check result
            if "'test'" in logs:
                print("❌ Single quotes detected")
            elif '"test"' in logs:
                print("✅ Double quotes detected")
            else:
                print("🤔 Neither quote type detected")
        
        # Cleanup
        batch_v1.delete_namespaced_job(name=config_item["name"], namespace="crucible")
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            batch_v1.delete_namespaced_job(name=config_item["name"], namespace="crucible")
        except:
            pass