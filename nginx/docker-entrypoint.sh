#!/bin/sh
set -e

# Function to fetch SSL certificates from AWS SSM Parameter Store
fetch_ssl_from_ssm() {
    # Only attempt if AWS CLI is available and we're in AWS
    if ! command -v aws >/dev/null 2>&1; then
        return 1
    fi
    
    # Check if we can reach EC2 metadata service
    if ! curl -s --max-time 2 http://169.254.169.254/latest/meta-data/instance-id >/dev/null 2>&1; then
        return 1
    fi
    
    echo "Checking for SSL certificates in SSM Parameter Store..."
    
    # Get region from EC2 metadata
    AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
    REGION=${AZ%?}  # Remove last character (the AZ letter)
    PROJECT=${PROJECT_NAME:-crucible-platform}
    
    # Check if certificates exist in SSM
    if aws ssm get-parameter --name "/${PROJECT}/ssl/certificate" --region $REGION >/dev/null 2>&1; then
        echo "SSL certificates found in Parameter Store, installing..."
        
        # Get certificate
        aws ssm get-parameter --name "/${PROJECT}/ssl/certificate" \
            --with-decryption --region $REGION \
            --query 'Parameter.Value' --output text > /etc/nginx/ssl/cert.pem
        
        # Get private key
        aws ssm get-parameter --name "/${PROJECT}/ssl/private_key" \
            --with-decryption --region $REGION \
            --query 'Parameter.Value' --output text > /etc/nginx/ssl/key.pem
        
        echo "Production SSL certificates installed from SSM"
        return 0
    fi
    
    return 1
}

# Function to generate self-signed certificates
generate_self_signed_cert() {
    echo "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/key.pem \
        -out /etc/nginx/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
}

# Create SSL directory
mkdir -p /etc/nginx/ssl

# Production mode: Always check SSM first, regardless of existing certs
if [ "$FORCE_SSL_REFRESH" = "true" ] || [ "$PRODUCTION_MODE" = "true" ]; then
    if fetch_ssl_from_ssm; then
        # Successfully fetched from SSM
        :
    elif [ "$PRODUCTION_MODE" = "true" ]; then
        echo "WARNING: Production mode but no SSM certificates available"
        # Could exit here if we want to be strict
        # exit 1
    fi
fi

# Check if certificates exist
if [ ! -f "/etc/nginx/ssl/cert.pem" ] || [ ! -f "/etc/nginx/ssl/key.pem" ]; then
    # Try environment variables first
    if [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ]; then
        echo "Installing SSL certificates from environment variables"
        echo "$SSL_CERT" > /etc/nginx/ssl/cert.pem
        echo "$SSL_KEY" > /etc/nginx/ssl/key.pem
    elif [ "$PRODUCTION_MODE" = "true" ]; then
        # Production MUST have certificates
        echo "ERROR: Production mode requires valid SSL certificates"
        echo "No certificates found at /etc/nginx/ssl/ or in environment variables"
        exit 1
    else
        # Development only: generate self-signed
        generate_self_signed_cert
    fi
else
    echo "Using existing SSL certificates"
    
    # In production, verify they're not self-signed
    if [ "$PRODUCTION_MODE" = "true" ]; then
        if openssl x509 -in /etc/nginx/ssl/cert.pem -noout -subject | grep -q "CN=localhost"; then
            echo "ERROR: Production cannot use self-signed certificates"
            exit 1
        fi
    fi
fi

# Set proper permissions
chmod 600 /etc/nginx/ssl/*
chown nginx:nginx /etc/nginx/ssl/*

# Test nginx configuration
nginx -t

# Start nginx
exec "$@"