# Kubernetes Ingress Configuration

This directory contains the Ingress setup that replaces the nginx container in Kubernetes.

## Overview

The nginx container functionality is replaced by:
1. **NGINX Ingress Controller** - Runs nginx at the cluster level
2. **Ingress resources** - Define routing rules
3. **cert-manager** - Automatic SSL certificates from Let's Encrypt

## Setup Instructions

### 1. Install NGINX Ingress Controller

```bash
# Option A: Standard installation
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Option B: With our custom configuration
kubectl apply -f nginx-ingress-controller.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

### 2. Install cert-manager (for SSL)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=60s

# Create certificate issuers
kubectl apply -f cert-manager.yaml
```

### 3. Update domain names

Edit `ingress.yaml` and replace `crucible.example.com` with your actual domain.

### 4. Deploy Ingress rules

```bash
kubectl apply -f ingress.yaml
```

### 5. Deploy Flower service (if using Celery monitoring)

```bash
# Create auth secret first
kubectl create secret generic flower-auth \
  --from-literal=basic-auth='admin:your-password-here' \
  -n crucible

# Deploy Flower
kubectl apply -f flower-service.yaml
```

## Feature Mapping

| nginx.conf Feature | Kubernetes Implementation |
|-------------------|--------------------------|
| SSL/TLS termination | Ingress Controller + cert-manager |
| Rate limiting (30r/s general) | `nginx.ingress.kubernetes.io/limit-rps: "30"` |
| Rate limiting (10r/s API) | Separate Ingress with `limit-rps: "10"` |
| Security headers | ConfigMap `custom-headers` |
| Path routing | Ingress rules |
| WebSocket support | Separate Ingress with upgrade headers |
| Static file caching | Browser caching (frontend handles) |
| HTTP→HTTPS redirect | `ssl-redirect: "true"` annotation |
| Gzip compression | ConfigMap setting |
| Client body size 50M | `proxy-body-size: "50m"` annotation |

## Differences from Docker Compose

1. **No nginx container** - Ingress Controller handles everything
2. **Dynamic certificates** - cert-manager auto-renews Let's Encrypt certs
3. **Multiple Ingress resources** - Different rate limits for different paths
4. **Cluster-wide** - Ingress Controller serves all namespaces

## Testing

```bash
# Check Ingress Controller is running
kubectl get pods -n ingress-nginx

# Check Ingress rules
kubectl describe ingress -n crucible

# Check certificate status
kubectl get certificate -n crucible

# Test endpoints
curl https://your-domain.com/health
curl https://your-domain.com/api/status
```

## Troubleshooting

### Certificate not issuing
```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate status
kubectl describe certificate crucible-tls -n crucible

# Check challenges
kubectl get challenges -n crucible
```

### Rate limiting not working
```bash
# Check Ingress Controller config
kubectl get configmap nginx-configuration -n ingress-nginx -o yaml

# Check Ingress annotations
kubectl get ingress crucible-ingress -n crucible -o yaml
```

### WebSocket connection failing
- Ensure the WebSocket ingress is applied
- Check that `/api/events/stream` is only in the WebSocket ingress

## Local Development

For local K3s/minikube, you might need to:
1. Use `letsencrypt-staging` instead of prod
2. Or create self-signed certificates
3. Or use HTTP only (remove TLS section from Ingress)