# Container Update Patterns

## Overview

This document compares different patterns for updating containers in production, from simple EC2 approaches to sophisticated Kubernetes GitOps workflows.

## Update Patterns Comparison

### 1. Push-Based Updates (Current Approach) ✅

**Flow:**
```
Developer → Git Push → GitHub Actions → Build → ECR → SSM Command → EC2 Pull & Restart
```

**Pros:**
- Immediate updates (< 2 minutes)
- Direct control over deployment
- Clear deployment logs in GitHub
- Works well for single instances

**Cons:**
- Requires SSM agent and permissions
- Push can fail if instance is down
- More complex orchestration

**Our Implementation:**
- GitHub Actions builds and pushes to ECR
- Uses SSM send-command to trigger update
- See: `.github/workflows/deploy-docker.yml`

### 2. Pull-Based Updates (Alternative) ⏸️

**Status: Prepared but not active** - Files exist in `infrastructure/terraform/templates/` but aren't deployed.

**Flow:**
```
Developer → Git Push → GitHub Actions → Build → ECR
EC2 → Timer (5 min) → Check ECR → Pull if new → Restart
```

**Pros:**
- Simple and resilient
- No push failures
- Instance can self-heal
- Similar to Kubernetes imagePullPolicy

**Cons:**
- **5-10 minute delay** (too slow for development!)
- No immediate feedback
- Harder to coordinate multiple instances

**Prepared Files (Not Active):**
- `crucible-updater.service` - Systemd service
- `crucible-updater.timer` - 5-minute timer
- `update-container.sh` - Update script

### 3. Webhook-Based Updates

**Flow:**
```
ECR Push → Webhook → Lambda/Server → Trigger Update
```

**Examples:**
- ECR EventBridge → Lambda → SSM Command
- Docker Hub webhooks
- Custom webhook receiver

**Pros:**
- Near-instant updates
- Event-driven
- Scalable

**Cons:**
- More infrastructure needed
- Webhook security concerns
- Still essentially push-based

## Kubernetes Patterns (For Reference)

### 4. GitOps with ArgoCD/Flux

**Flow:**
```
Git Push → Webhook → ArgoCD/Flux → Kubernetes API → Rolling Update
```

**How it Works:**
1. ArgoCD watches Git repository
2. Webhook triggers immediate sync
3. ArgoCD compares desired vs actual state
4. Updates deployments automatically

**Benefits:**
- Declarative configuration
- Automatic rollback on failures
- Git as single source of truth
- Audit trail of all changes

### 5. Flux Image Update Automation

**Flow:**
```
Container Registry → Flux Image Scanner → Git Commit → Flux Sync → Deploy
```

**Components:**

```yaml
# ImageRepository - Watches registry
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: myapp
spec:
  image: 123456789.dkr.ecr.us-west-2.amazonaws.com/myapp
  interval: 1m  # Scan every minute
```

```yaml
# ImagePolicy - Defines version strategy
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: myapp
spec:
  imageRepositoryRef:
    name: myapp
  policy:
    semver:
      range: '>=1.0.0'  # Semantic versioning
```

```yaml
# ImageUpdateAutomation - Updates Git
apiVersion: image.toolkit.fluxcd.io/v1beta1
kind: ImageUpdateAutomation
metadata:
  name: myapp-update
spec:
  interval: 5m
  git:
    commit:
      messageTemplate: |
        Auto-update {{range .Updated.Images}}{{println .}}{{end}}
  update:
    strategy: Setters
```

**Deployment with Markers:**
```yaml
spec:
  containers:
  - image: myapp:v1.2.3 # {"$imagepolicy": "flux-system:myapp"}
```

**What Happens:**
1. New image `v1.2.4` pushed to ECR
2. Flux detects it matches policy
3. Updates YAML in Git repository
4. Commits: "Auto-update myapp:v1.2.4"
5. Flux syncs Git → Cluster

### 6. Keel.sh Pattern

**Flow:**
```
Registry → Keel Webhook → Direct Deployment Update
```

- Watches container registries directly
- Updates deployments without Git
- Supports approvals via Slack/webhooks
- Simpler than Flux but less auditable

## Why We Use Push-Based (For Now)

During active development, we need:
1. **Immediate feedback** - Know if deployment succeeded
2. **Fast iteration** - Can't wait 5 minutes per change
3. **Direct control** - Push exactly when ready
4. **Clear logs** - See deployment output immediately

Once the platform stabilizes, we may switch to pull-based for:
- Better resilience
- Self-healing capabilities
- Simpler instance management

## Migration Path

If we move to Kubernetes:
1. Start with simple deployments
2. Add ArgoCD for GitOps
3. Enable Flux image automation for hands-off updates
4. Full CI/CD with Git as source of truth

## Summary

- **Current**: Push-based via GitHub Actions + SSM ✅
- **Prepared**: Pull-based with systemd timers ⏸️
- **Future**: Kubernetes with GitOps 🚀

The push-based approach gives us the speed we need during development, while the pull-based infrastructure is ready when we need more resilience.