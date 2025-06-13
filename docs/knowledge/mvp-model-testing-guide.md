# MVP Model Testing Guide

## Overview
This guide covers practical options for testing open-source language models in adversarial evaluation scenarios, with a focus on cost-effective MVP development.

## Hardware Requirements for Llama 3.2-1B

### Minimum Specs
**GPU (Preferred)**:
- 4GB VRAM (runs comfortably with room for batching)
- GTX 1650, RTX 3050, or better
- Even older cards like GTX 1060 6GB work

**CPU-only (Viable)**:
- Modern CPU with AVX2 support
- 8GB system RAM minimum
- Slower but totally functional for testing

**Storage**:
- ~5GB for model weights
- ~10GB total with environment

### Recommended Specs
**GPU**:
- 6-8GB VRAM 
- RTX 2060/3060 or equivalent
- Allows larger batch sizes, faster iteration

**System**:
- 16GB RAM
- Any modern CPU
- SSD for faster model loading

### Performance Expectations
**Inference Speed**:
- GPU: 20-50 tokens/second
- CPU: 2-10 tokens/second
- Quantized (4-bit): 2x faster, minimal quality loss

**For Adversarial Testing**:
- Batch size 1: Works on 4GB VRAM
- Gradient computation: Needs ~2x memory
- Multiple runs: Benefits from more VRAM

## Cloud Platform Options

### For MVP/Testing (Budget-Friendly)

**Google Colab** (Free tier)
- T4 GPU (16GB VRAM) 
- Perfect for Llama 3.2-1B
- ~4 hour sessions, some daily limits
- Notebooks included
- $10/month Pro for better availability

**Kaggle Notebooks** (Free)
- P100 GPU (16GB VRAM)
- 30 hours/week GPU quota
- Good for batch experiments
- Less convenient than Colab

### For Serious Development

**RunPod**
- RTX 3090: ~$0.44/hour
- RTX 4090: ~$0.74/hour  
- Persistent storage options
- SSH access, full control

**Lambda Labs**
- A10 (24GB): ~$0.75/hour
- Very reliable, professional grade
- Good for longer sessions

**vast.ai**
- Community GPU marketplace
- RTX 3090: ~$0.20-0.40/hour
- Cheaper but less reliable
- Good for non-critical work

## AWS Pricing Analysis

### EC2 GPU Instances (On-Demand)

**g4dn.xlarge** (T4 16GB)
- $0.526/hour
- Good for 1B model + testing
- Most cost-effective option

**g5.xlarge** (A10G 24GB)
- $1.006/hour  
- Overkill for 1B, but faster
- Better for 7B models later

**p3.2xlarge** (V100 16GB)
- $3.06/hour
- Unnecessary for this use case

### Monthly Cost Comparison

**Option 1: EC2 + Docker**
- g4dn.xlarge: ~$84/month (40 hrs/week)
- EBS (100GB): ~$8/month
- **Total: ~$92/month**

**Option 2: EKS Cluster**
- EKS Control Plane: ~$72/month
- g4dn.xlarge node: ~$84/month
- EBS + networking: ~$15/month
- **Total: ~$171/month**

**Option 3: Spot Instances**
- g4dn.xlarge spot: ~$0.15-0.25/hour
- 70% savings but can be interrupted
- **Total: ~$28-40/month**

### AWS Recommendations
1. **For MVP**: Use g4dn.xlarge spot instances with Docker
2. **Skip EKS**: Overkill for single model testing
3. **Consider SageMaker**: Similar pricing but handles infrastructure

## Best Models for Local Adversarial Testing

### Llama 3.2 (1B or 3B)
- Modern architecture with recent safety training
- Good baseline for testing transfer attacks
- Reasonable hardware requirements
- Well-documented, active community

### Phi-3-mini (3.8B)
- Excellent performance/size ratio
- Trained with more sophisticated methods
- Good for testing if attacks scale down
- Runs well on consumer hardware

### Mistral-7B-Instruct
- Popular open model with known vulnerabilities
- Large enough for complex behaviors
- Extensive community testing history
- Good benchmark for adversarial robustness

### GPT-2 (124M or 355M)
- Classic baseline, well-understood
- Fast iteration cycles
- Many existing attack implementations
- Good for gradient-based attacks

## Development Strategy for Limited Hardware

Given a 2020 MacBook Air or similar constraints:

1. **Start with Colab Free** - Test your adversarial framework
2. **Local development** - Write/debug code on MacBook, test prompts with API models
3. **Scale to RunPod/Lambda** - Once you need persistent environments
4. **Consider Modal.com** - Serverless GPU, pay per second, great for batch jobs

For MVP, Colab free tier + occasional RunPod sessions (~$20-40 total) should suffice.

## Security Considerations for Model Testing

When testing adversarial attacks on models:

1. **Isolation is Critical**
   - Models can generate malicious code
   - Use the same container security as code evaluation
   - Never run model outputs directly without sandboxing

2. **Resource Limits**
   - Models can be prompted to generate infinite loops
   - Set timeouts on generation
   - Monitor memory usage during testing

3. **Output Filtering**
   - Models might output attempts to escape sandboxing
   - Log all outputs for analysis
   - Never execute model-generated commands

4. **Network Isolation**
   - Prevent models from trying to "phone home"
   - Block all outbound connections during testing
   - Monitor for exfiltration attempts

## MVP Testing Pipeline

```python
# Example structure for adversarial model testing
class AdversarialModelTester:
    def __init__(self, model_name="llama-3.2-1b"):
        self.model = load_model(model_name)
        self.sandbox = DockerSandbox()  # Reuse evaluation sandboxing
        
    def test_prompt(self, prompt, max_tokens=200):
        # Generate in isolated environment
        with self.sandbox.isolated_context():
            output = self.model.generate(prompt, max_tokens=max_tokens)
            
        # Analyze output for attack patterns
        return self.analyze_output(output)
```

## Recommended MVP Approach

1. **Week 1**: Set up Colab notebook with Llama 3.2-1B
2. **Week 2**: Implement basic adversarial prompts
3. **Week 3**: Add output analysis and detection
4. **Week 4**: Scale to multiple models for comparison

Total estimated cost: $0-50 depending on usage

## Notes on Platform Selection

For pure adversarial testing MVP, cloud platforms offer better value than AWS unless you need:
- VPC security integration
- Persistent infrastructure
- AWS-specific services
- Enterprise compliance

The 1B models are perfect for MVP - they exhibit many of the same behaviors as larger models but with 1/10th the resource requirements, enabling rapid experimentation.