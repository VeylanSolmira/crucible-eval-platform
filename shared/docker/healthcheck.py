#!/usr/bin/env python3
"""
Common health check script for Crucible services.
Checks if the service responds to /health endpoint.
"""

import sys
import os

# Try using urllib instead of httpx which might not be installed everywhere
try:
    import urllib.request
    import urllib.error
    
    def check_health():
        health_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8080/health")
        timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT", "3"))
        
        try:
            with urllib.request.urlopen(health_url, timeout=timeout) as response:
                if response.status == 200:
                    return True
            return False
        except Exception:
            return False
            
except ImportError:
    # Fall back to httpx if available
    try:
        import httpx
        
        def check_health():
            health_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8080/health")
            timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT", "3"))
            
            try:
                response = httpx.get(health_url, timeout=timeout)
                return response.status_code == 200
            except Exception:
                return False
    except ImportError:
        # No HTTP library available
        print("No HTTP library available for health check", file=sys.stderr)
        sys.exit(1)


def main():
    """Check service health via HTTP endpoint."""
    if check_health():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
