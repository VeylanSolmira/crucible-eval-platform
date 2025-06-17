# AWS IAM Permissions Guide

This document explains the AWS IAM permissions used in the Crucible Platform and the security decisions behind them.

## Overview

We follow the principle of least privilege, granting only the minimum permissions required for each component to function. However, some AWS services have specific requirements that necessitate broader permissions.

## GitHub Actions OIDC Permissions

### SSM Permissions

#### SendCommand
`ssm:SendCommand` works with resource-level permissions:
```json
{
  "Effect": "Allow",
  "Action": "ssm:SendCommand",
  "Resource": [
    "arn:aws:ssm:region::document/AWS-RunShellScript",
    "arn:aws:ssm:region:account:instance/*",
    "arn:aws:ec2:region:account:instance/*"
  ]
}
```

#### GetCommandInvocation (Special Case)
`ssm:GetCommandInvocation` requires broader permissions due to AWS SSM's internal implementation:

```json
{
  "Effect": "Allow",
  "Action": [
    "ssm:GetCommandInvocation"
  ],
  "Resource": "arn:aws:ssm:region:account:*"
}
```

**Why the wildcard?**
- AWS SSM doesn't support fine-grained resource permissions for command status operations
- CloudTrail logs show SSM requesting access to `arn:aws:ssm:region:account:*` 
- AWS documentation recommends using `Resource: "*"` for these actions
- We use account-scoped wildcard (`account:*`) instead of global wildcard (`*`) as a security compromise

**Security considerations:**
- Still restricted to our AWS account only
- Cannot access SSM resources in other accounts
- Limited to read-only operations (getting command status)

### ECR Permissions

`ecr:GetAuthorizationToken` requires global wildcard:
```json
{
  "Effect": "Allow",
  "Action": "ecr:GetAuthorizationToken",
  "Resource": "*"
}
```

This is an AWS requirement - the action doesn't support resource-level permissions.

### EC2 Permissions

EC2 describe operations require wildcards:
```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:DescribeInstances",
    "ssm:DescribeInstanceInformation"
  ],
  "Resource": "*"
}
```

These are read-only operations that don't support resource-level permissions.

## EC2 Instance Permissions

The EC2 instances have minimal permissions:
- Read from specific S3 buckets
- Write to specific SSM parameters
- Pull from ECR repository

See `infrastructure/terraform/ec2.tf` for the complete policy.

## Security Best Practices

1. **Use OIDC instead of long-lived credentials**
   - GitHub Actions uses OIDC to assume roles
   - No AWS credentials stored in GitHub

2. **Scope wildcards when possible**
   - Use `account:*` instead of `*`
   - Limit to specific regions

3. **Regular audits**
   - Review CloudTrail logs
   - Check for unused permissions
   - Update as AWS improves their permission model

4. **Document exceptions**
   - Explain why broader permissions are needed
   - Link to AWS documentation
   - Track AWS feature requests for better permission models

## References

- [AWS SSM Permissions Documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/auth-and-access-control-iam-identity-based-access-control.html)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)