# Blue/Green Solutions with Current Terraform Setup

## Current Situation
- We have `for_each = toset(["blue", "green"])` on instances, EIPs, and security groups
- We need `lifecycle.ignore_changes` to be dynamic (not supported by Terraform)
- We want to update only green without touching blue

## Solution Options for Current Docker Compose Setup

### Option 1: Separate Terraform Modules
```bash
# infrastructure/terraform/modules/instance/main.tf
resource "aws_instance" "server" {
  # Single instance configuration
}

# infrastructure/terraform/blue.tf
module "blue_instance" {
  source = "./modules/instance"
  color  = "blue"
}

# infrastructure/terraform/green.tf  
module "green_instance" {
  source = "./modules/instance"
  color  = "green"
}
```
Then: `tofu apply -target=module.green_instance`

### Option 2: Terraform Workspaces with Conditionals
```hcl
resource "aws_instance" "eval_server" {
  for_each = toset(terraform.workspace == "blue" ? ["blue"] : ["green"])
  # ... rest of config
}
```
Then:
```bash
tofu workspace select green
tofu apply
```

### Option 3: External Data Source Pattern
```hcl
data "external" "deployment_config" {
  program = ["bash", "-c", "echo '{\"colors\": \"${DEPLOY_COLORS:-blue,green}\"}'"]
}

locals {
  enabled_colors = split(",", data.external.deployment_config.result.colors)
}

resource "aws_instance" "eval_server" {
  for_each = toset(local.enabled_colors)
}
```
Then: `DEPLOY_COLORS=green tofu apply`

### Option 4: Just Use -target (Embrace the Ugliness)
Create an alias or script:
```bash
alias deploy-green='tofu apply \
  -target=aws_instance.eval_server[\"green\"] \
  -target=aws_eip.eval_server[\"green\"] \
  -target=aws_eip_association.eval_server[\"green\"] \
  -target=aws_security_group.eval_server_color[\"green\"] \
  -target=module.monitoring'
```

## After Moving to Kubernetes

The entire problem disappears because Kubernetes has built-in deployment strategies:

### Option 1: Kubernetes Native Blue/Green
```yaml
# blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crucible-blue
  labels:
    version: blue

# green-deployment.yaml  
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crucible-green
  labels:
    version: green

# service.yaml - Point to active color
selector:
  app: crucible
  version: blue  # Switch to green when ready
```

Deploy: `kubectl apply -f green-deployment.yaml`
Switch: `kubectl patch service crucible -p '{"spec":{"selector":{"version":"green"}}}'`

### Option 2: GitOps with Flux/ArgoCD
```yaml
# Flux HelmRelease
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: crucible-green
spec:
  values:
    image:
      tag: ${GREEN_VERSION}
```
Just commit changes, Flux deploys automatically.

### Option 3: Kubernetes + Terraform (Best of Both)
```hcl
# Terraform manages the cluster
resource "aws_eks_cluster" "main" {
  name = "crucible-platform"
}

# Kubernetes provider manages deployments
resource "kubernetes_deployment" "green" {
  count = var.deploy_green ? 1 : 0
  # ... deployment config
}
```

### Option 4: Service Mesh (Istio/Linkerd)
```yaml
# VirtualService for traffic management
spec:
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: crucible
        subset: green
  - route:
    - destination:
        host: crucible
        subset: blue
```

## Why Kubernetes Makes This Natural

1. **Deployments are separate from infrastructure** - EKS cluster stays up, deployments change
2. **Built-in traffic management** - Services, Ingress, Service Mesh
3. **Native rollback** - `kubectl rollout undo`
4. **GitOps friendly** - Declarative configs in Git
5. **No state conflicts** - Each deployment is independent

## Recommendation

For now with Docker Compose: **Use Option 4 (targeted applies)** - It's ugly but it works and doesn't require restructuring.

After Kubernetes: The problem doesn't exist. Use native Kubernetes deployments + GitOps.