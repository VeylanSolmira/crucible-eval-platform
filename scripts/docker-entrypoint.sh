#!/bin/bash
# Docker entrypoint that dynamically handles Docker socket permissions

set -e

# Check if Docker socket exists
if [ -S /var/run/docker.sock ]; then
    echo "🔍 Docker socket found at /var/run/docker.sock"
    
    # Get the GID of the docker socket
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock 2>/dev/null || echo "")
    
    if [ -n "$DOCKER_GID" ]; then
        echo "📊 Docker socket GID: $DOCKER_GID"
        
        # Check if we're running as root (during container startup)
        if [ "$(id -u)" = "0" ]; then
            # Create a group with the same GID as the docker socket
            if ! getent group docker-host >/dev/null 2>&1; then
                groupadd -g "$DOCKER_GID" docker-host 2>/dev/null || true
            fi
            
            # Add appuser to this group
            usermod -aG docker-host appuser 2>/dev/null || true
            
            echo "✅ Added appuser to docker-host group (GID: $DOCKER_GID)"
            
            # Drop to appuser
            exec gosu appuser "$@"
        else
            echo "⚠️  Not running as root, cannot adjust groups"
            # Continue as current user
            exec "$@"
        fi
    else
        echo "⚠️  Could not determine Docker socket GID"
        exec "$@"
    fi
else
    echo "⚠️  Docker socket not found - code execution will be disabled"
    exec "$@"
fi