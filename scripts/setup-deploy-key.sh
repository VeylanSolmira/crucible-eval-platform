#!/bin/bash
# Generate SSH key pair for GitHub Actions deployment

set -e

echo "🔐 Generating SSH key pair for GitHub Actions deployment"

# Generate key without passphrase
ssh-keygen -t ed25519 -f ~/.ssh/crucible-deploy-key -N "" -C "github-actions@crucible"

echo ""
echo "✅ Key pair generated!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Add the private key to GitHub Secrets:"
echo "   - Go to: Settings → Secrets and variables → Actions → Secrets"
echo "   - Name: EC2_DEPLOY_KEY"
echo "   - Value: (copy the private key below)"
echo ""
echo "--- PRIVATE KEY (ADD TO GITHUB SECRETS) ---"
cat ~/.ssh/crucible-deploy-key
echo "--- END PRIVATE KEY ---"
echo ""
echo "2. Add the public key to EC2 instance:"
echo "   - SSH into your EC2 instance"
echo "   - Add the following to ~/.ssh/authorized_keys:"
echo ""
echo "--- PUBLIC KEY (ADD TO EC2) ---"
cat ~/.ssh/crucible-deploy-key.pub
echo "--- END PUBLIC KEY ---"
echo ""
echo "3. Test the deployment:"
echo "   - Push to main branch or run workflow manually"
echo ""
echo "⚠️  Security note: This key has deployment access. In production, use:"
echo "   - Separate keys per environment"
echo "   - Key rotation policy"
echo "   - Restricted commands in authorized_keys"