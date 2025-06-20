"""
Base test cases that all storage backends must pass.
"""

import unittest
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any
from abc import abstractmethod


class StorageServiceTestMixin:
    """
    Mixin class containing tests that all storage backends must pass.
    
    Usage:
        class MyStorageTests(StorageServiceTestMixin, unittest.TestCase):
            def create_storage(self):
                return MyStorage()
    """
    
    @abstractmethod
    def create_storage(self):
        """Create a fresh storage instance for testing"""
        pass
    
    def setUp(self):
        """Set up test fixtures"""
        self.storage = self.create_storage()
        self.test_eval_id = "test-eval-001"
        self.test_data = {
            'id': self.test_eval_id,
            'status': 'completed',
            'output': 'Hello, World!',
            'error': None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def tearDown(self):
        """Clean up after tests"""
        # Clean up any test data
        self.storage.delete_evaluation(self.test_eval_id)
    
    # Basic CRUD Operations
    
    def test_store_and_retrieve_evaluation(self):
        """Test basic evaluation storage and retrieval"""
        # Store
        result = self.storage.store_evaluation(self.test_eval_id, self.test_data)
        self.assertTrue(result, "Failed to store evaluation")
        
        # Retrieve
        retrieved = self.storage.retrieve_evaluation(self.test_eval_id)
        self.assertIsNotNone(retrieved, "Failed to retrieve evaluation")
        self.assertEqual(retrieved['id'], self.test_eval_id)
        self.assertEqual(retrieved['status'], 'completed')
        self.assertEqual(retrieved['output'], 'Hello, World!')
    
    def test_retrieve_nonexistent_evaluation(self):
        """Test retrieving evaluation that doesn't exist"""
        result = self.storage.retrieve_evaluation("nonexistent-id")
        self.assertIsNone(result)
    
    def test_update_evaluation(self):
        """Test updating existing evaluation"""
        # Store initial
        self.storage.store_evaluation(self.test_eval_id, self.test_data)
        
        # Update
        updated_data = self.test_data.copy()
        updated_data['status'] = 'failed'
        updated_data['error'] = 'Test error'
        
        result = self.storage.store_evaluation(self.test_eval_id, updated_data)
        self.assertTrue(result)
        
        # Verify update
        retrieved = self.storage.retrieve_evaluation(self.test_eval_id)
        self.assertEqual(retrieved['status'], 'failed')
        self.assertEqual(retrieved['error'], 'Test error')
    
    # Event Storage Tests
    
    def test_store_and_retrieve_events(self):
        """Test event storage and retrieval"""
        events = [
            {'type': 'submitted', 'timestamp': '2024-01-01T00:00:00Z', 'message': 'Evaluation submitted'},
            {'type': 'started', 'timestamp': '2024-01-01T00:00:01Z', 'message': 'Evaluation started'},
            {'type': 'completed', 'timestamp': '2024-01-01T00:00:10Z', 'message': 'Evaluation completed'}
        ]
        
        # Store
        result = self.storage.store_events(self.test_eval_id, events)
        self.assertTrue(result)
        
        # Retrieve
        retrieved = self.storage.retrieve_events(self.test_eval_id)
        self.assertEqual(len(retrieved), 3)
        self.assertEqual(retrieved[0]['type'], 'submitted')
        self.assertEqual(retrieved[2]['type'], 'completed')
    
    def test_retrieve_events_nonexistent(self):
        """Test retrieving events for nonexistent evaluation"""
        events = self.storage.retrieve_events("nonexistent-id")
        self.assertIsInstance(events, list)
        self.assertEqual(len(events), 0)
    
    # Metadata Storage Tests
    
    def test_store_and_retrieve_metadata(self):
        """Test metadata storage and retrieval"""
        metadata = {
            'user': 'test_user',
            'tags': ['test', 'example', 'unit-test'],
            'config': {
                'timeout': 30,
                'memory_limit': '512MB'
            }
        }
        
        # Store
        result = self.storage.store_metadata(self.test_eval_id, metadata)
        self.assertTrue(result)
        
        # Retrieve
        retrieved = self.storage.retrieve_metadata(self.test_eval_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['user'], 'test_user')
        self.assertEqual(len(retrieved['tags']), 3)
        self.assertEqual(retrieved['config']['timeout'], 30)
    
    def test_retrieve_metadata_nonexistent(self):
        """Test retrieving metadata for nonexistent evaluation"""
        metadata = self.storage.retrieve_metadata("nonexistent-id")
        self.assertIsNone(metadata)
    
    # Listing and Pagination Tests
    
    def test_list_evaluations(self):
        """Test listing evaluations"""
        # Store multiple evaluations
        eval_ids = []
        for i in range(5):
            eval_id = f"test-eval-{i:03d}"
            eval_ids.append(eval_id)
            self.storage.store_evaluation(eval_id, {'id': eval_id, 'index': i})
        
        try:
            # Test basic listing
            listed = self.storage.list_evaluations()
            for eval_id in eval_ids:
                self.assertIn(eval_id, listed)
            
            # Test limit
            limited = self.storage.list_evaluations(limit=3)
            self.assertLessEqual(len(limited), 3)
            
            # Test offset
            offset_list = self.storage.list_evaluations(limit=10, offset=2)
            # Should have at least 3 items (5 total - 2 offset)
            self.assertGreaterEqual(len([id for id in offset_list if id.startswith("test-eval-")]), 3)
            
        finally:
            # Clean up
            for eval_id in eval_ids:
                self.storage.delete_evaluation(eval_id)
    
    def test_list_empty_storage(self):
        """Test listing when storage is empty or near empty"""
        # Clear any test evaluations
        for eval_id in self.storage.list_evaluations(limit=1000):
            if eval_id.startswith("test-"):
                self.storage.delete_evaluation(eval_id)
        
        listed = self.storage.list_evaluations()
        # Should return a list (might not be empty in shared storage)
        self.assertIsInstance(listed, list)
    
    # Deletion Tests
    
    def test_delete_evaluation(self):
        """Test deleting evaluation and all associated data"""
        # Store all types of data
        self.storage.store_evaluation(self.test_eval_id, self.test_data)
        self.storage.store_events(self.test_eval_id, [{'type': 'test'}])
        self.storage.store_metadata(self.test_eval_id, {'test': True})
        
        # Verify data exists
        self.assertIsNotNone(self.storage.retrieve_evaluation(self.test_eval_id))
        self.assertGreater(len(self.storage.retrieve_events(self.test_eval_id)), 0)
        self.assertIsNotNone(self.storage.retrieve_metadata(self.test_eval_id))
        
        # Delete
        result = self.storage.delete_evaluation(self.test_eval_id)
        self.assertTrue(result)
        
        # Verify deletion
        self.assertIsNone(self.storage.retrieve_evaluation(self.test_eval_id))
        self.assertEqual(len(self.storage.retrieve_events(self.test_eval_id)), 0)
        self.assertIsNone(self.storage.retrieve_metadata(self.test_eval_id))
    
    def test_delete_nonexistent(self):
        """Test deleting evaluation that doesn't exist"""
        result = self.storage.delete_evaluation("nonexistent-id")
        # Should return False or True depending on implementation
        self.assertIsInstance(result, bool)
    
    # Data Integrity Tests
    
    def test_data_isolation(self):
        """Test that different evaluations don't interfere with each other"""
        eval_id_1 = "test-iso-001"
        eval_id_2 = "test-iso-002"
        
        try:
            # Store different data for each
            self.storage.store_evaluation(eval_id_1, {'id': eval_id_1, 'value': 'first'})
            self.storage.store_evaluation(eval_id_2, {'id': eval_id_2, 'value': 'second'})
            
            # Verify isolation
            data_1 = self.storage.retrieve_evaluation(eval_id_1)
            data_2 = self.storage.retrieve_evaluation(eval_id_2)
            
            self.assertEqual(data_1['value'], 'first')
            self.assertEqual(data_2['value'], 'second')
            
            # Delete one shouldn't affect the other
            self.storage.delete_evaluation(eval_id_1)
            
            data_2_after = self.storage.retrieve_evaluation(eval_id_2)
            self.assertIsNotNone(data_2_after)
            self.assertEqual(data_2_after['value'], 'second')
            
        finally:
            # Clean up
            self.storage.delete_evaluation(eval_id_1)
            self.storage.delete_evaluation(eval_id_2)
    
    def test_data_immutability(self):
        """Test that retrieved data doesn't affect stored data"""
        self.storage.store_evaluation(self.test_eval_id, self.test_data)
        
        # Retrieve and modify
        retrieved = self.storage.retrieve_evaluation(self.test_eval_id)
        retrieved['status'] = 'modified'
        
        # Re-retrieve and check
        fresh_retrieve = self.storage.retrieve_evaluation(self.test_eval_id)
        self.assertEqual(fresh_retrieve['status'], 'completed')  # Should be unchanged
    
    # Concurrency Tests
    
    def test_concurrent_writes(self):
        """Test concurrent write operations"""
        num_threads = 5
        writes_per_thread = 10
        results = []
        errors = []
        
        def write_evaluations(thread_id):
            try:
                for i in range(writes_per_thread):
                    eval_id = f"concurrent-{thread_id}-{i}"
                    data = {'id': eval_id, 'thread': thread_id, 'index': i}
                    success = self.storage.store_evaluation(eval_id, data)
                    results.append((eval_id, success))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=write_evaluations, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), num_threads * writes_per_thread)
        
        # Verify all writes succeeded
        for eval_id, success in results:
            self.assertTrue(success, f"Write failed for {eval_id}")
            
            # Verify data integrity
            data = self.storage.retrieve_evaluation(eval_id)
            self.assertIsNotNone(data, f"Failed to retrieve {eval_id}")
            self.assertEqual(data['id'], eval_id)
        
        # Clean up
        for eval_id, _ in results:
            self.storage.delete_evaluation(eval_id)
    
    def test_concurrent_read_write(self):
        """Test concurrent read and write operations"""
        shared_eval_id = "concurrent-shared"
        write_count = 0
        read_count = 0
        lock = threading.Lock()
        
        # Initial data
        self.storage.store_evaluation(shared_eval_id, {'counter': 0})
        
        def writer_thread():
            nonlocal write_count
            for i in range(20):
                self.storage.store_evaluation(shared_eval_id, {'counter': i})
                with lock:
                    write_count += 1
                time.sleep(0.001)  # Small delay to encourage interleaving
        
        def reader_thread():
            nonlocal read_count
            for _ in range(20):
                data = self.storage.retrieve_evaluation(shared_eval_id)
                self.assertIsNotNone(data)
                self.assertIn('counter', data)
                with lock:
                    read_count += 1
                time.sleep(0.001)
        
        # Start threads
        threads = []
        for _ in range(2):  # 2 writers
            t = threading.Thread(target=writer_thread)
            threads.append(t)
            t.start()
        
        for _ in range(3):  # 3 readers
            t = threading.Thread(target=reader_thread)
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify operations completed
        self.assertEqual(write_count, 40)  # 2 writers * 20 writes
        self.assertEqual(read_count, 60)   # 3 readers * 20 reads
        
        # Clean up
        self.storage.delete_evaluation(shared_eval_id)
    
    # Edge Cases
    
    def test_empty_data_storage(self):
        """Test storing empty or minimal data"""
        test_cases = [
            ({}, "empty dict"),
            ({'id': self.test_eval_id}, "minimal data"),
            ({'id': self.test_eval_id, 'data': None}, "null value"),
            ({'id': self.test_eval_id, 'list': []}, "empty list"),
        ]
        
        for i, (data, description) in enumerate(test_cases):
            eval_id = f"edge-case-{i}"
            
            # Store
            result = self.storage.store_evaluation(eval_id, data)
            self.assertTrue(result, f"Failed to store {description}")
            
            # Retrieve
            retrieved = self.storage.retrieve_evaluation(eval_id)
            self.assertIsNotNone(retrieved, f"Failed to retrieve {description}")
            
            # Clean up
            self.storage.delete_evaluation(eval_id)
    
    def test_large_data_storage(self):
        """Test storing large data structures"""
        large_eval_id = "test-large-data"
        
        # Create large data structure
        large_data = {
            'id': large_eval_id,
            'large_list': list(range(1000)),
            'nested': {
                f'key_{i}': f'value_{i}' * 100  # 100 chars per value
                for i in range(100)
            },
            'text': 'x' * 10000  # 10KB of text
        }
        
        # Store
        result = self.storage.store_evaluation(large_eval_id, large_data)
        self.assertTrue(result, "Failed to store large data")
        
        # Retrieve
        retrieved = self.storage.retrieve_evaluation(large_eval_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved['large_list']), 1000)
        self.assertEqual(len(retrieved['nested']), 100)
        self.assertEqual(len(retrieved['text']), 10000)
        
        # Clean up
        self.storage.delete_evaluation(large_eval_id)