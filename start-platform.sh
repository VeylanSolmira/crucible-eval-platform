#!/bin/bash
# One-command startup script for Crucible Platform
# Usage: ./start-platform.sh [build] [--skip-tests|--no-browser|--publish-executors]
#   build              - Force rebuild all images (no cache)
#   --skip-tests       - Skip running tests after startup
#   --no-browser       - Don't open browser after startup
#   --publish-executors - Build and push executor images to ECR
#
# This script will:
#   - Create/activate Python virtual environment
#   - Install development dependencies (requirements-dev.txt)
#   - Create Kind cluster if needed
#   - Build base Docker image
#   - Generate OpenAPI specifications
#   - Start all services with Skaffold
#
# Requirements:
#   - Python 3.11+
#   - Docker running
#   - kubectl installed
#   - Skaffold installed (or install from https://skaffold.dev/docs/install/)

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
PUBLISH_EXECUTORS=false

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
        --publish-executors)
            PUBLISH_EXECUTORS=true
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
    echo -e "${YELLOW}kubectl cannot connect to cluster. Checking for Kind...${NC}"
    
    # Check if kind is installed
    if command -v kind &> /dev/null; then
        # Check if crucible cluster exists
        if ! kind get clusters | grep -q "crucible"; then
            echo -e "${YELLOW}Creating Kind cluster 'crucible'...${NC}"
            if kind create cluster --name crucible; then
                echo -e "${GREEN}✓ Kind cluster created successfully${NC}"
                # Wait a moment for cluster to be ready
                sleep 5
            else
                echo -e "${RED}Failed to create Kind cluster${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}Kind cluster 'crucible' exists but kubectl can't connect.${NC}"
            echo "Try: kind export kubeconfig --name crucible"
            exit 1
        fi
    else
        echo -e "${RED}kubectl cannot connect to cluster and Kind is not installed.${NC}"
        echo "For Docker Desktop: Enable Kubernetes in settings"
        echo "For Kind: Install from https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
        exit 1
    fi
fi

# No registry setup needed - Skaffold will load images directly into Kind

# Load .env for ECR configuration
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create namespace and ECR secret if needed
if [ -n "$ECR_REGISTRY" ]; then
    echo -e "${YELLOW}Setting up ECR access...${NC}"
    # Create namespace if it doesn't exist
    kubectl create namespace crucible --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null
    
    # Create ECR pull secret
    if kubectl create secret docker-registry ecr-secret \
        --docker-server=$ECR_REGISTRY \
        --docker-username=AWS \
        --docker-password=$(aws ecr get-login-password --region ${AWS_REGION:-us-west-2}) \
        -n crucible \
        --dry-run=client -o yaml | kubectl apply -f -; then
        echo -e "${GREEN}✓ ECR pull secret ready${NC}"
    else
        echo -e "${RED}Failed to create ECR pull secret. Check AWS credentials.${NC}"
        exit 1
    fi
fi

# Check Skaffold is installed
if ! command -v skaffold &> /dev/null; then
    echo -e "${RED}Skaffold is not installed. Please install it first.${NC}"
    echo "Visit: https://skaffold.dev/docs/install/"
    exit 1
fi

# Check and setup Python virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3.11 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate venv and ensure requirements-dev is installed
echo -e "${YELLOW}Checking development dependencies...${NC}"
source venv/bin/activate

# Always ensure requirements are up to date (pip will skip unchanged packages)
echo -e "${YELLOW}Updating development dependencies...${NC}"
pip install -q -r requirements-dev.txt
echo -e "${GREEN}✓ Development dependencies ready${NC}"

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

# Publish executor images to ECR if requested
if [ "$PUBLISH_EXECUTORS" = true ]; then
    echo -e "${YELLOW}Publishing executor images to ECR...${NC}"
    if ./scripts/publish-executor-images.sh; then
        echo -e "${GREEN}✓ Executor images published to ECR${NC}"
    else
        echo -e "${RED}Failed to publish executor images to ECR${NC}"
        exit 1
    fi
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
    
    # Rebuild base image with no cache
    echo "Rebuilding base image..."
    if docker build -f shared/docker/base.Dockerfile -t crucible-platform/base:latest . --no-cache; then
        echo -e "${GREEN}✓ Base image rebuilt successfully${NC}"
    else
        echo -e "${RED}Failed to rebuild base image${NC}"
        exit 1
    fi
    
    # Clean builder cache
    echo "Cleaning builder cache..."
    docker builder prune -af
    
    # Start Skaffold with no-cache profile and cache disabled
    echo -e "${YELLOW}Starting Skaffold in dev mode with forced rebuild (no cache)...${NC}"
    skaffold dev --cache-artifacts=false --profile=no-cache --trigger=polling --watch-poll-interval=2000 2>&1 | tee /tmp/skaffold-${USER}-$$.log &
