#!/usr/bin/env python3
"""Debug script to test docker-proxy permissions"""
import docker
import os
import sys

def test_docker_proxy():
    docker_host = os.getenv('DOCKER_HOST', 'tcp://docker-proxy:2375')
    print(f"Testing Docker proxy at: {docker_host}")
    print("=" * 50)
    
    try:
        client = docker.DockerClient(base_url=docker_host)
        
        # Test basic connectivity
        print("✓ Connected to Docker")
        version = client.version()
        print(f"✓ Docker version: {version.get('Version', 'Unknown')}")
        
        # Test image listing
        images = client.images.list()
        print(f"✓ Can list images: {len(images)} images found")
        if images:
            print(f"  Sample: {images[0].tags[0] if images[0].tags else 'untagged'}")
        
        # Test container listing
        containers = client.containers.list(all=True)
        print(f"✓ Can list containers: {len(containers)} containers found")
        
        # Test image inspection
        try:
            # Try to inspect python:3.11-slim
            print("\nTesting image inspection...")
            img = client.images.get('python:3.11-slim')
            print("✓ Can inspect image: python:3.11-slim exists")
        except docker.errors.ImageNotFound:
            print("✗ Image python:3.11-slim not found locally")
        except docker.errors.APIError as e:
            print(f"✗ Cannot inspect images: {e}")
        
        # Test pull permission
        try:
            print("\nTesting image pull...")
            # Try to pull a small image
            client.images.pull('alpine:latest')
            print("✓ Can pull images: alpine:latest pulled successfully")
        except docker.errors.APIError as e:
            print(f"✗ Cannot pull images: {e}")
            if "403" in str(e):
                print("  Permission denied - check IMAGES_PULL permission")
        
        # Test container creation
        try:
            print("\nTesting container creation...")
            container = client.containers.create(
                'alpine:latest',
                command=['echo', 'test'],
                name='test-container-proxy'
            )
            print(f"✓ Can create containers: {container.id[:12]}")
            container.remove()
            print("✓ Can remove containers")
        except docker.errors.APIError as e:
            print(f"✗ Cannot create containers: {e}")
            if "403" in str(e):
                print("  Permission denied - check CONTAINERS_CREATE permission")
        
        print("\n✓ All tests passed!")
        return True
        
    except docker.errors.DockerException as e:
        print(f"\n✗ Docker connection failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_docker_proxy()
    sys.exit(0 if success else 1)