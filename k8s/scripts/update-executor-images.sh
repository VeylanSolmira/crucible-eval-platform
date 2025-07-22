#!/bin/bash
# Update executor-images ConfigMap with current Skaffold image SHAs

# Get the ML image that was stored by the build hook
ML_IMAGE=$(kubectl get configmap executor-images -n crucible -o jsonpath='{.data.ml-image}')
echo "ML_IMAGE from ConfigMap: ${ML_IMAGE}"

# Get base image from ConfigMap (if it exists)
BASE_IMAGE=$(kubectl get configmap executor-images -n crucible -o jsonpath='{.data.base-image}' 2>/dev/null)
echo "BASE_IMAGE from ConfigMap: ${BASE_IMAGE}"

# TODO: Remove this fallback once executor-base is added to Skaffold builds
# Default to a placeholder if base image not found
BASE_IMAGE=${BASE_IMAGE:-"crucible-platform/base:latest"}


# Exit with error if ML_IMAGE is empty
if [ -z "${ML_IMAGE}" ]; then
    echo "ERROR: Could not find executor-ml image in cluster"
    exit 1
fi

# Create/update the ConfigMap
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: executor-images
  namespace: crucible
data:
  images.yaml: |
    images:
      - name: "python-base"
        image: "${BASE_IMAGE}"
        description: "Basic Python 3.11 environment"
      - name: "python-ml"
        image: "${ML_IMAGE}"
        description: "Python with ML libraries (PyTorch, NumPy, etc.)"
        default: true
EOF