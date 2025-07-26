# Kubernetes Chaos Testing Guide

## Overview

This guide covers chaos testing approaches for the Crucible platform running on Kubernetes. Chaos testing helps verify system resilience by intentionally introducing failures.

## Approach Comparison

### 1. kubectl-based Testing (Recommended Starting Point)
**Pros:**
- Zero additional dependencies
- Simple to understand and debug
- Perfect for basic scenarios (pod deletion, scaling)
- Can be integrated into existing pytest framework

**Cons:**
- Limited to Kubernetes API operations
- No network delays, disk pressure, etc.
- Manual coordination of complex scenarios

**Example:**
```bash
# Delete a pod
kubectl delete pod <pod-name> -n crucible

# Scale deployment to 0 and back
kubectl scale deployment api-service --replicas=0 -n crucible
sleep 30
kubectl scale deployment api-service --replicas=1 -n crucible
```

### 2. Chaos Mesh (Recommended for Growth)
**License:** Apache 2.0
**Website:** https://chaos-mesh.org/

**Pros:**
- Comprehensive chaos types: network, IO, stress, time, kernel, DNS
- Nice web UI for experiment management
- Kubernetes-native (CRDs)
- Good documentation and examples
- Active community

**Cons:**
- Additional components to deploy
- YAML can get complex for advanced scenarios
- Learning curve for all features

**Best for:** Teams wanting comprehensive chaos engineering with good UX

### 3. Litmus
**License:** Apache 2.0
**Website:** https://litmuschaos.io/

**Pros:**
- Huge library of pre-built experiments
- Enterprise-ready with observability integrations
- Workflow engine for complex scenarios
- CNCF project

**Cons:**
- More complex setup
- Heavier resource footprint
- Overkill for simple use cases

**Best for:** Large organizations with complex chaos requirements

### 4. Kube-monkey (Simple but Limited)
**License:** Apache 2.0

**Pros:**
- Very simple - just randomly deletes pods
- Minimal configuration

**Cons:**
- Only does pod deletion
- Less actively maintained
- No UI or advanced features

**Best for:** Quick and dirty pod deletion testing

## Implementation Plan

### Phase 1: kubectl-based Tests (Current)
Start with simple Python tests using kubectl commands:
- Pod deletion during evaluation
- Service scaling during evaluation
- Multiple component failures
- Recovery verification

### Phase 2: Chaos Mesh (Future)
When we need:
- Network partitions between services
- Disk pressure testing
- CPU/memory stress
- DNS failures
- Time skew

## Test Scenarios

### Priority 1 (kubectl-based)
1. **API Service Restart**: Delete API pod during evaluation submission
2. **Dispatcher Failure**: Kill dispatcher during job creation
3. **Storage Worker Failure**: Kill storage worker during status updates
4. **Multiple Failures**: Cascade failures across components

### Priority 2 (Requires Chaos Mesh)
1. **Network Partition**: Split storage from API
2. **Slow Network**: Add latency between services
3. **Resource Pressure**: CPU/memory stress on evaluator nodes
4. **Clock Skew**: Time manipulation effects

## Safety Considerations

1. **Namespace Isolation**: Always target specific namespace
2. **Resource Labels**: Use labels to limit blast radius
3. **Cleanup**: Ensure all tests restore system state
4. **Monitoring**: Watch for cascading failures
5. **Documentation**: Clear warnings about destructive nature

## Getting Started

See `tests/chaos/kubernetes/` for implementation.

Start with the basic kubectl-based tests to verify:
- System handles pod failures gracefully
- Evaluations complete despite disruptions
- No data loss during failures
- Proper timeout handling