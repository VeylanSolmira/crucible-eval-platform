"""
Simple ML demo for the ML executor.
This shows a minimal text generation example.
"""

# This would work if models were pre-cached
# For demo purposes, we'll just show the imports work

try:
    import torch
    import transformers
    
    print(f"PyTorch version: {torch.__version__}")
    print(f"Transformers version: {transformers.__version__}")
    
    # Simple tensor operation to show PyTorch works
    x = torch.randn(2, 3)
    y = torch.randn(3, 2)
    z = torch.matmul(x, y)
    
    print(f"\nTensor multiplication result shape: {z.shape}")
    print(f"Result:\n{z}")
    
    # Note: Actually loading models would require:
    # 1. Pre-cached models in the image, or
    # 2. Mounted model volumes, or
    # 3. Network access (which we block for security)
    
    print("\n✓ ML libraries loaded successfully!")
    print("Note: Model loading disabled in offline mode for security")
    
except ImportError as e:
    print(f"Error: {e}")
    print("This code requires the ML executor image with PyTorch and Transformers")