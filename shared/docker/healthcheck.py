#!/usr/bin/env python3
"""
Common health check script for Crucible services.
Checks if the service responds to /health endpoint.
"""

import sys
import os
import httpx


def main():
    """Check service health via HTTP endpoint."""
    # Allow override of health check URL via environment
    health_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8080/health")
    timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT", "3"))

    try:
        response = httpx.get(health_url, timeout=timeout)
        if response.status_code == 200:
            sys.exit(0)
        else:
            print(f"Health check failed: HTTP {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
