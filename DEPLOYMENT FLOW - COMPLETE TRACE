DEPLOYMENT FLOW - COMPLETE TRACE

  1. GitHub Actions Triggered

  Happy? ✅ Fine

  2. GitHub Actions VM starts

  Happy? ✅ Fine

  3. Checkout code

  File: .github/workflows/deploy.yml line 18
  Happy? ✅ Standard

  4. Configure AWS credentials - OIDC request

  File: .github/workflows/deploy.yml lines 20-24
  Needs: AWS_ROLE_ARN in GitHub variables
  Happy? ❌ Complex for no reason

  5. OIDC token exchange

  Needs: IAM OIDC provider configured
  Needs: Trust relationship on IAM role
  File: infrastructure/terraform/github-oidc.tf
  Happy? ❌ So much setup for one EC2

  6. Run deploy-to-s3.sh

  File: .github/workflows/deploy.yml lines 26-29
  Happy? ✅ Fine

  7. deploy-to-s3.sh gets bucket name

  File: scripts/deployment/deploy-to-s3.sh lines 10-14
  Needs: SSM parameter /crucible/deployment-bucket
  EXISTS
  Happy? ❌ Why SSM? Could be environment variable

  8. Create tarball

  File: scripts/deployment/deploy-to-s3.sh lines 45-69
  Happy? ✅ Fine

  9. Upload to S3

  File: scripts/deployment/deploy-to-s3.sh lines 75-76
  Needs: S3 bucket exists
  Needs: IAM permissions for S3
  Happy? ✅ Good

  10. Update SSM parameters

  File: scripts/deployment/deploy-to-s3.sh lines 83-89
  Needs: SSM parameter write permissions
  Happy? ❌ More SSM complexity

  11. Find EC2 instances

  File: .github/workflows/deploy.yml lines 34-37
  Needs: EC2 DescribeInstances permission
  Needs: Instance tagged with Project=crucible
  Happy? ❌ We know the instance. Why search?

  12. Check instance count

  File: .github/workflows/deploy.yml lines 39-42
  Happy? ❌ Unnecessary check

  13. Check if update script exists - COMMAND 1

  File: .github/workflows/deploy.yml lines 48-53
  Needs: SSM SendCommand permission
  Needs: SSM Agent running on EC2
  Needs: EC2 has SSM permissions
  Happy? ❌❌❌ AWFUL. Extra round trip.

  14. Wait for command

  File: .github/workflows/deploy.yml line 55
  Happy? ❌ Hardcoded sleep

  15. Get command result

  File: .github/workflows/deploy.yml lines 57-61
  Needs: SSM GetCommandInvocation permission
  Happy? ❌ Parsing output with tr

  16. Check if bootstrap needed

  File: .github/workflows/deploy.yml line 63
  Happy? ❌ String comparison on parsed output

  17. IF BOOTSTRAP: Get bucket from SSM

  File: .github/workflows/deploy.yml line 67
  Needs: Parameter exists
  Happy? ❌ Redundant - already got it earlier

  18. IF BOOTSTRAP: Get version from SSM

  File: .github/workflows/deploy.yml line 68
  Happy? ❌ More SSM calls

  19. IF BOOTSTRAP: Send bootstrap command - COMMAND 2

  File: .github/workflows/deploy.yml lines 71-82
  The actual command string with interpolation:
  "commands=[
    \"aws s3 cp s3://${BUCKET_NAME}/crucible-platform-$
  {VERSION}.tar.gz /tmp/\",
    ...
  ]"
  Happy? ❌❌❌ HATE the escaped quotes and
  interpolation

  20. Bootstrap commands run on EC2:

  - 20a. Download from S3 (needs S3 permissions)
  - 20b. Create directory
  - 20c. Extract tarball
  - 20d. Copy update script
  - 20e. Make executable
  - 20f. Clean up
  Happy? ❌ Should be idempotent, not conditional

  21. Run update script - COMMAND 3 (or 2)

  File: .github/workflows/deploy.yml lines 87-93
  Happy? ❌ Third SSM command

  22. Wait again

  File: .github/workflows/deploy.yml line 98
  Happy? ❌ Another hardcoded sleep

  23. Check final status

  File: .github/workflows/deploy.yml lines 99-103
  Happy? ❌ May not be complete in 10 seconds

24. Update script runs on EC2:

File: infrastructure/scripts/update-platform.sh

25. Get bucket from SSM (AGAIN)

Lines: 8-12
Happy? ❌ Fourth time getting this

26. Get version from S3

Lines: 15-19
Happy? ❌ Why not from SSM parameter?

27. Download tarball (AGAIN if bootstrap)

Line: 25
Happy? ❌ Might download same file twice

28. Extract with strip-components

Line: 26
Happy? ⚠️ Different extract command than bootstrap

29. Check/create venv

Lines: 30-32
Happy? ❌ Should be in infrastructure

30. Install dependencies

Lines: 33-34
Happy? ✅ Fine IF venv exists

31. Update systemd service

Lines: 37-38
Happy? ✅ Good to check for changes

32. Restart service

Line: 41
Happy? ✅ Fine

33. Cleanup

Line: 44
Happy? ✅ Good

TOTAL DEPENDENCIES:

- AWS OIDC provider
- IAM role with trust policy
- GitHub variable AWS_ROLE_ARN
- S3 bucket exists
- SSM parameters (bucket, version)
- EC2 instance exists
- EC2 has Project=crucible tag
- EC2 has SSM Agent running
- EC2 has IAM role with S3 and SSM permissions
- Python 3.11 installed
- systemd configured
- All IAM permissions correct
- Network connectivity
- No AWS API throttling

FAILURE POINTS:

- Any SSM command fails
- Script doesn't exist when expected
- Variable interpolation breaks
- Hardcoded waits too short
- Bootstrap detection fails
- Different extract commands
- Venv creation race condition

OVERALL:

This is a Rube Goldberg machine. We turned "copy
files and restart" into a distributed systems problem
 with multiple services, conditional logic, and state
 management.

Happiness: 0/10