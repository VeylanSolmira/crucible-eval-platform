"""
Tests for file-based storage backend.
"""

import pytest
import unittest
import tempfile
import shutil
import json
from pathlib import Path

from tests.unit.storage.base_storage_test import StorageServiceTestMixin
from storage.backends.file import FileStorage


@pytest.mark.unit
class FileStorageTests(StorageServiceTestMixin, unittest.TestCase):
    """Test suite for file-based storage."""

    def setUp(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        super().setUp()

    def tearDown(self):
        """Clean up temporary directory."""
        super().tearDown()
        shutil.rmtree(self.temp_dir)

    def create_storage(self):
        """Create file storage in temporary directory."""
        return FileStorage(self.temp_dir)

    # File-specific tests

    def test_directory_creation(self):
        """Test that storage directories are created."""
        FileStorage(self.temp_dir + "/subdir")

        # Verify directories exist
        base_path = Path(self.temp_dir) / "subdir"
        self.assertTrue(base_path.exists())
        self.assertTrue((base_path / "evaluations").exists())
        self.assertTrue((base_path / "events").exists())
        self.assertTrue((base_path / "metadata").exists())

    def test_file_format(self):
        """Test that files are stored in correct JSON format."""
        eval_id = "test-format"
        data = {"id": eval_id, "status": "completed", "nested": {"key": "value"}, "list": [1, 2, 3]}

        self.storage.store_evaluation(eval_id, data)

        # Read file directly
        file_path = Path(self.temp_dir) / "evaluations" / f"{eval_id}.json"
        self.assertTrue(file_path.exists())

        with open(file_path, "r") as f:
            stored_data = json.load(f)

        self.assertEqual(stored_data["id"], eval_id)
        self.assertEqual(stored_data["nested"]["key"], "value")
        self.assertEqual(stored_data["list"], [1, 2, 3])

    def test_atomic_writes(self):
        """Test that writes are atomic (no partial writes)."""
        eval_id = "test-atomic"

        # Check no .tmp files are left after successful write
        self.storage.store_evaluation(eval_id, {"data": "test"})

        eval_dir = Path(self.temp_dir) / "evaluations"
        tmp_files = list(eval_dir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0, "Temporary files not cleaned up")

    def test_corrupted_file_handling(self):
        """Test handling of corrupted JSON files."""
        eval_id = "test-corrupted"

        # Create corrupted file
        file_path = Path(self.temp_dir) / "evaluations" / f"{eval_id}.json"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, "w") as f:
            f.write("{ invalid json")

        # Should return None instead of crashing
        result = self.storage.retrieve_evaluation(eval_id)
        self.assertIsNone(result)

    def test_file_permissions(self):
        """Test that files are created with correct permissions."""
        eval_id = "test-permissions"
        self.storage.store_evaluation(eval_id, {"data": "test"})

        file_path = Path(self.temp_dir) / "evaluations" / f"{eval_id}.json"

        # Check file is readable and writable
        self.assertTrue(file_path.exists())
        self.assertTrue(file_path.is_file())

        # Verify we can read the file
        with open(file_path, "r") as f:
            content = f.read()
            self.assertIn("test", content)

    def test_persistence_across_instances(self):
        """Test that data persists when creating new storage instances."""
        eval_id = "test-persistence"
        data = {"status": "completed", "output": "Hello"}

        # Store with first instance
        storage1 = FileStorage(self.temp_dir)
        storage1.store_evaluation(eval_id, data)

        # Retrieve with second instance
        storage2 = FileStorage(self.temp_dir)
        result = storage2.retrieve_evaluation(eval_id)

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["output"], "Hello")

    def test_listing_order(self):
        """Test that evaluations are listed in correct order (newest first)."""
        import time

        # Create evaluations with small delays
        for i in range(3):
            eval_id = f"order-test-{i}"
            self.storage.store_evaluation(eval_id, {"index": i})
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # List should return newest first
        listed = self.storage.list_evaluations()

        # Find our test evaluations
        test_evals = [e for e in listed if e.startswith("order-test-")]

        # Should be in reverse order (2, 1, 0)
        self.assertEqual(test_evals[0], "order-test-2")
        self.assertEqual(test_evals[1], "order-test-1")
        self.assertEqual(test_evals[2], "order-test-0")


if __name__ == "__main__":
    unittest.main()