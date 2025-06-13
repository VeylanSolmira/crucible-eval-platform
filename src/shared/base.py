"""
Base testable component for TRACE-AI architecture.
This can evolve into a full framework for testable distributed systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import unittest


class TestableComponent(ABC):
    """
    Base class for all components that must be testable.
    This emerged from realizing that untested evaluation platforms are dangerous!
    
    Future evolution:
    - Add distributed testing capabilities
    - Add performance benchmarking
    - Add chaos testing hooks
    - Add formal verification interfaces
    """
    
    @abstractmethod
    def self_test(self) -> Dict[str, Any]:
        """
        Every component must be able to test itself.
        Returns: {'passed': bool, 'tests_passed': [...], 'tests_failed': [...], 'message': str}
        """
        pass
    
    @abstractmethod
    def get_test_suite(self) -> unittest.TestSuite:
        """Return a unittest suite for this component"""
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """
        Basic health check that can be extended.
        Future: This could integrate with Kubernetes health probes.
        """
        return {
            'healthy': True,
            'component': self.__class__.__name__,
            'version': getattr(self, 'version', '1.0.0')
        }