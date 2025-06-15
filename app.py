#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Frontier Events Edition
Clean integration of all TRACE-AI components with Event-Driven Architecture.

This version demonstrates how loose coupling through events makes the system
more maintainable, extensible, and production-ready.

Run with: python extreme_mvp_frontier_events.py [--unsafe] [--fastapi] [--test] [--openapi]
"""

import sys
import time
import argparse
from pathlib import Path

# Import platform classes directly from core to avoid circular import
from src.core.core import QueuedEvaluationPlatform

# Import ALL modular components from components helper
from src.core.components import (
    SubprocessEngine,
    DockerEngine,
    GVisorEngine,
    AdvancedMonitor,
    TaskQueue,
    FileStorage,
    InMemoryStorage,
    create_api_service,
    create_api_handler,
    create_frontend,
    FrontendConfig,
    FrontendType,
    EventBus,
    EventTypes
)

def main():
    """Clean main entry point - just wire components together"""
    
    parser = argparse.ArgumentParser(description='Crucible Frontier')
    parser.add_argument('--unsafe', action='store_true', help='Use subprocess only')
    parser.add_argument('--require-gvisor', action='store_true', help='Require gVisor runtime (fail if unavailable)')
    parser.add_argument('--fastapi', action='store_true', help='Use FastAPI')
    parser.add_argument('--test', action='store_true', help='Run tests only')
    parser.add_argument('--memory-storage', action='store_true', help='Use in-memory storage')
    parser.add_argument('--openapi', action='store_true', help='Enable OpenAPI validation')
    parser.add_argument('--port', type=int, default=8000, help='Port (default: 8000)')
    parser.add_argument('--security-test', action='store_true', help='Run security attack scenarios')
    parser.add_argument('--security-demo', action='store_true', help='Run safe security demos (no attacks)')
    
    args = parser.parse_args()
    
    print("🚀 Crucible Frontier Events - Starting...")
    print("   Event-driven architecture enabled")
    if args.openapi:
        print("   with OpenAPI validation")
    print()
    
    # Select execution engine (gVisor > Docker > subprocess)
    if args.unsafe:
        engine = SubprocessEngine()
        print("⚠️  Using subprocess (--unsafe mode)")
    else:
        import platform
        
        # Check if gVisor is required but unavailable
        if args.require_gvisor and platform.system() != 'Linux':
            print("❌ ERROR: gVisor (runsc) is only available on Linux")
            print("   You are running on:", platform.system())
            print("   Remove --require-gvisor flag or run on Linux")
            sys.exit(1)
        
        # Try to initialize engines based on platform
        if platform.system() == 'Linux' or args.require_gvisor:
            try:
                engine = GVisorEngine()
                print("🛡️  Using gVisor (most secure)")
            except Exception as e:
                if args.require_gvisor:
                    print("❌ ERROR: gVisor required but not available")
                    print("   Reason:", str(e))
                    print("   Install gVisor or remove --require-gvisor flag")
                    sys.exit(1)
                else:
                    # Fall back to Docker
                    try:
                        engine = DockerEngine()
                        print("🐳 Using Docker (secure container isolation)")
                    except Exception as e:
                        print(f"⚠️  Docker not available: {e}")
                        print("   Falling back to subprocess (least secure)")
                        print("   For better security, please install Docker")
                        engine = SubprocessEngine()
        else:
            # macOS, Windows, etc - use Docker as the secure default
            try:
                engine = DockerEngine()
                print("🐳 Using Docker (secure container isolation)")
            except Exception as e:
                print(f"⚠️  Docker not available: {e}")
                print("   Falling back to subprocess (least secure)")
                print("   For better security, please install Docker Desktop")
                engine = SubprocessEngine()
    
    # Create event bus first - it's the backbone
    event_bus = EventBus()
    print("📢 Event bus initialized")
    
    # Create core components
    queue = TaskQueue(max_workers=4)
    monitor = AdvancedMonitor()
    
    # Storage layer
    if args.memory_storage:
        storage = InMemoryStorage()
    else:
        storage_base = Path("./storage")
        storage_dir = storage_base / "frontier"
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage = FileStorage(str(storage_dir))
    
    # Platform (skip tests by default for faster startup)
    platform = QueuedEvaluationPlatform(
        engine=engine,
        queue=queue,
        monitor=monitor,
        run_tests=args.test  # Only run tests if --test flag is passed
    )
    
    # Set up event handlers for loose coupling
    def handle_evaluation_completed(event):
        """Store evaluation results when completed"""
        eval_id = event['data'].get('eval_id')
        result = event['data'].get('result')
        if eval_id and result:
            storage.store(eval_id, result)
            print(f"💾 Stored evaluation {eval_id}")
    
    def handle_security_violation(event):
        """Handle security violations"""
        print(f"🚨 SECURITY ALERT: {event['data']}")
    
    # Subscribe handlers to events
    event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, handle_evaluation_completed)
    event_bus.subscribe(EventTypes.SECURITY_VIOLATION, handle_security_violation)
    
    print("✅ Event handlers configured")
    
    # Frontend configuration
    frontend_config = FrontendConfig(
        port=args.port,
        enable_monitoring=True,
        features={
            'async_execution': True,
            'real_time_updates': True,
            'batch_submission': True,
            'event_streaming': True,
            'security_warnings': True,
            'storage_enabled': True,
            'testing_enabled': True
        }
    )
    
    # Create API service and handler
    api_service = create_api_service(platform)
    api_handler = create_api_handler(api_service)
    
    print("📡 API service configured")
    
    # Create integrated frontend with API handler
    # Use AdvancedHTMLFrontend for full monitoring features
    frontend = create_frontend(
        frontend_type=FrontendType.ADVANCED_HTTP,
        config=frontend_config,
        api_handler=api_handler
    )
    
    # Run security demos if requested (SAFE)
    if args.security_demo:
        print("\n🔒 Running safe security demos...")
        print("   These demos show security concepts without performing attacks")
        try:
            from security_scenarios.safe_demo_scenarios import SAFE_DEMO_SCENARIOS
            from security_scenarios.security_runner import SecurityTestRunner
            
            # Use explicit scenario passing - no monkey patching!
            runner = SecurityTestRunner(
                scenarios=SAFE_DEMO_SCENARIOS,
                include_subprocess=True  # Safe to include subprocess for demos
            )
            runner.run_all_scenarios()
            return 0
        except Exception as e:
            print(f"❌ Security demo failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Run security tests if requested (DANGEROUS!)
    if args.security_test:
        print("\n🔒 Running security attack scenarios...")
        print("⚠️  WARNING: These are real attack scenarios!")
        print("⚠️  Only run in containers or VMs, never with subprocess!")
        
        response = input("\nAre you SURE you want to run attack scenarios? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return 0
            
        try:
            from security_scenarios.attack_scenarios import ATTACK_SCENARIOS
            from security_scenarios.security_runner import SecurityTestRunner
            
            # Explicit scenario passing - clear what we're running
            runner = SecurityTestRunner(
                scenarios=ATTACK_SCENARIOS,
                include_subprocess=False  # Never include subprocess for real attacks
            )
            runner.run_all_scenarios()
            return 0
        except Exception as e:
            print(f"❌ Security test failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Run tests if requested
    if args.test:
        components = [engine, queue, monitor, storage, platform, frontend, event_bus]
        passed = sum(1 for c in components if hasattr(c, 'self_test') and c.self_test()['passed'])
        print(f"Tests: {passed}/{len(components)} passed")
        
        # Show event history from tests
        print("\nEvent History from Tests:")
        for event in event_bus.get_history(limit=5):
            print(f"  {event['type']}: {event['data']}")
        
        return 0 if passed == len(components) else 1
    
    # Start integrated server
    print(f"\n🚀 Integrated server starting on http://localhost:{args.port}")
    print("   - Frontend routes: /, /assets/*")
    print("   - API routes: /api/*")
    print("📊 Event history available at: /events")
    
    try:
        # Start the integrated server
        frontend.start()
        
        print("\n✅ Server running. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nShutting down...")
        frontend.stop()

if __name__ == "__main__":
    sys.exit(main())