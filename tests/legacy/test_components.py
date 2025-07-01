#!/usr/bin/env python3
"""
Test runner for Crucible platform components.
Tests each component individually with proper timeouts.
"""

import sys
import signal
from contextlib import contextmanager

# Add project to path
sys.path.insert(0, '.')

@contextmanager
def timeout(seconds):
    """Context manager for timeouts"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def test_component(name, component, timeout_seconds=10):
    """Test a single component with timeout"""
    print(f"\nTesting {name}...")
    
    try:
        with timeout(timeout_seconds):
            if hasattr(component, 'self_test'):
                result = component.self_test()
                status = '✅' if result.get('passed', False) else '❌'
                print(f"{status} {name}: {result.get('message', 'No message')}")
                
                # Show detailed test results if available
                if 'tests' in result:
                    for test in result['tests']:
                        test_status = '  ✓' if test.get('passed', False) else '  ✗'
                        print(f"{test_status} {test.get('name', 'Unknown')}: {test.get('message', '')}")
                elif 'tests_passed' in result or 'tests_failed' in result:
                    # Alternative format used by ExecutionEngine
                    for test in result.get('tests_passed', []):
                        print(f"  ✓ {test}")
                    for test in result.get('tests_failed', []):
                        print(f"  ✗ {test}")
                        
                return result.get('passed', False)
            else:
                print(f"⚠️  {name}: No self_test method")
                return False
                
    except TimeoutError as e:
        print(f"❌ {name}: {e}")
        return False
    except Exception as e:
        print(f"❌ {name}: Error - {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up component if needed
        if hasattr(component, 'shutdown'):
            try:
                component.shutdown()
            except Exception:
                pass
        if hasattr(component, 'stop'):
            try:
                component.stop()
            except Exception:
                pass

def main():
    print("🧪 Crucible Platform Component Test Suite")
    print("=" * 50)
    
    from src.core.components import (
        SubprocessEngine,
        DockerEngine,
        TaskQueue,
        AdvancedMonitor,
        InMemoryStorage,
        FileStorage,
        EventBus,
        create_frontend,
        FrontendConfig,
        FrontendType
    )
    
    # Components to test
    test_configs = [
        ("SubprocessEngine", lambda: SubprocessEngine()),
        ("TaskQueue", lambda: TaskQueue(max_workers=2)),
        ("AdvancedMonitor", lambda: AdvancedMonitor()),
        ("InMemoryStorage", lambda: InMemoryStorage()),
        ("FileStorage", lambda: FileStorage("/tmp/test_storage")),
        ("EventBus", lambda: EventBus()),
        ("SimpleHTTPFrontend", lambda: create_frontend(
            FrontendType.SIMPLE_HTTP, 
            FrontendConfig(port=8089, features={'suppress_logs': True})
        )),
    ]
    
    # Try Docker if available
    try:
        engine = DockerEngine()
        test_configs.insert(1, ("DockerEngine", lambda: engine))
    except Exception as e:
        print(f"ℹ️  Docker not available: {e}")
        print("   Skipping DockerEngine tests")
    
    results = []
    for name, factory in test_configs:
        try:
            component = factory()
            passed = test_component(name, component)
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name}: Failed to create - {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = '✅' if passed else '❌'
        print(f"  {status} {name}")
    
    print(f"\n🎯 Total: {passed_count}/{total_count} passed")
    
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())