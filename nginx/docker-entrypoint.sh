#!/bin/sh
set -e

# Note: SSL certificate management is handled at the infrastructure layer
# - Docker Compose: Host fetches from AWS SSM, mounts via bind mount
# - Kubernetes: Cert-Manager or External Secrets Operator provides certs as Secrets
# The nginx container only reads certificates, never fetches them

# Function to generate self-signed certificates
generate_self_signed_cert() {
    echo "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/key.pem \
        -out /etc/nginx/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    # Set permissions for certificates we just created
    chmod 600 /etc/nginx/ssl/key.pem /etc/nginx/ssl/cert.pem
    chown nginx:nginx /etc/nginx/ssl/key.pem /etc/nginx/ssl/cert.pem
}

# Create SSL directory
mkdir -p /etc/nginx/ssl

# In production mode, certificates should already be mounted by infrastructure
# We no longer attempt to fetch from SSM as this is an infrastructure concern

# Check if certificates exist
if [ ! -f "/etc/nginx/ssl/cert.pem" ] || [ ! -f "/etc/nginx/ssl/key.pem" ]; then
    # Try environment variables first
    if [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ]; then
        echo "Installing SSL certificates from environment variables"
        echo "$SSL_CERT" > /etc/nginx/ssl/cert.pem
        echo "$SSL_KEY" > /etc/nginx/ssl/key.pem
        
        # Set permissions for certificates we just wrote
        chmod 600 /etc/nginx/ssl/cert.pem /etc/nginx/ssl/key.pem
        chown nginx:nginx /etc/nginx/ssl/cert.pem /etc/nginx/ssl/key.pem
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

# Permissions are now set in each certificate creation/write block above
# No need to set permissions here - avoiding issues with read-only mounts

# Test nginx configuration
nginx -t

# Start nginx
exec "$@"