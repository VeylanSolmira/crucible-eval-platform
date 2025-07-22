#!/usr/bin/env python3
"""Test Kubernetes log retrieval to see if it matches dispatcher behavior"""

from kubernetes import client, config

# Load kubeconfig
config.load_kube_config()

# Create API client
core_v1 = client.CoreV1Api()

# Get logs from our test job
namespace = "crucible"
job_name = "test-exact-code"

# Find pod for the job
pods = core_v1.list_namespaced_pod(
    namespace=namespace,
    label_selector=f"job-name={job_name}"
)

if not pods.items:
    print("No pods found")
    exit(1)

pod_name = pods.items[0].metadata.name
print(f"Getting logs from pod: {pod_name}")

# Get logs exactly like dispatcher does
logs = core_v1.read_namespaced_pod_log(
    name=pod_name,
    namespace=namespace,
    tail_lines=100
)

print(f"Logs type: {type(logs)}")
print(f"First 200 chars: {repr(logs[:200])}")
print(f"Has single quotes: {'\\'' in logs[:50]}")
print("\nFull logs:")
print(logs)