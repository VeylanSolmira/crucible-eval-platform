"""
Cluster resource monitoring utilities.

Provides comprehensive resource usage reporting including CPU, memory, and pod capacity.
"""

import subprocess
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_cluster_resources(namespace: str = "dev", verbose: bool = False) -> Dict:
    """
    Get comprehensive cluster resource usage information.
    
    Returns dict with:
    - nodes: List of node information including pod capacity
    - resource_quota: ResourceQuota usage if configured
    - pods: Pod count by status
    - resource_pressure: Any resource constraints detected
    """
    resources = {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": [],
        "resource_quota": {},
        "pods": {},
        "resource_pressure": [],
        "summary": {}
    }
    
    # Initialize totals outside try block to avoid UnboundLocalError
    total_pods_capacity = 0
    total_pods_used = 0
    total_cpu_capacity = 0
    total_cpu_allocatable = 0
    total_cpu_requests = 0
    total_memory_capacity = 0
    total_memory_allocatable = 0
    total_memory_requests = 0
    
    # Get node information with metrics
    try:
        # First get node basic info
        result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json"],
            capture_output=True, text=True, check=True
        )
        nodes_data = json.loads(result.stdout)
        
        # Try to get actual usage metrics
        metrics_available = False
        node_metrics = {}
        try:
            metrics_result = subprocess.run(
                ["kubectl", "top", "nodes", "--no-headers"],
                capture_output=True, text=True, check=True
            )
            metrics_available = True
            
            # Parse metrics output
            for line in metrics_result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 5:
                        node_name = parts[0]
                        cpu_usage = parse_cpu_to_millicores(parts[1])
                        cpu_percent = int(parts[2].rstrip('%'))
                        memory_usage = parse_memory_to_mb(parts[3])
                        memory_percent = int(parts[4].rstrip('%'))
                        
                        node_metrics[node_name] = {
                            "cpu_usage": cpu_usage,
                            "cpu_percent": cpu_percent,
                            "memory_usage": memory_usage,
                            "memory_percent": memory_percent
                        }
        except subprocess.CalledProcessError:
            logger.debug("Metrics server not available, using requests only")
        
        for node in nodes_data.get("items", []):
            node_name = node["metadata"]["name"]
            
            # Get capacity and allocatable resources
            capacity = node["status"]["capacity"]
            allocatable = node["status"]["allocatable"]
            
            # Get pod count on this node
            pods_result = subprocess.run(
                ["kubectl", "get", "pods", "--all-namespaces", 
                 "--field-selector", f"spec.nodeName={node_name}",
                 "-o", "json"],
                capture_output=True, text=True
            )
            
            if pods_result.returncode == 0:
                pods_data = json.loads(pods_result.stdout)
                all_pods = pods_data.get("items", [])
                
                # Count non-terminated pods (these consume pod slots)
                non_terminated = [p for p in all_pods if p["status"]["phase"] not in ["Succeeded", "Failed"]]
                running_pods = [p for p in all_pods if p["status"]["phase"] == "Running"]
                pending_pods = [p for p in all_pods if p["status"]["phase"] == "Pending"]
                
                # Calculate resource requests on this node
                cpu_requests = 0
                memory_requests = 0
                
                for pod in non_terminated:
                    for container in pod["spec"].get("containers", []):
                        requests = container.get("resources", {}).get("requests", {})
                        if "cpu" in requests:
                            cpu_requests += parse_cpu_to_millicores(requests["cpu"])
                        if "memory" in requests:
                            memory_requests += parse_memory_to_mb(requests["memory"])
            else:
                non_terminated = []
                running_pods = []
                pending_pods = []
                cpu_requests = 0
                memory_requests = 0
            
            # Get actual usage if metrics are available
            actual_cpu_usage = None
            actual_memory_usage = None
            if node_name in node_metrics:
                actual_cpu_usage = node_metrics[node_name]["cpu_usage"]
                actual_memory_usage = node_metrics[node_name]["memory_usage"]
            
            # Node information
            node_info = {
                "name": node_name,
                "instance_type": node["metadata"]["labels"].get("node.kubernetes.io/instance-type", "unknown"),
                "pods": {
                    "capacity": int(capacity.get("pods", 0)),
                    "allocatable": int(allocatable.get("pods", 0)),
                    "used": len(non_terminated),
                    "available": int(allocatable.get("pods", 0)) - len(non_terminated),
                    "running": len(running_pods),
                    "pending": len(pending_pods),
                    "utilization": f"{len(non_terminated) / int(allocatable.get('pods', 1)) * 100:.1f}%"
                },
                "cpu": {
                    "capacity": capacity.get("cpu", "0"),
                    "allocatable": allocatable.get("cpu", "0"),
                    "requests": f"{cpu_requests}m",
                    "usage": f"{actual_cpu_usage}m" if actual_cpu_usage is not None else "N/A",
                    "available": parse_cpu_to_millicores(allocatable.get("cpu", "0")) - cpu_requests,
                    "request_utilization": f"{cpu_requests / parse_cpu_to_millicores(allocatable.get('cpu', '1')) * 100:.1f}%",
                    "actual_utilization": f"{actual_cpu_usage / parse_cpu_to_millicores(allocatable.get('cpu', '1')) * 100:.1f}%" if actual_cpu_usage is not None else "N/A"
                },
                "memory": {
                    "capacity": capacity.get("memory", "0"),
                    "allocatable": allocatable.get("memory", "0"),
                    "requests": f"{memory_requests}Mi",
                    "usage": f"{actual_memory_usage}Mi" if actual_memory_usage is not None else "N/A",
                    "available": parse_memory_to_mb(allocatable.get("memory", "0")) - memory_requests,
                    "request_utilization": f"{memory_requests / parse_memory_to_mb(allocatable.get('memory', '1Mi')) * 100:.1f}%",
                    "actual_utilization": f"{actual_memory_usage / parse_memory_to_mb(allocatable.get('memory', '1Mi')) * 100:.1f}%" if actual_memory_usage is not None else "N/A"
                }
            }
            
            resources["nodes"].append(node_info)
            
            # Update totals
            total_pods_capacity += int(allocatable.get("pods", 0))
            total_pods_used += len(non_terminated)
            total_cpu_capacity += parse_cpu_to_millicores(capacity.get("cpu", "0"))
            total_cpu_allocatable += parse_cpu_to_millicores(allocatable.get("cpu", "0"))
            total_cpu_requests += cpu_requests
            total_memory_capacity += parse_memory_to_mb(capacity.get("memory", "0"))
            total_memory_allocatable += parse_memory_to_mb(allocatable.get("memory", "0"))
            total_memory_requests += memory_requests
            
            # Check for resource pressure
            pod_utilization = len(non_terminated) / int(allocatable.get("pods", 1))
            if pod_utilization > 0.9:
                resources["resource_pressure"].append({
                    "type": "pod_limit",
                    "node": node_name,
                    "message": f"Pod capacity near limit: {len(non_terminated)}/{allocatable.get('pods')} ({pod_utilization*100:.0f}%)"
                })
                
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get node information: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse node data: {e}")
    
    # Get ResourceQuota information
    try:
        result = subprocess.run(
            ["kubectl", "get", "resourcequota", "-n", namespace, "-o", "json"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            quota_data = json.loads(result.stdout)
            for quota in quota_data.get("items", []):
                quota_name = quota["metadata"]["name"]
                hard = quota["status"].get("hard", {})
                used = quota["status"].get("used", {})
                
                resources["resource_quota"][quota_name] = {
                    "limits.cpu": {
                        "hard": hard.get("limits.cpu", "0"),
                        "used": used.get("limits.cpu", "0"),
                        "available": parse_cpu_to_millicores(hard.get("limits.cpu", "0")) - parse_cpu_to_millicores(used.get("limits.cpu", "0")),
                        "utilization": f"{parse_cpu_to_millicores(used.get('limits.cpu', '0')) / parse_cpu_to_millicores(hard.get('limits.cpu', '1')) * 100:.1f}%"
                    },
                    "limits.memory": {
                        "hard": hard.get("limits.memory", "0"),
                        "used": used.get("limits.memory", "0"),
                        "available": parse_memory_to_mb(hard.get("limits.memory", "0")) - parse_memory_to_mb(used.get("limits.memory", "0")),
                        "utilization": f"{parse_memory_to_mb(used.get('limits.memory', '0')) / parse_memory_to_mb(hard.get('limits.memory', '1Mi')) * 100:.1f}%"
                    }
                }
                
                # Check for quota pressure
                if "limits.memory" in hard:
                    mem_utilization = parse_memory_to_mb(used.get("limits.memory", "0")) / parse_memory_to_mb(hard.get("limits.memory", "1Mi"))
                    if mem_utilization > 0.9:
                        resources["resource_pressure"].append({
                            "type": "memory_quota",
                            "quota": quota_name,
                            "message": f"Memory quota near limit: {used.get('limits.memory')}/{hard.get('limits.memory')} ({mem_utilization*100:.0f}%)"
                        })
                        
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.debug(f"No ResourceQuota found or error: {e}")
    
    # Get pod counts by status
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True, text=True, check=True
        )
        pods_data = json.loads(result.stdout)
        
        status_counts = {}
        evaluation_pods = {"running": 0, "pending": 0, "completed": 0, "failed": 0}
        
        for pod in pods_data.get("items", []):
            phase = pod["status"]["phase"]
            status_counts[phase] = status_counts.get(phase, 0) + 1
            
            # Count evaluation pods specifically
            if pod["metadata"]["labels"].get("app") == "evaluation":
                if phase == "Running":
                    evaluation_pods["running"] += 1
                elif phase == "Pending":
                    evaluation_pods["pending"] += 1
                elif phase == "Succeeded":
                    evaluation_pods["completed"] += 1
                elif phase == "Failed":
                    evaluation_pods["failed"] += 1
        
        resources["pods"] = {
            "all": status_counts,
            "evaluations": evaluation_pods
        }
        
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Failed to get pod information: {e}")
    
    # Create summary
    resources["summary"] = {
        "cluster_totals": {
            "pods": {
                "capacity": total_pods_capacity,
                "used": total_pods_used,
                "available": total_pods_capacity - total_pods_used,
                "utilization": f"{total_pods_used / max(total_pods_capacity, 1) * 100:.1f}%"
            },
            "cpu": {
                "capacity": f"{total_cpu_capacity}m",
                "allocatable": f"{total_cpu_allocatable}m",
                "requests": f"{total_cpu_requests}m",
                "available": f"{total_cpu_allocatable - total_cpu_requests}m",
                "utilization": f"{total_cpu_requests / max(total_cpu_allocatable, 1) * 100:.1f}%"
            },
            "memory": {
                "capacity": f"{total_memory_capacity}Mi",
                "allocatable": f"{total_memory_allocatable}Mi",
                "requests": f"{total_memory_requests}Mi",
                "available": f"{total_memory_allocatable - total_memory_requests}Mi",
                "utilization": f"{total_memory_requests / max(total_memory_allocatable, 1) * 100:.1f}%"
            }
        },
        "resource_pressure": len(resources["resource_pressure"]) > 0,
        "pressure_points": resources["resource_pressure"]
    }
    
    return resources


def parse_cpu_to_millicores(cpu_str: str) -> int:
    """Parse CPU string to millicores."""
    if not cpu_str:
        return 0
    
    cpu_str = str(cpu_str)
    if cpu_str.endswith('m'):
        return int(cpu_str[:-1])
    elif cpu_str.endswith('n'):
        return int(cpu_str[:-1]) // 1000000  # nanocores to millicores
    else:
        # Assume it's in cores
        try:
            return int(float(cpu_str) * 1000)
        except ValueError:
            return 0


def parse_memory_to_mb(memory_str: str) -> int:
    """Parse memory string to MB."""
    if not memory_str:
        return 0
    
    memory_str = str(memory_str)
    if memory_str.endswith('Ki'):
        return int(memory_str[:-2]) // 1024
    elif memory_str.endswith('Mi'):
        return int(memory_str[:-2])
    elif memory_str.endswith('Gi'):
        return int(memory_str[:-2]) * 1024
    elif memory_str.endswith('Ti'):
        return int(memory_str[:-2]) * 1024 * 1024
    else:
        # Assume bytes
        try:
            return int(memory_str) // (1024 * 1024)
        except ValueError:
            return 0


def format_resource_report(resources: Dict, show_details: bool = True) -> str:
    """Format resource data into a clear table format for log streams."""
    lines = []
    
    # Use box drawing characters for better visibility
    lines.append("\n╔" + "═" * 78 + "╗")
    lines.append("║" + f" CLUSTER RESOURCE MONITOR - {datetime.utcnow().strftime('%H:%M:%S UTC')} ".center(78) + "║")
    lines.append("╠" + "═" * 78 + "╣")
    
    # Summary table
    summary = resources["summary"]["cluster_totals"]
    
    # Resource pressure warnings first (if any)
    if resources["summary"]["resource_pressure"]:
        lines.append("║ ⚠️  RESOURCE PRESSURE DETECTED:".ljust(79) + "║")
        for pressure in resources["summary"]["pressure_points"]:
            msg = f"║   • {pressure['message']}"
            lines.append(msg[:78].ljust(79) + "║")
        lines.append("╠" + "─" * 78 + "╣")
    
    # Cluster summary in table format
    lines.append("║ Resource │ Used/Total │ Utilization │ Available │ Status               ║")
    lines.append("╠" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 13 + "┼" + "─" * 11 + "┼" + "─" * 22 + "╣")
    
    # Pod capacity
    pod_util = float(summary['pods']['utilization'].rstrip('%'))
    pod_status = "🟢 OK" if pod_util < 80 else "🟡 WARN" if pod_util < 90 else "🔴 CRITICAL"
    lines.append(f"║ Pods     │ {summary['pods']['used']:>3}/{summary['pods']['capacity']:<6} │ "
                f"{summary['pods']['utilization']:>11} │ {summary['pods']['available']:>9} │ {pod_status:<20} ║")
    
    # CPU (show both requests and actual usage if available)
    cpu_util = float(summary['cpu']['utilization'].rstrip('%'))
    cpu_status = "🟢 OK" if cpu_util < 80 else "🟡 WARN" if cpu_util < 90 else "🔴 CRITICAL"
    lines.append(f"║ CPU Req  │ {summary['cpu']['requests']:>10} │ "
                f"{summary['cpu']['utilization']:>11} │ {summary['cpu']['available']:>9} │ {cpu_status:<20} ║")
    
    # Memory (show both requests and actual usage if available)
    mem_util = float(summary['memory']['utilization'].rstrip('%'))
    mem_status = "🟢 OK" if mem_util < 80 else "🟡 WARN" if mem_util < 90 else "🔴 CRITICAL"
    lines.append(f"║ Mem Req  │ {summary['memory']['requests']:>10} │ "
                f"{summary['memory']['utilization']:>11} │ {summary['memory']['available']:>9} │ {mem_status:<20} ║")
    
    # Pod counts
    if resources["pods"] and resources["pods"]["evaluations"]:
        eval_pods = resources["pods"]["evaluations"]
        lines.append("╠" + "─" * 78 + "╣")
        lines.append(f"║ Evaluation Pods: "
                    f"Running={eval_pods['running']:>2} "
                    f"Pending={eval_pods['pending']:>2} "
                    f"Completed={eval_pods['completed']:>2} "
                    f"Failed={eval_pods['failed']:>2}".ljust(78) + " ║")
    
    # Per-node details if requested
    if show_details and resources["nodes"]:
        lines.append("╠" + "═" * 78 + "╣")
        lines.append("║ NODE DETAILS:".ljust(79) + "║")
        lines.append("╠" + "─" * 78 + "╣")
        
        for node in resources["nodes"]:
            node_name = node['name'].split('.')[0][:20]  # Shorten node name
            lines.append(f"║ {node_name} ({node['instance_type']}):".ljust(79) + "║")
            
            # Pod usage
            lines.append(f"║   Pods: {node['pods']['used']:>2}/{node['pods']['capacity']:<2} "
                        f"({node['pods']['utilization']:>5}) "
                        f"[{node['pods']['available']:>2} avail]".ljust(79) + "║")
            
            # CPU usage (show actual if available)
            cpu_info = f"║   CPU:  Req={node['cpu']['requests']:>6} "
            if node['cpu']['usage'] != "N/A":
                cpu_info += f"Use={node['cpu']['usage']:>6} ({node['cpu']['actual_utilization']:>5})"
            else:
                cpu_info += f"({node['cpu']['request_utilization']:>5})"
            lines.append(cpu_info.ljust(79) + "║")
            
            # Memory usage (show actual if available)
            mem_info = f"║   Mem:  Req={node['memory']['requests']:>6} "
            if node['memory']['usage'] != "N/A":
                mem_info += f"Use={node['memory']['usage']:>6} ({node['memory']['actual_utilization']:>5})"
            else:
                mem_info += f"({node['memory']['request_utilization']:>5})"
            lines.append(mem_info.ljust(79) + "║")
    
    lines.append("╚" + "═" * 78 + "╝")
    
    return "\n".join(lines)


def format_resource_table_compact(resources: Dict) -> str:
    """Format a compact single-line resource summary for continuous monitoring."""
    summary = resources["summary"]["cluster_totals"]
    eval_pods = resources["pods"].get("evaluations", {})
    
    # Create a compact one-liner
    pod_util = float(summary['pods']['utilization'].rstrip('%'))
    cpu_util = float(summary['cpu']['utilization'].rstrip('%'))
    mem_util = float(summary['memory']['utilization'].rstrip('%'))
    
    # Status indicators
    pod_ind = "🟢" if pod_util < 80 else "🟡" if pod_util < 90 else "🔴"
    cpu_ind = "🟢" if cpu_util < 80 else "🟡" if cpu_util < 90 else "🔴"
    mem_ind = "🟢" if mem_util < 80 else "🟡" if mem_util < 90 else "🔴"
    
    timestamp = datetime.utcnow().strftime('%H:%M:%S')
    
    return (f"[{timestamp}] CLUSTER: "
            f"Pods {pod_ind} {summary['pods']['used']}/{summary['pods']['capacity']} "
            f"CPU {cpu_ind} {summary['cpu']['utilization']} "
            f"Mem {mem_ind} {summary['memory']['utilization']} "
            f"| Evals: R={eval_pods.get('running', 0)} P={eval_pods.get('pending', 0)}")


def monitor_resources(namespace: str = "dev", interval: int = 5, duration: int = 60):
    """
    Monitor cluster resources for a specified duration.
    
    Args:
        namespace: Kubernetes namespace to monitor
        interval: Seconds between checks
        duration: Total seconds to monitor (0 for infinite)
    """
    import time
    
    start_time = time.time()
    iteration = 0
    
    while duration == 0 or (time.time() - start_time) < duration:
        iteration += 1
        resources = get_cluster_resources(namespace)
        
        # Clear screen for clean output (optional)
        print("\033[2J\033[H")  # ANSI escape codes to clear screen
        
        print(format_resource_report(resources, show_details=(iteration % 3 == 1)))
        
        if duration > 0:
            remaining = duration - (time.time() - start_time)
            print(f"\nMonitoring... {remaining:.0f}s remaining (Ctrl+C to stop)")
        else:
            print("\nMonitoring... (Ctrl+C to stop)")
        
        time.sleep(interval)


if __name__ == "__main__":
    # Example usage
    resources = get_cluster_resources()
    print(format_resource_report(resources))