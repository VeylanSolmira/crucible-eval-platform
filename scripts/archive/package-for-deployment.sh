#!/bin/bash
# Package Crucible platform for deployment

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${PROJECT_ROOT}/dist"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="crucible-platform-${TIMESTAMP}.tar.gz"

echo "🚀 Packaging Crucible Platform for deployment..."

# Create dist directory
mkdir -p "${OUTPUT_DIR}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

# Copy essential files
echo "📦 Copying files..."
cp -r "${PROJECT_ROOT}/app.py" "${TEMP_DIR}/"
cp -r "${PROJECT_ROOT}/src" "${TEMP_DIR}/"
cp -r "${PROJECT_ROOT}/pyproject.toml" "${TEMP_DIR}/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/requirements.txt" "${TEMP_DIR}/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/README.md" "${TEMP_DIR}/"

# Create requirements.txt if it doesn't exist
if [ ! -f "${TEMP_DIR}/requirements.txt" ]; then
    echo "📝 Generating requirements.txt..."
    cat > "${TEMP_DIR}/requirements.txt" <<EOF
# Core dependencies
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
prometheus-client>=0.19.0
openapi-core>=0.18.2

# Optional but recommended
redis>=5.0.0
celery>=5.3.0
EOF
fi

# Create deployment info
echo "📋 Adding deployment metadata..."
cat > "${TEMP_DIR}/DEPLOYMENT_INFO.txt" <<EOF
Deployment Package: ${PACKAGE_NAME}
Created: $(date)
Git Commit: $(cd "${PROJECT_ROOT}" && git rev-parse HEAD 2>/dev/null || echo "N/A")
Git Branch: $(cd "${PROJECT_ROOT}" && git branch --show-current 2>/dev/null || echo "N/A")
EOF

# Create .gitignore for deployment
cat > "${TEMP_DIR}/.gitignore" <<EOF
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
.env
*.log
storage/
*.db
EOF

# Package it up
echo "🗜️  Creating deployment package..."
cd "${TEMP_DIR}"
tar -czf "${OUTPUT_DIR}/${PACKAGE_NAME}" \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    .

# Create latest symlink
cd "${OUTPUT_DIR}"
ln -sf "${PACKAGE_NAME}" "crucible-platform-latest.tar.gz"

# Calculate package size
PACKAGE_SIZE=$(du -h "${OUTPUT_DIR}/${PACKAGE_NAME}" | cut -f1)

echo "✅ Deployment package created!"
echo "📦 Package: ${OUTPUT_DIR}/${PACKAGE_NAME}"
echo "📏 Size: ${PACKAGE_SIZE}"
echo ""
echo "🚀 To deploy to S3:"
echo "   aws s3 cp ${OUTPUT_DIR}/${PACKAGE_NAME} s3://your-bucket/"
echo "   # or"
echo "   aws s3 cp ${OUTPUT_DIR}/crucible-platform-latest.tar.gz s3://your-bucket/"
echo ""
echo "🔧 To deploy to EC2:"
echo "   terraform apply -var=\"deployment_bucket=your-bucket\" -var=\"deployment_key=${PACKAGE_NAME}\""