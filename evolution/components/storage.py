"""
Storage services for persisting evaluation data.
These can evolve into full data warehousing platforms.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import abstractmethod
import unittest
import tempfile
import shutil

from .base import TestableComponent


class StorageService(TestableComponent):
    """
    Abstract storage service that must be testable.
    
    Future evolution:
    - S3/Object storage backends
    - PostgreSQL with JSONB
    - MongoDB document store
    - Redis for hot storage
    - Data lake integration
    """
    
    @abstractmethod
    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        """Store evaluation results"""
        pass
    
    @abstractmethod
    def retrieve_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve evaluation results"""
        pass
    
    @abstractmethod
    def store_events(self, eval_id: str, events: List[Dict[str, Any]]) -> bool:
        """Store evaluation events"""
        pass
    
    @abstractmethod
    def retrieve_events(self, eval_id: str) -> List[Dict[str, Any]]:
        """Retrieve evaluation events"""
        pass
    
    @abstractmethod
    def store_metadata(self, eval_id: str, metadata: Dict[str, Any]) -> bool:
        """Store evaluation metadata"""
        pass
    
    @abstractmethod
    def retrieve_metadata(self, eval_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve evaluation metadata"""
        pass
    
    @abstractmethod
    def list_evaluations(self, limit: int = 100, offset: int = 0) -> List[str]:
        """List evaluation IDs"""
        pass
    
    @abstractmethod
    def delete_evaluation(self, eval_id: str) -> bool:
        """Delete all data for an evaluation"""
        pass
    
    def self_test(self) -> Dict[str, Any]:
        """Test storage capabilities"""
        test_id = "test-storage"
        tests_passed = []
        tests_failed = []
        
        # Test evaluation storage
        try:
            test_data = {
                'id': test_id,
                'status': 'completed',
                'output': 'test output',
                'error': None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Store and retrieve
            if self.store_evaluation(test_id, test_data):
                tests_passed.append("Evaluation storage")
            else:
                tests_failed.append("Evaluation storage: store failed")
                
            retrieved = self.retrieve_evaluation(test_id)
            if retrieved and retrieved['id'] == test_id:
                tests_passed.append("Evaluation retrieval")
            else:
                tests_failed.append("Evaluation retrieval: data mismatch")
                
        except Exception as e:
            tests_failed.append(f"Evaluation test: {str(e)}")
        
        # Test event storage
        try:
            test_events = [
                {'type': 'start', 'message': 'Starting', 'timestamp': datetime.now(timezone.utc).isoformat()},
                {'type': 'end', 'message': 'Completed', 'timestamp': datetime.now(timezone.utc).isoformat()}
            ]
            
            if self.store_events(test_id, test_events):
                tests_passed.append("Event storage")
            else:
                tests_failed.append("Event storage: store failed")
                
            retrieved_events = self.retrieve_events(test_id)
            if len(retrieved_events) == 2:
                tests_passed.append("Event retrieval")
            else:
                tests_failed.append(f"Event retrieval: expected 2, got {len(retrieved_events)}")
                
        except Exception as e:
            tests_failed.append(f"Event test: {str(e)}")
        
        # Test metadata storage
        try:
            test_metadata = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'source': 'test',
                'version': '1.0'
            }
            
            if self.store_metadata(test_id, test_metadata):
                tests_passed.append("Metadata storage")
            else:
                tests_failed.append("Metadata storage: store failed")
                
            retrieved_meta = self.retrieve_metadata(test_id)
            if retrieved_meta and retrieved_meta['source'] == 'test':
                tests_passed.append("Metadata retrieval")
            else:
                tests_failed.append("Metadata retrieval: data mismatch")
                
        except Exception as e:
            tests_failed.append(f"Metadata test: {str(e)}")
        
        # Test listing
        try:
            evals = self.list_evaluations()
            if test_id in evals:
                tests_passed.append("Evaluation listing")
            else:
                tests_failed.append("Evaluation listing: test eval not found")
        except Exception as e:
            tests_failed.append(f"Listing test: {str(e)}")
        
        # Test deletion
        try:
            if self.delete_evaluation(test_id):
                tests_passed.append("Evaluation deletion")
                
                # Verify deletion
                if self.retrieve_evaluation(test_id) is None:
                    tests_passed.append("Deletion verification")
                else:
                    tests_failed.append("Deletion verification: data still exists")
            else:
                tests_failed.append("Evaluation deletion: delete failed")
                
        except Exception as e:
            tests_failed.append(f"Deletion test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }


class InMemoryStorage(StorageService):
    """
    Simple in-memory storage for testing and development.
    
    Future evolution:
    - Add TTL support
    - Add size limits
    - Add LRU eviction
    - Add persistence snapshots
    """
    
    def __init__(self):
        self.evaluations = {}
        self.events = {}
        self.metadata = {}
        self.lock = threading.Lock()
    
    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        with self.lock:
            self.evaluations[eval_id] = data.copy()
            return True
    
    def retrieve_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.evaluations.get(eval_id, {}).copy() if eval_id in self.evaluations else None
    
    def store_events(self, eval_id: str, events: List[Dict[str, Any]]) -> bool:
        with self.lock:
            self.events[eval_id] = [event.copy() for event in events]
            return True
    
    def retrieve_events(self, eval_id: str) -> List[Dict[str, Any]]:
        with self.lock:
            return [event.copy() for event in self.events.get(eval_id, [])]
    
    def store_metadata(self, eval_id: str, metadata: Dict[str, Any]) -> bool:
        with self.lock:
            self.metadata[eval_id] = metadata.copy()
            return True
    
    def retrieve_metadata(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.metadata.get(eval_id, {}).copy() if eval_id in self.metadata else None
    
    def list_evaluations(self, limit: int = 100, offset: int = 0) -> List[str]:
        with self.lock:
            eval_ids = list(self.evaluations.keys())
            return eval_ids[offset:offset + limit]
    
    def delete_evaluation(self, eval_id: str) -> bool:
        with self.lock:
            deleted = False
            if eval_id in self.evaluations:
                del self.evaluations[eval_id]
                deleted = True
            if eval_id in self.events:
                del self.events[eval_id]
                deleted = True
            if eval_id in self.metadata:
                del self.metadata[eval_id]
                deleted = True
            return deleted
    
    def get_test_suite(self) -> unittest.TestSuite:
        class InMemoryStorageTests(unittest.TestCase):
            def setUp(self):
                self.storage = InMemoryStorage()
            
            def test_evaluation_persistence(self):
                eval_data = {
                    'id': 'test-1',
                    'status': 'completed',
                    'output': 'Hello, World!'
                }
                self.assertTrue(self.storage.store_evaluation('test-1', eval_data))
                
                retrieved = self.storage.retrieve_evaluation('test-1')
                self.assertIsNotNone(retrieved)
                self.assertEqual(retrieved['output'], 'Hello, World!')
            
            def test_event_persistence(self):
                events = [
                    {'type': 'start', 'message': 'Starting evaluation'},
                    {'type': 'progress', 'message': 'Processing'},
                    {'type': 'end', 'message': 'Completed'}
                ]
                self.assertTrue(self.storage.store_events('test-2', events))
                
                retrieved = self.storage.retrieve_events('test-2')
                self.assertEqual(len(retrieved), 3)
                self.assertEqual(retrieved[0]['type'], 'start')
                self.assertEqual(retrieved[2]['type'], 'end')
            
            def test_metadata_persistence(self):
                metadata = {
                    'created_at': '2024-01-01T00:00:00Z',
                    'user': 'test_user',
                    'tags': ['test', 'example']
                }
                self.assertTrue(self.storage.store_metadata('test-3', metadata))
                
                retrieved = self.storage.retrieve_metadata('test-3')
                self.assertIsNotNone(retrieved)
                self.assertEqual(retrieved['user'], 'test_user')
                self.assertEqual(len(retrieved['tags']), 2)
            
            def test_listing_evaluations(self):
                # Store multiple evaluations
                for i in range(5):
                    self.storage.store_evaluation(f'eval-{i}', {'id': f'eval-{i}'})
                
                # Test listing with pagination
                all_evals = self.storage.list_evaluations()
                self.assertGreaterEqual(len(all_evals), 5)
                
                # Test limit
                limited = self.storage.list_evaluations(limit=3)
                self.assertEqual(len(limited), 3)
                
                # Test offset
                offset_evals = self.storage.list_evaluations(limit=2, offset=2)
                self.assertEqual(len(offset_evals), 2)
            
            def test_deletion(self):
                # Store all types of data
                eval_id = 'test-delete'
                self.storage.store_evaluation(eval_id, {'id': eval_id})
                self.storage.store_events(eval_id, [{'type': 'test'}])
                self.storage.store_metadata(eval_id, {'test': True})
                
                # Verify data exists
                self.assertIsNotNone(self.storage.retrieve_evaluation(eval_id))
                self.assertEqual(len(self.storage.retrieve_events(eval_id)), 1)
                self.assertIsNotNone(self.storage.retrieve_metadata(eval_id))
                
                # Delete
                self.assertTrue(self.storage.delete_evaluation(eval_id))
                
                # Verify deletion
                self.assertIsNone(self.storage.retrieve_evaluation(eval_id))
                self.assertEqual(len(self.storage.retrieve_events(eval_id)), 0)
                self.assertIsNone(self.storage.retrieve_metadata(eval_id))
            
            def test_thread_safety(self):
                """Test concurrent access"""
                eval_id = 'test-concurrent'
                
                def store_data(thread_id):
                    for i in range(10):
                        self.storage.store_evaluation(
                            f'{eval_id}-{thread_id}-{i}',
                            {'thread': thread_id, 'index': i}
                        )
                
                # Start multiple threads
                threads = []
                for i in range(5):
                    t = threading.Thread(target=store_data, args=(i,))
                    threads.append(t)
                    t.start()
                
                # Wait for completion
                for t in threads:
                    t.join()
                
                # Verify all data was stored
                all_evals = self.storage.list_evaluations(limit=1000)
                concurrent_evals = [e for e in all_evals if e.startswith(eval_id)]
                self.assertEqual(len(concurrent_evals), 50)  # 5 threads * 10 items
        
        return unittest.TestLoader().loadTestsFromTestCase(InMemoryStorageTests)


class FileStorage(StorageService):
    """
    File-based storage with JSON serialization.
    Thread-safe implementation with proper file locking.
    
    Future evolution:
    - Add compression support
    - Add encryption at rest
    - Add file rotation/archival
    - Add database-style indexing
    - Add distributed file system support
    """
    
    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.lock = threading.Lock()
        
        # Create directory structure
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure storage directories exist"""
        directories = [
            self.base_path,
            self.base_path / "evaluations",
            self.base_path / "events",
            self.base_path / "metadata"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_eval_path(self, eval_id: str) -> Path:
        """Get evaluation file path"""
        return self.base_path / "evaluations" / f"{eval_id}.json"
    
    def _get_events_path(self, eval_id: str) -> Path:
        """Get events file path"""
        return self.base_path / "events" / f"{eval_id}.json"
    
    def _get_metadata_path(self, eval_id: str) -> Path:
        """Get metadata file path"""
        return self.base_path / "metadata" / f"{eval_id}.json"
    
    def _write_json(self, path: Path, data: Any) -> bool:
        """Write JSON data to file atomically"""
        try:
            # Write to temporary file first for atomicity
            temp_path = path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomic rename
            temp_path.replace(path)
            return True
            
        except Exception as e:
            # Clean up temp file if exists
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def _read_json(self, path: Path) -> Optional[Any]:
        """Read JSON data from file"""
        if not path.exists():
            return None
            
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Handle corrupted files
            return None
    
    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        with self.lock:
            try:
                path = self._get_eval_path(eval_id)
                return self._write_json(path, data)
            except Exception:
                return False
    
    def retrieve_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            path = self._get_eval_path(eval_id)
            return self._read_json(path)
    
    def store_events(self, eval_id: str, events: List[Dict[str, Any]]) -> bool:
        with self.lock:
            try:
                path = self._get_events_path(eval_id)
                return self._write_json(path, events)
            except Exception:
                return False
    
    def retrieve_events(self, eval_id: str) -> List[Dict[str, Any]]:
        with self.lock:
            path = self._get_events_path(eval_id)
            result = self._read_json(path)
            return result if result is not None else []
    
    def store_metadata(self, eval_id: str, metadata: Dict[str, Any]) -> bool:
        with self.lock:
            try:
                path = self._get_metadata_path(eval_id)
                return self._write_json(path, metadata)
            except Exception:
                return False
    
    def retrieve_metadata(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            path = self._get_metadata_path(eval_id)
            return self._read_json(path)
    
    def list_evaluations(self, limit: int = 100, offset: int = 0) -> List[str]:
        with self.lock:
            eval_dir = self.base_path / "evaluations"
            if not eval_dir.exists():
                return []
            
            # Get all evaluation files
            eval_files = sorted(eval_dir.glob("*.json"))
            
            # Extract IDs and apply pagination
            eval_ids = [f.stem for f in eval_files]
            return eval_ids[offset:offset + limit]
    
    def delete_evaluation(self, eval_id: str) -> bool:
        with self.lock:
            deleted = False
            
            # Delete all associated files
            for path_func in [self._get_eval_path, self._get_events_path, self._get_metadata_path]:
                path = path_func(eval_id)
                if path.exists():
                    path.unlink()
                    deleted = True
            
            return deleted
    
    def get_test_suite(self) -> unittest.TestSuite:
        storage = self
        
        class FileStorageTests(unittest.TestCase):
            def setUp(self):
                # Use temporary directory for tests
                self.temp_dir = tempfile.mkdtemp()
                self.storage = FileStorage(self.temp_dir)
            
            def tearDown(self):
                # Clean up temporary directory
                shutil.rmtree(self.temp_dir)
            
            def test_file_creation(self):
                """Test that files are created correctly"""
                eval_id = 'test-file-1'
                eval_data = {'id': eval_id, 'status': 'completed'}
                
                self.assertTrue(self.storage.store_evaluation(eval_id, eval_data))
                
                # Check file exists
                eval_path = self.storage._get_eval_path(eval_id)
                self.assertTrue(eval_path.exists())
                
                # Check content
                with open(eval_path, 'r') as f:
                    stored_data = json.load(f)
                    self.assertEqual(stored_data['id'], eval_id)
            
            def test_atomic_writes(self):
                """Test that writes are atomic (no partial writes)"""
                eval_id = 'test-atomic'
                
                # Store initial data
                self.storage.store_evaluation(eval_id, {'version': 1})
                
                # Simulate concurrent writes
                def write_data(version):
                    for i in range(10):
                        self.storage.store_evaluation(
                            eval_id,
                            {'version': version, 'iteration': i}
                        )
                
                threads = []
                for v in range(3):
                    t = threading.Thread(target=write_data, args=(v,))
                    threads.append(t)
                    t.start()
                
                for t in threads:
                    t.join()
                
                # Check final state is consistent (not corrupted)
                final_data = self.storage.retrieve_evaluation(eval_id)
                self.assertIsNotNone(final_data)
                self.assertIn('version', final_data)
                self.assertIn('iteration', final_data)
            
            def test_directory_structure(self):
                """Test proper directory organization"""
                eval_id = 'test-dirs'
                
                self.storage.store_evaluation(eval_id, {'type': 'evaluation'})
                self.storage.store_events(eval_id, [{'type': 'event'}])
                self.storage.store_metadata(eval_id, {'type': 'metadata'})
                
                # Check files are in correct directories
                self.assertTrue((Path(self.temp_dir) / "evaluations" / f"{eval_id}.json").exists())
                self.assertTrue((Path(self.temp_dir) / "events" / f"{eval_id}.json").exists())
                self.assertTrue((Path(self.temp_dir) / "metadata" / f"{eval_id}.json").exists())
            
            def test_json_serialization(self):
                """Test complex data serialization"""
                eval_id = 'test-json'
                complex_data = {
                    'id': eval_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'nested': {
                        'list': [1, 2, 3],
                        'dict': {'a': 1, 'b': 2}
                    },
                    'unicode': 'Hello 世界 🌍'
                }
                
                self.assertTrue(self.storage.store_evaluation(eval_id, complex_data))
                retrieved = self.storage.retrieve_evaluation(eval_id)
                
                self.assertEqual(retrieved['id'], eval_id)
                self.assertEqual(retrieved['nested']['list'], [1, 2, 3])
                self.assertEqual(retrieved['unicode'], 'Hello 世界 🌍')
            
            def test_missing_files(self):
                """Test handling of missing files"""
                self.assertIsNone(self.storage.retrieve_evaluation('nonexistent'))
                self.assertEqual(self.storage.retrieve_events('nonexistent'), [])
                self.assertIsNone(self.storage.retrieve_metadata('nonexistent'))
            
            def test_concurrent_access(self):
                """Test thread-safe operations"""
                results = []
                
                def store_and_retrieve(thread_id):
                    eval_id = f'concurrent-{thread_id}'
                    data = {'thread': thread_id, 'data': list(range(100))}
                    
                    # Store
                    success = self.storage.store_evaluation(eval_id, data)
                    results.append(('store', thread_id, success))
                    
                    # Retrieve
                    retrieved = self.storage.retrieve_evaluation(eval_id)
                    results.append(('retrieve', thread_id, retrieved is not None))
                    
                    # List
                    evals = self.storage.list_evaluations()
                    results.append(('list', thread_id, eval_id in evals))
                
                # Run concurrent operations
                threads = []
                for i in range(10):
                    t = threading.Thread(target=store_and_retrieve, args=(i,))
                    threads.append(t)
                    t.start()
                
                for t in threads:
                    t.join()
                
                # Verify all operations succeeded
                for op_type, thread_id, success in results:
                    self.assertTrue(success, f"Operation {op_type} failed for thread {thread_id}")
        
        return unittest.TestLoader().loadTestsFromTestCase(FileStorageTests)