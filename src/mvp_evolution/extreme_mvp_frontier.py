#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Frontier Edition
Clean integration of all TRACE-AI components with proper modular architecture.

Run with: python extreme_mvp_frontier.py [--unsafe] [--fastapi] [--test] [--openapi]
"""

import sys
import time
import argparse
from pathlib import Path

# Import ALL modular components
from components import (
    SubprocessEngine,
    DockerEngine,
    GVisorEngine,
    AdvancedMonitor,
    TaskQueue,
    QueuedEvaluationPlatform,
    FileStorage,
    InMemoryStorage,
    create_api,
    WebFrontendService,
    FrontendConfig,
    FrontendType,
    create_openapi_validated_api
)

def main():
    """Clean main entry point - just wire components together"""
    
    parser = argparse.ArgumentParser(description='Crucible Frontier')
    parser.add_argument('--unsafe', action='store_true', help='Use subprocess only')
    parser.add_argument('--fastapi', action='store_true', help='Use FastAPI')
    parser.add_argument('--test', action='store_true', help='Run tests only')
    parser.add_argument('--memory-storage', action='store_true', help='Use in-memory storage')
    parser.add_argument('--openapi', action='store_true', help='Enable OpenAPI validation')
    parser.add_argument('--port', type=int, default=8000, help='Port (default: 8000)')
    
    args = parser.parse_args()
    
    print("🚀 Crucible Frontier - Starting...")
    if args.openapi:
        print("   with OpenAPI validation enabled")
    print()
    
    # Select execution engine (gVisor > Docker > subprocess)
    if args.unsafe:
        engine = SubprocessEngine()
    else:
        try:
            engine = GVisorEngine()
            print("🛡️  Using gVisor")
        except:
            try:
                engine = DockerEngine()
                print("🐳 Using Docker")
            except:
                engine = SubprocessEngine()
                print("⚠️  Using subprocess")
    
    # Create core components
    queue = TaskQueue(max_workers=4)
    monitor = AdvancedMonitor()
    
    # Storage layer
    if args.memory_storage:
        storage = InMemoryStorage()
    else:
        storage_dir = Path("./frontier_storage")
        storage_dir.mkdir(exist_ok=True)
        storage = FileStorage(str(storage_dir))
    
    # Platform
    platform = QueuedEvaluationPlatform(
        engine=engine,
        queue=queue,
        monitor=monitor
    )
    
    # Wire storage to platform events
    def on_evaluation_complete(event):
        if event['type'] == 'complete':
            eval_id = event['eval_id']
            result = platform.get_evaluation_status(eval_id)
            if result:
                storage.store(eval_id, result)
    
    monitor.subscribe('evaluation', on_evaluation_complete)
    
    # Frontend configuration
    frontend_config = FrontendConfig(
        title="Crucible Frontier",
        enable_monitoring=True,
        enable_storage=True,
        enable_testing=True
    )
    
    frontend = WebFrontendService(
        config=frontend_config,
        ui_type=FrontendType.ADVANCED
    )
    
    # Run tests if requested
    if args.test:
        components = [engine, queue, monitor, storage, platform, frontend]
        passed = sum(1 for c in components if hasattr(c, 'self_test') and c.self_test()['passed'])
        print(f"Tests: {passed}/{len(components)} passed")
        return 0 if passed == len(components) else 1
    
    # Create API (with optional OpenAPI validation)
    framework = 'fastapi' if args.fastapi else 'http.server'
    
    if args.openapi and create_openapi_validated_api:
        print("📋 Using OpenAPI-validated API")
        api = create_openapi_validated_api(platform, "api/openapi.yaml")
        # Storage routes already defined in OpenAPI spec
    else:
        if args.openapi and not create_openapi_validated_api:
            print("⚠️  OpenAPI validation requested but openapi-core not installed")
            print("   Install with: pip install openapi-core pyyaml")
        api = create_api(platform, framework=framework, ui_html=frontend.get_html())
        
        # Add storage integration for non-OpenAPI mode
        def add_storage_routes():
            if hasattr(api, 'add_route'):
                api.add_route('/storage', 'GET', lambda: {'evaluations': storage.list_all()})
                api.add_route('/storage/<eval_id>', 'GET', lambda eval_id: storage.retrieve(eval_id))
                api.add_route('/storage/clear', 'POST', lambda: {'success': storage.clear()})
        
        add_storage_routes()
    
    # Start server
    print(f"\n🚀 Server starting on http://localhost:{args.port}")
    
    try:
        api.start(port=args.port)
        
        if framework == 'http.server':
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nShutting down...")
        api.stop()

if __name__ == "__main__":
    sys.exit(main())