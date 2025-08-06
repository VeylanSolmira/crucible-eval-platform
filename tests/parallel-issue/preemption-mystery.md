# Test Pod Preemption Mystery

## What We Know

1. **The e2e test pod was preempted (evicted) 4 times** by pods with UUID names:
   - efba872f-4622-4350-89f9-c1b24a5ffdd6
   - 29a25210-48c0-4ac6-a407-7194cc77c392
   - b387a755-0eb5-49f1-9025-6efac0edf266
   - 766d79cc-66a6-4291-bad2-5dee9641be08

2. **This caused the job to fail** with BackoffLimitExceeded because:
   - The pod was killed externally (preempted)
   - backoffLimit is set to 0, so any failure = immediate job failure

3. **Both test pods AND evaluation pods are being preempted**:
   - e2e-tests pods (preempted 3-4 times)
   - test-seq pods
   - evaluation pods (20250803-* format)

4. **The preempting pods are mysterious**:
   - UUID-style names we don't recognize
   - No events or records of these pods existing
   - Very ephemeral - created and destroyed quickly
   - Must have priority > 200 (test pod priority)

5. **Priority hierarchy should be**:
   - Test pods: 200 (test-priority)
   - Normal evaluation pods: 500 (normal-priority-evaluation)
   - Low priority evaluations: 100 (low-priority-evaluation)
   - But tests default to priority=-1, so they get low-priority (100)

## Theories

1. **Kubernetes Internal Pods**: These UUIDs might be internal Kubernetes mechanisms like:
   - Image garbage collection pods
   - Node pressure eviction pods
   - Some kind of cleanup or maintenance pods

2. **Priority Inversion Bug**: Some evaluation pods might be getting the wrong priority class

3. **External System**: Another service/operator creating high-priority ephemeral pods

4. **Cluster Autoscaler**: Might be creating temporary pods to trigger scaling

## Why Only in Parallel?

When running tests in parallel:
- Cluster reaches near capacity (28/35 pods)
- This triggers whatever mechanism creates these high-priority UUID pods
- Test pods, being lower priority than expected, get preempted
- Sequential runs don't hit the capacity threshold

## Next Steps

1. Check if there's a way to see what created those UUID pods
2. Investigate if the cluster has any operators/controllers that create ephemeral pods
3. Consider increasing test pod priority or decreasing evaluation pod priority
4. Add preemption protection to test pods