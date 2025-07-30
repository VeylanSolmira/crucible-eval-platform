#!/bin/bash
set -euo pipefail

# gVisor installer script for EKS nodes
# This script is run as an init container and exits after installation

LOG_FILE="/host/var/log/gvisor-installer.log"
CONTAINERD_CONFIG="/host/etc/containerd/config.toml"
GVISOR_VERSION="20240729.0"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if already installed
check_gvisor_installed() {
    if [ -f "/host/usr/local/bin/runsc" ] && [ -f "/host/usr/local/bin/containerd-shim-runsc-v1" ]; then
        log "gVisor binaries already present"
        
        # Check if containerd already has gVisor configured
        if grep -q "plugins.\"io.containerd.grpc.v1.cri\".containerd.runtimes.runsc" "$CONTAINERD_CONFIG"; then
            log "gVisor runtime already configured in containerd"
            return 0
        else
            log "gVisor binaries present but containerd not configured"
            return 1
        fi
    fi
    return 1
}

# Install gVisor binaries
install_gvisor() {
    log "Installing gVisor version $GVISOR_VERSION..."
    
    # Install required tools if not present
    if ! command -v curl &> /dev/null; then
        log "Installing curl..."
        apt-get update && apt-get install -y curl
    fi
    
    cd /tmp
    
    # Download gVisor binaries
    log "Downloading runsc..."
    curl -fsSL "https://storage.googleapis.com/gvisor/releases/release/${GVISOR_VERSION}/x86_64/runsc" -o runsc
    curl -fsSL "https://storage.googleapis.com/gvisor/releases/release/${GVISOR_VERSION}/x86_64/runsc.sha512" -o runsc.sha512
    
    log "Downloading containerd-shim-runsc-v1..."
    curl -fsSL "https://storage.googleapis.com/gvisor/releases/release/${GVISOR_VERSION}/x86_64/containerd-shim-runsc-v1" -o containerd-shim-runsc-v1
    curl -fsSL "https://storage.googleapis.com/gvisor/releases/release/${GVISOR_VERSION}/x86_64/containerd-shim-runsc-v1.sha512" -o containerd-shim-runsc-v1.sha512
    
    # Verify checksums
    log "Verifying checksums..."
    sha512sum -c runsc.sha512
    sha512sum -c containerd-shim-runsc-v1.sha512
    
    # Install binaries
    log "Installing binaries..."
    chmod +x runsc containerd-shim-runsc-v1
    cp runsc /host/usr/local/bin/
    cp containerd-shim-runsc-v1 /host/usr/local/bin/
    
    log "gVisor binaries installed successfully"
}

# Configure containerd using ConfigMap approach
configure_containerd() {
    log "Configuring containerd for gVisor..."
    
    # Backup original config
    if [ ! -f "${CONTAINERD_CONFIG}.original" ]; then
        cp "$CONTAINERD_CONFIG" "${CONTAINERD_CONFIG}.original"
        log "Backed up original containerd config"
    fi
    
    # Check if gVisor runtime already configured
    if grep -q "plugins.\"io.containerd.grpc.v1.cri\".containerd.runtimes.runsc" "$CONTAINERD_CONFIG"; then
        log "gVisor runtime already configured in containerd"
        return 0
    fi
    
    # Copy the complete config from ConfigMap
    log "Applying containerd config with gVisor runtime..."
    cp /config/config.toml "$CONTAINERD_CONFIG"
    
    log "containerd config updated with gVisor runtime"
}

# Restart containerd
restart_containerd() {
    log "Restarting containerd..."
    
    # Use nsenter to execute systemctl in the host namespace
    nsenter --target 1 --mount --uts --ipc --net --pid -- systemctl restart containerd
    
    # Wait for containerd to be ready
    log "Waiting for containerd to stabilize..."
    sleep 10
    
    # Verify containerd is running
    if nsenter --target 1 --mount --uts --ipc --net --pid -- systemctl is-active --quiet containerd; then
        log "containerd restarted successfully"
    else
        log "ERROR: containerd failed to restart"
        exit 1
    fi
}

# Verify installation
verify_installation() {
    log "Verifying gVisor installation..."
    
    # Check if runsc is accessible
    if nsenter --target 1 --mount --uts --ipc --net --pid -- /usr/local/bin/runsc --version; then
        log "runsc binary verified"
    else
        log "ERROR: runsc binary not accessible"
        return 1
    fi
    
    # Check if runtime is registered with containerd
    log "Checking containerd config for runsc:"
    if grep -q "plugins.\"io.containerd.grpc.v1.cri\".containerd.runtimes.runsc" "$CONTAINERD_CONFIG"; then
        log "SUCCESS: gVisor runtime configured in containerd"
        return 0
    else
        log "ERROR: gVisor runtime not found in containerd config"
        return 1
    fi
}

# Main installation flow
main() {
    log "=== Starting gVisor installation ==="
    log "Node: $(hostname)"
    log "Kernel: $(uname -r)"
    
    # Get the node name from environment or hostname
    NODE_NAME="${NODE_NAME:-$(hostname)}"
    log "Node name: $NODE_NAME"
    
    # Check if already installed
    if check_gvisor_installed; then
        log "gVisor is already fully installed and configured"
        log "=== Installation complete (no action needed) ==="
        exit 0
    fi
    
    # Install gVisor
    install_gvisor
    
    # Configure containerd
    configure_containerd
    
    # Restart containerd
    restart_containerd
    
    # Verify installation
    if verify_installation; then
        log "=== gVisor installation completed successfully ==="
        exit 0
    else
        log "=== gVisor installation failed ==="
        exit 1
    fi
}

# Run main function
main