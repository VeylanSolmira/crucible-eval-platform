#!/bin/bash
set -ex

# Log output to file for debugging
exec > >(tee /var/log/k3s-install.log)
exec 2>&1

# Add SSH key for ubuntu user
echo "${ssh_public_key}" >> /home/ubuntu/.ssh/authorized_keys
chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys
chmod 600 /home/ubuntu/.ssh/authorized_keys

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
apt-get install -y docker.io
systemctl enable docker
systemctl start docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install K3s (lightweight Kubernetes)
# Using K3s instead of full K8s because t2.micro only has 1GB RAM
curl -sfL https://get.k3s.io | sh -s - \
  --disable traefik \
  --disable servicelb \
  --disable-cloud-controller \
  --write-kubeconfig-mode 644 \
  --node-name ${cluster_name}-node

# Wait for K3s to be ready
sleep 30
until kubectl get nodes; do
  echo "Waiting for K3s to start..."
  sleep 5
done

# Create .kube config for ubuntu user
mkdir -p /home/ubuntu/.kube
cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
chown -R ubuntu:ubuntu /home/ubuntu/.kube
chmod 600 /home/ubuntu/.kube/config

# Replace localhost with actual IP in kubeconfig
INSTANCE_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
sed -i "s/127.0.0.1/$INSTANCE_IP/g" /home/ubuntu/.kube/config

# Label the node
kubectl label node ${cluster_name}-node node-role.kubernetes.io/master=true
kubectl label node ${cluster_name}-node node-role.kubernetes.io/worker=true

# Create a namespace for our apps
kubectl create namespace crucible

echo "K3s installation complete!"