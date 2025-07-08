#!/usr/bin/env python3
"""
Unit tests for Celery task cancellation functionality.
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.celery_client import cancel_celery_task, get_celery_task_info


class TestCeleryCancellation(unittest.TestCase):
    """Test the Celery cancellation functionality."""

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_cancel_pending_task(self, mock_celery_app):
        """Test cancelling a task that's still pending in queue."""
        # Setup mock
        mock_result = Mock()
        mock_result.state = "PENDING"
        mock_result.revoke = Mock()

        mock_celery_app.AsyncResult = Mock(return_value=mock_result)

        # Test cancellation
        result = cancel_celery_task("test-123")

        # Verify
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["task_id"], "celery-test-123")
        self.assertIn("pending in queue", result["message"])
        mock_result.revoke.assert_called_once()

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_cancel_running_task_without_terminate(self, mock_celery_app):
        """Test attempting to cancel a running task without terminate flag."""
        # Setup mock
        mock_result = Mock()
        mock_result.state = "STARTED"

        mock_celery_app.AsyncResult = Mock(return_value=mock_result)

        # Test cancellation
        result = cancel_celery_task("test-456", terminate=False)

        # Verify
        self.assertFalse(result["cancelled"])
        self.assertIn("already running", result["message"])
        self.assertIn("terminate=true", result["message"])

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_cancel_running_task_with_terminate(self, mock_celery_app):
        """Test forcefully terminating a running task."""
        # Setup mock
        mock_result = Mock()
        mock_result.state = "STARTED"
        mock_result.revoke = Mock()

        mock_celery_app.AsyncResult = Mock(return_value=mock_result)

        # Test cancellation with terminate
        result = cancel_celery_task("test-789", terminate=True)

        # Verify
        self.assertTrue(result["cancelled"])
        self.assertIn("forcefully terminated", result["message"])
        mock_result.revoke.assert_called_once_with(terminate=True)

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_cancel_completed_task(self, mock_celery_app):
        """Test attempting to cancel an already completed task."""
        # Setup mock
        mock_result = Mock()
        mock_result.state = "SUCCESS"

        mock_celery_app.AsyncResult = Mock(return_value=mock_result)

        # Test cancellation
        result = cancel_celery_task("test-completed")

        # Verify
        self.assertFalse(result["cancelled"])
        self.assertIn("already completed", result["message"])

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_cancel_already_revoked_task(self, mock_celery_app):
        """Test attempting to cancel an already cancelled task."""
        # Setup mock
        mock_result = Mock()
        mock_result.state = "REVOKED"

        mock_celery_app.AsyncResult = Mock(return_value=mock_result)

        # Test cancellation
        result = cancel_celery_task("test-revoked")

        # Verify
        self.assertFalse(result["cancelled"])
        self.assertIn("already cancelled", result["message"])

    @patch("api.celery_client.CELERY_ENABLED", False)
    def test_cancel_with_celery_disabled(self):
        """Test cancellation when Celery is not enabled."""
        result = cancel_celery_task("test-disabled")

        self.assertFalse(result["cancelled"])
        self.assertEqual(result["reason"], "Celery not enabled")

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_cancel_with_exception(self, mock_celery_app):
        """Test cancellation when an exception occurs."""
        # Setup mock to raise exception
        mock_celery_app.AsyncResult.side_effect = Exception("Connection failed")

        # Test cancellation
        result = cancel_celery_task("test-error")

        # Verify
        self.assertFalse(result["cancelled"])
        self.assertIn("Connection failed", result["error"])
        self.assertEqual(result["message"], "Failed to cancel task")

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_get_task_info_success(self, mock_celery_app):
        """Test getting task info for a successful task."""
        # Setup mock
        mock_result = Mock()
        mock_result.state = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.failed.return_value = False
        mock_result.result = {"output": "Hello World", "exit_code": 0}

        mock_celery_app.AsyncResult = Mock(return_value=mock_result)

        # Test getting info
        info = get_celery_task_info("test-success")

        # Verify
        self.assertEqual(info["state"], "SUCCESS")
        self.assertTrue(info["ready"])
        self.assertTrue(info["successful"])
        self.assertFalse(info["failed"])
        self.assertEqual(info["result"], {"output": "Hello World", "exit_code": 0})

    @patch("api.celery_client.CELERY_ENABLED", True)
    @patch("api.celery_client.celery_app")
    def test_get_task_info_failed(self, mock_celery_app):
        """Test getting task info for a failed task."""
        # Setup mock
        mock_result = Mock()
        mock_result.state = "FAILURE"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.failed.return_value = True
        mock_result.info = Exception("Task failed")
        mock_result.traceback = "Traceback..."

        mock_celery_app.AsyncResult = Mock(return_value=mock_result)

        # Test getting info
        info = get_celery_task_info("test-failed")

        # Verify
        self.assertEqual(info["state"], "FAILURE")
        self.assertTrue(info["ready"])
        self.assertFalse(info["successful"])
        self.assertTrue(info["failed"])
        self.assertIn("Task failed", info["error"])
        self.assertEqual(info["traceback"], "Traceback...")


if __name__ == "__main__":
    unittest.main()
