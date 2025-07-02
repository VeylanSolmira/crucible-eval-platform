#!/usr/bin/env python3
"""
Comprehensive network isolation tests for execution environments.
Tests that actually try to make network connections, not just import modules.
"""

import socket
import urllib.request
import subprocess
import sys


def test_network_access():
    """Test various network access methods"""

    results = []

    # Test 1: Raw socket connection
    print("1. Testing raw socket connection...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        # Try to connect to Google DNS
        sock.connect(("8.8.8.8", 53))
        sock.close()
        results.append("❌ FAIL: Raw socket connection succeeded")
    except Exception as e:
        results.append(f"✅ PASS: Raw socket blocked - {type(e).__name__}")

    # Test 2: HTTP request with urllib
    print("2. Testing HTTP with urllib...")
    try:
        response = urllib.request.urlopen("http://example.com", timeout=2)
        results.append(f"❌ FAIL: HTTP request succeeded - {response.status}")
    except Exception as e:
        results.append(f"✅ PASS: HTTP blocked - {type(e).__name__}")

    # Test 3: DNS resolution
    print("3. Testing DNS resolution...")
    try:
        ip = socket.gethostbyname("google.com")
        results.append(f"❌ FAIL: DNS resolution succeeded - {ip}")
    except Exception as e:
        results.append(f"✅ PASS: DNS blocked - {type(e).__name__}")

    # Test 4: Ping (if available)
    print("4. Testing ping command...")
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", "8.8.8.8"], capture_output=True, timeout=2
        )
        if result.returncode == 0:
            results.append("❌ FAIL: Ping succeeded")
        else:
            results.append("✅ PASS: Ping failed")
    except FileNotFoundError:
        results.append("✓ SKIP: Ping command not available")
    except Exception as e:
        results.append(f"✅ PASS: Ping blocked - {type(e).__name__}")

    # Test 5: Try localhost connection (should also fail with --network none)
    print("5. Testing localhost connection...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(("127.0.0.1", 80))
        sock.close()
        results.append("❌ FAIL: Localhost connection succeeded")
    except Exception as e:
        results.append(f"✅ PASS: Localhost blocked - {type(e).__name__}")

    # Test 6: Check network interfaces
    print("6. Checking network interfaces...")
    try:
        result = subprocess.run(["ip", "addr"], capture_output=True, text=True)
        if result.returncode == 0:
            # With --network none, should only have loopback
            if "eth0" in result.stdout or "ens" in result.stdout:
                results.append("❌ FAIL: Network interfaces found")
            else:
                results.append("✅ PASS: Only loopback interface")
    except (FileNotFoundError, OSError):
        results.append("✓ SKIP: ip command not available")

    # Test 7: Try to create a listening socket
    print("7. Testing socket binding...")
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("0.0.0.0", 9999))
        server.listen(1)
        server.close()
        results.append("⚠️  WARN: Can bind sockets (expected with --network none)")
    except Exception as e:
        results.append(f"✅ PASS: Socket binding failed - {type(e).__name__}")

    return results


def test_with_requests_library():
    """Test using requests library if available"""
    try:
        import requests

        print("\n8. Testing with requests library...")

        tests = []

        # Test actual HTTP request
        try:
            response = requests.get("http://httpbin.org/get", timeout=2)
            tests.append(f"❌ FAIL: Requests succeeded - {response.status_code}")
        except Exception as e:
            tests.append(f"✅ PASS: Requests blocked - {type(e).__name__}")

        # Test HTTPS
        try:
            response = requests.get("https://api.github.com", timeout=2)
            tests.append(f"❌ FAIL: HTTPS succeeded - {response.status_code}")
        except Exception as e:
            tests.append(f"✅ PASS: HTTPS blocked - {type(e).__name__}")

        return tests
    except ImportError:
        return ["✓ SKIP: requests library not installed"]


def main():
    print("=" * 60)
    print("Network Isolation Test Suite")
    print("=" * 60)
    print()

    # Run basic tests
    results = test_network_access()

    # Run requests tests
    results.extend(test_with_requests_library())

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for result in results:
        print(result)
        if "PASS" in result:
            passed += 1
        elif "FAIL" in result:
            failed += 1
        elif "SKIP" in result:
            skipped += 1

    print("\n" + "-" * 60)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print("-" * 60)

    if failed > 0:
        print("\n⚠️  WARNING: Network isolation is not working properly!")
        print("Submitted code can access the network!")
        return 1
    else:
        print("\n✅ SUCCESS: Network is properly isolated!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
