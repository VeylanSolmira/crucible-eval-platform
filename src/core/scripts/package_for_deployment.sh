#!/bin/bash
# Package evolution directory with all components for deployment

echo "📦 Packaging evolution directory for deployment..."

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
PACKAGE_NAME="evolution-package.tar.gz"

# Copy the evolution directory
cp -r . "$TEMP_DIR/evolution"

# Remove any unnecessary files
find "$TEMP_DIR/evolution" -name "*.pyc" -delete
find "$TEMP_DIR/evolution" -name "__pycache__" -delete
find "$TEMP_DIR/evolution" -name ".DS_Store" -delete
rm -rf "$TEMP_DIR/evolution/reference"  # Remove reference implementations
rm -rf "$TEMP_DIR/evolution/frontier_storage"  # Remove local storage

# Create the tarball
cd "$TEMP_DIR"
tar czf "$PACKAGE_NAME" evolution/

# Move back to original directory
cd - > /dev/null
mv "$TEMP_DIR/$PACKAGE_NAME" .

# Cleanup
rm -rf "$TEMP_DIR"

echo "✅ Package created: $PACKAGE_NAME"
echo ""
echo "📤 To deploy to your Linux server:"
echo "   scp $PACKAGE_NAME ubuntu@44.246.137.198:~/"
echo ""
echo "📥 On your Linux server:"
echo "   tar xzf $PACKAGE_NAME"
echo "   cd evolution"
echo "   python3 extreme_mvp_frontier_events.py"