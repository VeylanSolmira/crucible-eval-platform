# Deployment Colors Configuration

## Single Source of Truth: `.env`

All deployment color configuration is managed in the `.env` file:

```bash
# Terraform automatically uses these (TF_VAR_ prefix)
TF_VAR_enabled_deployment_colors='["blue","green"]'
TF_VAR_active_deployment_color="green"

# GitHub Actions default
DEFAULT_DEPLOYMENT_TARGET=green
```

## Usage

### Terraform
```bash
# Terraform automatically picks up TF_VAR_ prefixed variables
cd infrastructure/terraform
source ../../.env
tofu apply
```

### GitHub Actions
```bash
# Set the repository variable once
gh variable set DEFAULT_DEPLOYMENT_TARGET --body "green"

# Deploy (uses DEFAULT_DEPLOYMENT_TARGET if not specified)
gh workflow run deploy-compose.yml
```

## No Scripts Needed!

- Terraform: Automatically uses `TF_VAR_` prefixed environment variables
- GitHub Actions: Uses repository variables for defaults
- Everything configured in one place: `.env`