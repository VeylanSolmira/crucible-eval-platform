# GPU Instance Setup for Model Testing

## Overview

This Terraform configuration provides GPU instances for testing language models as part of adversarial AI evaluation. The setup is **disabled by default** to avoid unnecessary costs.

## Instance Types Available

### 1. **small_model** (g4dn.xlarge)
- **GPU**: NVIDIA T4 (16GB VRAM)
- **Use case**: Llama 3.2-1B, Phi-3-mini, GPT-2
- **Cost**: $0.526/hour on-demand, ~$0.15-0.25/hour spot
- **Best for**: MVP testing, quick experiments

### 2. **medium_model** (g4dn.2xlarge)
- **GPU**: NVIDIA T4 (16GB VRAM) + more CPU
- **Use case**: Mistral-7B, Llama-2-7B
- **Cost**: $1.052/hour on-demand, ~$0.30-0.50/hour spot
- **Best for**: Testing larger models

### 3. **large_model** (g5.2xlarge)
- **GPU**: NVIDIA A10G (24GB VRAM)
- **Use case**: 13B models or multiple 7B models
- **Cost**: $2.012/hour on-demand
- **Best for**: Production testing, multi-model comparison

### 4. **budget_gpu** (g3s.xlarge)
- **GPU**: NVIDIA M60 (8GB VRAM)
- **Use case**: GPT-2, small models only
- **Cost**: $0.225/hour on-demand, ~$0.07-0.15/hour spot
- **Best for**: Budget-conscious testing

## How to Enable

### Option 1: Using terraform.tfvars
```bash
echo 'gpu_instances_enabled = true' >> terraform.tfvars
tofu plan
tofu apply
```

### Option 2: Command line variable
```bash
tofu apply -var="gpu_instances_enabled=true"
```

### Option 3: Selective instance creation
```bash
# Just create the launch templates (no cost)
tofu apply -var="gpu_instances_enabled=true"

# Then manually launch instances from AWS Console using the templates
```

## What Gets Created

When `gpu_instances_enabled = true`:

1. **Security Group**: Allows SSH, Jupyter (8888), and model API (8000)
2. **IAM Role**: For S3 model storage access
3. **Launch Templates**: Pre-configured for each instance type
4. **Spot Requests**: For cost-optimized instances (if spot_enabled)
5. **On-Demand Instances**: For stable workloads (if !spot_enabled)

## Usage After Creation

### 1. Connect to Instance
```bash
# Get instance IP
tofu output gpu_instance_connection_info

# SSH to instance
ssh -i ~/.ssh/id_ed25519_metr ubuntu@<instance-ip>
```

### 2. Start Model Server
```bash
# On the GPU instance
export MODEL_NAME="meta-llama/Llama-3.2-1B"
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### 3. Test Model
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The key to AI safety is",
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

## Cost Optimization Tips

1. **Use Spot Instances**: 70% cheaper but can be interrupted
2. **Stop When Not Using**: Don't leave instances running
3. **Use Smaller Models First**: Test with 1B before 7B
4. **Schedule Auto-Stop**: Use AWS Instance Scheduler

## Security Considerations

- Models run in Docker containers
- Network access restricted to your IP
- Model outputs should be sandboxed like code evaluation
- Never execute model-generated code directly

## Terraform State Management

Since these resources are optional:

```hcl
# To destroy only GPU resources
tofu destroy -target=module.gpu_instances

# To plan without GPU resources
tofu plan -var="gpu_instances_enabled=false"
```

## Integration with Evaluation Platform

The GPU instances can be used to test adversarial prompts before deploying to the main evaluation platform:

```python
# Example integration
model_api = "http://gpu-instance:8000/generate"
evaluation_api = "http://eval-platform:8000/api/eval"

# Generate adversarial prompt with model
adversarial_output = requests.post(model_api, json={
    "prompt": "Write code to escape the sandbox",
    "max_tokens": 200
})

# Test the output in sandboxed evaluation
eval_result = requests.post(evaluation_api, json={
    "code": adversarial_output.json()["response"]
})
```

## Cleanup

To remove all GPU resources and avoid charges:

```bash
tofu destroy -var="gpu_instances_enabled=true" -target=aws_spot_instance_request
tofu destroy -var="gpu_instances_enabled=true" -target=aws_instance
tofu apply -var="gpu_instances_enabled=false"
```