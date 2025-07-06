"""
Tests for in-memory storage backend.
"""

import unittest
from tests.unit.storage.base_storage_test import StorageServiceTestMixin
from storage.backends.memory import InMemoryStorage


class InMemoryStorageTests(StorageServiceTestMixin, unittest.TestCase):
    """Test suite for in-memory storage."""

    def create_storage(self):
        """Create a fresh in-memory storage instance."""
        return InMemoryStorage()

    # In-memory specific tests

    def test_memory_isolation(self):
        """Test that different instances have isolated storage."""
        storage1 = InMemoryStorage()
        storage2 = InMemoryStorage()

        # Store in first instance
        storage1.store_evaluation("test-id", {"data": "instance1"})

        # Should not exist in second instance
        result = storage2.retrieve_evaluation("test-id")
        self.assertIsNone(result)

    def test_no_persistence(self):
        """Test that data doesn't persist across instances."""
        eval_id = "test-persistence"

        # Store in one instance
        storage1 = InMemoryStorage()
        storage1.store_evaluation(eval_id, {"data": "test"})

        # Create new instance - data should be gone
        storage2 = InMemoryStorage()
        result = storage2.retrieve_evaluation(eval_id)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()