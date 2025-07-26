# Recovering from Stuck Kubernetes Deployments

This guide covers how to recover from stuck deployment rollouts without restarting the cluster. This situation commonly occurs when:
- Old replicasets can't scale down due to pod failures
- Image pull errors prevent pods from starting
- ResourceQuota exhaustion blocks new pods
- Rolling update strategy creates deadlocks

## Common Symptoms

- Deployment shows "X old replicas are pending termination"
- Pods stuck in `ErrImagePull`, `ErrImageNeverPull`, or `ImagePullBackOff`
- ResourceQuota exhausted by failed pods
- `kubectl rollout status` hangs indefinitely

## Recovery Methods

### 1. Force Delete Stuck ReplicaSets (Most Direct)

Force scale down problematic replicasets:
```bash
# Force scale to zero
kubectl scale replicaset <replicaset-name> --replicas=0 -n <namespace>

# Or delete entirely (keeps pods with --cascade=orphan)
kubectl delete replicaset <replicaset-name> -n <namespace> --cascade=orphan
```

### 2. Fix the Deployment Rollout

Pause and fix the rollout:
```bash
# Pause the rollout
kubectl rollout pause deployment/<deployment-name> -n <namespace>

# Option A: Rollback to previous version
kubectl rollout undo deployment/<deployment-name> -n <namespace>

# Option B: Update to a working image
kubectl set image deployment/<deployment-name> <container>=<working-image> -n <namespace>

# Resume rollout
kubectl rollout resume deployment/<deployment-name> -n <namespace>
```

### 3. Override Deployment Strategy Temporarily

Change to Recreate strategy to force immediate termination:
```bash
# Change to Recreate strategy
kubectl patch deployment <deployment-name> -n <namespace> \
  --type='json' -p='[{"op": "replace", "path": "/spec/strategy/type", "value":"Recreate"}]'

# Scale down and up
kubectl scale deployment <deployment-name> --replicas=0 -n <namespace>
kubectl scale deployment <deployment-name> --replicas=<desired> -n <namespace>

# Restore RollingUpdate strategy
kubectl patch deployment <deployment-name> -n <namespace> \
  --type='json' -p='[{"op": "replace", "path": "/spec/strategy/type", "value":"RollingUpdate"}]'
```

### 4. Delete Stuck Pods to Free ResourceQuota

Clean up failed pods consuming quota:
```bash
# Force delete all failed pods
kubectl delete pods -n <namespace> --field-selector status.phase=Failed --force --grace-period=0

# Delete specific problematic pods
kubectl delete pod <pod-name> -n <namespace> --force --grace-period=0

# Find and delete pods with image errors
kubectl get pods -n <namespace> | grep -E "ErrImagePull|ImagePullBackOff|ErrImageNeverPull" | \
  awk '{print $1}' | xargs kubectl delete pod -n <namespace> --force --grace-period=0
```

### 5. Temporarily Increase ResourceQuota

If quota exhaustion is blocking recovery:
```bash
# Increase memory limit temporarily
kubectl patch resourcequota <quota-name> -n <namespace> \
  --type='json' -p='[{"op": "replace", "path": "/spec/hard/limits.memory", "value":"10Gi"}]'

# After recovery, restore original limits
kubectl patch resourcequota <quota-name> -n <namespace> \
  --type='json' -p='[{"op": "replace", "path": "/spec/hard/limits.memory", "value":"7Gi"}]'
```

### 6. Manual Deployment Recreation

For severe cases, recreate the deployment:
```bash
# Backup current deployment
kubectl get deployment <deployment-name> -n <namespace> -o yaml > deployment-backup.yaml

# Delete deployment keeping pods running
kubectl delete deployment <deployment-name> -n <namespace> --cascade=orphan

# Clean up all replicasets
kubectl delete replicasets -n <namespace> -l app=<app-label>

# Edit deployment-backup.yaml to fix image issues
# Then recreate
kubectl apply -f deployment-backup.yaml
```

## Prevention Strategies

1. **Use `imagePullPolicy: IfNotPresent`** instead of `Never` for more flexibility
2. **Set proper `progressDeadlineSeconds`** to automatically fail stuck rollouts
3. **Use specific image tags** instead of `:latest` in production
4. **Configure `maxUnavailable`** to allow pod termination during rollouts
5. **Monitor ResourceQuota usage** and set alerts before exhaustion

## Quick Diagnosis Commands

```bash
# Check deployment rollout status
kubectl rollout status deployment/<name> -n <namespace>

# View deployment conditions
kubectl describe deployment <name> -n <namespace> | grep -A10 Conditions

# List all replicasets for a deployment
kubectl get rs -n <namespace> -l app=<app-label>

# Check ResourceQuota usage
kubectl describe resourcequota -n <namespace>

# Find stuck pods
kubectl get pods -n <namespace> | grep -v Running | grep -v Completed
```

## Example: Fixing Our Stuck Deployment

In our case with the api-service stuck deployment:
```bash
# The deployment was stuck with old replicasets
kubectl scale replicaset api-service-75888497c8 --replicas=0 -n crucible

# Or fix by updating the deployment
kubectl set image deployment/api-service api-service=crucible-platform/api-service:valid-tag -n crucible
```

Remember: In production, always prefer methods that maintain service availability (options 1 & 2) over more disruptive approaches.