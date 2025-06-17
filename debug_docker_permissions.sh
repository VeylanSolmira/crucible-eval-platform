#!/bin/bash
# Debug script to check Docker socket permissions

echo "=== Docker Socket Permissions Debug ==="
echo

echo "1. Current user info:"
docker exec crucible-platform id

echo -e "\n2. Docker socket info inside container:"
docker exec crucible-platform ls -la /var/run/docker.sock

echo -e "\n3. Groups available in container:"
docker exec crucible-platform cat /etc/group | grep -E "docker|root"

echo -e "\n4. Trying to access Docker:"
docker exec crucible-platform docker version 2>&1 | head -10

echo -e "\n5. Host Docker socket info:"
ls -la /var/run/docker.sock

echo -e "\n6. Suggested fix:"
SOCKET_GID=$(stat -f "%g" /var/run/docker.sock 2>/dev/null || stat -c "%g" /var/run/docker.sock 2>/dev/null)
if [ -n "$SOCKET_GID" ]; then
    echo "The Docker socket GID on your host is: $SOCKET_GID"
    echo "Update docker-compose.yml group_add to use this GID"
else
    echo "Could not determine Docker socket GID automatically"
    echo "Check the group owner of /var/run/docker.sock manually"
fi