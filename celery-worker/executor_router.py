"""
Executor routing logic for Celery workers.
Mirrors the queue-worker's approach for consistency.
"""

import os
import random
import httpx
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ExecutorRouter:
    """Routes tasks to healthy executor services"""

    def __init__(self):
        self.executor_urls = self._discover_executors()
        self.client = httpx.Client(timeout=2.0)
        logger.info(f"Initialized router with {len(self.executor_urls)} executors")

    def _discover_executors(self) -> List[str]:
        """Discover available executor services"""
        executor_count = int(os.environ.get("EXECUTOR_COUNT", "2"))
        base_url = os.environ.get("EXECUTOR_BASE_URL", "http://executor")
        start_index = int(os.environ.get("EXECUTOR_START_INDEX", "1"))

        executors = []
        for i in range(start_index, start_index + executor_count):
            url = f"{base_url}-{i}:8083"
            executors.append(url)

        logger.info(f"Discovered executors: {executors}")
        return executors

    def check_health(self, executor_url: str) -> bool:
        """Check if an executor is healthy"""
        try:
            response = self.client.get(f"{executor_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed for {executor_url}: {e}")
            return False

    def check_capacity(self, executor_url: str) -> bool:
        """Check if an executor can accept new tasks"""
        try:
            response = self.client.get(f"{executor_url}/capacity")
            if response.status_code == 200:
                data = response.json()
                return data.get("can_accept", False)
            return False
        except Exception as e:
            logger.debug(f"Capacity check failed for {executor_url}: {e}")
            return False

    def get_available_executor(self) -> Optional[str]:
        """Get an executor that is both healthy and has capacity"""
        # Shuffle for load distribution
        executors = list(self.executor_urls)
        random.shuffle(executors)

        for executor_url in executors:
            if self.check_health(executor_url) and self.check_capacity(executor_url):
                logger.debug(f"Selected available executor: {executor_url}")
                return executor_url

        logger.debug("No executors with available capacity")
        return None

    def get_healthy_executor(self) -> Optional[str]:
        """Get a healthy executor using randomized selection"""
        # Shuffle for load distribution
        executors = list(self.executor_urls)
        random.shuffle(executors)

        for executor_url in executors:
            if self.check_health(executor_url):
                logger.debug(f"Selected healthy executor: {executor_url}")
                return executor_url

        logger.error("No healthy executors available!")
        return None

    def __del__(self):
        """Cleanup HTTP client"""
        if hasattr(self, "client"):
            self.client.close()


# Global router instance
router = ExecutorRouter()


def get_executor_url() -> str:
    """Get URL of a healthy executor service"""
    url = router.get_healthy_executor()
    if not url:
        raise RuntimeError("No healthy executor services available")
    return url


def get_available_executor_url() -> Optional[str]:
    """Get URL of an executor with available capacity"""
    return router.get_available_executor()
