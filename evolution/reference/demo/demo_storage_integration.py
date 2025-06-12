#!/usr/bin/env python3
"""
Demonstration of storage integration with the evaluation platform.

This shows how the storage component can be used to:
1. Persist evaluation results
2. Store event streams
3. Enable result retrieval and analysis
4. Support both in-memory and file-based storage
"""

import sys
import time
import json
from datetime import datetime, timezone

# Add current directory to path
sys.path.append('.')

from components import (
    SubprocessEngine,
    AdvancedMonitor,
    TestableEvaluationPlatform,
    InMemoryStorage,
    FileStorage
)


class StorageIntegratedPlatform(TestableEvaluationPlatform):
    """
    Extended platform that integrates storage for persistence.
    
    Future evolution:
    - Add automatic archival of old evaluations
    - Add result caching for repeated evaluations
    - Add distributed storage support
    - Add data analytics capabilities
    """
    
    def __init__(self, engine, monitor, storage):
        super().__init__(engine, monitor)
        self.storage = storage
    
    def evaluate(self, code: str) -> dict:
        """Override evaluate to add storage integration"""
        # Run evaluation
        result = super().evaluate(code)
        
        # Store evaluation result
        eval_data = {
            'id': result['id'],
            'status': result['status'],
            'output': result['output'],
            'error': result.get('error'),
            'code': code,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'execution_time': result.get('execution_time', 0)
        }
        self.storage.store_evaluation(result['id'], eval_data)
        
        # Store events
        events = self.monitor.get_events(result['id'])
        self.storage.store_events(result['id'], events)
        
        # Store metadata
        metadata = {
            'engine': self.engine.__class__.__name__,
            'monitor': self.monitor.__class__.__name__,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'code_length': len(code),
            'code_lines': len(code.splitlines())
        }
        self.storage.store_metadata(result['id'], metadata)
        
        return result
    
    def get_evaluation_history(self, limit: int = 10) -> list:
        """Retrieve recent evaluation history"""
        eval_ids = self.storage.list_evaluations(limit=limit)
        history = []
        
        for eval_id in eval_ids:
            eval_data = self.storage.retrieve_evaluation(eval_id)
            if eval_data:
                history.append({
                    'id': eval_id,
                    'timestamp': eval_data.get('timestamp'),
                    'status': eval_data.get('status'),
                    'code_preview': eval_data.get('code', '')[:50] + '...' if len(eval_data.get('code', '')) > 50 else eval_data.get('code', '')
                })
        
        return history
    
    def get_evaluation_details(self, eval_id: str) -> dict:
        """Get full details of an evaluation including events"""
        details = {
            'evaluation': self.storage.retrieve_evaluation(eval_id),
            'events': self.storage.retrieve_events(eval_id),
            'metadata': self.storage.retrieve_metadata(eval_id)
        }
        return details


