# Required CLI Tools for Kubernetes Development

## Essential Tools (Must Have)

### 1. kind - Kubernetes in Docker
Creates local Kubernetes clusters using Docker containers as nodes.

```bash
# Install with Homebrew
brew install kind

# Verify installation
kind --version

# Basic usage
kind create cluster --name my-cluster
kind delete cluster --name my-cluster
```

### 2. kubectl - Kubernetes CLI
The primary command-line tool for interacting with Kubernetes clusters.

```bash
# Install with Homebrew
brew install kubectl

# Verify installation
kubectl version --client

# Basic usage
kubectl get pods
kubectl apply -f deployment.yaml
kubectl logs pod-name
```

## Highly Recommended Tools

### 3. k9s - Terminal UI for Kubernetes
A terminal-based UI that provides a real-time view of your cluster.

```bash
# Install with Homebrew
brew install k9s

# Run it (after cluster is created)
k9s

# Navigation
# - Use arrow keys to navigate
# - Press 'd' to describe
# - Press 'l' to view logs
# - Press '?' for help
```

**Why it's great for learning**: Visual feedback helps understand what's happening in your cluster.

### 4. stern - Multi-pod Log Tailing
Tail logs from multiple pods simultaneously.

```bash
# Install with Homebrew
brew install stern

# Example usage
stern frontend              # All pods with 'frontend' in name
stern . -n production      # All pods in production namespace
stern . --tail 50          # Last 50 lines from each pod
```

### 5. kubectx + kubens - Context/Namespace Switching
Quickly switch between clusters and namespaces.

```bash
# Install both with Homebrew
brew install kubectx

# kubectx - switch between clusters
kubectx                     # List contexts
kubectx kind-crucible      # Switch to context
kubectx -                 # Switch to previous

# kubens - switch between namespaces  
kubens                     # List namespaces
kubens production         # Switch namespace
kubens -                  # Previous namespace
```

## Nice to Have (Install Later)

### 6. helm - Kubernetes Package Manager
```bash
brew install helm

# Used for installing pre-packaged applications
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install my-redis bitnami/redis
```

### 7. kustomize - Template-free Configuration
```bash
brew install kustomize

# Or use built-in kubectl version
kubectl apply -k overlays/production/
```

## Quick Install Script

Install all essential and recommended tools at once:

```bash
# Install everything
brew install kind kubectl k9s stern kubectx

# Verify all installations
echo "=== Checking installations ==="
kind --version
kubectl version --client
k9s --version
stern --version
kubectx --version
```

## Tool Purpose Summary

| Tool | Purpose | When You'll Use It |
|------|---------|-------------------|
| **kind** | Create local clusters | Every time you start |
| **kubectl** | Interact with K8s | Constantly |
| **k9s** | Visual cluster view | Debugging/monitoring |
| **stern** | Multi-pod logs | Debugging distributed apps |
| **kubectx** | Switch clusters | Multiple environments |
| **kubens** | Switch namespaces | Working with namespaces |

## Learning Path

1. **Start with**: Just `kind` and `kubectl`
2. **Add k9s**: Once you have your first pod running
3. **Add stern**: When you have multiple pods
4. **Add kubectx/kubens**: When managing multiple clusters/namespaces

## Pro Tips

1. **Shell Aliases**: Add to your `.zshrc`:
   ```bash
   alias k=kubectl
   alias kgp='kubectl get pods'
   alias kgs='kubectl get svc'
   alias kaf='kubectl apply -f'
   ```

2. **Kubectl Autocomplete**:
   ```bash
   echo 'source <(kubectl completion zsh)' >> ~/.zshrc
   ```

3. **K9s Skins**: Make k9s prettier:
   ```bash
   # Download skins
   mkdir -p ~/.k9s/skins
   # Then add skin files from https://github.com/derailed/k9s/tree/master/skins
   ```

Start simple with kind + kubectl, then add tools as needed!