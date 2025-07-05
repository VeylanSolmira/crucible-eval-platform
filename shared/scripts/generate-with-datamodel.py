#!/usr/bin/env python3
"""
Generate Python types using datamodel-code-generator.
This is a test to see if we can replace our custom generator.
"""

from pathlib import Path
from typing import List, Set
import tempfile

try:
    from datamodel_code_generator import generate
    from datamodel_code_generator.parser.openapi import OpenAPIParser
    from datamodel_code_generator import DataModelType, PythonVersion
except ImportError:
    print("Error: datamodel-code-generator is not installed.")
    print("Install it with: pip install datamodel-code-generator")
    exit(1)


def main():
    """Generate Python types using datamodel-code-generator."""
    script_dir = Path(__file__).parent
    shared_dir = script_dir.parent
    types_dir = shared_dir / "types"
    output_dir = shared_dir / "generated" / "python_new"  # Use different dir for testing
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating Python types with datamodel-code-generator...")
    
    # Process each YAML file
    for yaml_file in sorted(types_dir.glob("*.yaml")):
        output_file = output_dir / f"{yaml_file.stem.replace('-', '_')}.py"
        
        print(f"\nProcessing {yaml_file.name}...")
        
        # Generate code using the library
        generate(
            input_=yaml_file,
            output=output_file,
            input_file_type="openapi",
            output_model_type=DataModelType.PydanticV2BaseModel,
            field_constraints=True,
            use_annotated=True,
            use_field_description=True,
            target_python_version=PythonVersion.PY_39,
            encoding="utf-8",
            # Allow referencing other files
            use_standard_collections=True,
            reuse_model=True,
            collapse_root_models=True,
        )
        
        print(f"  Generated {output_file.name}")
        
        # Post-process the file
        post_process_file(output_file, yaml_file.stem)
    
    # Generate __init__.py
    generate_init_file(output_dir)
    
    print(f"\n✅ Generated files in {output_dir}")
    print("\nNow let's compare the output...")
    
    # Show a sample comparison
    compare_outputs(shared_dir)


def post_process_file(output_file: Path, original_stem: str):
    """Post-process generated files to add custom logic."""
    if not output_file.exists():
        return
        
    content = output_file.read_text()
    
    # Add custom logic for specific files
    if original_stem == "evaluation-status":
        # Add helper methods to EvaluationStatus enum
        content = add_enum_helpers(content)
    
    elif original_stem == "event-contracts":
        # Add EventChannels class
        content = add_event_channels(content)
    
    # Fix any import issues
    content = fix_imports(content)
    
    # Write back
    output_file.write_text(content)


def add_enum_helpers(content: str) -> str:
    """Add helper methods to EvaluationStatus enum."""
    # Find the EvaluationStatus class
    lines = content.split('\n')
    
    # First ensure we have List imported
    has_list_import = False
    typing_import_line = -1
    
    for i, line in enumerate(lines):
        if line.startswith('from typing import') and 'List' in line:
            has_list_import = True
            break
        elif line.startswith('from typing import'):
            typing_import_line = i
    
    # Add List to imports if needed
    if not has_list_import:
        if typing_import_line >= 0:
            lines[typing_import_line] = lines[typing_import_line].replace(
                'from typing import ',
                'from typing import List, '
            )
        else:
            # Add new import after other imports
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    continue
                elif line.strip():
                    lines.insert(i, 'from typing import List')
                    break
    
    # Now add helper methods
    in_enum = False
    indent = '    '
    insert_pos = -1
    
    for i, line in enumerate(lines):
        if 'class EvaluationStatus' in line and 'Enum' in line:
            in_enum = True
        elif in_enum and line.strip() and not line.startswith(indent):
            # We've reached the end of the enum
            insert_pos = i
            break
    
    if insert_pos > 0:
        helper_methods = [
            '',
            f'{indent}@classmethod',
            f'{indent}def terminal_states(cls) -> List["EvaluationStatus"]:',
            f'{indent}    """Get all terminal states."""',
            f'{indent}    return [cls.completed, cls.failed, cls.cancelled]',
            '',
            f'{indent}def is_terminal(self) -> bool:',
            f'{indent}    """Check if this is a terminal state."""',
            f'{indent}    return self in self.terminal_states()',
            '',
            f'{indent}def is_active(self) -> bool:',
            f'{indent}    """Check if this is an active (non-terminal) state."""',
            f'{indent}    return not self.is_terminal()',
        ]
        
        # Insert before the line that ends the class
        for method_line in reversed(helper_methods):
            lines.insert(insert_pos, method_line)
    
    return '\n'.join(lines)


