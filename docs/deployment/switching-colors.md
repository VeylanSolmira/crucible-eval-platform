# Switching Deployment Colors

## Quick Commands

### Switch to Blue
```bash
# Update .env
sed -i '' 's/TF_VAR_active_deployment_color="green"/TF_VAR_active_deployment_color="blue"/' .env
sed -i '' 's/DEFAULT_DEPLOYMENT_TARGET=green/DEFAULT_DEPLOYMENT_TARGET=blue/' .env

# Update GitHub variable
gh variable set DEFAULT_DEPLOYMENT_TARGET --body "blue"

# Update Route 53 to point to blue
cd infrastructure/terraform
source ../../.env
tofu apply -auto-approve
```

### Switch to Green
```bash
# Update .env
sed -i '' 's/TF_VAR_active_deployment_color="blue"/TF_VAR_active_deployment_color="green"/' .env
sed -i '' 's/DEFAULT_DEPLOYMENT_TARGET=blue/DEFAULT_DEPLOYMENT_TARGET=green/' .env

# Update GitHub variable
gh variable set DEFAULT_DEPLOYMENT_TARGET --body "green"

# Update Route 53 to point to green
cd infrastructure/terraform
source ../../.env
tofu apply -auto-approve
```

## One-Liner Color Switch

```bash
# Function to add to your shell profile
switch_deployment_color() {
    local color=$1
    if [[ "$color" != "blue" && "$color" != "green" ]]; then
        echo "Usage: switch_deployment_color [blue|green]"
        return 1
    fi
    
    # Update .env
    sed -i '' "s/TF_VAR_active_deployment_color=\".*\"/TF_VAR_active_deployment_color=\"$color\"/" .env
    sed -i '' "s/DEFAULT_DEPLOYMENT_TARGET=.*/DEFAULT_DEPLOYMENT_TARGET=$color/" .env
    
    # Update GitHub
    gh variable set DEFAULT_DEPLOYMENT_TARGET --body "$color"
    
    # Update Route 53
    cd infrastructure/terraform && source ../../.env && tofu apply -auto-approve && cd ../..
    
    echo "✅ Switched to $color deployment"
}
```

## Deployment Workflow

1. **Deploy to inactive color first**
   ```bash
   # If green is active, deploy to blue
   gh workflow run deploy-compose.yml -f deployment_color=blue
   ```

2. **Test the inactive deployment**
   ```bash
   # Get the blue instance IP
   cd infrastructure/terraform
   tofu output eval_server_blue_ip
   
   # Test it
   curl https://<blue-ip>/health
   ```

3. **Switch traffic to tested deployment**
   ```bash
   switch_deployment_color blue
   ```

## Current Status Check

```bash
# Check current settings
echo "Local .env settings:"
grep -E "active_deployment_color|DEFAULT_DEPLOYMENT_TARGET" .env

echo -e "\nGitHub repository variable:"
gh variable list | grep DEFAULT_DEPLOYMENT_TARGET

echo -e "\nActive deployment in AWS:"
cd infrastructure/terraform && tofu output active_deployment_dns
```