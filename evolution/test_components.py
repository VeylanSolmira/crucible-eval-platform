#!/usr/bin/env python3
"""
Unified test runner for components and configurations.

Usage:
    # Default: Test everything
    python test_components.py              # Test all components with all engines
    
    # Test individual components:
    python test_components.py execution    # Test all execution engines
    python test_components.py monitoring   # Test monitoring service
    python test_components.py queue        # Test task queue
    python test_components.py platform     # Test platform orchestration
    python test_components.py storage      # Test storage service
    python test_components.py api          # Test API component
    python test_components.py frontend     # Test web frontend
    
    # Test specific engines:
    python test_components.py --docker     # Test with Docker engine only
    python test_components.py --subprocess # Test with subprocess engine only
    python test_components.py --gvisor     # Test with gVisor engine only
"""

import sys
import subprocess
import unittest
from io import StringIO

# Add current directory to path
sys.path.append('.')

from components import (
    SubprocessEngine,
    DockerEngine,
    GVisorEngine,
    InMemoryMonitor,
    TaskQueue,
    TestableEvaluationPlatform,
    InMemoryStorage,
    FileStorage,
    RESTfulAPI,
    create_api,
    WebFrontendService,
    FrontendConfig,
    FrontendType,
    create_frontend
)


def test_component(component_name: str):
    """Test a specific component in isolation"""
    print(f"\n{'='*60}")
    print(f"Testing {component_name.upper()} Component")
    print('='*60)
    
    if component_name == 'execution':
        # Test all available execution engines
        engines_tested = 0
        all_passed = True
        
        # Test subprocess engine (always available)
        print("\n--- SubprocessEngine ---")
        engine = SubprocessEngine()
        result = engine.self_test()
        status = '✅ PASSED' if result['passed'] else '❌ FAILED'
        print(f"Self-test: {status} - {result['message']}")
        all_passed &= result['passed']
        engines_tested += 1
        
        # Test Docker engine if available
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            print("\n--- DockerEngine ---")
            engine = DockerEngine()
            result = engine.self_test()
            status = '✅ PASSED' if result['passed'] else '❌ FAILED'
            print(f"Self-test: {status} - {result['message']}")
            all_passed &= result['passed']
            engines_tested += 1
            
            # Test gVisor if available
            docker_info = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            if 'runsc' in docker_info.stdout:
                print("\n--- GVisorEngine ---")
                engine = GVisorEngine('runsc')
                result = engine.self_test()
                status = '✅ PASSED' if result['passed'] else '❌ FAILED'
                print(f"Self-test: {status} - {result['message']}")
                all_passed &= result['passed']
                engines_tested += 1
            else:
                print("\n--- GVisorEngine ---")
                print("⚠️  gVisor runtime not available")
                
        except:
            print("\n⚠️  Docker not available - skipping Docker/gVisor tests")
        
        print(f"\n✅ Tested {engines_tested} execution engines")
        return all_passed
        
    elif component_name == 'monitoring':
        # Test monitoring service
        monitor = InMemoryMonitor()
        result = monitor.self_test()
        status = '✅ PASSED' if result['passed'] else '❌ FAILED'
        print(f"\nInMemoryMonitor self-test: {status}")
        print(f"Message: {result['message']}")
        
        # Run unit tests
        print("\nRunning monitoring unit tests:")
        suite = monitor.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=1)
        test_result = runner.run(suite)
        
        return result['passed'] and test_result.wasSuccessful()
        
    elif component_name == 'platform':
        # Test platform with a simple engine
        print("\nTesting platform orchestration...")
        engine = SubprocessEngine()
        monitor = InMemoryMonitor()
        platform = TestableEvaluationPlatform(engine, monitor)
        
        result = platform.self_test()
        status = '✅ PASSED' if result['passed'] else '❌ FAILED'
        print(f"Platform self-test: {status}")
        print(f"Message: {result['message']}")
        
        # Test orchestration
        if result['passed']:
            print("\nTesting evaluation orchestration:")
            eval_result = platform.evaluate("print('Platform orchestration works!')")
            print(f"  Evaluation ID generated: {eval_result['id']}")
            print(f"  Execution status: {eval_result['status']}")
            print(f"  Output: {eval_result['output'].strip()}")
            
            # Check monitoring integration
            events = monitor.get_events(eval_result['id'])
            print(f"  Events recorded: {len(events)}")
            for event in events:
                print(f"    - {event['type']}: {event['message']}")
        
        return result['passed']
    
    elif component_name == 'queue':
        # Test task queue
        print("\nTesting task queue...")
        queue = TaskQueue(max_workers=2)  # Use fewer workers for testing
        
        try:
            result = queue.self_test()
            status = '✅ PASSED' if result['passed'] else '❌ FAILED'
            print(f"\nTaskQueue self-test: {status}")
            print(f"Message: {result['message']}")
            
            if result.get('tests_passed'):
                print(f"Passed tests: {', '.join(result['tests_passed'])}")
            if result.get('tests_failed'):
                print(f"Failed tests: {', '.join(result['tests_failed'])}")
            
            # Run unit tests
            print("\nRunning queue unit tests:")
            suite = queue.get_test_suite()
            runner = unittest.TextTestRunner(verbosity=1)
            test_result = runner.run(suite)
            
            # Show queue status
            print("\nQueue status after tests:")
            status = queue.get_status()
            print(f"  Completed tasks: {status['completed']}")
            print(f"  Failed tasks: {status['failed']}")
            print(f"  Queue size: {status['queued']}")
            print(f"  Workers: {status['workers']}")
            
            return result['passed'] and test_result.wasSuccessful()
            
        finally:
            # Always shutdown the queue
            print("\nShutting down queue...")
            queue.shutdown()
    
    elif component_name == 'storage':
        # Test storage services
        all_passed = True
        
        # Test InMemoryStorage
        print("\n--- InMemoryStorage ---")
        storage = InMemoryStorage()
        result = storage.self_test()
        status = '✅ PASSED' if result['passed'] else '❌ FAILED'
        print(f"Self-test: {status} - {result['message']}")
        all_passed &= result['passed']
        
        # Run unit tests
        print("\nRunning InMemoryStorage unit tests:")
        suite = storage.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=1)
        test_result = runner.run(suite)
        all_passed &= test_result.wasSuccessful()
        
        # Test FileStorage
        print("\n--- FileStorage ---")
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStorage(temp_dir)
            result = storage.self_test()
            status = '✅ PASSED' if result['passed'] else '❌ FAILED'
            print(f"Self-test: {status} - {result['message']}")
            all_passed &= result['passed']
            
            # Run unit tests
            print("\nRunning FileStorage unit tests:")
            suite = storage.get_test_suite()
            runner = unittest.TextTestRunner(verbosity=1)
            test_result = runner.run(suite)
            all_passed &= test_result.wasSuccessful()
        
        print(f"\n✅ Tested 2 storage implementations")
        return all_passed
    
    elif component_name == 'api':
        # Test API component
        all_passed = True
        
        # Create a simple platform for testing
        print("\n--- Creating test platform ---")
        engine = SubprocessEngine()
        monitor = InMemoryMonitor()
        platform = TestableEvaluationPlatform(engine, monitor)
        
        # Test RESTfulAPI
        print("\n--- RESTfulAPI ---")
        api = RESTfulAPI(platform)
        result = api.self_test()
        status = '✅ PASSED' if result['passed'] else '❌ FAILED'
        print(f"Self-test: {status} - {result['message']}")
        all_passed &= result['passed']
        
        # Run unit tests
        print("\nRunning RESTfulAPI unit tests:")
        suite = api.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=1)
        test_result = runner.run(suite)
        all_passed &= test_result.wasSuccessful()
        
        # Test create_api factory
        print("\n--- Testing create_api factory ---")
        try:
            api_http = create_api(platform, framework='http.server')
            print("✅ Created http.server API")
        except Exception as e:
            print(f"❌ Failed to create http.server API: {e}")
            all_passed = False
            
        print(f"\n✅ Tested API component")
        return all_passed
    
    elif component_name == 'frontend' or component_name == 'web_frontend':
        # Test web frontend components
        all_passed = True
        
        # Mock platform for frontend testing
        class MockPlatform:
            def handle_evaluation(self, code: str):
                return {'output': f'Mock: {code[:30]}...', 'error': None}
            
            def get_status(self):
                return {
                    'status': 'healthy',
                    'components': {
                        'engine': {'healthy': True, 'component': 'Mock'},
                        'monitor': {'healthy': True, 'component': 'Mock'}
                    }
                }
        
        platform = MockPlatform()
        
        # Test SimpleHTTPFrontend
        print("\n--- SimpleHTTPFrontend ---")
        config = FrontendConfig(features={'suppress_logs': True})
        frontend = create_frontend(FrontendType.SIMPLE_HTTP, config, platform)
        result = frontend.self_test()
        status = '✅ PASSED' if result['passed'] else '❌ FAILED'
        print(f"Self-test: {status} - {result['message']}")
        all_passed &= result['passed']
        
        # Test WebFrontendService directly
        print("\n--- WebFrontendService ---")
        frontend_service = WebFrontendService(
            config=FrontendConfig(title="Test Frontend"),
            ui_type=FrontendType.ADVANCED
        )
        result = frontend_service.self_test()
        status = '✅ PASSED' if result['passed'] else '❌ FAILED'
        print(f"Self-test: {status} - {result['message']}")
        all_passed &= result['passed']
        
        # Show frontend evolution
        print("\n--- Frontend Evolution ---")
        print("  1. SimpleHTTPFrontend: Basic Python server")
        print("  2. FlaskFrontend: Professional framework")
        print("  3. FastAPIFrontend: Modern async + WebSockets")
        print("  4. ReactFrontend: Full microservice SPA")
        
        print(f"\n✅ Tested web frontend component")
        return all_passed
    
    else:
        print(f"❌ Unknown component: {component_name}")
        return False


