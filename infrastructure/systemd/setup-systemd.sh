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
cp evaluation-platform.service /etc/systemd/system/

# Set proper permissions
chmod 644 /etc/systemd/system/evaluation-platform.service

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service..."
systemctl enable evaluation-platform.service

# Start the service
echo "🚀 Starting service..."
systemctl start evaluation-platform.service

# Check status
echo "📊 Checking service status..."
systemctl status evaluation-platform.service --no-pager

echo ""
echo "✅ Setup complete!"
echo ""
echo "Useful commands:"
echo "  - Check status:  sudo systemctl status evaluation-platform"
echo "  - View logs:     sudo journalctl -u evaluation-platform -f"
echo "  - Stop service:  sudo systemctl stop evaluation-platform"
echo "  - Start service: sudo systemctl start evaluation-platform"
echo "  - Restart:       sudo systemctl restart evaluation-platform"
echo "  - Disable:       sudo systemctl disable evaluation-platform"