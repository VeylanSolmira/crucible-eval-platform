#!/usr/bin/env python3
"""Test YAML-based job creation to see if it fixes dict repr issue"""

from kubernetes import client, config
import time
import yaml

# Load kubeconfig
config.load_kube_config()

# Create API clients
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

def test_yaml_job_creation():
    """Test creating a job from YAML dict instead of V1Job objects"""
    
    # User's Python code that should output JSON
    user_code = '''
import json

# Test with the same code that fails in dispatcher
libraries_to_test = ['numpy', 'pandas']
results = {"available": [], "unavailable": []}

for lib in libraries_to_test:
    try:
        __import__(lib)
        results["available"].append(lib)
    except ImportError:
        results["unavailable"].append(lib)

# This should produce proper JSON with double quotes
print(json.dumps(results, indent=2))
'''
    
    job_name = "test-yaml-job"
    
    # Create job as a dict (YAML approach)
    job_dict = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": "crucible",
            "labels": {
                "app": "evaluation",
                "test": "yaml-approach"
            }
        },
        "spec": {
            "ttlSecondsAfterFinished": 300,
            "backoffLimit": 0,
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "evaluation",
                        "image": "python:3.11-slim",
                        "imagePullPolicy": "IfNotPresent",
                        "command": ["python", "-u", "-c", user_code],
                        "env": [
                            {"name": "PYTHONUNBUFFERED", "value": "1"}
                        ],
                        "resources": {
                            "limits": {
                                "memory": "512Mi",
                                "cpu": "500m"
                            },
                            "requests": {
                                "memory": "128Mi",
                                "cpu": "100m"
                            }
                        }
                    }]
                }
            }
        }
    }
    
    print("Creating job using YAML dict approach...")
    print(f"Job name: {job_name}")
    
    try:
        # Create job from dict
        batch_v1.create_namespaced_job(namespace="crucible", body=job_dict)
        
        # Wait for completion
        print("Waiting for job to complete...")
        time.sleep(5)
        
        # Get logs
        pods = core_v1.list_namespaced_pod(
            namespace="crucible",
            label_selector=f"job-name={job_name}"
        )
        
        if pods.items:
            pod_name = pods.items[0].metadata.name
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace="crucible"
            )
            
            print("\n" + "="*60)
            print("YAML Dict Approach Results:")
            print("="*60)
            print(f"Output type: {type(logs)}")
            print(f"Output repr: {repr(logs)}")
            print(f"\nRaw output:")
            print(logs)
            print("="*60)
            
            # Check quote types
            if logs.strip().startswith('{'):
                if "'available'" in logs:
                    print("❌ STILL DICT REPR (single quotes)")
                elif '"available"' in logs:
                    print("✅ PROPER JSON (double quotes)!")
                else:
                    print("🤔 Unexpected format")
        else:
            print("No pods found")
        
        # Cleanup
        print("\nCleaning up...")
        batch_v1.delete_namespaced_job(name=job_name, namespace="crucible")
        
    except Exception as e:
        print(f"Error: {e}")
        # Try cleanup anyway
        try:
            batch_v1.delete_namespaced_job(name=job_name, namespace="crucible")
        except:
            pass

def test_yaml_with_args():
    """Test using args instead of command for code"""
    
    user_code = '''
import json
data = {"test": "args-approach", "numbers": [1, 2, 3]}
print(json.dumps(data))
'''
    
    job_name = "test-yaml-args"
    
    # Try with args instead of embedding in command
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
                        "command": ["python", "-u", "-c"],
                        "args": [user_code]  # Code in args instead of command
                    }]
                }
            }
        }
    }
    
    print("\n\nTesting with code in args field...")
    
    try:
        batch_v1.create_namespaced_job(namespace="crucible", body=job_dict)
        time.sleep(3)
        
        pods = core_v1.list_namespaced_pod(
            namespace="crucible",
            label_selector=f"job-name={job_name}"
        )
        
        if pods.items:
            pod_name = pods.items[0].metadata.name
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace="crucible"
            )
            
            print(f"Args approach output: {repr(logs)}")
            if '"test"' in logs:
                print("✅ Args approach produces proper JSON!")
            else:
                print("❌ Args approach still has dict repr")
        
        batch_v1.delete_namespaced_job(name=job_name, namespace="crucible")
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            batch_v1.delete_namespaced_job(name=job_name, namespace="crucible")
        except:
            pass

if __name__ == "__main__":
    print("Testing YAML-based job creation...")
    test_yaml_job_creation()
    test_yaml_with_args()