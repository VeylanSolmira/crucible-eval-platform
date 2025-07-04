# Code Templates

This directory contains template code for common evaluation scenarios.

## Available Templates

### hello_world_distilgpt2.py
A beginner-friendly introduction to language models using DistilGPT2 (82M parameters).

**Features:**
- Runs on CPU - no GPU required
- Multiple generation examples (basic, creative, deterministic)
- Only ~300MB download
- Perfect for learning and prototyping

**Usage:**
```bash
# Install dependencies
pip install transformers torch

# Run the example
python hello_world_distilgpt2.py
```

**Why DistilGPT2?**
- Smallest practical transformer model
- Same architecture as larger models
- Can demonstrate adversarial attacks
- Runs on any modern laptop

## Future Templates

- `adversarial_testing.py` - Basic adversarial prompt testing
- `model_evaluation.py` - Comprehensive model evaluation framework
- `security_sandbox.py` - Running models in isolated environments
- `batch_processing.py` - Efficient batch evaluation

## Contributing

When adding new templates:
1. Keep them self-contained and runnable
2. Include comprehensive comments
3. Show best practices for security
4. Demonstrate resource efficiency
5. Add clear requirements and usage instructions