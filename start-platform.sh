#!/bin/bash
# One-command startup script for Crucible Platform
# Usage: ./start-platform.sh [build] [--skip-tests|--no-browser]
#   build        - Force rebuild all images (no cache)
#   --skip-tests - Skip running tests after startup
#   --no-browser - Don't open browser after startup
#
# Requirements:
#   - Docker running
#   - Kubernetes cluster running (Docker Desktop, Kind, etc.)
#   - kubectl configured
#   - Skaffold installed

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORCE_BUILD=false
SKIP_TESTS=false
NO_BROWSER=false

# Check for additional flags
for arg in "$@"; do
    case $arg in
        build)
            FORCE_BUILD=true
            ;;
        --skip-tests)
            SKIP_TESTS=true
            ;;
        --no-browser)
            NO_BROWSER=true
            ;;
    esac
done

echo -e "${GREEN}Starting Crucible Platform with Kubernetes/Skaffold...${NC}"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check kubectl is available and cluster is accessible
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo -e "${RED}kubectl cannot connect to cluster. Please ensure Kubernetes is running.${NC}"
    echo "For Docker Desktop: Enable Kubernetes in settings"
    echo "For Kind: Run 'kind create cluster'"
    exit 1
fi

# Check Skaffold is installed
if ! command -v skaffold &> /dev/null; then
    echo -e "${RED}Skaffold is not installed. Please install it first.${NC}"
    echo "Visit: https://skaffold.dev/docs/install/"
    exit 1
fi

# Check if base image exists
if ! docker image inspect crucible-platform/base:latest > /dev/null 2>&1; then
    echo -e "${YELLOW}Base image not found. Building it now...${NC}"
    if docker build -f shared/docker/base.Dockerfile -t crucible-platform/base:latest .; then
        echo -e "${GREEN}✓ Base image built successfully${NC}"
    else
        echo -e "${RED}Failed to build base image. Please check the Dockerfile.${NC}"
        exit 1
    fi
fi

# Create necessary directories
echo "Creating data directories..."
mkdir -p data  # For file-based storage

# Generate OpenAPI specs (needed for frontend build)
echo -e "${YELLOW}Generating OpenAPI specifications...${NC}"
if ./scripts/generate-all-openapi-specs.sh; then
    echo -e "${GREEN}✓ OpenAPI specs ready${NC}"
else
    echo -e "${YELLOW}⚠️  Some OpenAPI specs failed to generate${NC}"
    echo "   Frontend type generation may use fallback types"
fi

# Function to cleanup on exit
cleanup() {
    if [ -n "$SKAFFOLD_PID" ]; then
        echo -e "\n${YELLOW}Stopping Skaffold...${NC}"
        kill $SKAFFOLD_PID 2>/dev/null || true
        wait $SKAFFOLD_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Platform stopped.${NC}"
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Force rebuild if requested
if [ "$FORCE_BUILD" = true ]; then
    echo -e "${BLUE}Force rebuilding all images...${NC}"
    # Clean builder cache
    echo "Cleaning builder cache..."
    docker builder prune -af
    
    # Start Skaffold with no-cache profile and cache disabled
    echo -e "${YELLOW}Starting Skaffold in dev mode with forced rebuild (no cache)...${NC}"
    skaffold dev --cache-artifacts=false --profile=no-cache &
else
    # Normal Skaffold dev mode
    echo -e "${YELLOW}Starting Skaffold in dev mode...${NC}"
    skaffold dev &
fi

# Store Skaffold PID
SKAFFOLD_PID=$!

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
echo "This may take a few minutes on first run..."

# Wait for API to be ready
MAX_ATTEMPTS=60
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if kubectl get pods | grep -E "api-.*Running" > /dev/null 2>&1; then
        # Check if API is actually responding
        if kubectl exec -it deployment/api-service -- curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ API service is ready!${NC}"
            break
        fi
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    if [ $((ATTEMPT % 10)) -eq 0 ]; then
        echo "  Still waiting... ($ATTEMPT/$MAX_ATTEMPTS)"
    fi
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}Services did not become ready in time.${NC}"
    echo "Check pod status with: kubectl get pods"
    echo "Check logs with: kubectl logs deployment/[service-name]"
    exit 1
fi

# Display service status
echo -e "\n${GREEN}Platform Status:${NC}"
kubectl get pods

# Display access URLs
echo -e "\n${GREEN}Access URLs:${NC}"
echo "  Frontend:        http://localhost:3000"
echo "  API:            http://localhost:8080/api"
echo "  API Docs:       http://localhost:8080/api/docs"
echo "  Storage API:    http://localhost:8081"

# Note about port forwarding
echo -e "\n${YELLOW}Note: If services are not accessible, you may need to set up port forwarding:${NC}"
echo "  kubectl port-forward deployment/api-service 8080:8080 &"
echo "  kubectl port-forward deployment/storage-service 8081:8081 &"
echo "  kubectl port-forward deployment/frontend 3000:3000 &"

echo -e "\n${GREEN}Useful commands:${NC}"
echo "  View logs:      kubectl logs deployment/[service-name] -f"
echo "  Get pods:       kubectl get pods"
echo "  Describe pod:   kubectl describe pod [pod-name]"
echo "  Shell into pod: kubectl exec -it deployment/[service-name] -- /bin/bash"
echo "  Stop platform:  Press Ctrl+C (Skaffold will clean up)"
echo "  Force rebuild:  ./start-platform.sh build"

echo -e "\n${GREEN}✓ Platform is running with Skaffold!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop and clean up all resources.${NC}"

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

# Wait for Skaffold (it runs until interrupted)
if [ -n "$SKAFFOLD_PID" ]; then
    wait $SKAFFOLD_PID
fi