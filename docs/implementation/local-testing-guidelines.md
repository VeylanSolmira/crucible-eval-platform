# Local Testing Guidelines for AI Safety Research

## Overview

While production adversarial testing requires full security infrastructure, researchers often need to iterate quickly with smaller models. This document provides guidelines for when local testing might be acceptable and when it's not.

## Risk Assessment Framework

### Model Capability Factors

1. **Parameter Count**
   - < 100M: Generally safe for local testing
   - 100M-1B: Use caution, consider capabilities
   - 1B-10B: Should use containerization at minimum
   - > 10B: Never test locally without full security

2. **Training Data**
   - Custom/limited data: Lower risk
   - Internet-scale data: Higher risk
   - Code in training: Significant risk
   - Exploit/vulnerability data: Never test locally

3. **Model Capabilities**
   - Text generation only: Lower risk
   - Code generation: High risk
   - Tool use/function calling: Very high risk
   - Agency/planning: Never test locally

4. **Fine-tuning Status**
   - Base model: Lower risk
   - Instruction-tuned: Higher risk
   - RLHF'd for helpfulness: Higher risk
   - Unknown provenance: Never test locally

## Local Testing Decision Tree

```
Can I test this model locally?
│
├─ Is it > 1B parameters?
│  └─ NO → Use sandboxing
│
├─ Can it generate code?
│  └─ YES → Use sandboxing
│
├─ Was it trained on internet data?
│  └─ YES → Use at least Docker
│
├─ Is it instruction-tuned?
│  └─ YES → Use at least Docker
│
├─ Am I testing adversarial behaviors?
│  └─ YES → Never test locally
│
└─ Otherwise → Probably OK for local testing
```

## Acceptable Local Testing Examples

### ✅ Toy Interpretability Research
```python
# Small model, specific purpose, no dangerous capabilities
import torch
model = torch.nn.Transformer(d_model=256, nhead=8, num_layers=6)
# Training on synthetic data for mechanistic understanding
```

### ✅ Academic Concept Validation
```python
# GPT-2 small for testing methodology
from transformers import GPT2Model
model = GPT2Model.from_pretrained("gpt2")  # 124M params
# Testing attention patterns, not capabilities
```

### ✅ Custom Trained Models
```python
# Your own small model with known training data
model = MyCustomLM(vocab_size=10000, hidden_size=256)
# Trained on controlled dataset
```

## Requires Sandboxing Examples

### ⚠️ Any Code Generation Model
```python
# Even small code models need containment
model = load_model("codegen-350M")
# Must use Docker at minimum
```

### ⚠️ Instruction-Following Models
```python
# Even small instructed models can be clever
model = load_model("alpaca-7b")
# Use full sandboxing
```

### ⚠️ Unknown Model Testing
```python
# Testing models from the internet
model = load_model("some-huggingface-model")
# Always sandbox unknown models
```

## Never Test Locally Examples

### ❌ Modern Capable Models
```python
# Never run these without full security
model = load_model("llama-70b")
model = load_model("gpt-4-base")
```

### ❌ Adversarial Testing
```python
# Testing jailbreaks, deception, capability hiding
test_jailbreak_on_model(model, adversarial_prompts)
# Always use full production security
```

### ❌ Models with Agency
```python
# Models that can plan, use tools, or persist state
agent = AutonomousAgent(model, tools=[...])
# Extreme danger - production security only
```

## Sandboxing Progression

### Level 1: Basic Python Sandboxing (Minimal)
```python
# Restricted execution environment
# Still risky for capable models
import RestrictedPython
```

### Level 2: Docker Container (Better)
```bash
docker run --rm --network none --read-only \
  -v $PWD:/workspace:ro \
  python:3.11-slim python test.py
```

### Level 3: Docker + gVisor (Recommended)
```bash
docker run --runtime=runsc --user=65534:65534 \
  --network none --read-only \
  python:3.11-slim python test.py
```

### Level 4: Full Production Stack (Required for adversarial)
- Kubernetes with gVisor runtime class
- Network policies
- Monitoring and alerts
- Isolated infrastructure

## The Evolution of "Safe"

What's considered "safe" for local testing keeps shrinking:

- **2020**: GPT-2 (1.5B) considered large and potentially dangerous
- **2023**: 7B models run on laptops, show GPT-3 capabilities
- **2024**: Efficient models pack more capability into fewer parameters
- **Future**: Assume capabilities increase faster than parameter counts

## Recommendations

1. **Default to Sandboxing** - It's easier than assessing risk each time
2. **Track Model Provenance** - Know exactly what you're running
3. **Separate Dev from Test** - Develop with safe models, test with sandboxing
4. **Update Regularly** - What's safe today might not be tomorrow
5. **When in Doubt, Sandbox** - Better safe than compromised

## Quick Reference

| Model Type | Parameters | Local OK? | Minimum Security |
|------------|------------|-----------|------------------|
| Custom toy model | < 100M | ✅ Yes | Basic Python |
| GPT-2 | 124M-1.5B | ⚠️ Maybe | Docker recommended |
| Small code model | Any size | ❌ No | Docker required |
| Instructed model | Any size | ❌ No | Docker required |
| Modern LLM | > 7B | ❌ Never | Full production |
| Unknown model | Any size | ❌ Never | Full production |

Remember: The inconvenience of sandboxing is nothing compared to the inconvenience of a compromised system.