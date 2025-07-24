"""
Example of how to integrate resource cleanup into test suites.

This can be added to conftest.py or imported as needed.
"""

import pytest
import os
from tests.utils.resource_manager import resource_manager, with_resource_cleanup

# Make the resource_manager fixture available to all tests
pytest.fixture(resource_manager)


# Example: Auto-cleanup for specific test classes
@pytest.mark.usefixtures("resource_manager")
class TestWithAutoCleanup:
    """All tests in this class get automatic resource cleanup."""
    pass


# Example: Conditional cleanup based on markers
@pytest.fixture(autouse=True)
def conditional_cleanup(request, resource_manager):
    """Apply different cleanup strategies based on test markers."""
    
    # Heavy tests get full cleanup
    if request.node.get_closest_marker("heavy"):
        resource_manager.cleanup_level = "all"
    # Load tests preserve everything for analysis  
    elif request.node.get_closest_marker("load"):
        resource_manager.cleanup_level = "none"
    # Default: just clean pods
    else:
        resource_manager.cleanup_level = "pods"


# Example usage in tests:
"""
@pytest.mark.heavy
def test_concurrent_evaluations(api_session, resource_manager):
    # This test will get full cleanup (pods + jobs)
    
    # Track specific resources if needed
    for eval_id in submitted_evaluations:
        resource_manager.track_resource("jobs", f"job-{eval_id}")
    
    # Test code here...


@with_resource_cleanup(cleanup_level="pods", wait_after=5)
def test_with_decorator():
    # This test will have pods cleaned up after completion
    pass


def test_with_context_manager():
    with managed_test_resources("my_test", cleanup_level="all"):
        # Resources cleaned up when context exits
        pass
"""