#!/usr/bin/env python3
"""Test prefix/suffix workarounds for K8s API JSON issue"""

from kubernetes import client, config
import time

config.load_kube_config()
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

workarounds = [
    {
        "name": "no-workaround",
        "description": "Original problem - single json.dumps",
        "code": '''
import json
data = {"test": "broken", "value": 123}
print(json.dumps(data))
'''
    },
    {
        "name": "prefix-workaround",
        "description": "Add a prefix marker",
        "code": '''
import json
data = {"test": "prefix", "value": 123}
print("JSON_OUTPUT:" + json.dumps(data))
'''
    },
    {
        "name": "newline-before",
        "description": "Print empty line first",
        "code": '''
import json
data = {"test": "newline-before", "value": 123}
print("")  # Empty line
print(json.dumps(data))
'''
    },
    {
        "name": "comment-after",
        "description": "Print comment after JSON",
        "code": '''
import json
data = {"test": "comment-after", "value": 123}
print(json.dumps(data))
print("# End of output")
'''
    },
    {
        "name": "wrapped-markers",
        "description": "Wrap with start/end markers",
        "code": '''
import json
data = {"test": "wrapped", "value": 123}
print("---JSON_START---")
print(json.dumps(data))
print("---JSON_END---")
'''
    },
    {
        "name": "minimal-prefix",
        "description": "Minimal prefix - just a space",
        "code": '''
import json
data = {"test": "minimal", "value": 123}
print(" " + json.dumps(data))  # Just a leading space
'''
    }
]

print("Testing prefix/suffix workarounds for single-line JSON output...")

for workaround in workarounds:
    print(f"\n{'='*60}")
    print(f"Test: {workaround['description']}")
    
    job = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": workaround["name"],
            "namespace": "crucible"
        },
        "spec": {
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "test",
                        "image": "python:3.11-slim",
                        "command": ["python", "-u", "-c", workaround["code"]]
                    }]
                }
            }
        }
    }
    
    try:
        batch_v1.create_namespaced_job(namespace="crucible", body=job)
        time.sleep(3)
        
        pods = core_v1.list_namespaced_pod(
            namespace="crucible",
            label_selector=f"job-name={workaround['name']}"
        )
        
        if pods.items:
            logs = core_v1.read_namespaced_pod_log(
                name=pods.items[0].metadata.name,
                namespace="crucible"
            )
            
            print(f"\nRaw output:")
            print(repr(logs))
            
            # Check if JSON is preserved
            if '"test"' in logs:
                print("✅ JSON preserved with double quotes!")
                
                # Show how to extract it
                if "JSON_OUTPUT:" in logs:
                    json_part = logs.split("JSON_OUTPUT:")[1].strip()
                    print(f"Extracted JSON: {json_part}")
                elif "---JSON_START---" in logs:
                    json_part = logs.split("---JSON_START---")[1].split("---JSON_END---")[0].strip()
                    print(f"Extracted JSON: {json_part}")
                    
            elif "'test'" in logs:
                print("❌ Still converted to dict repr")
            else:
                print("🤔 Unexpected output format")
        
        batch_v1.delete_namespaced_job(name=workaround["name"], namespace="crucible")
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            batch_v1.delete_namespaced_job(name=workaround["name"], namespace="crucible")
        except:
            pass

print("\n\nSummary: Adding ANY additional output (prefix, suffix, or extra lines) prevents the dict repr conversion!")