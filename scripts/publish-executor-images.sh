#!/bin/bash
# Publish user-selectable executor images to ECR
# These are the stable, versioned images that users can select for evaluations

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Load .env file if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configuration
ECR_REPO="${ECR_REPOSITORY:-$ECR_REGISTRY}"  # Support both naming conventions
PROJECT_NAME="${PROJECT_NAME:-crucible-platform}"
VERSION="${VERSION:-latest}"

# Check if ECR_REPO is set
if [ -z "$ECR_REPO" ]; then
    echo -e "${RED}Error: ECR_REGISTRY must be set in .env or ECR_REPOSITORY environment variable${NC}"
    echo "Example: ECR_REGISTRY=123456789.dkr.ecr.us-east-1.amazonaws.com"
    exit 1
fi

echo -e "${YELLOW}Publishing executor images to $ECR_REPO...${NC}"

# Login to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
if aws ecr get-login-password --region ${AWS_REGION:-us-west-2} | docker login --username AWS --password-stdin $ECR_REPO; then
    echo -e "${GREEN}✓ Successfully logged in to ECR${NC}"
else
    echo -e "${RED}✗ Failed to login to ECR${NC}"
    exit 1
fi

# Find all executor directories (those with Dockerfile)
EXECUTORS=()
for dir in evaluation-environments/*/; do
    if [[ -f "$dir/Dockerfile" ]] && [[ $(basename "$dir") != "shared" ]]; then
        EXECUTORS+=("$(basename "$dir")")
    fi
done

echo -e "${YELLOW}Found ${#EXECUTORS[@]} executor images: ${EXECUTORS[*]}${NC}"

for executor in "${EXECUTORS[@]}"; do
    echo -e "\n${YELLOW}Processing $executor...${NC}"
    
    # Check if repository exists, create if not
    echo -e "${YELLOW}Checking if ECR repository '$executor' exists...${NC}"
    if aws ecr describe-repositories --repository-names $executor --region ${AWS_REGION:-us-west-2} >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Repository $executor already exists${NC}"
    else
        echo -e "${YELLOW}Creating ECR repository '$executor'...${NC}"
        if aws ecr create-repository --repository-name $executor --region ${AWS_REGION:-us-west-2} >/dev/null; then
            echo -e "${GREEN}✓ Created repository $executor${NC}"
        else
            echo -e "${RED}✗ Failed to create repository $executor${NC}"
            exit 1
        fi
    fi
    
    # Build the image
    echo -e "${YELLOW}Building $executor:$VERSION...${NC}"
    if docker build -f evaluation-environments/$executor/Dockerfile \
                   -t $executor:$VERSION .; then
        echo -e "${GREEN}✓ Built $executor successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build $executor${NC}"
        exit 1
    fi
    
    # Tag for ECR (standard format: registry/repository:tag)
    docker tag $executor:$VERSION $ECR_REPO/$executor:$VERSION
    
    # Push to ECR
    echo -e "${YELLOW}Pushing to ECR as $executor:$VERSION...${NC}"
    if docker push $ECR_REPO/$executor:$VERSION; then
        echo -e "${GREEN}✓ Pushed to ECR successfully${NC}"
    else
        echo -e "${RED}✗ Failed to push $executor${NC}"
        exit 1
    fi
done

echo -e "\n${GREEN}✓ All executor images published successfully!${NC}"
echo -e "Available images:"
for executor in "${EXECUTORS[@]}"; do
    echo -e "  - $ECR_REPO/$executor:$VERSION"
done