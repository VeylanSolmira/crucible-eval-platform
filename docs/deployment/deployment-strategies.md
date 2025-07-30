# Deployment Strategy Options: From Manual to Full GitOps

## Current State Analysis

Our current deployment process has several pain points:
- Manual `kubectl apply -k` commands
- Build script creates the same tag for all services
- Manual rollout restart required for single service updates
- No automated rollback mechanism
- Limited audit trail of deployments

## Deployment Strategy Options

### 1. Current State + Small Improvements (1-2 days)

**What we have:**
- Manual `kubectl apply -k`
- Build script creates same tag for all services
- Manual rollout restart for single service updates

**Quick improvements:**
- Script to update single service in kustomization.yaml
- Deploy script that builds, pushes, and applies
- Add git SHA to tags for traceability

**Pros:**
- Minimal change from current workflow
- Quick to implement
- No new tools to learn

**Cons:**
- Still manual and error-prone
- No rollback mechanism
- No audit trail
- Tag synchronization issues

**Implementation example:**
```bash
# scripts/deploy-service.sh
SERVICE=$1
TAG=${2:-$(git rev-parse --short HEAD)}
./scripts/build-and-push-images.sh $SERVICE
kustomize edit set image $SERVICE=$ECR_REGISTRY/$SERVICE:$TAG
kubectl apply -k k8s/overlays/dev
```

### 2. Helm-based Deployment (3-5 days)

**Changes:**
- Convert kustomize to Helm charts
- Use values files per environment
- Helm release management

**Pros:**
- Built-in rollback (`helm rollback`)
- Release history
- Templating for complex scenarios
- Package versioning

**Cons:**
- Need to rewrite all manifests
- Learning curve for Helm
- Still manual deployment
- Helm complexity for simple needs

**Implementation example:**
```yaml
# values-dev.yaml
dispatcher:
  image:
    tag: "abc123"
api:
  image:
    tag: "def456"
```

### 3. GitHub Actions CD Pipeline (2-3 days) ⭐ RECOMMENDED

**Changes:**
- Extend existing GitHub Actions
- Auto-deploy on merge to main
- Per-service deployment workflows

**Pros:**
- Builds on existing CI
- Automated deployments
- Good for single repo
- PR-based workflow
- No additional infrastructure needed

**Cons:**
- GitHub-specific
- Secrets in GitHub
- Limited deployment strategies
- No drift detection

**Implementation example:**
```yaml
# .github/workflows/deploy-dev.yml
on:
  push:
    branches: [main]
    paths:
      - 'dispatcher_service/**'
jobs:
  deploy-dispatcher:
    steps:
      - name: Build and push
        run: ./scripts/build-and-push-images.sh dispatcher
      - name: Deploy
        run: |
          kubectl set image deployment/dispatcher \
            dispatcher=$ECR_REGISTRY/dispatcher:$GITHUB_SHA
```

### 4. Flux CD (Lightweight GitOps) (5-7 days)

**Changes:**
- Install Flux in cluster
- Git repo as source of truth
- Automated sync from git

**Pros:**
- True GitOps
- Automatic drift correction
- Multi-tenancy support
- Lighter than ArgoCD
- Good SOPS integration
- ~100-200m CPU, 200-400Mi memory overhead

**Cons:**
- Less UI than Argo
- Flux-specific CRDs
- Learning curve

### 5. ArgoCD (Full GitOps) (7-10 days)

**Changes:**
- Install ArgoCD
- Apps of Apps pattern
- Full UI for deployments
- RBAC and SSO integration

**Pros:**
- Industry standard
- Excellent UI
- Multi-cluster support
- Advanced sync strategies
- Built-in RBAC
- Rollback UI
- Diff visualization

**Cons:**
- More complex setup
- Additional infrastructure
- Learning curve
- Resource overhead (~300-400m CPU, 600-800Mi memory)

**Implementation example:**
```yaml
# argocd/applications/crucible-dev.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: crucible-dev
spec:
  source:
    repoURL: https://github.com/yourorg/crucible
    targetRevision: main
    path: k8s/overlays/dev
  destination:
    server: https://kubernetes.default.svc
    namespace: dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 6. ArgoCD + Image Updater (Additional 2-3 days)

**Changes:**
- Add ArgoCD Image Updater
- Automatic image updates from ECR
- Git commits for image updates

**Pros:**
- Fully automated
- Maintains git history
- Separates app changes from image updates

**Cons:**
- Another component
- Complex regex patterns
- ECR authentication complexity

## Resource Overhead Comparison

| Solution | CPU | Memory | Notes |
|----------|-----|--------|-------|
| Current (manual) | 0 | 0 | No cluster resources |
| GitHub Actions | 0 | 0 | Runs outside cluster |
| Flux CD | 100-200m | 200-400Mi | Lightweight GitOps |
| ArgoCD Minimal | 220m | 352Mi | Basic installation |
| ArgoCD Typical | 300-400m | 600-800Mi | With UI and all components |
| ArgoCD + Image Updater | 350-450m | 700-900Mi | Full automation |

## Recommendation

Given our current state and constraints:

1. **Short term (Do now):** Option 1 - Quick improvements to current process
   - Add deploy scripts
   - Use git SHA tags
   - Simple but effective

2. **Medium term (Next sprint):** Option 3 - GitHub Actions CD
   - Leverages existing GitHub workflows
   - Good for demonstrating CI/CD knowledge
   - Quick win for automation
   - No additional cluster resources needed

3. **Long term (Interview talking point):** Option 5 - ArgoCD
   - Industry standard for Kubernetes deployments
   - Shows advanced platform engineering skills
   - Great for METR-scale operations

## Next Steps

See [Week 8 Crucible Platform Tasks - Section 21: Deployment Automation](../planning/sprints/week-8-crucible-platform.md#21-deployment-automation-githubactions-cd) for implementation tasks.

## Interview Talking Points

When discussing deployment strategies:

1. **Current manual process** shows understanding of basics but acknowledges limitations
2. **GitHub Actions CD** demonstrates practical automation within existing tooling
3. **GitOps knowledge** shows awareness of industry best practices
4. **Resource constraints** consideration shows production mindset
5. **Progressive enhancement** approach shows mature engineering judgment

## Additional Resources

- [Flux vs ArgoCD Comparison](https://fluxcd.io/flux/faq/#flux-vs-argo-cd)
- [GitHub Actions for Kubernetes](https://docs.github.com/en/actions/deployment/deploying-to-your-cloud-provider/deploying-to-kubernetes)
- [ArgoCD Best Practices](https://argoproj.github.io/argo-cd/user-guide/best_practices/)
- [Kustomize vs Helm](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)