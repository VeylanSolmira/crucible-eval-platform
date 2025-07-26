#!/usr/bin/env python3
"""
Unit tests for dispatcher service.
Tests job creation, status checking, and log retrieval.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from kubernetes.client import V1Job, V1ObjectMeta, V1JobStatus, V1JobCondition
from kubernetes.client.rest import ApiException
from datetime import datetime

# Import dispatcher components
from dispatcher_service import ExecuteRequest, ExecuteResponse


@pytest.mark.whitebox
@pytest.mark.unit
class TestDispatcherService:
    """Test dispatcher service functionality."""
    
    @pytest.fixture
    def mock_k8s_batch(self):
        """Mock Kubernetes batch API."""
        with patch('dispatcher_service.app.batch_v1') as mock:
            yield mock
    
    @pytest.fixture
    def mock_k8s_core(self):
        """Mock Kubernetes core API."""
        with patch('dispatcher_service.app.core_v1') as mock:
            yield mock
    
    @patch('dispatcher_service.app.check_gvisor_availability')
    @patch('dispatcher_service.app.core_v1')
    def test_execute_creates_job(self, mock_k8s_core, mock_gvisor_check, mock_k8s_batch):
        """Test that execute creates a Kubernetes job."""
        from dispatcher_service.app import execute
        from kubernetes.client import V1Node, V1NodeStatus, V1ContainerImage
        
        # Mock gVisor check to avoid permission errors
        mock_gvisor_check.return_value = False
        
        # Mock ResourceQuota to return 404 (not found)
        from kubernetes.client.rest import ApiException
        from kubernetes.client import V1ConfigMap
        mock_k8s_core.read_namespaced_resource_quota.side_effect = ApiException(status=404)
        
        # Mock ConfigMap for executor images
        mock_config_map = V1ConfigMap(
            data={"images.yaml": """images:
  - name: "executor-ml"
    image: "executor-ml"
    default: true
"""}
        )
        mock_k8s_core.read_namespaced_config_map.return_value = mock_config_map
        
        # Mock node images to simulate development environment
        mock_node = V1Node(
            status=V1NodeStatus(
                images=[
                    V1ContainerImage(
                        names=[
                            "crucible-platform/executor-ml:6fffbe9ad576",
                            "docker.io/crucible-platform/executor-ml:6fffbe9ad576"
                        ]
                    ),
                    V1ContainerImage(
                        names=[
                            "crucible-platform/executor-base:abc123def456",
                            "docker.io/crucible-platform/executor-base:abc123def456"
                        ]
                    )
                ]
            )
        )
        mock_k8s_core.list_node.return_value.items = [mock_node]
        
        # Prepare request
        request = ExecuteRequest(
            eval_id="test_eval_123",
            code='print("Hello, World!")',
            language="python",
            timeout=60,
            memory_limit="256Mi",
            cpu_limit="0.5"
        )
        
        # Mock the create_namespaced_job response
        mock_k8s_batch.create_namespaced_job.return_value = V1Job(
            metadata=V1ObjectMeta(name="test-eval-123-abc123")
        )
        
        # Execute
        import asyncio
        response = asyncio.run(execute(request))
        
        # Assertions
        assert isinstance(response, ExecuteResponse)
        assert response.eval_id == "test_eval_123"
        assert response.status == "created"
        assert response.job_name.startswith("test-eval-123-")
        
        # Verify Kubernetes API was called
        mock_k8s_batch.create_namespaced_job.assert_called_once()
        call_args = mock_k8s_batch.create_namespaced_job.call_args
        assert call_args[1]['namespace'] == 'crucible'
        
        # Verify job spec
        job = call_args[1]['body']
        # Check that the image is correct (no registry prefix in test environment)
        image = job.spec.template.spec.containers[0].image
        assert image == "executor-ml:latest"
        assert job.spec.template.spec.containers[0].command == ["timeout_wrapper.sh", str(request.timeout), "python", "-u", "-c", request.code]
        assert job.spec.template.spec.containers[0].resources.limits['memory'] == "256Mi"
        assert job.spec.template.spec.containers[0].resources.limits['cpu'] == "0.5"
    
    @patch('dispatcher_service.app.core_v1')
    def test_execute_handles_k8s_error(self, mock_k8s_core, mock_k8s_batch):
        """Test that execute handles Kubernetes API errors."""
        from dispatcher_service.app import execute
        from kubernetes.client.rest import ApiException
        
        # Mock ResourceQuota to return 404 (not found)
        mock_k8s_core.read_namespaced_resource_quota.side_effect = ApiException(status=404)
        
        # Mock ConfigMap for executor images
        from kubernetes.client import V1ConfigMap
        mock_config_map = V1ConfigMap(
            data={"images.yaml": """images:
  - name: "executor-ml"
    image: "executor-ml"
    default: true
