# Kubernetes Migration Path

## Phase 1: Learn with EKS (Month 1-2)
Start with EKS to focus on Kubernetes concepts without control plane complexity.

### Minimal EKS Setup
```bash
# Cost: ~$130/month
- EKS Control Plane: $73
- 2x t3.small nodes: $30  
- No load balancer (use NodePort): $0
- Reuse existing Elastic IP: $0
Total: ~$103/month
```

### What You'll Learn
- Deployments, Services, Ingress
- ConfigMaps, Secrets
- Resource management
- Networking concepts
- Monitoring and logging

## Phase 2: Add Production Features (Month 3-4)
Once comfortable, add production features while still on EKS.

### Enhanced Setup
```bash
# Add these gradually
- Ingress controller (nginx)
- cert-manager for SSL
- Prometheus for monitoring
- HPA for autoscaling
```

## Phase 3: Self-Managed Cluster (Month 5-6)
When ready, create a self-managed cluster alongside EKS.

### Setup Options

#### Option A: k3s (Easiest Start)
```bash
# Single node to start (~$30/month)
curl -sfL https://get.k3s.io | sh -
k3s kubectl get nodes

# Your existing manifests work immediately
k3s kubectl apply -f k8s/
```

#### Option B: kubeadm (Full Experience)
```bash
# 3 control plane nodes + 2 workers (~$150/month)
# You'll learn:
- etcd management
- Certificate rotation  
- Upgrade procedures
- Backup strategies
```

### Migration Process
```bash
# 1. Export from EKS
kubectl config use-context eks-crucible
kubectl get all,cm,secret,ing,pvc -A -o yaml > crucible-backup.yaml

# 2. Clean up AWS-specific annotations
sed -i '/eks.amazonaws.com/d' crucible-backup.yaml

# 3. Apply to new cluster
kubectl config use-context k3s-crucible
kubectl apply -f crucible-backup.yaml

# 4. Update DNS
# Point crucible.veylan.dev to new cluster

# 5. Keep EKS running until confirmed working
# Then: eksctl delete cluster crucible
```

## Cost Comparison

### Development Phase
| Setup | Monthly Cost | Good For |
|-------|-------------|----------|
| k3s single node | $30 | Learning control plane |
| EKS minimal | $103 | Learning Kubernetes |
| Docker Compose | $20 | Current setup |

### Production Phase  
| Setup | Monthly Cost | Complexity |
|-------|-------------|------------|
| k3s HA | $90 | Medium |
| EKS production | $188 | Low |
| kubeadm HA | $150 | High |

## Quick Start Commands

### 1. Create EKS Cluster (This Week)
```bash
eksctl create cluster \
  --name crucible \
  --region us-west-2 \
  --nodegroup-name workers \
  --node-type t3.small \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3
```

### 2. Deploy Your App
```bash
# Your existing containers work!
kubectl create namespace production
kubectl apply -k k8s/overlays/production
```

### 3. Access Without Load Balancer
```bash
# Get a node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}')

# Use NodePort
kubectl expose deployment api-service \
  --type=NodePort \
  --port=8080 \
  --node-port=30080

# Access via: http://$NODE_IP:30080
```

## Why This Path Makes Sense

1. **Start Simple**: EKS lets you focus on learning Kubernetes
2. **Low Risk**: Can always fall back to EKS if self-managed gets complex
3. **Gradual Learning**: Add complexity as you get comfortable
4. **Real Experience**: You'll understand what EKS does for you
5. **Cost Effective**: Only pay for what you need at each phase

## Decision Points

### Stay with EKS if:
- You value time over money
- You need enterprise features
- You want AWS integration
- You're building a team

### Move to Self-Managed if:
- You want deep Kubernetes knowledge
- You have time to manage it
- You need specific configurations
- You're cost-sensitive

## Next Steps

1. **This Week**: Terminate Docker Compose instances
2. **This Week**: Create minimal EKS cluster
3. **Next Week**: Deploy your app to Kubernetes
4. **Month 2**: Add production features
5. **Month 3**: Evaluate self-managed options
6. **Month 6**: Potentially migrate to self-managed