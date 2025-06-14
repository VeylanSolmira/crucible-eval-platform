# Systemd Service File Location Decision

## Current Setup
- **Location**: `infrastructure/systemd/crucible-platform.service`
- **Deployment**: Copied from repository during userdata execution

## Why This Location?

### 1. Version Control
- Service definition lives with code
- Changes tracked in git
- Easy to review in PRs

### 2. Single Source of Truth
- No duplication between userdata and repository
- Updates in one place propagate everywhere

### 3. Testing
- Can validate syntax before deployment
- Can test locally with same file

### 4. Flexibility
- Works with multiple deployment methods (GitHub, S3, manual)
- Can be included in deployment packages
- Can be used in containerized environments

## Alternative Locations Considered

### `/deployment/systemd/`
- Pro: Groups all deployment artifacts
- Con: Mixes infrastructure with application deployment

### `/etc/systemd/` (in repo)
- Pro: Mirrors actual system location
- Con: Confusing - not actually system files

### Inline in Terraform
- Pro: Infrastructure as code
- Con: Hard to test, version, and reuse

## Recommendation
Keep it in `infrastructure/systemd/` because:
1. Clear separation of concerns
2. Easy to find all infrastructure components
3. Can be reused across different deployment methods
4. Follows common open-source patterns