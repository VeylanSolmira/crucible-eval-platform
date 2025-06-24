#!/bin/bash
# Setup script for Python virtual environment

echo "🔧 Setting up Python virtual environment for METR Evaluation Platform..."

# Get the script directory (which IS the project root now)
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment at project root..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🚀 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Install the project in development mode (if setup.py exists)
if [ -f "setup.py" ]; then
    echo "🔗 Installing project in development mode..."
    pip install -e .
fi

echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate, run:"
echo "  deactivate"