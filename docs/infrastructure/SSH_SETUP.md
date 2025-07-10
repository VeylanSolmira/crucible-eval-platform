# SSH Setup Guide

## Quick SSH Access

If deployment is complete, SSH to your instance:
```bash
ssh -i ~/.ssh/id_ed25519_metr ubuntu@$(tofu output -raw eval_server_public_ip)
```

## Initial Setup Steps

### 1. Generate SSH Key (if needed)
```bash
ssh-keygen -t ed25519 -C "metr-eval-platform" -f ~/.ssh/id_ed25519_metr -N ""
```

### 2. Get Your Public Key
```bash
cat ~/.ssh/id_ed25519_metr.pub
```

### 3. Update Infrastructure
- Add the public key to `ec2.tf` in the `aws_key_pair` resource
- Ensure `allowed_ssh_ip` variable has your current IP

### 4. Deploy
```bash
tofu apply
```

## Updating Your IP Address

When your IP changes:

### Option 1: Command Line
```bash
# Get your current IP
curl -s https://api.ipify.org

# Apply with new IP
tofu apply -var="allowed_ssh_ip=YOUR_NEW_IP/32"
```

### Option 2: Update Default
Edit `variables.tf` and change the default value for `allowed_ssh_ip`

### Option 3: Use terraform.tfvars
Create `terraform.tfvars`:
```hcl
allowed_ssh_ip = "YOUR_IP/32"
```

## Troubleshooting

### Permission Denied
- Ensure you're using the correct key: `-i ~/.ssh/id_ed25519_metr`
- Check the key permissions: `chmod 600 ~/.ssh/id_ed25519_metr`

### Connection Timeout
- Verify your IP is allowed: `curl -s https://api.ipify.org`
- Check security group in AWS console
- Ensure instance is running: `tofu output`

### Lost Your Key
- Generate a new key pair
- Update `ec2.tf` with new public key
- Run `tofu apply` (will replace instance)

## Security Best Practices

1. **Never commit your private key** to version control
2. **Restrict SSH to your IP only** (already configured)
3. **Use SSH agent** for convenience:
   ```bash
   ssh-add ~/.ssh/id_ed25519_metr
   ssh ubuntu@$(tofu output -raw eval_server_public_ip)
   ```
4. **Consider AWS Systems Manager Session Manager** for production (no open SSH port needed)