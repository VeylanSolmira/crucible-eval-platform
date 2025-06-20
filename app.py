#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Frontier Events Edition
Clean integration of all TRACE-AI components with Event-Driven Architecture.

This version demonstrates how loose coupling through events makes the system
more maintainable, extensible, and production-ready.

Run with: python extreme_mvp_frontier_events.py [--unsafe] [--fastapi] [--test] [--openapi]
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Import platform classes directly from core to avoid circular import
from src.core.core import QueuedEvaluationPlatform

# Import ALL modular components from components helper
from src.core.components import (
    DockerEngine,
    GVisorEngine,
    DisabledEngine,
    AdvancedMonitor,
    TaskQueue,
    create_api_service,
    create_api_handler,
    EventBus,
    EventTypes
)

# Import new storage system
from storage import FlexibleStorageManager
from storage.config import StorageConfig

def main():
    """Clean main entry point - just wire components together"""
    
    parser = argparse.ArgumentParser(description='Crucible Frontier')
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
    
    # Try to set up execution engine, but don't fail if unavailable
    import platform
    engine = None
    execution_available = False
    execution_error = None
    
    print("🔍 Checking execution engine availability...")
    
    # Check if gVisor is required but unavailable
    if args.require_gvisor and platform.system() != 'Linux':
        execution_error = "gVisor (runsc) is only available on Linux"
        print(f"❌ ERROR: {execution_error}")
        print("   You are running on:", platform.system())
    else:
        # Try to initialize engines based on platform
        if platform.system() == 'Linux' or args.require_gvisor:
            try:
                engine = GVisorEngine()
                print("🛡️  Using gVisor (most secure)")
                execution_available = True
            except Exception as e:
                if args.require_gvisor:
                    execution_error = f"gVisor required but not available: {e}"
                    print(f"❌ ERROR: {execution_error}")
                else:
                    # Fall back to Docker
                    try:
                        engine = DockerEngine()
                        print("🐳 Using Docker (secure container isolation)")
                        execution_available = True
                    except Exception as e:
                        execution_error = f"Docker not available: {e}"
                        print(f"⚠️  WARNING: {execution_error}")
        else:
            # macOS, Windows, etc - use Docker as the secure default
            try:
                engine = DockerEngine()
                print("🐳 Using Docker (secure container isolation)")
                execution_available = True
            except Exception as e:
                execution_error = f"Docker not available: {e}"
                print(f"⚠️  WARNING: {execution_error}")
    
    if not execution_available:
        print("   ⚠️  Code execution is disabled - web interface will still work")
        print("   ⚠️  To enable code execution, ensure Docker is accessible")
        
        # Use the DisabledEngine when no secure execution is available
        engine = DisabledEngine(execution_error or "No execution engine available")
    
    # Create event bus first - it's the backbone
    event_bus = EventBus()
    print("📢 Event bus initialized")
    
    # Create core components
    queue = TaskQueue(max_workers=4)
    monitor = AdvancedMonitor()
    
    # Configure storage based on arguments and environment
    if args.memory_storage:
        storage_config = StorageConfig.for_testing(use_memory=True)
        print("💾 Using in-memory storage")
    else:
        storage_config = StorageConfig.from_environment()
        
        # Ensure file storage directory exists
        if storage_config.file_storage_path:
            Path(storage_config.file_storage_path).mkdir(parents=True, exist_ok=True)
        
        if storage_config.database_url:
            print("💾 Using database storage with file fallback")
        else:
            print("💾 Using file storage")
    
    # Create flexible storage manager
    storage = FlexibleStorageManager.from_config(storage_config)
    
    # Platform (skip tests by default for faster startup)
    platform = QueuedEvaluationPlatform(
        engine=engine,  # Now engine is always defined (might be DisabledEngine)
        queue=queue,
        monitor=monitor,
        run_tests=args.test,  # Only run tests if --test flag is passed
        event_bus=event_bus,  # Pass event bus for event-driven architecture
        storage=storage  # Pass storage for retrieving full evaluation data
    )
    
    # Set up event handlers for loose coupling
    def handle_evaluation_queued(event):
        """Store initial evaluation when queued"""
        eval_id = event['data'].get('eval_id')
        code = event['data'].get('code')
        if eval_id and code:
            success = storage.create_evaluation(eval_id, code, status='queued')
            if success:
                print(f"📝 Created evaluation {eval_id}")
            else:
                print(f"⚠️  Failed to create evaluation {eval_id}")
    
    def handle_evaluation_completed(event):
        """Store evaluation results when completed"""
        eval_id = event['data'].get('eval_id')
        result = event['data'].get('result')
        if eval_id and result:
            # Update the evaluation with completed status and results
            success = storage.update_evaluation(
                eval_id,
                status='completed',
                output=result.get('output'),
                error=result.get('error'),
                success=result.get('success')
            )
            if success:
                print(f"💾 Stored evaluation {eval_id}")
            else:
                print(f"⚠️  Failed to store evaluation {eval_id}")
    
    def handle_security_violation(event):
        """Handle security violations"""
        print(f"🚨 SECURITY ALERT: {event['data']}")
    
    # Subscribe handlers to events
    event_bus.subscribe(EventTypes.EVALUATION_QUEUED, handle_evaluation_queued)
    event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, handle_evaluation_completed)
    event_bus.subscribe(EventTypes.SECURITY_VIOLATION, handle_security_violation)
    
    print("✅ Event handlers configured")
    
    # Create API service and handler with storage
    api_service = create_api_service(platform, storage=storage)
    api_handler = create_api_handler(api_service)
    
    print("📡 API service configured")
    
    # Run security demos if requested (SAFE)
    if args.security_demo:
        print("\n🔒 Running safe security demos...")
        print("   These demos show security concepts without performing attacks")
        try:
            from src.security_scanner.scenarios.safe_demo_scenarios import SAFE_DEMO_SCENARIOS
            from src.security_scanner.security_runner import SecurityTestRunner
            
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
            from src.security_scanner.scenarios.attack_scenarios import ATTACK_SCENARIOS
            from src.security_scanner.security_runner import SecurityTestRunner
            
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
        components = [engine, queue, monitor, storage, platform, event_bus]
        passed = sum(1 for c in components if hasattr(c, 'self_test') and c.self_test()['passed'])
        print(f"Tests: {passed}/{len(components)} passed")
        
        # Show event history from tests
        print("\nEvent History from Tests:")
        for event in event_bus.get_history(limit=5):
            print(f"  {event['type']}: {event['data']}")
        
        return 0 if passed == len(components) else 1
    
    # Start FastAPI server
    from api.servers.fastapi_server import app as fastapi_app
    import api.servers.fastapi_server as fastapi_server
    import uvicorn
    
    # Override the global api_handler in fastapi_server
    fastapi_server.api_handler = api_handler
    
    # Start integrated server
    bind_host = os.environ.get('BIND_HOST', 'localhost')
    print(f"\n🚀 FastAPI server starting on http://{bind_host}:{args.port}")
    print("   - API routes: /api/*")
    print("   - Interactive docs: /docs")
    print("   - React frontend should connect to this API")
    print("📊 Event history available at: /events")
    
    print("\n✅ Server running. Press Ctrl+C to stop.")
    
    try:
        uvicorn.run(
            fastapi_app,
            host='0.0.0.0',
            port=args.port,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    sys.exit(main())