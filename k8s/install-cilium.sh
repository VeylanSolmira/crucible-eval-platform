#!/bin/bash
# Install Cilium CNI for NetworkPolicy support

# Install Cilium CLI
if ! command -v cilium &> /dev/null; then
    echo "Installing Cilium CLI..."
    CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
    GOOS=$(go env GOOS)
    GOARCH=$(go env GOARCH)
    curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-${GOOS}-${GOARCH}.tar.gz
    sudo tar -C /usr/local/bin -xzvf cilium-${GOOS}-${GOARCH}.tar.gz
    rm cilium-${GOOS}-${GOARCH}.tar.gz
fi

# Install Cilium in the cluster
echo "Installing Cilium in cluster..."
cilium install --version 1.15.0

# Wait for Cilium to be ready
echo "Waiting for Cilium to be ready..."
cilium status --wait

# Enable Hubble for network observability (optional)
echo "Enabling Hubble..."
cilium hubble enable

echo "Cilium installation complete!"