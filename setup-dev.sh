#!/bin/bash
# Setup development environment the professional way

echo "🔧 Setting up Crucible Platform for development"
echo "============================================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install in development mode
echo "Installing package in development mode..."
pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the platform professionally:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Run as module: python -m src.platform"
echo "  3. Or use script: crucible --help"
echo ""
echo "The 'crucible' command is now available in your PATH when venv is active."