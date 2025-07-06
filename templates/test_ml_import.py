"""
Test that ML libraries are available in the executor.
This should work with the executor-ml image.
"""

print("Testing ML library imports...")

try:
    import torch
    print(f"✓ PyTorch {torch.__version__} imported successfully")
    
    import transformers
    print(f"✓ Transformers {transformers.__version__} imported successfully")
    
    import numpy as np
    print(f"✓ NumPy {np.__version__} imported successfully")
    
    # Simple computation to verify it works
    x = torch.tensor([1.0, 2.0, 3.0])
    y = x * 2
    print(f"\nTensor computation: {x} * 2 = {y}")
    
    print("\n✅ All ML libraries are working correctly!")
    
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("Make sure the executor is using the executor-ml image")