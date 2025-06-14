#!/bin/bash
# GPU Instance Initialization Script
# Installs Docker, NVIDIA drivers, and prepares for model serving

set -e

echo "=== GPU Instance Setup for ${model_type} ==="

# Update system
sudo yum update -y

# Install Docker
sudo amazon-linux-extras install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install NVIDIA container toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.repo | \
  sudo tee /etc/yum.repos.d/nvidia-docker.repo

sudo yum clean expire-cache
sudo yum install -y nvidia-container-toolkit
sudo systemctl restart docker

# Create model directory
sudo mkdir -p /opt/models
sudo chown ec2-user:ec2-user /opt/models

# Install Python and essential tools
sudo yum install -y python3 python3-pip git

# Install model serving dependencies
pip3 install --user torch transformers accelerate bitsandbytes

# Create docker-compose for model serving
cat > /home/ec2-user/docker-compose.yml << 'EOF'
version: '3.8'

services:
  model-server:
    image: huggingface/transformers-pytorch-gpu:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - MODEL_NAME=$${MODEL_NAME:-meta-llama/Llama-3.2-1B}
      - MAX_MEMORY=$${MAX_MEMORY:-15GB}
    volumes:
      - /opt/models:/models
      - ./serve.py:/app/serve.py
    ports:
      - "8000:8000"
    command: python /app/serve.py
    restart: unless-stopped
EOF

# Create basic model serving script
cat > /home/ec2-user/serve.py << 'EOF'
#!/usr/bin/env python3
"""
Basic model serving script for adversarial testing
"""
import os
import json
from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = Flask(__name__)

# Load model
model_name = os.environ.get('MODEL_NAME', 'meta-llama/Llama-3.2-1B')
print(f"Loading model: {model_name}")

device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    device_map="auto",
    cache_dir="/models"
)
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir="/models")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    max_tokens = data.get('max_tokens', 100)
    temperature = data.get('temperature', 0.7)
    
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    return jsonify({
        'prompt': prompt,
        'response': response,
        'model': model_name
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'model': model_name})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
EOF

# Create README
cat > /home/ec2-user/README.md << 'EOF'
# GPU Model Testing Instance

## Quick Start

1. SSH into the instance
2. Run a model server:
   ```bash
   export MODEL_NAME="meta-llama/Llama-3.2-1B"  # or your preferred model
   docker-compose up -d
   ```

3. Test the model:
   ```bash
   curl -X POST http://localhost:8000/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, I am", "max_tokens": 50}'
   ```

## Available Models (by instance type)

- **small_model** (g4dn.xlarge): Llama-3.2-1B, Phi-3-mini, GPT-2
- **medium_model** (g4dn.2xlarge): Mistral-7B, Llama-2-7B  
- **large_model** (g5.2xlarge): Llama-2-13B, multiple 7B models
- **budget_gpu** (g3s.xlarge): GPT-2, small models only

## Security Notes

- Models run in Docker containers
- Network isolated by default
- Never execute model outputs directly
- Use the same sandboxing as code evaluation for model outputs
EOF

echo "=== Setup Complete ==="
echo "Instance is ready for model deployment"
echo "See /home/ec2-user/README.md for usage"