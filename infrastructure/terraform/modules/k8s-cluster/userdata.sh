#!/bin/bash
set -ex

# Add SSH key
echo "${ssh_public_key}" >> /home/ubuntu/.ssh/authorized_keys

# Install K3s agent that will auto-join the cluster
# Note: First node becomes the server, others join as agents

# Check if this is the first node by looking for existing K3s server
K3S_URL=""
K3S_TOKEN=""

# Try to find existing server in the cluster
for i in {1..30}; do
  # Get all instances in the ASG
  INSTANCE_IPS=$(aws ec2 describe-instances \
    --filters "Name=tag:k8s.io/cluster-autoscaler/${cluster_name},Values=owned" \
              "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].PrivateIpAddress' \
    --output text \
    --region $(ec2-metadata --availability-zone | cut -d' ' -f2 | sed 's/[a-z]$//')
  )
  
  for ip in $INSTANCE_IPS; do
    if [[ "$ip" != "$(ec2-metadata --local-ipv4 | cut -d' ' -f2)" ]]; then
      # Try to get token from existing server
      if curl -sf http://$ip:6443 > /dev/null 2>&1; then
        K3S_URL="https://$ip:6443"
        # For demo purposes, using a fixed token. In production, store in Secrets Manager
        K3S_TOKEN="MySecretClusterToken123"
        break 2
      fi
    fi
  done
  
  sleep 5
done

# Install K3s
if [[ -z "$K3S_URL" ]]; then
  # This is the first node - install as server
  echo "Installing as K3s server (first node)"
  curl -sfL https://get.k3s.io | sh -s - server \
    --token="MySecretClusterToken123" \
    --write-kubeconfig-mode 644 \
    --disable traefik \
    --disable servicelb \
    --node-taint CriticalAddonsOnly=true:NoExecute \
    --node-label node.kubernetes.io/instance-type=$(ec2-metadata --instance-type | cut -d' ' -f2)
    
  # Wait for K3s to be ready
  sleep 30
  
  # Remove taint from first node so pods can schedule
  kubectl taint nodes $(hostname) CriticalAddonsOnly-
  
  # Copy kubeconfig for external access
  PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
  cp /etc/rancher/k3s/k3s.yaml /tmp/kubeconfig
  sed -i "s/127.0.0.1/$PUBLIC_IP/g" /tmp/kubeconfig
  
  # Upload kubeconfig to S3 (optional, for easy access)
  # aws s3 cp /tmp/kubeconfig s3://${cluster_name}-config/kubeconfig
  
else
  # This is an additional node - install as agent
  echo "Installing as K3s agent, joining $K3S_URL"
  curl -sfL https://get.k3s.io | K3S_URL=$K3S_URL K3S_TOKEN=$K3S_TOKEN sh -s - agent \
    --node-label node.kubernetes.io/instance-type=$(ec2-metadata --instance-type | cut -d' ' -f2)
fi

# Install AWS CLI and instance metadata tool
apt-get update
apt-get install -y awscli amazon-ec2-utils

# Wait for K3s to be ready
until kubectl get nodes > /dev/null 2>&1; do
  echo "Waiting for K3s to be ready..."
  sleep 5
done

# Install ECR credentials controller (only on first/server node)
if [[ -z "$K3S_URL" ]]; then
  echo "Installing ECR credentials controller..."
  kubectl apply -f https://raw.githubusercontent.com/nabsul/k8s-ecr-login-renew/main/deploy/all-in-one.yaml
fi

echo "K3s installation complete!"