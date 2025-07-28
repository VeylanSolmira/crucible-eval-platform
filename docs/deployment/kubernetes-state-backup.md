# Kubernetes State Backup & Restore

## What You Lose When Deleting EKS

### 1. Cluster State (Stored in etcd)
- **Deployments, Services, ConfigMaps, Secrets**
- **Ingress rules, NetworkPolicies**
- **PersistentVolumeClaims**
- **RBAC rules (Roles, RoleBindings)**
- **Custom Resources (CRDs)**

### 2. What You DON'T Lose
- **Container images** (stored in ECR)
- **Persistent data** (if using EBS volumes)
- **Application code** (in Git)
- **Infrastructure** (VPC, subnets, etc.)

## Complete Backup Solution

### backup-k8s-state.sh
```bash
#!/bin/bash
# Comprehensive Kubernetes state backup

BACKUP_DIR="k8s-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

echo "📦 Backing up Kubernetes state to $BACKUP_DIR"

# 1. Export all namespaced resources
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    echo "Backing up namespace: $ns"
    kubectl get -n $ns \
        deployments,services,configmaps,secrets,ingresses,persistentvolumeclaims,serviceaccounts,roles,rolebindings \
        -o yaml > "$BACKUP_DIR/namespace-$ns.yaml"
done

# 2. Export cluster-wide resources
echo "Backing up cluster resources..."
kubectl get \
    namespaces,nodes,persistentvolumes,clusterroles,clusterrolebindings,storageclasses,priorityclasses \
    -o yaml > "$BACKUP_DIR/cluster-resources.yaml"

# 3. Export CRDs and their instances
kubectl get crd -o yaml > "$BACKUP_DIR/crds.yaml"

# 4. Special handling for secrets (encrypted)
echo "Encrypting secrets..."
kubectl get secrets -A -o yaml | \
    gpg --symmetric --cipher-algo AES256 --output "$BACKUP_DIR/secrets-encrypted.gpg"

# 5. Save cluster info
kubectl config view --minify --flatten > "$BACKUP_DIR/kubeconfig-backup.yaml"
aws eks describe-cluster --name crucible-platform > "$BACKUP_DIR/eks-cluster-config.json"

# 6. Compress everything
tar -czf "k8s-backup-$(date +%Y%m%d-%H%M%S).tar.gz" $BACKUP_DIR

echo "✅ Backup complete: k8s-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
```

### restore-k8s-state.sh
```bash
#!/bin/bash
# Restore Kubernetes state to new cluster

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

echo "📥 Restoring from $BACKUP_FILE"

# Extract backup
RESTORE_DIR="restore-$(date +%Y%m%d-%H%M%S)"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# 1. Restore namespaces first
kubectl apply -f "$RESTORE_DIR/*/cluster-resources.yaml" --dry-run=client -o yaml | \
    grep -A10 "kind: Namespace" | kubectl apply -f -

# 2. Restore secrets (after decrypting)
echo "Enter backup password:"
gpg --decrypt "$RESTORE_DIR/*/secrets-encrypted.gpg" | kubectl apply -f -

# 3. Restore other resources
for file in "$RESTORE_DIR"/*/namespace-*.yaml; do
    echo "Restoring: $file"
    kubectl apply -f "$file"
done

# 4. Restore cluster resources (carefully)
kubectl apply -f "$RESTORE_DIR/*/cluster-resources.yaml"

echo "✅ Restore complete!"
```

## Velero: Professional Backup Solution

### Install Velero (Recommended)
```bash
# Install Velero for automated backups
velero install \
    --provider aws \
    --bucket my-velero-backups \
    --backup-location-config region=us-west-2 \
    --snapshot-location-config region=us-west-2

# Create backup
velero backup create full-backup --include-namespaces '*'

# Delete cluster
eksctl delete cluster --name crucible-platform

# ... Later, create new cluster ...

# Restore everything
velero restore create --from-backup full-backup
```

## What Actually Matters for Your Use Case

### Minimal State to Preserve
Since you're learning, you probably only need:

```yaml
# backup-essential.yaml
---
# Your app deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  namespace: production
spec:
  replicas: 3
  # ... your config
---
# Your service
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: production
spec:
  # ... your config
---
# Your secrets (store these encrypted!)
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: production
data:
  # ... your secrets
```

## Practical Approach for Learning

### Option 1: Git-Based State (Simplest)
```bash
# Store everything in Git
k8s/
├── base/
│   ├── deployments.yaml
│   ├── services.yaml
│   └── configmaps.yaml
└── overlays/
    ├── dev/
    └── production/

# To "restore": just apply from Git
kubectl apply -k k8s/overlays/production
```

### Option 2: Essential State Only
```bash
# Before deleting cluster
kubectl get deploy,svc,cm,secret -A -o yaml > my-app-state.yaml

# After creating new cluster
kubectl apply -f my-app-state.yaml
```

### Option 3: Full State Backup
Use the comprehensive scripts above or Velero.

## Cost-Effective Strategy

### For Development/Learning:
1. **Keep manifests in Git** (primary source of truth)
2. **Simple backup script** for current state
3. **Delete cluster** when not using for weeks
4. **Recreate and restore** from Git when needed

### Example Workflow:
```bash
# Friday: Done for the week
./scripts/backup-k8s-state.sh
eksctl delete cluster --name crucible-platform  # Save $73/month

# Next month: Ready to continue
terraform apply  # Recreate cluster
kubectl apply -k k8s/  # Restore from Git
./scripts/restore-k8s-state.sh  # Restore any dynamic state
```

## Things That Are Annoying to Restore

1. **Load Balancer IPs** - Will change
2. **PersistentVolume data** - Need separate backup
3. **Certificates** - May need reissuing
4. **OIDC providers** - Need reconfiguring
5. **Webhooks** - External services need updating

## My Recommendation

For learning Kubernetes:
1. **Use Git as source of truth** (you're already doing this)
2. **Delete cluster between learning sessions** if gaps > 2 weeks
3. **Use simple backup script** for anything created via kubectl
4. **Don't worry about perfect restoration** - it's a learning opportunity

The $73/month for idle control plane adds up. If you're not actively using it, delete it!

## Delete/Restore Commands

```bash
# Complete deletion (saves $73/month)
./scripts/backup-k8s-state.sh
eksctl delete cluster --name crucible-platform

# Complete restoration
terraform apply  # Recreate EKS
./scripts/restore-k8s-state.sh k8s-backup-20240126.tar.gz
```

The backup/restore cycle takes ~30 minutes but saves real money when you're not actively developing!