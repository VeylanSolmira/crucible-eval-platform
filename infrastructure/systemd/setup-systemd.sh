#!/bin/bash
# Setup systemd service for Crucible Evaluation Platform

set -e

echo "🔧 Setting up systemd service for Crucible Evaluation Platform"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Copy service file
echo "📋 Installing service file..."
cp crucible-platform.service /etc/systemd/system/

# Set proper permissions
chmod 644 /etc/systemd/system/crucible-platform.service

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service..."
systemctl enable crucible-platform.service

# Start the service
echo "🚀 Starting service..."
systemctl start crucible-platform.service

# Check status
echo "📊 Checking service status..."
systemctl status crucible-platform.service --no-pager

echo ""
echo "✅ Setup complete!"
echo ""
echo "Useful commands:"
echo "  - Check status:  sudo systemctl status crucible-platform"
echo "  - View logs:     sudo journalctl -u crucible-platform -f"
echo "  - Stop service:  sudo systemctl stop crucible-platform"
echo "  - Start service: sudo systemctl start crucible-platform"
echo "  - Restart:       sudo systemctl restart crucible-platform"
echo "  - Disable:       sudo systemctl disable crucible-platform"