# AWS Provider Compatibility with OpenTofu

## Summary
When using OpenTofu with the AWS provider, certain versions have initialization issues that cause timeouts. Through testing, we've identified the compatible version ranges.

## Tested Configurations

### Working Versions ✅
- **5.40.0** - Works without any workarounds
- **5.80.0** - Works with `TF_PLUGIN_TIMEOUT=300`
- **5.89.0** - Works without any workarounds (latest compatible)

### Problematic Versions ❌
- **5.99.0** - Timeout issues even with extended timeout
- **5.99.1** - Timeout issues even with extended timeout
- **5.90+** - General compatibility issues with OpenTofu

## Recommended Configuration

```hcl
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 5.90"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}
```

## Authentication Setup

### Using AWS SSO with aws-vault

1. **Install aws-vault**:
   ```bash
   brew install aws-vault  # macOS
   ```

2. **Login to SSO**:
   ```bash
   aws sso login --profile AdministratorAccess-503132503803
   ```

3. **Run OpenTofu commands**:
   ```bash
   aws-vault exec AdministratorAccess-503132503803 -- tofu plan
   ```

### Environment Setup (.envrc)

Create `.envrc` in the terraform directory:

```bash
# AWS Profile for this project
export AWS_VAULT_PROFILE="AdministratorAccess-503132503803"

# Increase plugin timeout for AWS provider compatibility (if using 5.80+)
export TF_PLUGIN_TIMEOUT=300

# Alias for running OpenTofu with aws-vault
alias tf='aws-vault exec $AWS_VAULT_PROFILE -- tofu'
```

Then run `direnv allow` to activate.

## Troubleshooting

### Provider Timeout Error
```
Error: Failed to load plugin schemas
Error while loading schemas for plugin components: Failed to obtain
provider schema: Could not load the schema for provider
registry.opentofu.org/hashicorp/aws: failed to instantiate provider
"registry.opentofu.org/hashicorp/aws" to obtain schema: timeout while
waiting for plugin to start..
```

**Solutions**:
1. Use AWS provider version < 5.90
2. Set `export TF_PLUGIN_TIMEOUT=300` for versions 5.80-5.89
3. Clear provider cache: `rm -rf .terraform .terraform.lock.hcl && tofu init`

### SSO Token Errors
```
Error: failed to refresh cached credentials, refresh cached SSO token failed
```

**Solution**: Re-login to SSO:
```bash
aws sso login --profile your-profile-name
```

### Alternative Authentication Methods

If SSO is problematic, export temporary credentials:
```bash
# Get credentials
aws configure export-credentials --profile AdministratorAccess-503132503803

# Export them (replace with your actual values)
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
```

## Version History

- **2025-06-10**: Tested AWS provider versions with OpenTofu v1.9.1
- Found compatibility issues with versions 5.90+
- Established working configuration with aws-vault and SSO