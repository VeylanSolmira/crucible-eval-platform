"""
Base storage interface for all storage backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import unittest


class StorageService(ABC):
    """
    Abstract storage service interface.

    All storage backends (database, file, memory, S3, etc.) must implement this interface.
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

    def get_test_suite(self) -> unittest.TestSuite:
        """Get test suite for this storage implementation"""
        return unittest.TestSuite()
