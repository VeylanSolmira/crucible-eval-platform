#!/usr/bin/env python3
"""Test hypothesis: single json.dumps output gets converted to dict repr"""

from kubernetes import client, config
import time

config.load_kube_config()
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

tests = [
    {
        "name": "single-json",
        "code": 'import json; print(json.dumps({"test": "single"}))'
    },
    {
        "name": "json-with-newline",
        "code": 'import json; print(json.dumps({"test": "newline"}) + "\\n")'
    },
    {
        "name": "json-with-prefix",
        "code": 'import json; print("OUTPUT:" + json.dumps({"test": "prefix"}))'
    },
    {
        "name": "json-with-empty-first",
        "code": 'import json; print(""); print(json.dumps({"test": "empty-first"}))'
    },
    {
        "name": "json-no-print",
        "code": 'import json; json.dumps({"test": "no-print"})'  # Last expression
    },
    {
        "name": "json-sys-stdout",
        "code": 'import json, sys; sys.stdout.write(json.dumps({"test": "stdout"}))'
    },
    {
        "name": "json-with-flush",
        "code": 'import json, sys; print(json.dumps({"test": "flush"})); sys.stdout.flush()'
    }
]

for test in tests:
    print(f"\nTest: {test['name']}")
    print(f"Code: {test['code']}")
    
    job = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": test["name"], "namespace": "crucible"},
        "spec": {
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "test",
                        "image": "python:3.11-slim",
                        "command": ["python", "-u", "-c", test["code"]]
                    }]
                }
            }
        }
    }
    
    try:
        batch_v1.create_namespaced_job(namespace="crucible", body=job)
        time.sleep(2)
        
        pods = core_v1.list_namespaced_pod(
            namespace="crucible",
            label_selector=f"job-name={test['name']}"
        )
        
        if pods.items:
            logs = core_v1.read_namespaced_pod_log(
                name=pods.items[0].metadata.name,
                namespace="crucible"
            )
            print(f"Output: {repr(logs)}")
            
            if logs and '"test"' in logs:
                print("✅ JSON preserved")
            elif logs and "'test'" in logs:
                print("❌ Converted to dict repr")
            else:
                print("🤔 No output or unexpected format")
        
        batch_v1.delete_namespaced_job(name=test["name"], namespace="crucible")
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            batch_v1.delete_namespaced_job(name=test["name"], namespace="crucible")
        except:
            pass