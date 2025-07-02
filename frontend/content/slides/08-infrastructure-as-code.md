---
title: 'Chapter 6: Infrastructure as Code'
duration: 2
tags: ['terraform', 'automation']
---

## Chapter 6: Infrastructure as Code

### Problem: Manual EC2 setup doesn't scale

**Terraform Deployment:**

```hcl
resource "aws_instance" "eval_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"  # Free tier

  user_data = templatefile("userdata.sh.tpl", {
    github_repo = var.github_repo
    deployment_bucket = var.deployment_bucket
  })

  tags = {
    Name = "crucible-eval-server"
    Purpose = "AI evaluation with gVisor"
  }
}
```

**Benefits:**

- Reproducible deployments
- Version controlled infrastructure
- Easy to destroy/recreate
- Cost tracking via tags
