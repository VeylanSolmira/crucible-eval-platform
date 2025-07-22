#!/bin/bash
# Security scanning script using Docker Scout
# Run this before commits or as part of CI/CD

set -e

echo "🔍 Docker Scout Security Scan"
echo "============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Images to scan
IMAGES=(
    "crucible-base"
    "crucible-platform/api-service"
    "crucible-platform/storage_service"
    "crucible-platform/storage_worker"
    "crucible-platform/celery_worker"
    "crucible-platform/dispatcher_service"
    "crucible-platform/executor-ml"
)

# Track if any critical vulnerabilities found
CRITICAL_FOUND=0

# Scan each image
for IMAGE in "${IMAGES[@]}"; do
    echo "Scanning $IMAGE..."
    
    # Check if image exists
    if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Image $IMAGE not found, skipping${NC}"
        echo ""
        continue
    fi
    
    # Run quickview and capture output
    OUTPUT=$(docker scout quickview "$IMAGE" 2>&1 || true)
    
    # Extract vulnerability counts using grep
    if echo "$OUTPUT" | grep -q "Storing image for indexing"; then
        # Parse the vulnerability summary line
        VULN_LINE=$(echo "$OUTPUT" | grep -E "^\s*Target.*[0-9]+C.*[0-9]+H.*[0-9]+M.*[0-9]+L" | head -1)
        
        if [[ -n "$VULN_LINE" ]]; then
            # Extract critical count (number before 'C')
            CRITICAL=$(echo "$VULN_LINE" | grep -oE "[0-9]+C" | grep -oE "[0-9]+" || echo "0")
            HIGH=$(echo "$VULN_LINE" | grep -oE "[0-9]+H" | grep -oE "[0-9]+" || echo "0")
            
            if [[ "$CRITICAL" -gt 0 ]]; then
                echo -e "${RED}❌ CRITICAL: $IMAGE has $CRITICAL critical vulnerabilities!${NC}"
                CRITICAL_FOUND=1
            elif [[ "$HIGH" -gt 0 ]]; then
                echo -e "${YELLOW}⚠️  WARNING: $IMAGE has $HIGH high vulnerabilities${NC}"
            else
                echo -e "${GREEN}✅ OK: $IMAGE has no critical/high vulnerabilities${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  Could not scan $IMAGE${NC}"
    fi
    
    echo ""
done

# Summary and recommendations
echo "============================="
if [[ $CRITICAL_FOUND -eq 1 ]]; then
    echo -e "${RED}❌ CRITICAL VULNERABILITIES FOUND!${NC}"
    echo ""
    echo "Run these commands for details:"
    echo "  docker scout cves <image-name>"
    echo "  docker scout recommendations <image-name>"
    echo ""
    echo "To fix base image vulnerabilities:"
    echo "  1. Update dependencies in requirements files"
    echo "  2. Rebuild base image: docker build -f shared/docker/base.Dockerfile -t crucible-base ."
    echo "  3. Rebuild all dependent images"
    exit 1
else
    echo -e "${GREEN}✅ No critical vulnerabilities found${NC}"
    echo ""
    echo "For detailed reports, run:"
    echo "  docker scout cves <image-name>"
fi