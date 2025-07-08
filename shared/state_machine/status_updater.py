"""
Shared status update utilities with state machine validation
Used by multiple services to ensure consistent state transitions
"""

from typing import Dict, Any, Optional, Tuple, Protocol
from datetime import datetime, timezone
import logging
from shared.generated.python import EvaluationStatus
from .evaluation_state_machine import get_state_machine

logger = logging.getLogger(__name__)


class HTTPClient(Protocol):
    """Protocol for HTTP clients - works with httpx, aiohttp, etc."""
    async def get(self, url: str) -> Any:
        """Make GET request."""
        ...
    
    async def put(self, url: str, json: Dict[str, Any]) -> Any:
        """Make PUT request with JSON body."""
        ...


async def validate_and_update_status(
    http_client: HTTPClient,
    storage_url: str,
    eval_id: str, 
    new_status: str,
    update_data: Optional[Dict[str, Any]] = None,
    force: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Shared implementation of the validate-and-update pattern.
    
    This function:
    1. Fetches current evaluation status from storage service
    2. Validates the state transition using the state machine
    3. Updates the status if valid
    
    Args:
        http_client: HTTP client instance (must have get/put methods)
        storage_url: Base URL of storage service
        eval_id: Evaluation ID to update
        new_status: Desired new status
        update_data: Additional fields to update
        force: Skip state validation (use sparingly!)
        
    Returns:
        Tuple of (success, error_message)
        
    Example:
        success, error = await validate_and_update_status(
            self.client,
            "http://storage-service:8082",
            "eval-123",
            "running",
            {"executor_id": "exec-1"}
        )
    """
    state_machine = get_state_machine()
    storage_url = storage_url.rstrip('/')
    
    try:
        # Get current evaluation state
        response = await http_client.get(f"{storage_url}/evaluations/{eval_id}")
        
        if response.status_code == 404:
            return False, f"Evaluation {eval_id} not found"
        
        if response.status_code != 200:
            return False, f"Failed to get evaluation: HTTP {response.status_code}"
        
        current_data = response.json()
        current_status = current_data.get("status", "unknown")
        
        # Skip validation if forced
        if not force:
            # Validate transition
            is_valid, error_msg = state_machine.validate_transition(current_status, new_status)
            
            if not is_valid:
                logger.info(f"State transition rejected for {eval_id}: {error_msg}")
                return False, error_msg
        
        # Prepare update payload
        update_payload = {"status": new_status}
        
        # Add timestamp fields based on transition
        now = datetime.now(timezone.utc).isoformat()
        
        if new_status == EvaluationStatus.RUNNING.value:
            if current_status in [EvaluationStatus.SUBMITTED.value, EvaluationStatus.QUEUED.value, EvaluationStatus.PROVISIONING.value]:
                update_payload["started_at"] = now
        
        elif new_status in [EvaluationStatus.COMPLETED.value, EvaluationStatus.FAILED.value, EvaluationStatus.CANCELLED.value]:
            update_payload["completed_at"] = now
            
            # Calculate runtime if we have started_at
            if current_data.get("started_at"):
                started = datetime.fromisoformat(current_data["started_at"].replace("Z", "+00:00"))
                completed = datetime.fromisoformat(now)
                runtime_ms = int((completed - started).total_seconds() * 1000)
                update_payload["runtime_ms"] = runtime_ms
        
        # Merge additional data
        if update_data:
            update_payload.update(update_data)
        
        # Update evaluation
        update_response = await http_client.put(
            f"{storage_url}/evaluations/{eval_id}",
            json=update_payload
        )
        
        if update_response.status_code != 200:
            return False, f"Failed to update evaluation: HTTP {update_response.status_code}"
        
        logger.info(f"Successfully updated evaluation {eval_id} from {current_status} to {new_status}")
        return True, None
        
    except Exception as e:
        error_msg = f"Error updating {eval_id}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def get_valid_transitions(current_status: str) -> list[str]:
    """Get list of valid transitions from current status."""
    state_machine = get_state_machine()
    return state_machine.get_allowed_transitions(current_status)


def is_terminal_status(status: str) -> bool:
    """Check if a status is terminal."""
    state_machine = get_state_machine()
    return state_machine.is_terminal_state(status)