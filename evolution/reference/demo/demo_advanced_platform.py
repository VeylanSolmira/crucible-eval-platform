#!/usr/bin/env python3
"""
Demo of the advanced platform features:
- Queued asynchronous execution
- Advanced monitoring with real-time subscriptions
- Production-grade security (if gVisor available)

This demonstrates how all components work together.
"""

import time
import threading
from components import (
    DockerEngine,
    GVisorEngine,
    AdvancedMonitor,
    TaskQueue,
    QueuedEvaluationPlatform
)


def monitor_evaluation(monitor: AdvancedMonitor, eval_id: str):
    """Subscribe to and print real-time events for an evaluation"""
    print(f"\n📡 Subscribing to events for {eval_id}...")
    subscriber = monitor.subscribe(eval_id)
    
    def print_events():
        while True:
            try:
                event = subscriber.get(timeout=5)
                if event.get('type') == 'stream_end':
                    print(f"📡 Stream ended for {eval_id}")
                    break
                print(f"📡 [{eval_id}] {event['type']}: {event['message']}")
            except:
                break
    
    # Run in background thread
    thread = threading.Thread(target=print_events, daemon=True)
    thread.start()
    return thread


def main():
    print("🚀 Advanced Crucible Platform Demo")
    print("==================================\n")
    
    # Create components
    print("1️⃣ Creating advanced components...")
    
    # Use best available engine
    try:
        import subprocess
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        if 'runsc' in result.stdout:
            engine = GVisorEngine('runsc')
            print("   ✅ Using gVisor engine (production security)")
        else:
            engine = DockerEngine()
            print("   ✅ Using Docker engine")
    except:
        print("   ❌ Docker not available!")
        return
    
    monitor = AdvancedMonitor()
    print("   ✅ Created advanced monitor with subscription support")
    
    queue = TaskQueue(max_workers=3)
    print("   ✅ Created task queue with 3 workers")
    
    platform = QueuedEvaluationPlatform(engine, monitor, queue)
    print("   ✅ Created queued evaluation platform")
    
    # Check health
    print("\n2️⃣ Running component tests...")
    if platform.test_results['overall']['passed']:
        print("   ✅ All tests passed!")
    else:
        print("   ❌ Some tests failed:")
        for component, result in platform.test_results.items():
            if component != 'overall' and not result['passed']:
                print(f"      - {component}: {result['message']}")
        return
    
    # Demo async evaluation
    print("\n3️⃣ Submitting evaluations to queue...")
    
    # Submit multiple evaluations
    eval_ids = []
    for i in range(3):
        code = f"""
import time
print("Evaluation {i} starting...")
time.sleep(2)  # Simulate work
print("Evaluation {i} complete!")
print(f"Result: {{i * 10}}")
"""
        result = platform.evaluate_async(code)
        eval_ids.append(result['eval_id'])
        print(f"   📝 Submitted evaluation {i}: {result['eval_id']}")
        
        # Subscribe to events for first evaluation
        if i == 0:
            monitor_evaluation(monitor, result['eval_id'])
    
    # Show queue status
    print("\n4️⃣ Queue status:")
    status = platform.get_queue_status()
    print(f"   Queued: {status['queue']['queued']}")
    print(f"   Workers: {status['queue']['workers']}")
    print(f"   Completed: {status['queue']['completed']}")
    
    # Wait and check status
    print("\n5️⃣ Waiting for evaluations to complete...")
    time.sleep(1)
    
    # Check evaluation status
    for i, eval_id in enumerate(eval_ids):
        print(f"\n   Checking evaluation {i} ({eval_id}):")
        status = platform.get_evaluation_status(eval_id)
        print(f"   Status: {status['status']}")
        
        if status['status'] == 'completed':
            print(f"   Output: {status['result']['output']}")
    
    # Wait for all to complete
    print("\n6️⃣ Waiting for all evaluations to finish...")
    time.sleep(5)
    
    # Final status
    print("\n7️⃣ Final platform status:")
    final_status = platform.get_status()
    print(f"   Queue completed: {final_status['queue_status']['queue']['completed']}")
    print(f"   Queue failed: {final_status['queue_status']['queue']['failed']}")
    print(f"   Total evaluations: {final_status['queue_status']['evaluations']['total']}")
    
    # Show evaluation history
    print("\n8️⃣ All evaluations:")
    for eval_id in monitor.get_all_evaluations():
        events = monitor.get_events(eval_id)
        print(f"\n   {eval_id}: {len(events)} events")
        for event in events[-2:]:  # Show last 2 events
            print(f"     - {event['type']}: {event['message']}")
    
    # Cleanup
    print("\n9️⃣ Shutting down...")
    platform.shutdown()
    print("   ✅ Platform shutdown complete")
    
    print("\n✨ Demo complete! This shows:")
    print("   - Queued async execution")
    print("   - Real-time event monitoring")
    print("   - Component health checks")
    print("   - Production-ready architecture")


if __name__ == '__main__':
    main()