def test_engine_configuration(engine_name: str, engine_class, *args):
    """Test a full configuration with a specific engine"""
    print(f"\n{'='*60}")
    print(f"Testing {engine_name} Configuration")
    print('='*60)
    
    # Create components
    engine = engine_class(*args)
    monitor = InMemoryMonitor()
    platform = TestableEvaluationPlatform(engine, monitor)
    
    # Show component test results
    print("\nComponent Self-Tests:")
    all_passed = True
    for component, result in platform.test_results.items():
        if component != 'overall':
            status = '✅ PASSED' if result['passed'] else '❌ FAILED'
            print(f"  {component.upper()}: {status} - {result['message']}")
            all_passed &= result['passed']
    
    print(f"\nOVERALL: {platform.test_results['overall']['message']}")
    
    # Run unit test suite
    if all_passed:
        print(f"\nRunning {engine_name} Unit Tests:")
        suite = platform.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)
        
        # Quick execution test
        print(f"\nIntegration Test:")
        eval_result = platform.evaluate(f"print('{engine_name} integration test passed!')")
        print(f"  Output: {eval_result['output'].strip()}")
        print(f"  Status: {eval_result['status']}")
        
        return result.wasSuccessful()
    else:
        print(f"\n⚠️  Skipping unit tests - component tests failed")
        return False


