"""
Evaluation State Machine
Handles state transitions and enforces valid state changes
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from shared.generated.python import EvaluationStatus
import logging

logger = logging.getLogger(__name__)


class EvaluationStateMachine:
    """
    Manages evaluation state transitions based on defined rules.
    
    This class loads transition rules from a YAML file and provides
    methods to validate and explain state transitions.
    """
    
    def __init__(self, transitions_file: Optional[Path] = None):
        """Initialize the state machine with transition rules."""
        if transitions_file is None:
            # Default to the shared types file
            base_path = Path(__file__).parent.parent
            transitions_file = base_path / "types" / "evaluation-state-transitions.yaml"
        
        self.transitions = self._load_transitions(transitions_file)
        self._validate_transitions()
    
    def _load_transitions(self, file_path: Path) -> Dict[str, List[str]]:
        """Load transition rules from YAML file."""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('transitions', {})
        except Exception as e:
            logger.error(f"Failed to load transitions from {file_path}: {e}")
            # Fallback to minimal safe transitions
            return {
                "submitted": ["queued", "failed", "cancelled"],
                "queued": ["running", "failed", "cancelled"],
                "running": ["completed", "failed", "cancelled"],
                "completed": [],
                "failed": [],
                "cancelled": []
            }
    
    def _validate_transitions(self):
        """Validate that all states in transitions are valid EvaluationStatus values."""
        valid_states = {status.value for status in EvaluationStatus}
        
        for from_state, to_states in self.transitions.items():
            if from_state not in valid_states:
                logger.warning(f"Unknown state in transitions: {from_state}")
            
            for to_state in to_states:
                if to_state not in valid_states:
                    logger.warning(f"Unknown state in transitions: {from_state} -> {to_state}")
    
    def can_transition(self, from_status: str, to_status: str) -> bool:
        """
        Check if a transition from one status to another is allowed.
        
        Args:
            from_status: Current evaluation status
            to_status: Desired new status
            
        Returns:
            True if transition is allowed, False otherwise
        """
        # Same state is always allowed (idempotent)
        if from_status == to_status:
            return True
        
        # Check if transition is in allowed list
        allowed_transitions = self.transitions.get(from_status, [])
        return to_status in allowed_transitions
    
    def validate_transition(self, from_status: str, to_status: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a state transition and provide explanation if invalid.
        
        Args:
            from_status: Current evaluation status
            to_status: Desired new status
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Same state transitions are always valid (idempotent)
        if from_status == to_status:
            return True, None
        
        # Check if from_status is a terminal state
        try:
            from_enum = EvaluationStatus(from_status)
            if from_enum.is_terminal():
                return False, f"Cannot transition from terminal state '{from_status}' to '{to_status}'"
        except ValueError:
            return False, f"Unknown status: {from_status}"
        
        # Check if transition is allowed
        if not self.can_transition(from_status, to_status):
            allowed = self.transitions.get(from_status, [])
            if allowed:
                return False, f"Invalid transition: '{from_status}' -> '{to_status}'. Allowed: {allowed}"
            else:
                return False, f"No transitions allowed from state '{from_status}'"
        
        return True, None
    
    def get_allowed_transitions(self, from_status: str) -> List[str]:
        """Get list of allowed transitions from a given status."""
        return self.transitions.get(from_status, [])
    
    def is_terminal_state(self, status: str) -> bool:
        """Check if a status is terminal (no outgoing transitions)."""
        try:
            status_enum = EvaluationStatus(status)
            return status_enum.is_terminal()
        except ValueError:
            # Unknown status - treat as terminal to be safe
            return True


# Singleton instance for easy import
_state_machine = None

def get_state_machine() -> EvaluationStateMachine:
    """Get the singleton state machine instance."""
    global _state_machine
    if _state_machine is None:
        _state_machine = EvaluationStateMachine()
    return _state_machine