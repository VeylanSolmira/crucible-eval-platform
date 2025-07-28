#!/bin/bash
# Build and push all images to ECR

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# ECR Registry
ECR_REGISTRY="503132503803.dkr.ecr.us-west-2.amazonaws.com"

# Generate a tag (git commit hash or 'latest')
if [ -n "$1" ]; then
    TAG="$1"
elif [ -d .git ]; then
    TAG=$(git rev-parse --short HEAD)
else
    TAG="latest"
fi

echo -e "${GREEN}Building images with tag: $TAG${NC}"

# Generate OpenAPI specs first (needed for frontend build)
echo -e "${YELLOW}Generating OpenAPI specs...${NC}"
if [ -f ./scripts/generate-all-openapi-specs.sh ]; then
    ./scripts/generate-all-openapi-specs.sh || echo "Warning: OpenAPI generation had issues"
fi

# Login to ECR
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build base image first (others depend on it)
echo -e "${YELLOW}Building base image for AMD64...${NC}"
TAG=$TAG docker buildx bake -f docker-compose.build.yml --set '*.platform=linux/amd64' --push base

# Build all other images in parallel
echo -e "${YELLOW}Building all other images for AMD64...${NC}"
TAG=$TAG docker buildx bake -f docker-compose.build.yml --set '*.platform=linux/amd64' --push

# Push all images (except base which has build-only profile)
echo -e "${YELLOW}Pushing images to ECR...${NC}"
TAG=$TAG docker compose -f docker-compose.build.yml push

echo -e "${GREEN}✅ All images built and pushed with tag: $TAG${NC}"
echo ""
echo "Update your k8s/overlays/dev/kustomization.yaml with:"
echo "  newTag: $TAG"