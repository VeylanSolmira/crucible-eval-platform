#!/usr/bin/env python3
"""
Fix test imports to use proper package imports instead of sys.path manipulation.
"""

import os
import re
from pathlib import Path

# Mapping of old import patterns to new package imports
IMPORT_MAPPINGS = {
    '../../../storage-worker': 'storage_worker',
    '../../../storage-service': 'storage_service',
    '../../../dispatcher-service': 'dispatcher_service',
    '../../../api': 'api',
    '../../../celery-worker': 'celery_worker',
}

def fix_test_file(file_path):
    """Fix imports in a single test file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Find sys.path manipulations
    pattern = r'import sys\s*\nimport os\s*\nsys\.path\.insert\(0,\s*os\.path\.join\(os\.path\.dirname\(__file__\),\s*[\'"]([^\'"]*)[\'"]\)\)\s*\n\nfrom\s+(\w+)\s+import\s+([^\n]+)'
    
    def replace_import(match):
        path_suffix = match.group(1)
        module_name = match.group(2)
        imports = match.group(3)
        
        # Map the path to the package name
        package_name = IMPORT_MAPPINGS.get(path_suffix)
        
        if not package_name:
            # Try to guess from path
            if 'storage-worker' in path_suffix:
                package_name = 'storage_worker'
            elif 'storage-service' in path_suffix:
                package_name = 'storage_service'
            elif 'dispatcher-service' in path_suffix:
                package_name = 'dispatcher_service'
            elif 'celery-worker' in path_suffix:
                package_name = 'celery_worker'
            else:
                print(f"  ⚠️  Unknown path pattern: {path_suffix}")
                return match.group(0)
        
        # Handle special cases
        if module_name == 'app' and package_name != 'storage_worker':
            # For services that export app directly
            return f"from {package_name} import {imports}"
        elif module_name == 'app' and package_name == 'storage_worker':
            # Storage worker exports specific classes
            return f"from {package_name} import {imports}"
        else:
            # General case
            return f"from {package_name}.{module_name} import {imports}"
    
    # Replace the imports
    content = re.sub(pattern, replace_import, content, flags=re.MULTILINE)
    
    # Also handle simpler sys.path.insert patterns that might not have the full pattern
    simple_pattern = r'#[^\n]*\nimport sys\s*\nimport os\s*\nsys\.path\.insert\([^)]+\)\s*\n'
    content = re.sub(simple_pattern, '', content, flags=re.MULTILINE)
    
    if content != original_content:
        print(f"✓ Fixed: {file_path}")
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    else:
        print(f"  No changes: {file_path}")
        return False

def main():
    """Fix all test files."""
    test_dir = Path('tests')
    fixed_count = 0
    
    print("Fixing test imports...")
    print("=" * 60)
    
    for test_file in test_dir.rglob('test_*.py'):
        if fix_test_file(test_file):
            fixed_count += 1
    
    print("=" * 60)
    print(f"Fixed {fixed_count} files")

if __name__ == '__main__':
    main()