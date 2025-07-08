"""
Tests for the flexible storage manager.
"""

import pytest
import unittest
import asyncio

from storage.core.flexible_manager import FlexibleStorageManager
from storage.backends.memory import InMemoryStorage


@pytest.mark.unit
class TestFlexibleStorageManager(unittest.TestCase):
    """Test suite for flexible storage manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Create storage backends
        self.primary = InMemoryStorage()
        self.fallback = InMemoryStorage()
        self.cache = InMemoryStorage()

        # Create manager
        self.manager = FlexibleStorageManager(
            primary_storage=self.primary, fallback_storage=self.fallback, cache_storage=self.cache
        )

    def tearDown(self):
        """Clean up."""
        self.loop.close()

    def run_async(self, coro):
        """Helper to run async functions in tests."""
        return self.loop.run_until_complete(coro)

    def test_create_evaluation(self):
        """Test creating an evaluation."""
        eval_id = "test-001"
        code = "print('Hello, World!')"

        # Create evaluation
        result = self.run_async(self.manager.create_evaluation(eval_id, code))
        self.assertTrue(result)

        # Verify stored in primary
        data = self.primary.retrieve_evaluation(eval_id)
        self.assertIsNotNone(data)
        self.assertEqual(data["id"], eval_id)
        self.assertEqual(data["status"], "queued")
        self.assertIn("code_hash", data)

        # Verify event was created
        events = self.primary.retrieve_events(eval_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "submitted")

    def test_update_evaluation_status(self):
        """Test updating evaluation status."""
        eval_id = "test-002"
        code = "x = 1 + 1"

        # Create
        self.run_async(self.manager.create_evaluation(eval_id, code))

        # Update to running
        result = self.run_async(self.manager.update_evaluation(eval_id, status="running"))
        self.assertTrue(result)

        # Verify update
        data = self.run_async(self.manager.get_evaluation(eval_id))
        self.assertEqual(data["status"], "running")
        self.assertIn("started_at", data)

        # Update to completed
        result = self.run_async(
            self.manager.update_evaluation(eval_id, status="completed", output="2", exit_code=0)
        )
        self.assertTrue(result)

        # Verify final state
        data = self.run_async(self.manager.get_evaluation(eval_id))
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output"], "2")
        self.assertEqual(data["exit_code"], 0)
        self.assertIn("completed_at", data)
        self.assertIn("runtime_ms", data)

    def test_cache_usage(self):
        """Test that cache is used for retrieval."""
        eval_id = "test-003"
        code = "pass"

        # Create evaluation
        self.run_async(self.manager.create_evaluation(eval_id, code))

        # Clear primary storage to simulate it being unavailable
        self.primary.delete_evaluation(eval_id)

        # Should still get from cache
        data = self.run_async(self.manager.get_evaluation(eval_id))
        self.assertIsNotNone(data)
        self.assertEqual(data["id"], eval_id)

    def test_fallback_on_primary_failure(self):
        """Test fallback storage is used when primary fails."""

        # Create manager with a broken primary storage
        class BrokenStorage(InMemoryStorage):
            def store_evaluation(self, eval_id, data):
                raise Exception("Storage is broken!")

        manager = FlexibleStorageManager(
            primary_storage=BrokenStorage(), fallback_storage=self.fallback
        )

        eval_id = "test-004"
        code = "import sys"

        # Should succeed using fallback
        result = self.run_async(manager.create_evaluation(eval_id, code))
        self.assertTrue(result)

        # Verify in fallback storage
        data = self.fallback.retrieve_evaluation(eval_id)
        self.assertIsNotNone(data)
        self.assertEqual(data["id"], eval_id)

    def test_large_output_handling(self):
        """Test handling of large outputs."""
        eval_id = "test-005"
        code = "print('x' * 1000000)"  # 1MB of output

        # Create and run evaluation
        self.run_async(self.manager.create_evaluation(eval_id, code))

        # Generate large output
        large_output = "x" * (2 * 1024 * 1024)  # 2MB

        # Update with large output
        result = self.run_async(
            self.manager.update_evaluation(eval_id, status="completed", output=large_output)
        )
        self.assertTrue(result)

        # Verify only preview is stored inline
        data = self.run_async(self.manager.get_evaluation(eval_id))
        self.assertEqual(len(data["output"]), 1024)  # Preview size
        self.assertEqual(data["output_size"], 2 * 1024 * 1024)

    def test_event_tracking(self):
        """Test event tracking throughout evaluation lifecycle."""
        eval_id = "test-006"
        code = "time.sleep(1)"

        # Create
        self.run_async(self.manager.create_evaluation(eval_id, code))

        # Add custom event
        self.run_async(
            self.manager.add_event(
                eval_id, "custom", "Custom event message", custom_field="custom_value"
            )
        )

        # Update status (adds another event)
        self.run_async(self.manager.update_evaluation(eval_id, status="running"))

        # Get all events
        events = self.run_async(self.manager.get_events(eval_id))

        # Should have: submitted, custom, status_changed
        self.assertEqual(len(events), 3)

        event_types = [e["type"] for e in events]
        self.assertIn("submitted", event_types)
        self.assertIn("custom", event_types)
        self.assertIn("status_changed", event_types)

        # Check custom event data
        custom_event = next(e for e in events if e["type"] == "custom")
        self.assertEqual(custom_event["message"], "Custom event message")
        self.assertEqual(custom_event["custom_field"], "custom_value")

    def test_list_evaluations_with_filter(self):
        """Test listing evaluations with status filter."""
        # Create multiple evaluations
        for i in range(5):
            eval_id = f"list-test-{i}"
            self.run_async(self.manager.create_evaluation(eval_id, f"code_{i}"))

            # Update some to completed
            if i % 2 == 0:
                self.run_async(self.manager.update_evaluation(eval_id, status="completed"))

        # List all
        all_evals = self.run_async(self.manager.list_evaluations())
        self.assertGreaterEqual(len(all_evals), 5)

        # List only completed
        completed = self.run_async(self.manager.list_evaluations(status="completed"))

        # Should have 3 completed (0, 2, 4)
        completed_test_evals = [e for e in completed if e.startswith("list-test-")]
        self.assertEqual(len(completed_test_evals), 3)

    def test_delete_evaluation(self):
        """Test deleting evaluation removes all data."""
        eval_id = "test-delete"
        code = "to_delete = True"

        # Create evaluation with events
        self.run_async(self.manager.create_evaluation(eval_id, code))
        self.run_async(self.manager.add_event(eval_id, "test", "Test event"))

        # Verify exists
        data = self.run_async(self.manager.get_evaluation(eval_id))
        self.assertIsNotNone(data)

        # Delete
        result = self.run_async(self.manager.delete_evaluation(eval_id))
        self.assertTrue(result)

        # Verify deleted from all storages
        self.assertIsNone(self.primary.retrieve_evaluation(eval_id))
        self.assertIsNone(self.cache.retrieve_evaluation(eval_id))

        # Events should also be gone
        events = self.run_async(self.manager.get_events(eval_id))
        self.assertEqual(len(events), 0)


if __name__ == "__main__":
    unittest.main()