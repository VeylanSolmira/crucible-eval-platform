---
title: "Chapter 7: SSH Tunneling & Security"
duration: 2
tags: ["security", "deployment"]
---

## Chapter 7: SSH Tunneling & Security
### Problem: Platform exposed to internet, private repo needs secure deployment

**SSH Tunnel Solution:**
```bash
# Instead of exposing port 8080 to the world:
ssh -L 8080:localhost:8080 ubuntu@<ec2-ip>

# Access locally while platform stays private:
http://localhost:8080
```

**S3 Deployment for Private Repos:**
```bash
# Build and upload
tar -czf crucible-${VERSION}.tar.gz .
aws s3 cp crucible-${VERSION}.tar.gz s3://deployment-bucket/

# EC2 pulls from S3 (using IAM role, no credentials)
aws s3 cp s3://deployment-bucket/crucible-${VERSION}.tar.gz .
```

**Security Benefits:**
- No open ports except SSH
- No git credentials on servers
- Audit trail via S3 access logs
- IAM role-based permissions