# Loki Query Guide for METR Platform

## Available Labels

Based on our Loki setup, these labels are available:
- `job` - Always "fluentbit" (not "fluent-bit")
- `kubernetes_namespace_name` - Currently only "dev"
- `kubernetes_pod_name` - Full pod names
- `kubernetes_container_name` - Container names within pods

## Working Query Examples

### Basic Queries
```bash
# All logs from fluentbit
{job="fluentbit"}

# Logs from specific namespace
{job="fluentbit",kubernetes_namespace_name="dev"}

# Logs from specific container type
{job="fluentbit",kubernetes_container_name="evaluation"}

# Using regex patterns
{kubernetes_pod_name=~".*055650.*"}
```

### Direct API Queries
```bash
# Query with limit
kubectl exec -n dev deployment/loki -- wget -q -O - 'http://localhost:3100/loki/api/v1/query?query={job="fluentbit"}&limit=10'

# Query with time range (nanoseconds since epoch)
kubectl exec -n dev deployment/loki -- wget -q -O - 'http://localhost:3100/loki/api/v1/query_range?query={job="fluentbit"}&limit=5&start=1754100000000000000'

# List available labels
kubectl exec -n dev deployment/loki -- wget -q -O - 'http://localhost:3100/loki/api/v1/labels'

# List values for a label
kubectl exec -n dev deployment/loki -- wget -q -O - 'http://localhost:3100/loki/api/v1/label/kubernetes_pod_name/values'
```

## Common Issues

1. **No results returned**: The label names use underscores, not double underscores or dashes
2. **Pod-specific queries often return empty**: Pods may have finished and logs may not persist
3. **Time ranges**: Use nanosecond timestamps, not seconds

## Debugging Steps

1. Check Loki is running: `kubectl get pods -n dev | grep loki`
2. Verify readiness: `kubectl exec -n dev deployment/loki -- wget -q -O - 'http://localhost:3100/ready'`
3. List available labels: Use the `/loki/api/v1/labels` endpoint
4. Check label values: Use `/loki/api/v1/label/{label_name}/values`
5. Start with broad queries and narrow down

## Log Retention

**Important**: Logs ARE retained for 24 hours for all pods (including completed ones).

The key is using the correct query endpoint:
- `/query` - Searches only recent logs (default time window)
- `/query_range` - Searches within specified time range (use this for completed pods)

### Querying Completed Pod Logs

```bash
# CORRECT: Use query_range with explicit time window
kubectl exec -n dev deployment/loki -- wget -q -O - \
  'http://localhost:3100/loki/api/v1/query_range?query={kubernetes_pod_name="your-pod-name"}&start=1754000000000000000&end=1754200000000000000'

# INCORRECT: This often returns empty for completed pods
kubectl exec -n dev deployment/loki -- wget -q -O - \
  'http://localhost:3100/loki/api/v1/query?query={kubernetes_pod_name="your-pod-name"}'
```

### Time Range Tips
- Use nanosecond timestamps (19 digits)
- Current time in nanoseconds: `date +%s%N`
- 24 hours ago: `echo $(( $(date +%s) - 86400 ))000000000`

## Retrieving Complete Stdout/Stderr from Evaluations

To get all logs from an evaluation pod in chronological order:

```bash
# Find pods by evaluation ID pattern (e.g., if eval_id is 20250802_061425_a5bc5117)
kubectl exec -n dev deployment/loki -- wget -q -O - \
  'http://localhost:3100/loki/api/v1/query_range?query={kubernetes_pod_name=~".*061425.*"}&start='$(echo $(( $(date +%s) - 300 ))000000000)'&limit=30' \
  | jq -r '.data.result[0].values[] | .[1]' | jq -r '.log'
```

This returns output like:
```
2025-08-02T06:14:27.37833634Z stdout F Starting 15-second test evaluation
2025-08-02T06:14:27.378474051Z stdout F Process ID: -c
2025-08-02T06:14:27.378599758Z stdout F Second 1/15: Still running...
...
2025-08-02T06:14:42.402759655Z stderr F RuntimeError: BOOM! This is the intentional exception after 15 seconds
```

### Key Parameters
- `direction=forward` - Get logs in chronological order (oldest first)
- `limit=30` - Adjust based on expected output volume
- `start=` - Use recent timestamp (e.g., 5 minutes ago)
- Pattern match on evaluation ID timestamp part for finding pods

### Get Exact Pod Name
```bash
kubectl exec -n dev deployment/loki -- wget -q -O - \
  'http://localhost:3100/loki/api/v1/query_range?query={kubernetes_pod_name=~".*061425.*"}&start='$(echo $(( $(date +%s) - 300 ))000000000)'&limit=1' \
  | jq -r '.data.result[0].stream.kubernetes_pod_name'
```