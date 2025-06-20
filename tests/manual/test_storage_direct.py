#!/usr/bin/env python3
"""Test storage directly to verify data persistence.

This bypasses the API and checks what's actually stored in the storage backend.
Useful for debugging storage issues.

Usage: python test_storage_direct.py [--storage-type file|database]
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from storage import FlexibleStorageManager
from storage.config import StorageConfig

def test_file_storage():
    """Test file storage directly"""
    config = StorageConfig(
        file_storage_path="./storage/evaluations",
        enable_caching=True
    )
    return FlexibleStorageManager.from_config(config)

def test_database_storage():
    """Test database storage directly"""
    database_url = os.environ.get('DATABASE_URL', 
                                  'postgresql://crucible:changeme@localhost:5432/crucible')
    config = StorageConfig(
        database_url=database_url,
        prefer_database=True,
        enable_caching=True
    )
    return FlexibleStorageManager.from_config(config)

def analyze_evaluations(storage):
    """Analyze stored evaluations"""
    print("Checking stored evaluations directly from storage...")
    print("="*60)
    
    # List all evaluations
    evaluations = storage.list_evaluations(limit=20)
    print(f"Found {len(evaluations)} evaluations in storage")
    
    if evaluations:
        # Analyze evaluations
        truncated_count = 0
        total_output_size = 0
        
        print("\nRecent evaluations:")
        for i, eval_data in enumerate(evaluations[:5]):
            print(f"\nEvaluation {i+1}:")
            print(f"  ID: {eval_data.get('id')}")
            print(f"  Status: {eval_data.get('status')}")
            print(f"  Created: {eval_data.get('created_at', 'N/A')}")
            
            # Check output fields
            if 'output' in eval_data:
                output_len = len(eval_data['output'])
                print(f"  Output length: {output_len} chars")
                if output_len > 100:
                    print(f"  Output preview: {eval_data['output'][:50]}...")
                else:
                    print(f"  Output: {eval_data['output']}")
            
            # Check truncation fields
            output_truncated = eval_data.get('output_truncated', False)
            output_size = eval_data.get('output_size', 0)
            
            print(f"  output_truncated: {output_truncated}")
            print(f"  output_size: {output_size:,} bytes")
            print(f"  output_location: {eval_data.get('output_location', 'None')}")
            
            if output_truncated:
                truncated_count += 1
            total_output_size += output_size
            
            # Show all fields for debugging
            print(f"  All fields: {sorted(eval_data.keys())}")
        
        # Summary statistics
        print(f"\nSummary:")
        print(f"  Total evaluations: {len(evaluations)}")
        print(f"  Truncated outputs: {truncated_count}")
        print(f"  Total output size: {total_output_size:,} bytes")
        print(f"  Average output size: {total_output_size // len(evaluations):,} bytes")
    else:
        print("No evaluations found in storage")
    
    # Test events storage
    print("\n" + "="*60)
    print("Checking events storage...")
    if evaluations:
        eval_id = evaluations[0].get('id')
        events = storage.get_events(eval_id)
        print(f"Events for evaluation {eval_id}:")
        for event in events:
            print(f"  - {event.get('timestamp', 'N/A')}: {event.get('type')} - {event.get('message')}")

def main():
    parser = argparse.ArgumentParser(description='Test storage directly')
    parser.add_argument('--storage-type', choices=['file', 'database'], 
                        default='file', help='Storage type to test')
    args = parser.parse_args()
    
    print(f"Testing {args.storage_type} storage backend...\n")
    
    if args.storage_type == 'file':
        storage = test_file_storage()
    else:
        storage = test_database_storage()
    
    analyze_evaluations(storage)

if __name__ == "__main__":
    main()