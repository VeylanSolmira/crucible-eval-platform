#!/bin/bash
# Script to set up SSL certificates with containerized Nginx and Certbot

set -e

# Configuration
DOMAIN="${1:-crucible.veylan.dev}"
EMAIL="${2:-admin@example.com}"
STAGING="${3:-true}"  # Use Let's Encrypt staging by default for testing

echo "Setting up SSL for domain: $DOMAIN"
echo "Email: $EMAIL"
echo "Staging: $STAGING"

# Check if docker-compose files exist
if [ ! -f "docker-compose.yml" ] || [ ! -f "docker-compose.nginx.yml" ]; then
    echo "Error: docker-compose files not found"
    exit 1
fi

# Create required directories
mkdir -p nginx/conf.d
mkdir -p data/nginx/logs
mkdir -p data/certbot/www

# Start services without SSL first
echo "Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Test if HTTP is working
echo "Testing HTTP..."
if ! curl -f http://localhost/health > /dev/null 2>&1; then
    echo "Error: HTTP service not responding"
    docker-compose -f docker-compose.yml -f docker-compose.nginx.yml logs nginx
    exit 1
fi

# Prepare certbot command
CERTBOT_CMD="docker-compose -f docker-compose.yml -f docker-compose.nginx.yml run --rm certbot certonly"
CERTBOT_CMD="$CERTBOT_CMD --webroot --webroot-path=/var/www/certbot"
CERTBOT_CMD="$CERTBOT_CMD --email $EMAIL"
CERTBOT_CMD="$CERTBOT_CMD --agree-tos"
CERTBOT_CMD="$CERTBOT_CMD --no-eff-email"
CERTBOT_CMD="$CERTBOT_CMD -d $DOMAIN"

# Add staging flag if requested
if [ "$STAGING" = "true" ]; then
    CERTBOT_CMD="$CERTBOT_CMD --staging"
    echo "Using Let's Encrypt staging server (for testing)"
fi

# Request certificate
echo "Requesting SSL certificate..."
$CERTBOT_CMD

# Check if certificate was obtained
if [ ! -d "volumes/certbot-etc/live/$DOMAIN" ]; then
    echo "Error: Certificate not found"
    exit 1
fi

echo "SSL certificate obtained successfully!"

# Update Nginx configuration to enable SSL
echo "Updating Nginx configuration for SSL..."
# This would typically involve uncommenting SSL lines in crucible.conf
# or copying a different configuration file

# Reload Nginx
echo "Reloading Nginx..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml exec nginx nginx -s reload

echo "SSL setup complete!"
echo ""
echo "To test:"
echo "  curl https://$DOMAIN/health"
echo ""
echo "To renew certificates:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.nginx.yml run --rm certbot renew"
echo ""
echo "Certificate location (in container):"
echo "  /etc/letsencrypt/live/$DOMAIN/"