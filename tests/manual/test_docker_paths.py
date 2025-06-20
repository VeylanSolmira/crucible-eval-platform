#!/usr/bin/env python3
"""Test Docker execution from different working directories.

This ensures the Docker path fix continues to work correctly when
the app is run from various directories in the project.

Usage: python test_docker_paths.py
"""

import os
import sys
import tempfile

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../..')
sys.path.insert(0, project_root)

from src.execution_engine.execution import DockerEngine

def test_from_directory(test_name, directory):
    """Test Docker execution from a specific directory"""
    original_cwd = os.getcwd()
    
    try:
        os.chdir(directory)
        print(f"\n{test_name}")
        print(f"Working directory: {os.getcwd()}")
        
        # Create engine and check temp_base_dir
        engine = DockerEngine()
        print(f"temp_base_dir: {engine.temp_base_dir}")
        print(f"Is absolute: {os.path.isabs(engine.temp_base_dir)}")
        
        # Try executing code
        code = f'print("Executed from: {test_name}")'
        result = engine.execute(code, f'test-{test_name.lower().replace(" ", "-")}')
        
        if result['status'] == 'completed':
            print(f"✓ Execution successful: {result['output'].strip()}")
        else:
            print(f"✗ Execution failed: {result}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        os.chdir(original_cwd)

def main():
    print("Testing Docker path handling from different directories...")
    print("="*60)
    
    # Test directories
    test_cases = [
        ("Project Root", project_root),
        ("Storage Directory", os.path.join(project_root, "storage")),
        ("Migrations Directory", os.path.join(project_root, "storage/database/migrations")),
        ("Tests Directory", os.path.dirname(__file__)),
        ("System Temp", tempfile.gettempdir()),
    ]
    
    for test_name, directory in test_cases:
        if os.path.exists(directory):
            test_from_directory(test_name, directory)
        else:
            print(f"\n{test_name}: Directory not found - {directory}")
    
    print("\n" + "="*60)
    print("Test complete!")
    
    # Additional test with explicit temp_base_dir
    print("\nTesting with explicit temp_base_dir...")
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = DockerEngine(temp_base_dir=temp_dir)
        print(f"Custom temp_base_dir: {engine.temp_base_dir}")
        result = engine.execute('print("Custom temp dir test")', 'test-custom')
        if result['status'] == 'completed':
            print(f"✓ Custom temp dir works: {result['output'].strip()}")
        else:
            print(f"✗ Custom temp dir failed: {result}")

if __name__ == "__main__":
    main()