"""}
        )
        mock_k8s_core.read_namespaced_config_map.return_value = mock_config_map
        
        request = ExecuteRequest(
            eval_id="test_eval_error",
            code='print("test")',
            language="python"
        )
        
        # Mock API error
        mock_k8s_batch.create_namespaced_job.side_effect = ApiException(
            status=403,
            reason="Forbidden"
        )
        
        # Execute should raise HTTPException
        import asyncio
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(execute(request))
        
        assert exc_info.value.status_code == 403  # Returns K8s error code as-is
        assert "Kubernetes API error" in str(exc_info.value.detail)
    
    def test_get_job_status_running(self, mock_k8s_batch):
        """Test getting status of a running job."""
        from dispatcher_service.app import get_job_status
        
        # Mock job with running status
        mock_job = V1Job(
            metadata=V1ObjectMeta(
                name="test-job",
                labels={"eval-id": "test-eval-123"}
            ),
            status=V1JobStatus(
                active=1,
                succeeded=None,
                failed=None,
                conditions=[]
            )
        )
        mock_k8s_batch.read_namespaced_job_status.return_value = mock_job
        
        # Get status
        import asyncio
        status = asyncio.run(get_job_status("test-job"))
        
        assert status["job_name"] == "test-job"
        assert status["status"] == "running"
    
    def test_get_job_status_completed(self, mock_k8s_batch):
        """Test getting status of a completed job."""
        from dispatcher_service.app import get_job_status
        
        # Mock completed job
        mock_job = V1Job(
            metadata=V1ObjectMeta(
                name="test-job",
                labels={"eval-id": "test-eval-123"}
            ),
            status=V1JobStatus(
                active=0,
                succeeded=1,
                failed=None,
                conditions=[
                    V1JobCondition(
                        type="Complete",
                        status="True",
                        last_probe_time=datetime.now(),
                        last_transition_time=datetime.now()
                    )
                ]
            )
        )
        mock_k8s_batch.read_namespaced_job_status.return_value = mock_job
        
        # Get status
        import asyncio
        status = asyncio.run(get_job_status("test-job"))
        
        assert status["status"] == "succeeded"  # Note: dispatcher returns "succeeded" not "completed"
    
    def test_get_job_status_failed(self, mock_k8s_batch):
        """Test getting status of a failed job."""
        from dispatcher_service.app import get_job_status
        
        # Mock failed job
        mock_job = V1Job(
            metadata=V1ObjectMeta(
                name="test-job",
                labels={"eval-id": "test-eval-123"}
            ),
            status=V1JobStatus(
                active=0,
                succeeded=None,
                failed=1,
                conditions=[
                    V1JobCondition(
                        type="Failed",
                        status="True",
                        reason="BackoffLimitExceeded",
                        last_probe_time=datetime.now(),
                        last_transition_time=datetime.now()
                    )
                ]
            )
        )
        mock_k8s_batch.read_namespaced_job_status.return_value = mock_job
        
        # Get status
        import asyncio
        status = asyncio.run(get_job_status("test-job"))
        
        assert status["status"] == "failed"
    
    def test_get_job_status_not_found(self, mock_k8s_batch):
        """Test getting status of non-existent job."""
        from dispatcher_service.app import get_job_status
        
        # Mock 404 error
        mock_k8s_batch.read_namespaced_job_status.side_effect = ApiException(
            status=404,
            reason="Not Found"
        )
        
        # Execute should raise HTTPException
        import asyncio
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_job_status("non-existent-job"))
        
        assert exc_info.value.status_code == 404
    
    def test_get_job_logs_success(self, mock_k8s_core, mock_k8s_batch):
        """Test getting logs from a successful job."""
        from dispatcher_service.app import get_job_logs
        
        # Mock pod list
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-job-pod"
        mock_pod.metadata.labels = {"job-name": "test-job"}
        
        mock_pod_list = MagicMock()
        mock_pod_list.items = [mock_pod]
        mock_k8s_core.list_namespaced_pod.return_value = mock_pod_list
        
        # Mock logs
        test_logs = '{"status": "success", "output": "Hello, World!"}'
        mock_k8s_core.read_namespaced_pod_log.return_value = test_logs
        
        # Get logs
        import asyncio
        result = asyncio.run(get_job_logs("test-job"))
        
        assert result["job_name"] == "test-job"
        assert result["pod_name"] == "test-job-pod"
        assert result["logs"] == test_logs
        
        # Verify API calls
        mock_k8s_core.list_namespaced_pod.assert_called_once_with(
            namespace="crucible",
            label_selector="job-name=test-job"
        )
        mock_k8s_core.read_namespaced_pod_log.assert_called_once()
    
    @patch('dispatcher_service.app.get_logs_from_loki')
    def test_get_job_logs_no_pods(self, mock_loki, mock_k8s_core, mock_k8s_batch):
        """Test getting logs when no pods exist."""
        from dispatcher_service.app import get_job_logs_internal
        
        # Mock empty pod list
        mock_pod_list = MagicMock()
        mock_pod_list.items = []
        mock_k8s_core.list_namespaced_pod.return_value = mock_pod_list
        
        # Mock Loki returning no logs
        mock_loki.return_value = None
        
        # Get logs
        import asyncio
        result = asyncio.run(get_job_logs_internal("test-job"))
        
        assert result["logs"] == ""
        assert result["exit_code"] == 1
        assert result["message"] == "No pods found for job and no logs in Loki"
    
    @patch('dispatcher_service.app.core_v1')
    def test_eval_id_sanitization(self, mock_k8s_core):
        """Test that eval IDs are properly sanitized for K8s names."""
        from dispatcher_service.app import execute
        from kubernetes.client.rest import ApiException
        
        # Mock ResourceQuota to return 404 (not found)
        mock_k8s_core.read_namespaced_resource_quota.side_effect = ApiException(status=404)
        
        # Mock ConfigMap for executor images
        from kubernetes.client import V1ConfigMap
        mock_config_map = V1ConfigMap(
            data={"images.yaml": """images:
  - name: "executor-ml"
    image: "executor-ml"
    default: true
