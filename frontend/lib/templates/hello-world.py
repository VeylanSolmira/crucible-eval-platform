#!/usr/bin/env python3
"""Basic Hello World demo for Crucible Platform"""


def main():
    print("Hello from Crucible Platform!")
    print("This evaluation is running in a secure, isolated container.")
    print()
    print("Container limits:")
    print("- Memory: 512MB")
    print("- CPU: 0.5 cores")
    print("- Network: Disabled")
    print("- Filesystem: Read-only (except /tmp)")
    print()
    
    # Quick Python feature test
    numbers = [1, 2, 3, 4, 5]
    squared = [n**2 for n in numbers]
    print(f"Python test - squared numbers: {squared}")
    print()
    print("Execution successful! ✓")


if __name__ == "__main__":
    main()
