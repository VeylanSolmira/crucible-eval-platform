#!/usr/bin/env python3
"""
Script to add white box/black box markers to test files based on classification.

Usage:
    python tests/add_test_markers.py           # Dry run - show what would be changed
    python tests/add_test_markers.py --apply   # Actually modify the files
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Test classifications based on TEST_CLASSIFICATION.md
CLASSIFICATIONS = {
    # Black box tests (API-only)
    "test_core_flows.py": "blackbox",
    "test_evaluation_lifecycle.py": "blackbox",
    "test_input_validation.py": "blackbox", 
    "test_memory_backend.py": "blackbox",
    "test_evaluation_status_display.py": "blackbox",  # Likely black box
    
    # Gray box tests (mostly behavioral)
    "test_evaluation_request.py": "graybox",
    "test_network_isolation.py": "graybox",
    "test_filesystem_isolation.py": "graybox",
    "test_available_libraries.py": "graybox",
    
    # White box tests (implementation-specific)
    "test_retry_config.py": "whitebox",
    "test_database_backend.py": "whitebox",
    "test_file_backend.py": "whitebox",
    "test_flexible_manager.py": "whitebox",
    "test_postgresql_operations.py": "whitebox",
    "test_celery_cancellation.py": "whitebox",
    "test_celery_connection.py": "whitebox",
    "test_celery_integration.py": "whitebox",
    "test_celery_tasks.py": "whitebox",
    "test_docker_event_diagnostics.py": "whitebox",
    "test_executor_imports.py": "whitebox",
    "test_evaluation_job_imports.py": "blackbox",
    "test_fast_failing_containers.py": "whitebox",
    "test_redis_cleanup.py": "whitebox",
    "test_db_flow.py": "whitebox",
    "test_storage_direct.py": "whitebox",
    "test_priority_celery.py": "whitebox",
    "test_priority_queue.py": "whitebox",
    "test_load.py": "whitebox",  # Likely uses internal APIs
    "test_resilience.py": "whitebox",  # Likely tests internals
    "test_status_update_comprehensive.py": "whitebox",
    "test_dual_write.py": "whitebox",
    "test_evaluation_throughput.py": "whitebox",  # Benchmarks often need internals
}


def find_test_files(base_dir: str) -> List[Path]:
    """Find all test files in the test directory."""
    test_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(Path(root) / file)
    return test_files


def get_file_classification(filepath: Path) -> str:
    """Get the classification for a test file."""
    filename = filepath.name
    return CLASSIFICATIONS.get(filename, "whitebox")  # Default to whitebox if unknown


def add_marker_to_file(filepath: Path, marker: str, dry_run: bool = True) -> Tuple[bool, str]:
    """Add pytest marker to a test file if not already present."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if marker already exists
    if f"@pytest.mark.{marker}" in content:
        return False, f"Already has {marker} marker"
    
    # Check if any box marker exists
    if any(f"@pytest.mark.{m}box" in content for m in ["black", "white", "gray"]):
        return False, "Already has a box marker"
    
    # Find where to insert the marker
    lines = content.split('\n')
    modified = False
    
    for i, line in enumerate(lines):
        # Look for test functions or classes
        if (line.startswith("def test_") or line.startswith("class Test")) and not modified:
            # Find where decorators start (if any)
            j = i - 1
            while j >= 0 and lines[j].strip().startswith("@"):
                j -= 1
            # Insert after the last non-decorator line
            insert_pos = j + 1
            lines.insert(insert_pos, f"@pytest.mark.{marker}")
            modified = True
            break
    
    if modified:
        new_lines = lines
    else:
        new_lines = lines
    
    if not modified:
        return False, "No test classes or functions found"
    
    new_content = '\n'.join(new_lines)
    
    # Ensure pytest is imported
    if "import pytest" not in new_content and "from pytest" not in new_content:
        # Add import after docstring and other imports
        import_added = False
        final_lines = []
        in_docstring = False
        docstring_count = 0
        
        for line in new_content.split('\n'):
            final_lines.append(line)
            
            # Track docstrings
            if '"""' in line:
                docstring_count += line.count('"""')
                in_docstring = (docstring_count % 2 == 1)
            
            # Add import after docstring and initial imports
            if not import_added and not in_docstring and line.strip() == "" and any(
                final_lines[-2].startswith(imp) for imp in ["import ", "from "] if len(final_lines) > 1
            ):
                final_lines.insert(-1, "import pytest")
                import_added = True
        
        new_content = '\n'.join(final_lines)
    
    if not dry_run:
        with open(filepath, 'w') as f:
            f.write(new_content)
    
    return True, f"Added {marker} marker"


def main():
    """Main function to process all test files."""
    dry_run = "--apply" not in sys.argv
    
    if dry_run:
        print("DRY RUN MODE - No files will be modified")
        print("Use --apply flag to actually modify files\n")
    
    base_dir = Path(__file__).parent.parent  # Go up to tests directory
    test_files = find_test_files(base_dir)
    
    results = {
        "blackbox": [],
        "graybox": [],
        "whitebox": [],
        "skipped": []
    }
    
    for filepath in sorted(test_files):
        relative_path = filepath.relative_to(base_dir)
        classification = get_file_classification(filepath)
        
        modified, message = add_marker_to_file(filepath, classification, dry_run)
        
        if modified:
            results[classification].append(str(relative_path))
            print(f"✓ {relative_path}: {message}")
        else:
            results["skipped"].append(str(relative_path))
            print(f"- {relative_path}: {message}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for category, files in results.items():
        if files and category != "skipped":
            print(f"\n{category.upper()} ({len(files)} files):")
            for f in files[:5]:  # Show first 5
                print(f"  - {f}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
    
    print(f"\nTotal files processed: {len(test_files)}")
    print(f"Files to be modified: {sum(len(f) for c, f in results.items() if c != 'skipped')}")
    print(f"Files skipped: {len(results['skipped'])}")
    
    if dry_run:
        print("\nRun with --apply flag to actually modify the files")


if __name__ == "__main__":
    main()