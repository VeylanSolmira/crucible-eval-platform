# Claude Development Notes

## Monkey Patching Guidelines

### When Monkey Patching Might Be Acceptable:
1. **Testing/Mocking** - Temporarily replacing functions for unit tests
   ```python
   # OK: Mocking external API for tests
   def test_api_call(monkeypatch):
       monkeypatch.setattr(requests, 'get', mock_api_response)
   ```

2. **Debugging** - Adding temporary logging to diagnose issues
   ```python
   # OK: Temporary debugging (remove after fixing)
   original_func = module.function
   def debug_wrapper(*args, **kwargs):
       print(f"Called with: {args}")
       return original_func(*args, **kwargs)
   module.function = debug_wrapper
   ```

3. **Third-party Bug Fixes** - When you can't wait for upstream fix
   ```python
   # OK: Fixing known bug in external library
   # Document with issue link and remove when fixed upstream
   ```

### When NOT to Monkey Patch:
1. **Security-Critical Code** - NEVER monkey patch security functions
2. **Runtime Behavior Changes** - Don't swap implementations at runtime
3. **Module Import Side Effects** - Don't rely on import order for patches
4. **Production Code** - Prefer proper inheritance/composition
5. **Cross-Module Dependencies** - Creates hidden coupling

### The Security Runner Bug:
The bug in our security test runner happened because:
```python
# BAD: Tried to monkey patch after import
import security_scenarios.attack_scenarios
security_scenarios.attack_scenarios.ATTACK_SCENARIOS = SAFE_DEMOS  # Too late!
```

The module had already imported ATTACK_SCENARIOS, so our patch didn't affect it.

### Better Patterns:
1. **Dependency Injection** - Pass dependencies as parameters
2. **Strategy Pattern** - Pass behavior as objects
3. **Configuration Objects** - Use explicit config instead of module globals
4. **Factory Functions** - Create instances with proper parameters

Remember: Explicit is better than implicit, especially for security-critical code.

## Project Context
Building a demonstration platform for METR (Model Evaluation and Threat Research) that showcases platform engineering skills relevant to AI safety evaluation infrastructure.

## Key Requirements to Demonstrate
1. **Large-scale system design** - Kubernetes orchestration, microservices
2. **Container expertise** - Docker, security hardening, isolation
3. **Python backend development** - FastAPI, async patterns
4. **TypeScript frontend** - React dashboard for monitoring
5. **Infrastructure as Code** - Terraform, K8s manifests
6. **CI/CD pipelines** - GitHub Actions, automated testing
7. **Security mindset** - Network isolation, sandboxing, audit logging

## Documentation Philosophy
- **Over-document everything** - This is for learning and interview preparation
- **Explain the "why"** - Every technical decision should have clear reasoning
- **Show alternatives considered** - Demonstrate broad knowledge
- **Include trade-offs** - Show mature engineering judgment
- **Add interview tips** - How to discuss each component

## Architecture Documentation Pattern

For each component/decision, document:

### 1. What We Built
Clear description of the component and its purpose

### 2. Why This Approach
- Business requirements it addresses
- Technical benefits
- How it fits the overall system

### 3. Alternatives Considered
- Other valid approaches
- Why we didn't choose them
- When they might be better

### 4. Implementation Details
- Key code patterns
- Configuration examples
- Important dependencies

### 5. Trade-offs & Limitations
- What we're giving up
- Scaling limits
- Cost implications

### 6. Interview Talking Points
- Questions to expect
- How to explain the decision
- Related topics to study

### 7. Learning Resources
- Documentation links
- Tutorials for unfamiliar tech
- Related concepts to explore

## Current Project Status

### Completed
- [x] System architecture design
- [x] Docker containerization setup
- [x] Project structure

### In Progress
- [ ] Python evaluation framework
- [ ] Kubernetes manifests
- [ ] CI/CD pipeline
- [ ] TypeScript frontend
- [ ] Comprehensive documentation

## Key Technologies to Master

### Must Have Deep Knowledge
- **Kubernetes**: Pod security policies, network policies, RBAC
- **Docker**: Multi-stage builds, security scanning, runtime security
- **Python**: AsyncIO, FastAPI, Celery for task queuing
- **AWS/Cloud**: EKS, IAM, VPC design

### Should Be Familiar With
- **TypeScript/React**: Basic component design, state management
- **Monitoring**: Prometheus queries, Grafana dashboards
- **CI/CD**: GitHub Actions, ArgoCD for GitOps

### Nice to Know
- **AI/ML Basics**: Understanding model serving, GPU scheduling
- **Security Tools**: Falco, OPA, admission controllers

## Interview Preparation Notes

### Platform Engineering Questions
1. "How do you ensure secure isolation between evaluation runs?"
   - Container runtime security (gVisor/Firecracker)
   - Network policies
   - Resource limits
   - Audit logging

2. "How does the system scale?"
   - Horizontal pod autoscaling
   - Cluster autoscaling
   - Queue-based architecture
   - Caching strategies

3. "What happens when an evaluation fails?"
   - Circuit breakers
   - Retry logic with exponential backoff
   - Dead letter queues
   - Alerting pipeline

### METR-Specific Topics
1. **Autonomous Replication Prevention**
   - Network egress monitoring
   - File system restrictions
   - CPU/memory limits
   - Behavioral anomaly detection

2. **Evaluation Reproducibility**
   - Deterministic environments
   - Version pinning
   - Artifact storage
   - Comprehensive logging

## Git Hooks and GitHub Actions

### Local Git Hooks (.githooks/)
This repository uses custom Git hooks to prevent accidental exposure of sensitive files:

**`.githooks/pre-push`** - Privacy reminder hook
- Reminds about sensitive files before pushing
- Lists files that should NEVER be public (interview-prep.md, CLAUDE.md, etc.)
- Requires manual confirmation before push
- Can bypass with `git push --no-verify` if needed

To install the hooks:
```bash
git config core.hooksPath .githooks
```

### GitHub Actions Workflows (.github/workflows/)

**`privacy-check.yml`** - Automated privacy check
- Runs on every push and PR to main
- Checks for presence of sensitive files
- Warns if repository contains interview materials
- Does NOT fail the build (just warns)

**`deploy-docker.yml`** - Docker deployment pipeline
- Builds and pushes Docker images to ECR
- Deploys to EC2 instances via SSM
- Uses repository variables for configuration
- Triggers on push to main or manual dispatch

**`deploy.yml`** - S3 deployment (DEPRECATED)
- Previous deployment method using S3
- Disabled automatic triggers
- Kept for reference/emergency use

### Repository Variables
Set in GitHub Settings → Secrets and variables → Actions → Variables:
- `AWS_ROLE_ARN` - IAM role for OIDC authentication
- `AWS_REGION` - Target AWS region (default: us-west-2)
- `PROJECT_NAME` - Project identifier (default: crucible-platform)
- `CONTAINER_NAME` - Docker container name
- `ECR_REPOSITORY` - ECR repository name

## Commands to Remember

```bash
# Linting
ruff check .
mypy src/

# Testing
pytest tests/ -v
pytest tests/integration/ -k "kubernetes"

# Local development
docker-compose up -d
skaffold dev

# Kubernetes debugging
kubectl describe pod <pod-name>
kubectl logs -f deployment/evaluator
kubectl exec -it <pod-name> -- /bin/bash

# Git hooks
git config core.hooksPath .githooks  # Install local hooks
git push --no-verify                  # Bypass pre-push hook
```

## Next Learning Priorities
1. Study gVisor for container isolation
2. Learn Celery best practices for distributed tasks
3. Understand Kubernetes admission controllers
4. Research AI model serving patterns