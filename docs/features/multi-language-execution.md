# Multi-Language Code Execution Support

## Overview

The Crucible platform is designed to support evaluation of code written in multiple programming languages, enabling researchers to test diverse AI-generated code beyond just Python.

## Use Cases

Researchers may need to evaluate AI systems that generate code in various languages:

- **JavaScript/Node.js**: Web-based agent testing, browser automation, API interactions
- **Go**: High-performance system tasks, concurrent operations, network services  
- **Rust**: Memory-safe systems programming, performance-critical code
- **Python**: Data science, ML models, general scripting (default)
- **Shell/Bash**: System administration tasks, deployment scripts
- **C/C++**: Low-level system programming, performance benchmarks

## Architecture Design

### Language Detection

```python
def detect_language(code: str, hint: str = None) -> str:
    """Detect programming language from code content or hint"""
    if hint:
        return normalize_language(hint)
    
    # Check shebang line
    if code.startswith('#!'):
        first_line = code.split('\n')[0]
        if 'python' in first_line:
            return 'python'
        elif 'node' in first_line:
            return 'javascript'
        elif 'bash' in first_line or 'sh' in first_line:
            return 'bash'
    
    # Check for language-specific patterns
    if 'console.log' in code or 'const ' in code:
        return 'javascript'
    elif 'fmt.Println' in code or 'package main' in code:
        return 'go'
    elif 'fn main()' in code or 'let mut' in code:
        return 'rust'
    
    # Default to Python
    return 'python'
```

### Docker Base Images

Each language would use an appropriate Docker base image:

```python
LANGUAGE_CONFIGS = {
    'python': {
        'image': 'python:3.11-slim',
        'command': ['python', '-u'],
        'file_extension': '.py'
    },
    'javascript': {
        'image': 'node:18-slim',
        'command': ['node'],
        'file_extension': '.js'
    },
    'go': {
        'image': 'golang:1.21-alpine',
        'command': ['go', 'run'],
        'file_extension': '.go'
    },
    'rust': {
        'image': 'rust:1.75-slim',
        'command': ['cargo', 'script'],  # Requires cargo-script
        'file_extension': '.rs'
    },
    'bash': {
        'image': 'alpine:latest',
        'command': ['sh'],
        'file_extension': '.sh'
    }
}
```

### API Usage

Researchers could specify the language explicitly or let the system detect it:

```json
// Explicit language specification
{
  "code": "console.log('Hello from Node.js');",
  "language": "javascript",
  "engine": "docker"
}

// Automatic detection
{
  "code": "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello from Go\") }",
  "engine": "docker"
}
```

### Execution Engine Updates

The execution engines would be updated to handle multiple languages:

```python
class MultiLanguageDockerEngine(DockerEngine):
    def execute(self, code: str, eval_id: str, language: str = None) -> Dict[str, Any]:
        # Detect or validate language
        lang = language or detect_language(code)
        config = LANGUAGE_CONFIGS.get(lang, LANGUAGE_CONFIGS['python'])
        
        # Create temp file with appropriate extension
        suffix = config['file_extension']
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, dir=temp_dir) as f:
            f.write(code)
            temp_file = f.name
        
        # Build Docker command with language-specific image and command
        docker_cmd = [
            'docker', 'run', '--rm',
            '--network', 'none',
            '--memory', self.memory_limit,
            '--cpus', self.cpu_limit,
            '--read-only',
            '-v', f'{temp_file}:/code{suffix}:ro',
            config['image']
        ] + config['command'] + [f'/code{suffix}']
        
        # Execute and return results...
```

## Security Considerations

Each language brings unique security challenges:

### JavaScript/Node.js
- Prevent `require()` of dangerous modules
- Block network access via Docker
- Limit access to Node.js APIs

### Go
- Prevent `import` of network packages
- Block system calls via seccomp
- Memory limits are crucial

### Rust
- Generally memory-safe but still needs sandboxing
- Prevent unsafe blocks if possible
- Monitor for infinite loops

### Shell/Bash
- Highest risk - many system utilities available
- Must block dangerous commands (rm, curl, etc.)
- Consider using restricted shell

## Implementation Priority

Given time constraints, the recommended approach is:

### Phase 1 (Day 5 - 2 hours)
- Document the architecture (this document)
- Implement language detection logic
- Add Node.js support as proof of concept
- Update API to accept language parameter

### Phase 2 (Future Work)
- Add Go and Rust support
- Implement language-specific security policies
- Add compilation step for compiled languages
- Performance optimization per language

### Phase 3 (Long Term)
- Support for more languages (Java, C++, etc.)
- Language-specific resource limits
- Custom security policies per language
- Language version management

## Testing Strategy

Multi-language support requires additional testing:

```python
def test_javascript_execution():
    engine = MultiLanguageDockerEngine()
    result = engine.execute(
        code='console.log("Hello"); process.exit(0);',
        eval_id='test-js-1',
        language='javascript'
    )
    assert result['status'] == 'completed'
    assert 'Hello' in result['output']

def test_language_detection():
    assert detect_language('print("hello")') == 'python'
    assert detect_language('console.log("hello")') == 'javascript'
    assert detect_language('fn main() {}') == 'rust'
```

## Resource Considerations

Different languages have different resource requirements:

- **Python**: Moderate memory, quick startup
- **Node.js**: Higher memory usage, quick startup
- **Go**: Fast execution, moderate memory
- **Rust**: Compilation time overhead, efficient runtime
- **Java**: High memory, slow startup (JVM)

Consider adjusting timeouts and memory limits per language.

## Alternative Approach: Focus on Python Excellence

If multi-language support proves too ambitious, consider focusing on Python with:

1. **Multiple Python versions** (3.8, 3.9, 3.10, 3.11, 3.12)
2. **Pre-installed scientific libraries** (NumPy, Pandas, SciPy, etc.)
3. **GPU-enabled Python** for ML workloads
4. **Virtual environment isolation** per evaluation
5. **Custom Python security policies**

This would still demonstrate platform flexibility while reducing complexity.

## Decision Point

For the 7-day plan, recommend:
- **Minimum**: Document the architecture (this document) ✓
- **Realistic**: Add Node.js support as proof of concept
- **Stretch**: Include Go support if time permits
- **Future**: Full multi-language support post-submission