#!/usr/bin/env python3
"""
Run all storage tests.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
from storage.backends.memory.tests import InMemoryStorageTests
from storage.backends.file.tests import FileStorageTests
from storage.backends.database.tests import DatabaseStorageTests
from storage.tests.test_manager import TestFlexibleStorageManager


def run_all_tests():
    """Run all storage tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add backend tests
    print("Loading backend tests...")
    suite.addTests(loader.loadTestsFromTestCase(InMemoryStorageTests))
    suite.addTests(loader.loadTestsFromTestCase(FileStorageTests))
    suite.addTests(loader.loadTestsFromTestCase(DatabaseStorageTests))

    # Add manager tests
    print("Loading manager tests...")
    suite.addTests(loader.loadTestsFromTestCase(TestFlexibleStorageManager))

    # Run tests
    print("\nRunning storage tests...\n")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
