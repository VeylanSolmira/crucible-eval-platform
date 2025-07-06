#!/usr/bin/env python3
"""
Test script to verify ML executor functionality.
This demonstrates what code can run in the ML executor.
"""

def test_pytorch():
    """Test PyTorch is available and working."""
    print("Testing PyTorch...")
    try:
        import torch
        print(f"✓ PyTorch version: {torch.__version__}")
        
        # Simple tensor operation
        x = torch.tensor([[1, 2], [3, 4]])
        y = torch.tensor([[5, 6], [7, 8]])
        z = torch.matmul(x, y)
        print(f"✓ Tensor multiplication works: {z.shape}")
        return True
    except Exception as e:
        print(f"✗ PyTorch error: {e}")
        return False

def test_transformers():
    """Test Transformers library is available."""
    print("\nTesting Transformers...")
    try:
        import transformers
        print(f"✓ Transformers version: {transformers.__version__}")
        
        # Note: Actually loading models would fail in offline mode
        # This just tests the library is importable
        from transformers import AutoTokenizer
        print("✓ Can import tokenizer classes")
        return True
    except Exception as e:
        print(f"✗ Transformers error: {e}")
        return False

def test_ml_dependencies():
    """Test common ML dependencies."""
    print("\nTesting ML dependencies...")
    deps = {
        'numpy': None,
        'regex': None,
        'tqdm': None,
    }
    
    for dep in deps:
        try:
            module = __import__(dep)
            deps[dep] = getattr(module, '__version__', 'unknown')
            print(f"✓ {dep}: {deps[dep]}")
        except ImportError:
            print(f"✗ {dep}: not available")
    
    return all(v is not None for v in deps.values())

def main():
    """Run all tests."""
    print("ML Executor Test Suite")
    print("=" * 50)
    
    results = {
        'PyTorch': test_pytorch(),
        'Transformers': test_transformers(),
        'Dependencies': test_ml_dependencies(),
    }
    
    print("\nSummary")
    print("-" * 50)
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{test}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())