def test_all_configurations():
    """Test all available configurations"""
    configurations_tested = 0
    all_passed = True
    
    # Always test subprocess (unsafe but always available)
    all_passed &= test_engine_configuration("Subprocess (UNSAFE)", SubprocessEngine)
    configurations_tested += 1
    
    # Test Docker if available
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        all_passed &= test_engine_configuration("Docker", DockerEngine)
        configurations_tested += 1
        
        # Test gVisor if available
        docker_info = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        if 'runsc' in docker_info.stdout:
            all_passed &= test_engine_configuration("gVisor", GVisorEngine, 'runsc')
        else:
            all_passed &= test_engine_configuration("Docker (standard runtime)", GVisorEngine, 'runc')
        configurations_tested += 1
        
    except:
        print("\n⚠️  Docker not available - skipping Docker/gVisor configurations")
    
    print(f"\n✅ Tested {configurations_tested} configurations")
    return all_passed


def main():
    """Main test runner"""
    args = sys.argv[1:]
    
    print("🧪 Crucible Platform Test Suite")
    print("================================")
    
    # Default behavior: test everything
    if len(args) == 0:
        print("\nRunning comprehensive test suite...")
        print("(Use 'python test_components.py -h' for options)")
        
        all_passed = True
        
        # Test individual components
        print("\n" + "="*60)
        print("COMPONENT TESTS")
        print("="*60)
        
        for component in ['execution', 'monitoring', 'queue', 'platform', 'storage', 'api', 'frontend']:
            all_passed &= test_component(component)
        
        # Test full configurations
        print("\n" + "="*60)
        print("CONFIGURATION TESTS")
        print("="*60)
        
        all_passed &= test_all_configurations()
        
    # Help
    elif '-h' in args or '--help' in args:
        print(__doc__)
        return 0
        
    # Component testing
    elif args[0] in ['execution', 'monitoring', 'queue', 'platform', 'storage', 'api']:
        all_passed = test_component(args[0])
        
    # Specific engine testing
    elif args[0] == '--docker':
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            all_passed = test_engine_configuration("Docker", DockerEngine)
        except:
            print("❌ Docker not available!")
            return 1
            
    elif args[0] == '--subprocess':
        all_passed = test_engine_configuration("Subprocess (UNSAFE)", SubprocessEngine)
        
    elif args[0] == '--gvisor':
        try:
            docker_info = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            if 'runsc' in docker_info.stdout:
                all_passed = test_engine_configuration("gVisor", GVisorEngine, 'runsc')
            else:
                print("⚠️  gVisor runtime not available, testing with standard runtime")
                all_passed = test_engine_configuration("Docker (standard)", GVisorEngine, 'runc')
        except:
            print("❌ Docker not available!")
            return 1
            
    else:
        print(f"❌ Unknown argument: {args[0]}")
        print("Use 'python test_components.py -h' for help")
        return 1
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())