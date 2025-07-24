#!/usr/bin/env python3
"""
Lightweight cleanup controller for failed pods in Kubernetes.

Watches for pod state changes and immediately deletes failed pods
to free up resources, unless they have a debug annotation.
"""

from kubernetes import client, config, watch
import time
import os
import logging

# Kubernetes pod phases
# https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
TERMINAL_POD_PHASES = {'Failed', 'Succeeded'}
NON_TERMINAL_POD_PHASES = {'Pending', 'Running', 'Unknown'}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cleanup-controller')

# Configuration
NAMESPACE = os.environ.get('CLEANUP_NAMESPACE', 'crucible')
WATCH_ALL_NAMESPACES = os.environ.get('WATCH_ALL_NAMESPACES', 'false').lower() == 'true'
DELETE_GRACE_PERIOD = int(os.environ.get('DELETE_GRACE_PERIOD', '0'))
PRESERVE_DEBUG_PODS = os.environ.get('PRESERVE_DEBUG_PODS', 'true').lower() == 'true'

def load_k8s_config():
    """Load Kubernetes configuration."""
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster configuration")
    except:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig")

def should_delete_pod(pod):
    """Determine if a pod should be deleted."""
    # Skip if has debug annotation
    if PRESERVE_DEBUG_PODS:
        annotations = pod.metadata.annotations or {}
        if annotations.get('debug') == 'true' or annotations.get('preserve') == 'true':
            logger.debug(f"Skipping {pod.metadata.name} - has preserve annotation")
            return False
    
    # Only delete pods in explicitly terminal states
    if pod.status.phase not in TERMINAL_POD_PHASES:
        return False
    
    # For succeeded pods, only delete if they're evaluation pods
    if pod.status.phase == 'Succeeded':
        labels = pod.metadata.labels or {}
        if labels.get('app') != 'evaluation':
            return False
    
    return True

def cleanup_failed_pods():
    """Watch for pod events and clean up failed pods."""
    v1 = client.CoreV1Api()
    w = watch.Watch()
    
    # Determine what to watch
    if WATCH_ALL_NAMESPACES:
        logger.info("Watching pods in all namespaces")
        stream = w.stream(v1.list_pod_for_all_namespaces)
    else:
        logger.info(f"Watching pods in namespace: {NAMESPACE}")
        stream = w.stream(v1.list_namespaced_pod, namespace=NAMESPACE)
    
    for event in stream:
        try:
            pod = event['object']
            event_type = event['type']
            
            # Only process ADDED or MODIFIED events
            if event_type not in ['ADDED', 'MODIFIED']:
                continue
            
            # Check if pod should be deleted
            if should_delete_pod(pod):
                pod_name = pod.metadata.name
                pod_namespace = pod.metadata.namespace
                pod_phase = pod.status.phase
                
                # Get pod age
                if pod.metadata.creation_timestamp:
                    age_seconds = time.time() - pod.metadata.creation_timestamp.timestamp()
                    age_minutes = age_seconds / 60
                    age_str = f" (age: {age_minutes:.1f}m)"
                    
                    # Skip pods younger than 5 seconds to allow log collection
                    if age_seconds < 10:
                        continue
                else:
                    age_str = ""
                
                logger.info(f"Deleting {pod_phase} pod: {pod_namespace}/{pod_name}{age_str}")
                
                try:
                    v1.delete_namespaced_pod(
                        name=pod_name,
                        namespace=pod_namespace,
                        grace_period_seconds=DELETE_GRACE_PERIOD
                    )
                    logger.info(f"Successfully deleted pod: {pod_namespace}/{pod_name}")
                except client.exceptions.ApiException as e:
                    if e.status == 404:
                        logger.debug(f"Pod already deleted: {pod_namespace}/{pod_name}")
                    else:
                        logger.error(f"Error deleting pod {pod_namespace}/{pod_name}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error deleting pod {pod_namespace}/{pod_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing event: {e}")

def main():
    """Main controller loop."""
    logger.info("Starting cleanup controller")
    logger.info(f"Configuration:")
    logger.info(f"  NAMESPACE: {NAMESPACE}")
    logger.info(f"  WATCH_ALL_NAMESPACES: {WATCH_ALL_NAMESPACES}")
    logger.info(f"  DELETE_GRACE_PERIOD: {DELETE_GRACE_PERIOD}")
    logger.info(f"  PRESERVE_DEBUG_PODS: {PRESERVE_DEBUG_PODS}")
    
    load_k8s_config()
    
    while True:
        try:
            cleanup_failed_pods()
        except Exception as e:
            logger.error(f"Watch stream failed: {e}")
            logger.info("Restarting watch in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()