else
    # Normal Skaffold dev mode with polling for file sync
    echo -e "${YELLOW}Starting Skaffold in dev mode with polling...${NC}"
    skaffold dev --trigger=polling --watch-poll-interval=2000 2>&1 | tee /tmp/skaffold-${USER}-$$.log &
fi

# Store Skaffold PID (it's the tee process, but that's OK for our cleanup)
SKAFFOLD_PID=$!

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
echo "This may take a few minutes on first run..."

# Get the log file path
SKAFFOLD_LOG="/tmp/skaffold-${USER}-$$.log"

# Wait for Skaffold to report deployments are stabilized
MAX_ATTEMPTS=300  # 10 minutes to allow for slow frontend builds
ATTEMPT=0
DEPLOYMENTS_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Check if Skaffold reports deployments are stabilized
    if grep -q "Deployments stabilized" "$SKAFFOLD_LOG" 2>/dev/null; then
        echo -e "${GREEN}✓ Skaffold reports all deployments are stabilized!${NC}"
        DEPLOYMENTS_READY=true
        
        # Additional verification - check critical services are actually responding
        echo -e "\n${YELLOW}Verifying service health endpoints...${NC}"
        
        # Check API health
        if kubectl exec deployment/api-service -n crucible -- curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ API service health check passed${NC}"
        else
            echo -e "  ${YELLOW}⚠ API service health check failed (may still be starting)${NC}"
        fi
        
        # Check Storage health
        if kubectl exec deployment/storage-service -n crucible -- curl -s http://localhost:8082/health > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Storage service health check passed${NC}"
        else
            echo -e "  ${YELLOW}⚠ Storage service health check failed (may still be starting)${NC}"
        fi
        
        break
    fi
    
    # Check for build/deploy errors
    if grep -q "Failed to deploy" "$SKAFFOLD_LOG" 2>/dev/null || grep -q "Build Failed" "$SKAFFOLD_LOG" 2>/dev/null; then
        echo -e "${RED}✗ Skaffold reported deployment failure!${NC}"
        echo "Check the log file: $SKAFFOLD_LOG"
        exit 1
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    if [ $((ATTEMPT % 10)) -eq 0 ]; then
        echo "  Still waiting for deployments to stabilize... ($ATTEMPT/$MAX_ATTEMPTS)"
        # Show current pod status
        kubectl get pods -n crucible --no-headers 2>/dev/null | awk '{print "    " $1 ": " $3}' | head -10
    fi
    sleep 2
done

if [ "$DEPLOYMENTS_READY" = false ]; then
    echo -e "${RED}Services did not become ready in time.${NC}"
    echo "Check pod status with: kubectl get pods -n crucible"
    echo "Check logs with: kubectl logs deployment/[service-name] -n crucible"
    echo "Check Skaffold log: $SKAFFOLD_LOG"
    exit 1
fi


# Display service status
echo -e "\n${GREEN}Platform Status:${NC}"
kubectl get pods -n crucible

# Display access URLs
echo -e "\n${GREEN}Access URLs:${NC}"
echo "  Frontend:        http://localhost:3000"
echo "  API:            http://localhost:8080/api"
echo "  API Docs:       http://localhost:8080/api/docs"
echo "  Storage API:    http://localhost:8081"

# Note about port forwarding
echo -e "\n${YELLOW}Note: If services are not accessible, you may need to set up port forwarding:${NC}"
echo "  kubectl port-forward deployment/api-service -n crucible 8080:8080 &"
echo "  kubectl port-forward deployment/storage-service -n crucible 8081:8081 &"
echo "  kubectl port-forward deployment/frontend -n crucible 3000:3000 &"

echo -e "\n${GREEN}Useful commands:${NC}"
echo "  View logs:      kubectl logs deployment/[service-name] -n crucible -f"
echo "  Get pods:       kubectl get pods -n crucible"
echo "  Describe pod:   kubectl describe pod [pod-name] -n crucible"
echo "  Shell into pod: kubectl exec -it deployment/[service-name] -n crucible -- /bin/bash"
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