def add_event_channels(content: str) -> str:
    """Add EventChannels class to event contracts."""
    event_channels = '''

class EventChannels:
    """Redis pub/sub channel names for events."""
    EVALUATION_QUEUED = "evaluation:queued"
    EVALUATION_RUNNING = "evaluation:running"
    EVALUATION_COMPLETED = "evaluation:completed"
    EVALUATION_FAILED = "evaluation:failed"
'''
    return content + event_channels


def fix_imports(content: str) -> str:
    """Fix any import issues in generated code."""
    # datamodel-code-generator might generate imports like:
    # from .evaluation_status import EvaluationStatus
    # But we need to ensure the module exists
    
    # For now, just return as-is
    # We can add fixes as we discover issues
    return content


def generate_init_file(output_dir: Path):
    """Generate __init__.py file."""
    all_exports = []
    modules = []
    
    for py_file in sorted(output_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
            
        module_name = py_file.stem
        exports = extract_exports(py_file)
        
        if exports:
            modules.append((module_name, exports))
            all_exports.extend(exports)
    
    # Generate content
    init_content = '''"""
Generated Python types from shared contracts.
DO NOT EDIT FILES IN THIS DIRECTORY - They are auto-generated.

Generated using datamodel-code-generator
Run 'python shared/scripts/generate-with-datamodel.py' to regenerate.
"""

'''
    
    # Add imports
    for module_name, exports in modules:
        init_content += f"from .{module_name} import {', '.join(exports)}\n"
    
    # Add __all__
    init_content += "\n__all__ = [\n"
    for export in sorted(all_exports):
        init_content += f'    "{export}",\n'
    init_content += "]\n"
    
    (output_dir / "__init__.py").write_text(init_content)
    print(f"Generated __init__.py with {len(all_exports)} exports")


def extract_exports(py_file: Path) -> List[str]:
    """Extract exportable names from a Python file."""
    exports = []
    content = py_file.read_text()
    
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('class ') and not line.startswith('class _'):
            # Extract class name
            if '(' in line:
                class_name = line[6:line.index('(')].strip()
            elif ':' in line:
                class_name = line[6:line.index(':')].strip()
            else:
                continue
            exports.append(class_name)
    
    return exports


def compare_outputs(shared_dir: Path):
    """Compare outputs from both generators."""
    old_dir = shared_dir / "generated" / "python"
    new_dir = shared_dir / "generated" / "python_new"
    
    print("\n" + "="*60)
    print("COMPARISON OF OUTPUTS")
    print("="*60)
    
    # Compare evaluation_status.py as an example
    if (old_dir / "evaluation_status.py").exists() and (new_dir / "evaluation_status.py").exists():
        print("\n--- evaluation_status.py ---")
        old_content = (old_dir / "evaluation_status.py").read_text()
        new_content = (new_dir / "evaluation_status.py").read_text()
        
        print(f"Old generator: {len(old_content)} chars, {len(old_content.splitlines())} lines")
        print(f"New generator: {len(new_content)} chars, {len(new_content.splitlines())} lines")
        
        # Show first few lines of each
        print("\nOld (first 10 lines):")
        for line in old_content.splitlines()[:10]:
            print(f"  {line}")
        
        print("\nNew (first 10 lines):")  
        for line in new_content.splitlines()[:10]:
            print(f"  {line}")


if __name__ == "__main__":
    main()