"""}
        )
        mock_k8s_core.read_namespaced_config_map.return_value = mock_config_map
        
        with patch('dispatcher_service.app.batch_v1') as mock_batch:
            mock_batch.create_namespaced_job.return_value = V1Job(
                metadata=V1ObjectMeta(name="eval-test-under-score-abc")
            )
            
            # Test with underscores (should be replaced with hyphens)
            request = ExecuteRequest(
                eval_id="test_under_score_id",
                code='print("test")',
                language="python"
            )
            
            import asyncio
            response = asyncio.run(execute(request))
            
            # Verify job name has hyphens instead of underscores
            # Job name format is "{eval_id_safe}-{uuid}"
            assert response.job_name.startswith("test-under-score-")
    
    @patch('dispatcher_service.app.core_v1')
    def test_timeout_configuration(self, mock_k8s_core, mock_k8s_batch):
        """Test that timeout is properly configured in job spec."""
        from dispatcher_service.app import execute
        from kubernetes.client.rest import ApiException
        
        # Mock ResourceQuota to return 404 (not found)
        mock_k8s_core.read_namespaced_resource_quota.side_effect = ApiException(status=404)
        
        # Mock ConfigMap for executor images
        from kubernetes.client import V1ConfigMap
        mock_config_map = V1ConfigMap(
            data={"images.yaml": """images:
  - name: "executor-ml"
    image: "executor-ml"
    default: true
"""}
        )
        mock_k8s_core.read_namespaced_config_map.return_value = mock_config_map
        
        request = ExecuteRequest(
            eval_id="test_timeout",
            code='import time; time.sleep(100)',
            language="python",
            timeout=30  # 30 second timeout
        )
        
        mock_k8s_batch.create_namespaced_job.return_value = V1Job(
            metadata=V1ObjectMeta(name="eval-test-timeout-abc")
        )
        
        import asyncio
        asyncio.run(execute(request))
        
        # Check job spec
        call_args = mock_k8s_batch.create_namespaced_job.call_args
        job = call_args[1]['body']
        
        # Verify timeout settings (now includes 5 minute buffer)
        assert job.spec.active_deadline_seconds == 330  # 30 + 300 buffer
        assert job.spec.backoff_limit == 0  # No retries for user code