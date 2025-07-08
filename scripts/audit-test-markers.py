#!/usr/bin/env python3
"""
Audit pytest markers across the test suite.

This script analyzes test files to:
1. Find tests missing expected markers
2. Find undefined markers being used
3. Suggest appropriate markers based on test content
4. Generate a report of marker usage
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import tomllib


class MarkerAuditor:
    """Analyze test files for pytest marker usage and consistency."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.defined_markers = self._load_defined_markers()
        self.test_files: List[Path] = []
        self.marker_usage: Dict[str, List[str]] = {}
        self.missing_markers: Dict[str, List[str]] = {}
        self.undefined_markers: Set[str] = set()
        
    def _load_defined_markers(self) -> Set[str]:
        """Load markers defined in pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return set()
            
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
            
        markers = set()
        pytest_config = config.get("tool", {}).get("pytest", {}).get("ini_options", {})
        marker_list = pytest_config.get("markers", [])
        
        for marker in marker_list:
            # Extract marker name from definition
            marker_name = marker.split(":")[0].strip()
            markers.add(marker_name)
            
        return markers
    
    def find_test_files(self) -> List[Path]:
        """Find all test files in the project."""
        test_dirs = [
            self.project_root / "tests",
            self.project_root / "test",
        ]
        
        test_files = []
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files.extend(test_dir.rglob("test_*.py"))
                test_files.extend(test_dir.rglob("*_test.py"))
                
        self.test_files = test_files
        return test_files
    
    def extract_markers_from_file(self, file_path: Path) -> Dict[str, Set[str]]:
        """Extract markers used in a test file."""
        markers_by_item = {}
        
        try:
            with open(file_path, "r") as f:
                content = f.read()
                
            # Parse AST
            tree = ast.parse(content)
            
            # Find all test functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if self._is_test_item(node):
                        markers = self._extract_markers_from_decorators(node)
                        markers_by_item[node.name] = markers
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return markers_by_item
    
    def _is_test_item(self, node: ast.AST) -> bool:
        """Check if a node is a test function or class."""
        if isinstance(node, ast.FunctionDef):
            return node.name.startswith("test_")
        elif isinstance(node, ast.ClassDef):
            return node.name.startswith("Test")
        return False
    
    def _extract_markers_from_decorators(self, node: ast.AST) -> Set[str]:
        """Extract pytest markers from decorators."""
        markers = set()
        
        for decorator in node.decorator_list:
            # Handle @pytest.mark.marker_name
            if isinstance(decorator, ast.Attribute):
                if (isinstance(decorator.value, ast.Attribute) and 
                    isinstance(decorator.value.value, ast.Name) and
                    decorator.value.value.id == "pytest" and
                    decorator.value.attr == "mark"):
                    markers.add(decorator.attr)
                    
            # Handle @pytest.mark.parametrize and other complex decorators
            elif isinstance(decorator, ast.Call):
                if (isinstance(decorator.func, ast.Attribute) and
                    isinstance(decorator.func.value, ast.Attribute) and
                    isinstance(decorator.func.value.value, ast.Name) and
                    decorator.func.value.value.id == "pytest" and
                    decorator.func.value.attr == "mark"):
                    markers.add(decorator.func.attr)
                    
        return markers
    
    def suggest_markers(self, file_path: Path, content: str) -> Set[str]:
        """Suggest appropriate markers based on file content and location."""
        suggestions = set()
        
        # Determine test category based on path
        relative_path = file_path.relative_to(self.project_root)
        path_parts = relative_path.parts
        
        if "unit" in path_parts:
            suggestions.add("unit")
        elif "integration" in path_parts:
            suggestions.add("integration")
        elif "e2e" in path_parts:
            suggestions.add("e2e")
        elif "performance" in path_parts:
            suggestions.add("performance")
        elif "security" in path_parts:
            suggestions.add("security")
        elif "benchmarks" in path_parts:
            suggestions.add("benchmark")
            
        # Analyze content for service dependencies
        if re.search(r'api_session|requests\.(get|post|put|delete)', content):
            suggestions.add("api")
        if re.search(r'redis_client|Redis|redis\.', content):
            suggestions.add("redis")
        if re.search(r'celery|send_task|apply_async', content):
            suggestions.add("celery")
        if re.search(r'docker|container|executor', content, re.IGNORECASE):
            suggestions.add("docker")
        if re.search(r'postgres|psql|database|db_session', content):
            suggestions.add("database")
            
        # Check for test characteristics
        if re.search(r'time\.sleep\s*\(\s*\d+\s*\)|timeout\s*=\s*\d{2,}', content):
            suggestions.add("slow")
        if re.search(r'stop.*service|restart.*service|docker.*stop', content):
            suggestions.add("destructive")
        if re.search(r'concurrent|parallel|threading|asyncio', content):
            suggestions.add("concurrency")
            
        return suggestions
    
    def audit(self):
        """Run the complete audit."""
        print(f"Auditing test markers in {self.project_root}")
        print(f"Defined markers: {sorted(self.defined_markers)}\n")
        
        self.find_test_files()
        
        for file_path in self.test_files:
            relative_path = file_path.relative_to(self.project_root)
            
            # Read file content
            with open(file_path, "r") as f:
                content = f.read()
                
            # Extract markers
            markers_by_item = self.extract_markers_from_file(file_path)
            
            # Suggest markers
            suggested_markers = self.suggest_markers(file_path, content)
            
            # Analyze each test item
            for item_name, used_markers in markers_by_item.items():
                # Track usage
                for marker in used_markers:
                    if marker not in self.marker_usage:
                        self.marker_usage[marker] = []
                    self.marker_usage[marker].append(f"{relative_path}::{item_name}")
                    
                    # Check if marker is defined (skip built-in pytest markers)
                    builtin_markers = {'skip', 'skipif', 'xfail', 'parametrize', 'usefixtures'}
                    if marker not in self.defined_markers and marker not in builtin_markers:
                        self.undefined_markers.add(marker)
                
                # Check for missing suggested markers
                missing = suggested_markers - used_markers
                if missing:
                    key = str(relative_path)
                    if key not in self.missing_markers:
                        self.missing_markers[key] = []
                    self.missing_markers[key].append({
                        "item": item_name,
                        "missing": sorted(missing),
                        "has": sorted(used_markers)
                    })
    
    def generate_report(self) -> str:
        """Generate audit report."""
        report = []
        report.append("# Test Marker Audit Report\n")
        report.append(f"Total test files analyzed: {len(self.test_files)}\n")
        
        # Undefined markers
        if self.undefined_markers:
            report.append("## ⚠️  Undefined Markers Being Used\n")
            for marker in sorted(self.undefined_markers):
                report.append(f"- `{marker}` used in:")
                for usage in sorted(self.marker_usage.get(marker, [])):
                    report.append(f"  - {usage}")
            report.append("")
        
        # Missing markers
        if self.missing_markers:
            report.append("## 📝 Suggested Missing Markers\n")
            for file_path, items in sorted(self.missing_markers.items()):
                report.append(f"### {file_path}\n")
                for item_info in items:
                    report.append(f"- **{item_info['item']}**")
                    report.append(f"  - Has: {', '.join(item_info['has']) if item_info['has'] else 'none'}")
                    report.append(f"  - Suggested to add: {', '.join(item_info['missing'])}")
                report.append("")
        
        # Marker usage statistics
        report.append("## 📊 Marker Usage Statistics\n")
        marker_counts = [(marker, len(usages)) for marker, usages in self.marker_usage.items()]
        marker_counts.sort(key=lambda x: x[1], reverse=True)
        
        for marker, count in marker_counts:
            defined = "✅" if marker in self.defined_markers else "❌"
            report.append(f"- `{marker}`: {count} uses {defined}")
        
        # Unused defined markers
        used_markers = set(self.marker_usage.keys())
        unused_markers = self.defined_markers - used_markers
        if unused_markers:
            report.append("\n## 🔍 Defined But Unused Markers\n")
            for marker in sorted(unused_markers):
                report.append(f"- `{marker}`")
        
        return "\n".join(report)


def main():
    """Run the marker audit."""
    # Find project root (where pyproject.toml is)
    current_dir = Path.cwd()
    project_root = current_dir
    
    # Search up for pyproject.toml
    while project_root.parent != project_root:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    else:
        if not (project_root / "pyproject.toml").exists():
            print("Could not find pyproject.toml. Please run from project directory.")
            return
    
    auditor = MarkerAuditor(project_root)
    auditor.audit()
    
    report = auditor.generate_report()
    print(report)
    
    # Save report
    report_path = project_root / "tests" / "marker-audit-report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()