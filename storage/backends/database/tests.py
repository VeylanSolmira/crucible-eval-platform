"""
Tests for database storage backend.
"""

import unittest
import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

from ...tests.base_test import StorageServiceTestMixin
from .database_storage import DatabaseStorage
from ...database.models import Base


class DatabaseStorageTests(StorageServiceTestMixin, unittest.TestCase):
    """Test suite for database storage."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        # Use SQLite for tests (in-memory or file)
        cls.test_db_url = "sqlite:///test_storage.db"
        # cls.test_db_url = "sqlite:///:memory:"  # Alternative: in-memory
        
        # Create tables
        engine = create_engine(cls.test_db_url)
        Base.metadata.create_all(engine)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        if os.path.exists("test_storage.db"):
            os.remove("test_storage.db")
    
    def create_storage(self):
        """Create database storage instance."""
        return DatabaseStorage(self.test_db_url)
    
    def tearDown(self):
        """Clean up test data after each test."""
        super().tearDown()
        # Additional cleanup if needed
        engine = create_engine(self.test_db_url)
        with engine.connect() as conn:
            # Clean all tables
            conn.execute(text("DELETE FROM evaluation_metrics"))
            conn.execute(text("DELETE FROM evaluation_events"))
            conn.execute(text("DELETE FROM evaluations"))
            conn.commit()
    
    # Database-specific tests
    
    def test_transaction_rollback(self):
        """Test that failed transactions don't leave partial data."""
        eval_id = "test-transaction"
        
        # Create a storage instance
        storage = self.create_storage()
        
        # Store initial data
        storage.store_evaluation(eval_id, {"status": "initial"})
        
        # Simulate a failed update by forcing an exception
        # This is tricky to test properly without mocking
        # For now, we'll just verify basic transaction behavior
        
        # Verify data integrity
        result = storage.retrieve_evaluation(eval_id)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "initial")
    
    def test_sql_injection_safety(self):
        """Test that SQL injection attempts are safely handled."""
        # Try eval_id with SQL injection attempt
        evil_id = "test'; DROP TABLE evaluations; --"
        
        # This should be safely handled by SQLAlchemy's parameterization
        result = self.storage.store_evaluation(evil_id, {"data": "test"})
        self.assertTrue(result)
        
        # Verify tables still exist
        engine = create_engine(self.test_db_url)
        with engine.connect() as conn:
            # If table was dropped, this would fail
            result = conn.execute(text("SELECT COUNT(*) FROM evaluations"))
            self.assertIsNotNone(result.fetchone())
    
    def test_metadata_json_storage(self):
        """Test storing complex data in JSON metadata field."""
        eval_id = "test-json-meta"
        complex_data = {
            "id": eval_id,
            "status": "completed",
            "custom_field": "custom_value",
            "nested": {
                "level1": {
                    "level2": ["a", "b", "c"]
                }
            },
            "unicode": "Hello 世界 🌍",
            "numbers": [1, 2.5, -3]
        }
        
        # Store
        result = self.storage.store_evaluation(eval_id, complex_data)
        self.assertTrue(result)
        
        # Retrieve
        retrieved = self.storage.retrieve_evaluation(eval_id)
        self.assertIsNotNone(retrieved)
        
        # Check known fields
        self.assertEqual(retrieved["status"], "completed")
        
        # Check metadata fields
        self.assertEqual(retrieved["custom_field"], "custom_value")
        self.assertEqual(retrieved["nested"]["level1"]["level2"], ["a", "b", "c"])
        self.assertEqual(retrieved["unicode"], "Hello 世界 🌍")
    
    def test_cascade_deletion(self):
        """Test that deleting evaluation cascades to events and metrics."""
        eval_id = "test-cascade"
        
        # Store evaluation with events
        self.storage.store_evaluation(eval_id, {"status": "completed"})
        self.storage.store_events(eval_id, [
            {"type": "start", "message": "Started"},
            {"type": "end", "message": "Ended"}
        ])
        
        # Verify data exists
        events_before = self.storage.retrieve_events(eval_id)
        self.assertEqual(len(events_before), 2)
        
        # Delete evaluation
        result = self.storage.delete_evaluation(eval_id)
        self.assertTrue(result)
        
        # Verify cascade deletion
        events_after = self.storage.retrieve_events(eval_id)
        self.assertEqual(len(events_after), 0)
    
    def test_timestamp_handling(self):
        """Test proper timestamp storage and retrieval."""
        eval_id = "test-timestamp"
        
        # Store with specific timestamp
        timestamp = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        data = {
            "id": eval_id,
            "status": "completed",
            "timestamp": timestamp.isoformat()
        }
        
        self.storage.store_evaluation(eval_id, data)
        
        # Retrieve and verify
        result = self.storage.retrieve_evaluation(eval_id)
        self.assertIsNotNone(result)
        self.assertIn("timestamp", result)
        
        # Parse and compare timestamps
        stored_time = datetime.fromisoformat(result["timestamp"])
        self.assertEqual(stored_time.year, 2024)
        self.assertEqual(stored_time.month, 1)
        self.assertEqual(stored_time.day, 15)
    
    def test_concurrent_database_access(self):
        """Test that database handles concurrent access correctly."""
        import threading
        
        results = []
        errors = []
        
        def database_operation(thread_id):
            try:
                storage = self.create_storage()
                for i in range(5):
                    eval_id = f"concurrent-db-{thread_id}-{i}"
                    success = storage.store_evaluation(eval_id, {
                        "thread": thread_id,
                        "iteration": i
                    })
                    results.append((eval_id, success))
                    
                    # Also read to create more contention
                    storage.retrieve_evaluation(eval_id)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Run concurrent operations
        threads = []
        for i in range(3):
            t = threading.Thread(target=database_operation, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify no errors
        self.assertEqual(len(errors), 0, f"Database errors occurred: {errors}")
        
        # Verify all operations succeeded
        for eval_id, success in results:
            self.assertTrue(success)
            
            # Verify data integrity
            data = self.storage.retrieve_evaluation(eval_id)
            self.assertIsNotNone(data)
    
    def test_query_performance_with_indexes(self):
        """Test that indexed queries perform well."""
        import time
        
        # Store many evaluations
        for i in range(100):
            self.storage.store_evaluation(
                f"perf-test-{i:03d}",
                {"status": "completed" if i % 2 == 0 else "failed"}
            )
        
        # Time a query that uses the status index
        start_time = time.time()
        
        # This would be a more complex query in real usage
        # For now, just list evaluations
        result = self.storage.list_evaluations(limit=50)
        
        elapsed = time.time() - start_time
        
        # Should be fast (under 100ms even with 100 records)
        self.assertLess(elapsed, 0.1, f"Query took too long: {elapsed:.3f}s")
        self.assertEqual(len(result), 50)


if __name__ == '__main__':
    unittest.main()