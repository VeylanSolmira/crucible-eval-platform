---
title: 'From Pain to Automation'
duration: 2
tags: ['automation', 'ci-cd']
---

## From Pain to Automation

### The CI/CD Solution

**GitHub Actions Workflow:**

```yaml
on:
  push:
    branches: [main]

jobs:
  deploy:
    steps:
      - Deploy to S3
      - Trigger EC2 update via SSM
      - Zero manual steps
```

**What We're Building:**

1. **Push to main** → Automatic deployment
2. **S3 as artifact store** → Version control
3. **SSM for updates** → No SSH needed
4. **SystemD service** → Auto-restarts

**Benefits:**

- No more manual tar commands
- No more SSH deployment dance
- No more SystemD formatting errors
- Consistent, reliable deployments

**The Lesson:**

> "Feel the pain, understand the problem, then automate the solution"
