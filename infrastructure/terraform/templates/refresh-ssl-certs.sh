#!/bin/bash
set -e

# This script refreshes SSL certificates from AWS SSM Parameter Store
# It's designed to be run by systemd timer on EC2 instances

# Get region from availability zone
AZ=$(ec2metadata --availability-zone)
REGION=${AZ%?}

# Configuration - passed as environment variables or defaults
PROJECT_NAME="${PROJECT_NAME:-crucible-platform}"
LOG_FILE="${LOG_FILE:-/var/log/ssl-refresh.log}"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting SSL certificate refresh for project: $PROJECT_NAME"

# Check if certificates exist in SSM
if ! aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/certificate" --region "$REGION" >/dev/null 2>&1; then
    log "ERROR: No SSL certificates found in Parameter Store"
    exit 1
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Fetch certificates to temporary location
log "Fetching certificates from SSM Parameter Store..."

aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/certificate" \
    --with-decryption --region "$REGION" \
    --query 'Parameter.Value' --output text > "$TEMP_DIR/cert.pem"

aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/private_key" \
    --with-decryption --region "$REGION" \
    --query 'Parameter.Value' --output text > "$TEMP_DIR/key.pem"

# Fetch issuer chain if available
if aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/issuer_pem" --region "$REGION" >/dev/null 2>&1; then
    aws ssm get-parameter --name "/${PROJECT_NAME}/ssl/issuer_pem" \
        --with-decryption --region "$REGION" \
        --query 'Parameter.Value' --output text > "$TEMP_DIR/chain.pem"
    
    # Create full chain for nginx
    cat "$TEMP_DIR/cert.pem" "$TEMP_DIR/chain.pem" > "$TEMP_DIR/fullchain.pem"
    log "Created certificate full chain"
fi

# Compare with existing certificates
NEEDS_UPDATE=false
CERT_DIR="/etc/nginx/ssl"

if [ ! -f "$CERT_DIR/cert.pem" ]; then
    log "No existing certificate found, initial installation required"
    NEEDS_UPDATE=true
elif ! cmp -s "$TEMP_DIR/cert.pem" "$CERT_DIR/cert.pem"; then
    log "Certificate content has changed"
    NEEDS_UPDATE=true
elif [ -f "$TEMP_DIR/chain.pem" ] && [ ! -f "$CERT_DIR/chain.pem" ]; then
    log "Chain certificate now available"
    NEEDS_UPDATE=true
elif [ -f "$TEMP_DIR/chain.pem" ] && ! cmp -s "$TEMP_DIR/chain.pem" "$CERT_DIR/chain.pem"; then
    log "Chain certificate has changed"
    NEEDS_UPDATE=true
fi

if [ "$NEEDS_UPDATE" = true ]; then
    log "Updating certificates..."
    
    # Ensure directory exists with correct permissions
    mkdir -p "$CERT_DIR"
    
    # Copy new certificates
    cp "$TEMP_DIR"/*.pem "$CERT_DIR/"
    chmod 600 "$CERT_DIR"/*.pem
    chown root:root "$CERT_DIR"/*.pem
    
    # Find and reload nginx container
    NGINX_CONTAINER=$(docker ps --filter "name=crucible-nginx" --filter "status=running" -q)
    
    if [ -n "$NGINX_CONTAINER" ]; then
        log "Reloading nginx container: $NGINX_CONTAINER"
        if docker exec "$NGINX_CONTAINER" nginx -t 2>&1 | tee -a "$LOG_FILE"; then
            docker exec "$NGINX_CONTAINER" nginx -s reload
            log "Nginx reloaded successfully"
        else
            log "ERROR: Nginx configuration test failed, not reloading"
            exit 1
        fi
    else
        log "No running nginx container found, certificates updated for next start"
    fi
    
    log "SSL certificates updated successfully"
else
    log "SSL certificates are up to date, no changes needed"
fi

# Exit successfully
exit 0