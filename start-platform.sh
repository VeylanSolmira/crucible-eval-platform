#!/bin/bash
# One-command startup script for Crucible Platform
# Usage: ./start-platform.sh [dev|prod|build|build-all] [--skip-tests|--no-browser]
#   dev       - Start in development mode (default)
#   prod      - Start with production configuration
#   build     - Rebuild core images then start in dev mode (excludes ML executor)
#   build-all - Rebuild ALL images including ML executor (adds ~3 minutes)
#   --skip-tests - Skip running tests after startup
#   --no-browser - Don't open browser after startup
#
# Note: The ML executor image (1.3GB) is not built by default to save time.
#       Build it manually with: docker compose build executor-ml-image

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
MODE="${1:-dev}"
SKIP_TESTS=false
NO_BROWSER=false

# Check for additional flags
for arg in "$@"; do
    case $arg in
        --skip-tests)
            SKIP_TESTS=true
            ;;
        --no-browser)
            NO_BROWSER=true
            ;;
    esac
done

REBUILD_ALL=false
BUILD_ML=false

if [ "$MODE" = "build" ]; then
    echo -e "${BLUE}Rebuilding core services...${NC}"
    REBUILD_ALL=true
    MODE="dev"  # After building, start in dev mode
elif [ "$MODE" = "build-all" ]; then
    echo -e "${BLUE}Rebuilding ALL services (including ML executor)...${NC}"
    REBUILD_ALL=true
    BUILD_ML=true
    MODE="dev"  # After building, start in dev mode
fi

echo -e "${GREEN}Starting Crucible Platform in ${MODE} mode...${NC}"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check Docker Compose is available
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}docker compose is not installed. Please install it first.${NC}"
    exit 1
fi


# Create necessary directories
echo "Creating data directories..."
mkdir -p data  # For file-based storage

# Build images
if [ "$REBUILD_ALL" = true ]; then
    echo -e "${BLUE}Building images...${NC}"
    # First build base image since other images depend on it
    echo "Building base image first..."
    docker compose build --no-cache base
    
    # Build executor-ml image only if requested with 'all'
    if [ "$BUILD_ML" = true ]; then
        echo "Building ML executor image (this takes ~3 minutes)..."
        docker compose build --no-cache executor-ml-image
    fi
    
    # Then build all other images in parallel, excluding base and executor-ml-image
    echo "Building all other services in parallel..."
    # Get all services except 'base' and 'executor-ml-image' and build them
    SERVICES=$(docker compose config --services | grep -v '^base$' | grep -v '^executor-ml-image$' | tr '\n' ' ')
    docker compose build --parallel --no-cache $SERVICES
else
    # Just build base image for normal startup
    echo "Building base image..."
    docker compose build base
    
    # Check if executor-ml image exists
    if ! docker image inspect executor-ml:latest >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  ML executor image not found. ML workloads will fail.${NC}"
        echo "   To build it, run: docker compose build executor-ml-image"
        echo "   Or use: ./start-platform.sh build-all"
    fi
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
echo "  Rebuild core:   ./start-platform.sh build"
echo "  Rebuild all:    ./start-platform.sh build-all"

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

# Run tests unless skipped
if [ "$SKIP_TESTS" = false ]; then
    echo -e "\n${YELLOW}Running platform tests...${NC}"
    
    # Wait a bit for services to stabilize
    sleep 5
    
    # Check if Python virtual environment exists
    if [ -d "venv" ]; then
        # Activate venv and run tests
        source venv/bin/activate
        python tests/run_tests.py
        TEST_RESULT=$?
        deactivate
    else
        # Try running with system Python
        python3 tests/run_tests.py
        TEST_RESULT=$?
    fi
    
    if [ $TEST_RESULT -ne 0 ]; then
        echo -e "${YELLOW}⚠ Tests did not pass. Platform may not be fully functional.${NC}"
    fi
else
    echo -e "\n${YELLOW}Skipping tests (--skip-tests flag provided)${NC}"
fi

# Optional: Open browser
if [ "$NO_BROWSER" = false ]; then
    if command -v open &> /dev/null; then
        # macOS
        open http://localhost &
    elif command -v xdg-open &> /dev/null; then
        # Linux
        xdg-open http://localhost &
    fi
fi

echo -e "\n${GREEN}Platform is ready!${NC}"