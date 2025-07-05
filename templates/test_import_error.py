#!/usr/bin/env python3
"""
Test script to verify import errors are captured in stderr.
This should fail with an ImportError since torch is not installed in the container.
"""

import sys

print("Starting import test...", file=sys.stdout)
print("This message goes to stdout", file=sys.stdout)

try:
    import torch
    print("Successfully imported torch!", file=sys.stdout)
    print(f"Torch version: {torch.__version__}", file=sys.stdout)
except ImportError as e:
    print(f"Import error (this should appear in stderr): {e}", file=sys.stderr)
    sys.exit(1)

print("This line should not be reached", file=sys.stdout)