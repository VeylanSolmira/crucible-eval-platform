#!/bin/bash
# One-command startup script for Crucible Platform
# Usage: ./start-platform.sh [dev|prod]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default to development mode
MODE="${1:-dev}"

echo -e "${GREEN}Starting Crucible Platform in ${MODE} mode...${NC}"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check Docker Compose is available
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}dockercompose is not installed. Please install it first.${NC}"
    exit 1
fi

# Function to wait for service to be healthy
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $service to be healthy..."
    
    while [ $attempt -lt $max_attempts ]; do
        # Check if service is healthy (not just running)
        if docker compose ps "$service" 2>/dev/null | grep -q "(healthy)"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        # Also accept services without health checks as "ready"
        if docker compose ps "$service" 2>/dev/null | grep -E "Up.*[^)]$" | grep -v "(health" > /dev/null; then
            echo -e " ${GREEN}✓${NC} (no health check)"
            return 0
        fi
        echo -n "."
        sleep 3  # Increased from 2 to 3 seconds to better align with health check intervals
        ((attempt++))
    done
    
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}$service failed to become healthy${NC}"
    echo "Recent logs:"
    docker compose logs "$service" --tail=10
    return 1
}

# Create necessary directories
echo "Creating data directories..."
mkdir -p data  # For file-based storage

# Build base image first
echo "Building base image..."
docker compose build base

# Start services based on mode
if [ "$MODE" = "prod" ]; then
    echo "Starting services with production configuration..."
    
    # Note: Production volumes are defined in docker-compose.prod.yml
    # They will be created automatically by Docker
    
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
else
    echo "Starting services in development mode..."
    docker compose up -d
fi

# Wait for critical services
echo -e "\n${YELLOW}Waiting for services to initialize...${NC}"

# Wait for core infrastructure
wait_for_service "postgres"
wait_for_service "redis"

# Wait for storage-service since other services depend on it
wait_for_service "storage-service"

# Give services a moment to fully initialize
sleep 3

# Check all services are up
echo -e "\nChecking all services..."

# Run database migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
docker compose run --rm migrate || echo -e "${YELLOW}Migrations may have already been applied${NC}"

# Display service status
echo -e "\n${GREEN}Platform Status:${NC}"
docker compose ps

# Display access URLs
echo -e "\n${GREEN}Access URLs:${NC}"
echo "  Frontend:        http://localhost"
echo "  API:            http://localhost/api"
echo "  API Docs:       http://localhost/api/docs"
echo "  Flower:         http://localhost:5555"
echo "  Queue Status:   http://localhost/api/queue-status"
echo "  Celery Status:  http://localhost/api/celery-status"

# Display helpful commands
echo -e "\n${GREEN}Useful commands:${NC}"
echo "  View logs:      docker compose logs -f [service-name]"
echo "  Stop platform:  docker compose down"
echo "  Clean restart:  docker compose down -v && ./start-platform.sh"

# Check if all services are healthy
if docker compose ps | grep -E "unhealthy|Exit|Restarting" > /dev/null 2>&1; then
    echo -e "\n${YELLOW}Warning: Some services may not be healthy. Check logs with:${NC}"
    echo "  docker compose logs [service-name]"
else
    echo -e "\n${GREEN}✓ All services started successfully!${NC}"
fi

# Optional: Open browser (add --no-browser flag to skip)
if [[ "$2" != "--no-browser" ]]; then
    if command -v open &> /dev/null; then
        # macOS
        open http://localhost &
    elif command -v xdg-open &> /dev/null; then
        # Linux
        xdg-open http://localhost &
    fi
fi

echo -e "\n${GREEN}Platform is ready!${NC}"