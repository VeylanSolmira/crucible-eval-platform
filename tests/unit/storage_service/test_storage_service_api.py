#!/usr/bin/env python3
"""
Comprehensive unit tests for storage service REST API.
Tests all API endpoints including event handling, statistics, and concurrent requests.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import json

# Import storage service app using proper package import
from storage_service.app import app


@pytest.mark.unit
class TestStorageServiceAPI:
    """Test storage service REST API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage manager."""
        with patch('storage_service.app.storage') as mock:
            yield mock
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "storage_backend" in response.json()
        assert "timestamp" in response.json()
    
    def test_get_evaluation_success(self, client, mock_storage):
        """Test successful evaluation retrieval."""
        # Mock storage response
        mock_eval = {
            "id": "test-123",
            "code_hash": "abc123",
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "output": "Hello, World!",
            "runtime_ms": 100,
            "memory_used_mb": 50
        }
        mock_storage.get_evaluation.return_value = mock_eval
        
        # Get evaluation
        response = client.get("/evaluations/test-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-123"
        assert data["status"] == "completed"
        assert data["output"] == "Hello, World!"
        
        # Verify storage was called
        mock_storage.get_evaluation.assert_called_once_with("test-123")
    
    def test_get_evaluation_not_found(self, client, mock_storage):
        """Test evaluation not found."""
        mock_storage.get_evaluation.return_value = None
        
        response = client.get("/evaluations/non-existent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_create_evaluation(self, client, mock_storage):
        """Test creating a new evaluation."""
        # Prepare request
        eval_data = {
            "id": "new-eval-123",
            "code": "print('test')",  # Required field
            "language": "python",
            "metadata": {"test": True}
        }
        
        # Mock storage - create returns True, then get returns the created eval
        mock_storage.create_evaluation.return_value = True
        mock_created_eval = {
            "id": "new-eval-123",
            "code": "print('test')",
            "language": "python",
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"test": True}
        }
        mock_storage.get_evaluation.return_value = mock_created_eval
        
        # Create evaluation
        response = client.post("/evaluations", json=eval_data)
        
        assert response.status_code == 200  # FastAPI returns 200 by default, not 201
        assert response.json()["id"] == "new-eval-123"
        
        # Verify storage was called
        mock_storage.create_evaluation.assert_called_once()
        call_args = mock_storage.create_evaluation.call_args
        assert call_args[0][0] == "new-eval-123"  # First positional arg
        assert call_args[0][1] == "print('test')"  # Second positional arg (code)
    
    def test_delete_evaluation(self, client, mock_storage):
        """Test deleting an evaluation."""
        # Mock that evaluation exists
        mock_storage.get_evaluation.return_value = {"id": "test-123", "status": "completed"}
        # Delete actually uses update_evaluation for soft delete
        mock_storage.update_evaluation.return_value = True
        
        response = client.delete("/evaluations/test-123")
        
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verify get was called
        mock_storage.get_evaluation.assert_called_once_with("test-123")
        # Verify update was called for soft delete
        mock_storage.update_evaluation.assert_called_once()
        call_kwargs = mock_storage.update_evaluation.call_args[1]
        assert "deleted_at" in call_kwargs
    
    def test_list_evaluations(self, client, mock_storage):
        """Test listing evaluations with filters."""
        # Mock storage response
        mock_evals = [
            {"id": "eval-1", "status": "completed", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "eval-2", "status": "completed", "created_at": "2024-01-02T00:00:00Z"}
        ]
        mock_storage.list_evaluations.return_value = mock_evals
        # Mock count method that storage service expects
        mock_storage.count_evaluations.return_value = len(mock_evals)
        
        # List with filters
        response = client.get("/evaluations?status=completed&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["evaluations"]) == 2
        assert data["total"] == 2
        
        # Verify list was called
        mock_storage.list_evaluations.assert_called_once()
        mock_storage.count_evaluations.assert_called_once()
    
    def test_get_evaluation_events(self, client, mock_storage):
        """Test retrieving evaluation events."""
        # Mock that evaluation exists
        mock_storage.get_evaluation.return_value = {"id": "test-123", "status": "completed"}
        
        mock_events = [
            {
                "type": "status_change",  # EventResponse expects 'type' not 'event_type'
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Status changed from queued to running",
                "metadata": {"old_status": "queued", "new_status": "running"}
            }
        ]
        # Storage uses get_events, not get_evaluation_events
        mock_storage.get_events.return_value = mock_events
        
        response = client.get("/evaluations/test-123/events")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Response is a list, not a dict with "events" key
        assert data[0]["type"] == "status_change"
    
    def test_error_handling(self, client, mock_storage):
        """Test error handling for storage failures."""
        # Mock storage error
        mock_storage.get_evaluation.side_effect = Exception("Database connection error")
        
        # The storage service doesn't catch exceptions, so this will raise
        with pytest.raises(Exception, match="Database connection error"):
            response = client.get("/evaluations/test-123")
    
    def test_update_evaluation(self, client, mock_storage):
        """Test updating an evaluation."""
        # Mock existing evaluation
        mock_eval = {"id": "test-123", "status": "running"}
        mock_storage.get_evaluation.return_value = mock_eval
        mock_storage.update_evaluation.return_value = True
        
        # Update - use PUT not PATCH
        update_data = {"status": "completed", "output": "Done!"}
        response = client.put("/evaluations/test-123", json=update_data)
        
        assert response.status_code == 200
        assert "id" in response.json()
        
        # Verify update was called with keyword arguments
        mock_storage.update_evaluation.assert_called_once()
        call_args = mock_storage.update_evaluation.call_args
        assert call_args[0][0] == "test-123"  # eval_id is first positional arg
        # Check keyword arguments
        assert "status" in call_args[1]
        assert call_args[1]["status"] == "completed"
    
    # ========== Additional Tests from Non-Simple Versions ==========
    
    def test_root_endpoint_exists(self, client):
        """Test root endpoint exists."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Storage Service" in response.json()["service"]
    
    def test_openapi_endpoint_exists(self, client):
        """Test OpenAPI endpoint exists."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()
    
    def test_docs_endpoint_exists(self, client):
        """Test docs endpoint exists."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
    
    def test_create_event(self, client, mock_storage):
        """Test creating an evaluation event."""
        # Mock that evaluation exists
        mock_storage.get_evaluation.return_value = {"id": "test-123", "status": "running"}
        
        event_data = {
            "type": "custom_event",
            "message": "Something happened",
            "metadata": {"key": "value"}
        }
        
        mock_storage.add_event.return_value = True
        
        response = client.post("/evaluations/test-123/events", json=event_data)
        
        assert response.status_code == 200  # FastAPI default, not 201
        assert response.json()["type"] == "custom_event"
        assert "timestamp" in response.json()
        
        # Verify event was stored
        mock_storage.add_event.assert_called_once()
        call_args = mock_storage.add_event.call_args
        assert call_args[0][0] == "test-123"
        assert call_args[0][1] == "custom_event"
    
    def test_get_statistics(self, client, mock_storage):
        """Test getting storage statistics."""
        # Mock evaluations for stats calculation
        mock_evals = [
            {"id": "eval-1", "status": "completed", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "eval-2", "status": "failed", "created_at": "2024-01-02T00:00:00Z"},
            {"id": "eval-3", "status": "completed", "created_at": "2024-01-03T00:00:00Z"}
        ]
        mock_storage.list_evaluations.return_value = mock_evals
        
        response = client.get("/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_evaluations"] == 3
        assert data["by_status"]["completed"] == 2
        assert data["by_status"]["failed"] == 1
    
    def test_celery_update_endpoint(self, client, mock_storage):
        """Test Celery task status update endpoint."""
        # Mock existing evaluation
        mock_eval = {"id": "test-123", "status": "running", "metadata": {}}
        mock_storage.get_evaluation.return_value = mock_eval
        mock_storage.update_evaluation.return_value = True
        
        celery_update = {
            "celery_task_id": "task-abc-123",
            "task_state": "SUCCESS",
            "retries": 0,
            "output": "Task completed successfully"
        }
        
        response = client.post("/evaluations/test-123/celery-update", json=celery_update)
        
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verify update was called
        mock_storage.update_evaluation.assert_called_once()
        call_kwargs = mock_storage.update_evaluation.call_args[1]
        assert call_kwargs["status"] == "completed"  # SUCCESS maps to completed
        assert "metadata" in call_kwargs
        assert call_kwargs["metadata"]["celery_task_id"] == "task-abc-123"
    
    def test_get_running_evaluations(self, client):
        """Test listing running evaluations from Redis."""
        # Create a mock redis client
        mock_redis = MagicMock()
        mock_redis.smembers = AsyncMock(return_value=set())
        
        # Patch it at module level
        with patch('storage_service.app.redis_client', mock_redis):
            response = client.get("/evaluations/running")
            
            # Now it should work
            assert response.status_code == 200
            data = response.json()
            assert "running_evaluations" in data
            assert data["count"] == 0
    
    def test_get_storage_info(self, client):
        """Test storage info endpoint."""
        response = client.get("/storage-info")
        assert response.status_code == 200
        data = response.json()
        assert "primary_backend" in data
        assert "cache_enabled" in data
        assert "backends_available" in data
        assert isinstance(data["backends_available"], list)
    
    def test_concurrent_requests(self, client, mock_storage):
        """Test handling concurrent requests."""
        import threading
        
        results = []
        
        def make_request():
            resp = client.get("/evaluations/test-123")
            results.append(resp.status_code)
        
        # Mock storage with delay
        def slow_retrieve(eval_id):
            import time
            time.sleep(0.1)
            return {"id": eval_id, "status": "completed"}
        
        mock_storage.get_evaluation.side_effect = slow_retrieve
        
        # Make concurrent requests
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All should succeed
        assert all(code == 200 for code in results)
        assert len(results) == 5