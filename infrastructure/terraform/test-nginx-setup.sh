#!/bin/bash
# Test script for nginx setup - run on EC2 instance
set -e

echo "=== Testing Nginx Setup ==="

# Set variables (these would come from Terraform)
PROJECT_NAME="crucible-platform"
DOMAIN_NAME="crucible.veylan.dev"

# Test 1: Region extraction
echo "1. Testing region extraction..."
AZ=$(ec2metadata --availability-zone)
REGION=${AZ%?}
echo "   AZ: $AZ"
echo "   Region: $REGION"

# Test 2: Check SSL certificates in SSM
echo "2. Checking for SSL certificates in SSM..."
if aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/certificate" --region $REGION >/dev/null 2>&1; then
    echo "   ✓ SSL certificates found!"
    SSL_AVAILABLE=true
else
    echo "   ✗ No SSL certificates found"
    echo "   Would exit here in real script"
    SSL_AVAILABLE=false
    # In real script: exit 1
fi

# Test 3: Create nginx config (if not exists)
echo "3. Testing nginx config creation..."
if [ ! -f /etc/nginx/sites-available/crucible ]; then
    echo "   Creating test nginx config..."
    sudo tee /etc/nginx/sites-available/crucible > /dev/null <<'EOF'
server {
    listen 80;
    server_name crucible.veylan.dev;
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name crucible.veylan.dev;
    
    # ssl_certificate /etc/letsencrypt/live/crucible.veylan.dev/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/crucible.veylan.dev/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
    }
}
EOF
fi

# Test 4: SSL certificate download (if available)
if [ "$SSL_AVAILABLE" = "true" ]; then
    echo "4. Testing SSL certificate download..."
    
    # Create SSL directory
    sudo mkdir -p /etc/nginx/ssl
    
    # Test downloading certs
    echo "   Downloading certificate..."
    sudo aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/certificate" \
        --with-decryption --region $REGION \
        --query 'Parameter.Value' --output text > /tmp/test.crt
    
    if [ -s /tmp/test.crt ]; then
        echo "   ✓ Certificate downloaded successfully"
        sudo mv /tmp/test.crt /etc/nginx/ssl/${DOMAIN_NAME}.crt
    else
        echo "   ✗ Certificate download failed"
    fi
    
    # Test other downloads
    echo "   Downloading private key..."
    sudo aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/private_key" \
        --with-decryption --region $REGION \
        --query 'Parameter.Value' --output text > /etc/nginx/ssl/${DOMAIN_NAME}.key
    
    echo "   Downloading issuer chain..."
    sudo aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/issuer_pem" \
        --with-decryption --region $REGION \
        --query 'Parameter.Value' --output text > /etc/nginx/ssl/${DOMAIN_NAME}.chain.crt
    
    # Create full chain
    echo "   Creating full chain..."
    sudo cat /etc/nginx/ssl/${DOMAIN_NAME}.crt /etc/nginx/ssl/${DOMAIN_NAME}.chain.crt > /etc/nginx/ssl/${DOMAIN_NAME}.fullchain.crt
    
    # Set permissions
    sudo chmod 600 /etc/nginx/ssl/*
    sudo chown root:root /etc/nginx/ssl/*
    
    echo "   ✓ SSL files created"
    ls -la /etc/nginx/ssl/
fi

# Test 5: Sed commands
echo "5. Testing sed commands..."
if [ "$SSL_AVAILABLE" = "true" ]; then
    # Backup original
    sudo cp /etc/nginx/sites-available/crucible /etc/nginx/sites-available/crucible.bak
    
    # Test sed replacements
    echo "   Testing certificate path replacement..."
    sudo sed -i "s|# ssl_certificate .*|ssl_certificate /etc/nginx/ssl/${DOMAIN_NAME}.fullchain.crt;|" /etc/nginx/sites-available/crucible
    sudo sed -i "s|# ssl_certificate_key .*|ssl_certificate_key /etc/nginx/ssl/${DOMAIN_NAME}.key;|" /etc/nginx/sites-available/crucible
    
    echo "   Checking sed results:"
    grep ssl_certificate /etc/nginx/sites-available/crucible || echo "   No ssl_certificate lines found"
else
    echo "   Would remove SSL server block here"
    # In real script: sed -i '/listen 443 ssl/,/^}/d' /etc/nginx/sites-available/crucible
fi

# Test 6: Nginx configuration test
echo "6. Testing nginx configuration..."
if sudo nginx -t 2>&1; then
    echo "   ✓ Nginx configuration is valid"
else
    echo "   ✗ Nginx configuration failed"
    echo "   Config content:"
    sudo cat /etc/nginx/sites-available/crucible
fi

# Test 7: Check if site is enabled
echo "7. Checking nginx site enablement..."
if [ -L /etc/nginx/sites-enabled/crucible ]; then
    echo "   ✓ Site is enabled"
else
    echo "   Creating symlink..."
    sudo ln -sf /etc/nginx/sites-available/crucible /etc/nginx/sites-enabled/
fi

echo ""
echo "=== Test Summary ==="
echo "Region extraction: OK"
echo "SSL available: $SSL_AVAILABLE"
if [ "$SSL_AVAILABLE" = "true" ]; then
    echo "SSL certificates: $(ls -1 /etc/nginx/ssl/ 2>/dev/null | wc -l) files"
fi
echo "Nginx config test: $(sudo nginx -t 2>&1 > /dev/null && echo 'PASS' || echo 'FAIL')"
echo ""
echo "To start nginx: sudo systemctl start nginx"
echo "To check status: sudo systemctl status nginx"