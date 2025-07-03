#!/bin/bash
# One-command startup script for Crucible Platform
# Usage: ./start-platform.sh [dev|prod|build]
#   dev   - Start in development mode
#   prod  - Start with production configuration
#   build - Rebuild all images then start in dev mode

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command
MODE="${1:-dev}"

if [ "$MODE" = "build" ]; then
    echo -e "${BLUE}Rebuilding all services...${NC}"
    REBUILD_ALL=true
    MODE="dev"  # After building, start in dev mode
else
    REBUILD_ALL=false
fi

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


# Create necessary directories
echo "Creating data directories..."
mkdir -p data  # For file-based storage

# Build images
if [ "$REBUILD_ALL" = true ]; then
    echo -e "${BLUE}Building all images (this may take several minutes)...${NC}"
    docker compose build --no-cache
else
    # Just build base image for normal startup
    echo "Building base image..."
    docker compose build base
fi

# Start services based on mode with --wait flag
if [ "$MODE" = "prod" ]; then
    echo "Starting services with production configuration..."
    
    # Note: Production volumes are defined in docker-compose.prod.yml
    # They will be created automatically by Docker
    
    echo -e "\n${YELLOW}Starting all services (this may take a minute)...${NC}"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --wait --wait-timeout 120
else
    echo "Starting services in development mode..."
    echo -e "\n${YELLOW}Starting all services (this may take a minute)...${NC}"
    docker compose up -d --wait --wait-timeout 120
fi

# Check if the wait was successful
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All services are healthy!${NC}"
else
    echo -e "\n${YELLOW}⚠ Some services may still be starting. Checking status...${NC}"
    docker compose ps
fi

# Check all services are up
echo -e "\nChecking all services..."

# Run database migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
# Note: The migrate service uses the storage-service image, so it must be built first
if docker compose run --rm migrate 2>&1 | grep -q "Will assume transactional DDL"; then
    echo -e "${GREEN}Migrations completed successfully${NC}"
else
    echo -e "${YELLOW}Migrations may have already been applied or there was an error${NC}"
fi

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
echo "  Rebuild all:    ./start-platform.sh build"

# Check if all services are healthy
if docker compose ps | grep -E "unhealthy|Exit|Restarting" > /dev/null 2>&1; then
    echo -e "\n${YELLOW}Warning: Some services may not be healthy yet.${NC}"
    
    # Check if it's just nginx restarting (common during initial startup)
    if docker compose ps | grep -E "unhealthy|Exit" | grep -v nginx > /dev/null 2>&1; then
        echo "  Check logs with: docker compose logs [service-name]"
    else
        echo "  nginx may still be starting up. This is normal and should resolve within 30 seconds."
        echo "  You can check status with: docker compose ps"
    fi
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