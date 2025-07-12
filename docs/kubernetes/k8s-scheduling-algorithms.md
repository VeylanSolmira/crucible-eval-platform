# Kubernetes Scheduling: From NP-Complete to Practical

## The Theoretical Problem

Bin packing is NP-complete, meaning:
- Finding the OPTIMAL solution requires checking all combinations
- That's computationally infeasible for real clusters
- Example: 100 pods on 50 nodes = 50^100 possible arrangements!

## Kubernetes' Practical Approach

### Two-Phase Scheduling

```
Phase 1: Filtering (Fast)
├─ Eliminate nodes that CAN'T run the pod
├─ O(n) time complexity
└─ Reduces 1000 nodes → maybe 50 candidates

Phase 2: Scoring (Heuristic)
├─ Score remaining nodes
├─ Pick highest score
└─ O(n) for each scoring function
```

### Default Scoring Plugins

```go
// Simplified view of scheduler scoring
type Plugin interface {
    Score(pod *Pod, node *Node) int
}

// 1. Balanced Resource Allocation
// Prefers nodes with balanced CPU/memory usage
score1 := 10 - abs(cpuFraction - memoryFraction)*10

// 2. Least Requested Priority  
// Prefers nodes with more free resources
score2 := ((capacity - requested) / capacity) * 10

// 3. Node Affinity
// Bonus points for preferred nodes
score3 := matchesPreferredRules(pod, node) ? 10 : 0

// 4. Inter-Pod Affinity
// Co-locate related pods
score4 := countMatchingPods(pod.affinity, node) * 2

// Final score
totalScore := score1*weight1 + score2*weight2 + score3*weight3 + score4*weight4
```

## Real-World Scheduling Example

```yaml
# Your pod needs 2 CPU, 4GB RAM
apiVersion: v1
kind: Pod
spec:
  containers:
  - resources:
      requests:
        cpu: "2"
        memory: "4Gi"
```

### Scheduler's Decision Process

```
Available Nodes:
Node A: 4 CPU total, 1 CPU free, 8GB free  ❌ Filtered out (not enough CPU)
Node B: 4 CPU total, 3 CPU free, 5GB free  ✓ Score: 75
Node C: 8 CPU total, 6 CPU free, 16GB free ✓ Score: 85 (winner)
Node D: 4 CPU total, 2 CPU free, 4GB free  ✓ Score: 60 (too tight)
```

## Common Heuristics Used

### 1. First Fit Decreasing
```python
# Sort pods by size (largest first)
pods.sort(key=lambda p: p.cpu + p.memory, reverse=True)

# Place each pod in first node with space
for pod in pods:
    for node in nodes:
        if node.fits(pod):
            node.place(pod)
            break
```

### 2. Best Fit
```python
# Find node with least waste
best_node = None
min_waste = float('inf')

for node in nodes:
    if node.fits(pod):
        waste = node.free_resources_after(pod)
        if waste < min_waste:
            min_waste = waste
            best_node = node
```

### 3. Spread vs Pack
```yaml
# Spread: Distribute pods across nodes
apiVersion: v1
kind: Deployment
spec:
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: DoNotSchedule

# Pack: Consolidate pods on fewer nodes
# (Configure via scheduler scoring weights)
```

## Scheduler Configuration

### Custom Scoring Weights
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesFit
        weight: 100  # Heavily favor good fit
      - name: NodeAffinity
        weight: 50
      - name: PodTopologySpread
        weight: 20
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated  # Pack nodes tightly
        # or: LeastAllocated (spread pods out)
```

## Performance Implications

### Scheduling Latency
```
Small cluster (10 nodes):    ~50ms per pod
Medium cluster (100 nodes):  ~100ms per pod  
Large cluster (1000 nodes):  ~300ms per pod
Huge cluster (5000 nodes):   ~1s per pod

With 16 parallel scheduler threads:
Can schedule ~300 pods/second in medium cluster
```

### Optimization Techniques

1. **Node Grouping**
```yaml
# Scheduler only considers nodes in same zone first
nodeSelector:
  topology.kubernetes.io/zone: us-west-2a
```

2. **Scheduling Hints**
```yaml
# Pre-filter nodes with required attributes
nodeSelector:
  node.kubernetes.io/instance-type: c5.large
  
# Reduces 1000 nodes → 50 nodes to evaluate
```

3. **Priority Classes**
```yaml
# High-priority pods get scheduled first
priorityClassName: high-priority
```

## Practical Impact on Your System

### Good Enough is Good Enough

```
Optimal packing: 87% node utilization
Kubernetes default: 78% node utilization
Random placement: 45% node utilization

The 9% difference from optimal is worth it for:
- Sub-second scheduling decisions
- Predictable performance
- Respecting all constraints
```

### Your Executor Scenario

```yaml
# Anti-affinity forces "bad" packing (one per node)
# But that's what you want for isolation!
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: executor
            topologyKey: kubernetes.io/hostname
```

This intentionally creates a "worst case" bin packing scenario, but for good reasons:
- Process isolation
- Resource guarantees
- Failure isolation

## Advanced: Scheduling Framework

Since Kubernetes 1.19, you can write custom schedulers:

```go
// Custom plugin for ML workload placement
type MLScheduler struct{}

func (m *MLScheduler) Score(ctx context.Context, 
    state *framework.CycleState, 
    pod *v1.Pod, 
    nodeName string) (int64, *framework.Status) {
    
    node := getNode(nodeName)
    
    // Prefer nodes with GPUs for ML pods
    if hasGPU(node) && needsGPU(pod) {
        return 100, nil
    }
    
    // Avoid placing on GPU nodes if not needed
    if hasGPU(node) && !needsGPU(pod) {
        return 0, nil
    }
    
    // Default scoring
    return 50, nil
}
```

## The Bottom Line

Kubernetes makes pragmatic choices:
1. **Fast over optimal** - 100ms scheduling beats 10s for 2% better packing
2. **Predictable over clever** - Simple heuristics are debuggable
3. **Configurable defaults** - You can tune for your use case
4. **Extensible** - Write custom schedulers for special needs

For most workloads, the default scheduler is excellent. It's only when you have special requirements (like your one-executor-per-node) that you need to think about the underlying algorithms.