def demonstrate_storage_integration():
    """Demonstrate storage capabilities"""
    print("🗄️  Storage Integration Demo")
    print("=" * 60)
    
    # Test with InMemoryStorage first
    print("\n1. Testing with InMemoryStorage")
    print("-" * 40)
    
    engine = SubprocessEngine()
    monitor = AdvancedMonitor()
    storage = InMemoryStorage()
    platform = StorageIntegratedPlatform(engine, monitor, storage)
    
    # Run some evaluations
    test_codes = [
        "print('Hello from evaluation 1')",
        "import time\nfor i in range(3):\n    print(f'Progress: {i+1}/3')\n    time.sleep(0.1)",
        "result = sum(range(100))\nprint(f'Sum of 0-99: {result}')"
    ]
    
    print("\nRunning evaluations...")
    for i, code in enumerate(test_codes):
        print(f"\nEvaluation {i+1}:")
        print(f"Code: {code[:50]}..." if len(code) > 50 else f"Code: {code}")
        result = platform.evaluate(code)
        print(f"Result: {result['status']} - Output: {result['output'].strip()}")
    
    # Show evaluation history
    print("\n\nEvaluation History:")
    history = platform.get_evaluation_history()
    for item in history:
        print(f"- {item['id']}: {item['status']} at {item['timestamp'][:19]}")
        print(f"  Code: {item['code_preview']}")
    
    # Show detailed info for one evaluation
    if history:
        eval_id = history[0]['id']
        print(f"\n\nDetailed info for {eval_id}:")
        details = platform.get_evaluation_details(eval_id)
        
        print("\nEvaluation Data:")
        print(f"  Status: {details['evaluation']['status']}")
        print(f"  Output: {details['evaluation']['output'].strip()}")
        
        print("\nEvents:")
        for event in details['events']:
            print(f"  [{event['timestamp'][:19]}] {event['type']}: {event['message']}")
        
        print("\nMetadata:")
        for key, value in details['metadata'].items():
            print(f"  {key}: {value}")
    
    # Test with FileStorage
    print("\n\n2. Testing with FileStorage")
    print("-" * 40)
    
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Storage directory: {temp_dir}")
        
        file_storage = FileStorage(temp_dir)
        file_platform = StorageIntegratedPlatform(engine, monitor, file_storage)
        
        # Run evaluation
        result = file_platform.evaluate("print('Persistent storage test!')")
        print(f"\nEvaluation {result['id']} completed")
        print(f"Output: {result['output'].strip()}")
        
        # Show files created
        import os
        print("\nFiles created:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
        
        # Verify persistence
        print("\nVerifying persistence...")
        details = file_platform.get_evaluation_details(result['id'])
        print(f"Retrieved evaluation status: {details['evaluation']['status']}")
        print(f"Retrieved output: {details['evaluation']['output'].strip()}")
    
    # Test storage swap
    print("\n\n3. Demonstrating Storage Swap")
    print("-" * 40)
    
    # Start with in-memory
    platform.storage = InMemoryStorage()
    result1 = platform.evaluate("print('In memory')")
    
    # Switch to file storage
    with tempfile.TemporaryDirectory() as temp_dir:
        platform.storage = FileStorage(temp_dir)
        result2 = platform.evaluate("print('In file')")
        
        # Try to retrieve both
        print("\nTrying to retrieve evaluations after storage swap:")
        print(f"Evaluation {result1['id']} (was in memory): ", end="")
        details1 = platform.get_evaluation_details(result1['id'])
        print("Not found" if details1['evaluation'] is None else "Found")
        
        print(f"Evaluation {result2['id']} (in file): ", end="")
        details2 = platform.get_evaluation_details(result2['id'])
        print("Not found" if details2['evaluation'] is None else "Found")
    
    print("\n✅ Storage integration demo completed!")


def demonstrate_analytics():
    """Demonstrate analytics capabilities with stored data"""
    print("\n\n📊 Analytics Demo")
    print("=" * 60)
    
    engine = SubprocessEngine()
    monitor = AdvancedMonitor()
    storage = InMemoryStorage()
    platform = StorageIntegratedPlatform(engine, monitor, storage)
    
    # Run various evaluations
    test_scenarios = [
        ("print('Success')", "success"),
        ("import time\ntime.sleep(0.5)\nprint('Slow')", "slow"),
        ("1/0", "error"),
        ("print('A' * 1000)", "large_output"),
        ("for i in range(5):\n    print(i)", "loop")
    ]
    
    print("\nRunning test scenarios...")
    for code, scenario in test_scenarios:
        try:
            result = platform.evaluate(code)
            print(f"- {scenario}: {result['status']}")
        except Exception as e:
            print(f"- {scenario}: error - {str(e)}")
    
    # Analyze stored data
    print("\n\nAnalyzing evaluation data:")
    
    eval_ids = storage.list_evaluations(limit=100)
    total_evals = len(eval_ids)
    successful = 0
    failed = 0
    total_output_length = 0
    
    for eval_id in eval_ids:
        eval_data = storage.retrieve_evaluation(eval_id)
        if eval_data:
            if eval_data['status'] in ['success', 'completed']:
                successful += 1
            else:
                failed += 1
            total_output_length += len(eval_data.get('output', ''))
    
    print(f"\nStatistics:")
    print(f"  Total evaluations: {total_evals}")
    print(f"  Successful: {successful} ({successful/total_evals*100:.1f}%)")
    print(f"  Failed: {failed} ({failed/total_evals*100:.1f}%)")
    print(f"  Average output length: {total_output_length/total_evals:.1f} chars")
    
    # Event analysis
    print("\n\nEvent Analysis:")
    event_types = {}
    for eval_id in eval_ids:
        events = storage.retrieve_events(eval_id)
        for event in events:
            event_type = event.get('type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print("Event type distribution:")
    for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {event_type}: {count}")


if __name__ == '__main__':
    try:
        demonstrate_storage_integration()
        demonstrate_analytics()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()