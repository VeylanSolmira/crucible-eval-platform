#!/usr/bin/env python3
"""
Hello World example using DistilGPT2 - a lightweight language model.

DistilGPT2 has only 82M parameters (vs 124M for GPT-2), making it perfect
for getting started with language models on resource-constrained systems.

Requirements:
    pip install transformers torch

This example will:
1. Load the DistilGPT2 model (downloads ~300MB on first run)
2. Generate text from a prompt
3. Show different generation strategies
"""

from transformers import pipeline, set_seed
import torch

def basic_generation():
    """Basic text generation with DistilGPT2."""
    print("=== Basic Text Generation ===")
    
    # Create a text generation pipeline
    generator = pipeline('text-generation', model='distilgpt2')
    
    # Generate text from a prompt
    prompt = "Hello world, I am learning about"
    result = generator(
        prompt,
        max_length=50,
        num_return_sequences=1,
        temperature=0.8
    )
    
    print(f"Prompt: {prompt}")
    print(f"Generated: {result[0]['generated_text']}\n")


def creative_generation():
    """Generate more creative text with higher temperature."""
    print("=== Creative Generation (Higher Temperature) ===")
    
    generator = pipeline('text-generation', model='distilgpt2')
    
    prompt = "In a world where AI can"
    result = generator(
        prompt,
        max_length=80,
        temperature=1.2,  # Higher temperature = more creative
        do_sample=True,
        top_p=0.95
    )
    
    print(f"Prompt: {prompt}")
    print(f"Generated: {result[0]['generated_text']}\n")


def multiple_completions():
    """Generate multiple different completions for the same prompt."""
    print("=== Multiple Completions ===")
    
    generator = pipeline('text-generation', model='distilgpt2')
    
    prompt = "The future of technology is"
    results = generator(
        prompt,
        max_length=40,
        num_return_sequences=3,
        temperature=0.9,
        do_sample=True
    )
    
    print(f"Prompt: {prompt}")
    for i, result in enumerate(results, 1):
        print(f"Completion {i}: {result['generated_text']}")
    print()


def deterministic_generation():
    """Generate deterministic output using a seed."""
    print("=== Deterministic Generation (With Seed) ===")
    
    # Set seed for reproducibility
    set_seed(42)
    
    generator = pipeline('text-generation', model='distilgpt2')
    
    prompt = "Machine learning is"
    result = generator(
        prompt,
        max_length=50,
        do_sample=False  # Greedy decoding for deterministic output
    )
    
    print(f"Prompt: {prompt}")
    print(f"Generated: {result[0]['generated_text']}\n")


def system_info():
    """Display system information."""
    print("=== System Information ===")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"Using device: {'cuda' if torch.cuda.is_available() else 'cpu'}\n")


def main():
    """Run all examples."""
    print("\n🤖 DistilGPT2 Hello World Examples\n")
    print("This will download ~300MB on first run.\n")
    
    # Display system info
    system_info()
    
    # Run examples
    basic_generation()
    creative_generation()
    multiple_completions()
    deterministic_generation()
    
    print("✅ All examples completed!")
    print("\nTips:")
    print("- Lower temperature (0.1-0.7) = more focused/deterministic")
    print("- Higher temperature (0.8-1.5) = more creative/random")
    print("- max_length controls output length")
    print("- Use do_sample=False for deterministic output")


if __name__ == "__main__":
    main()