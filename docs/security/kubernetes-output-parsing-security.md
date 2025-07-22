# Kubernetes Output Parsing Security Analysis

## The Problem

Jobs created via Kubernetes Python API produce Python dict representation (single quotes) instead of proper JSON (double quotes). This is a known issue with the Kubernetes Python client that converts JSON responses to string representations of Python dictionaries.

## Root Cause

The Kubernetes Python client forces `response_type='str'` which gives you the string representation of the dict() instead of proper JSON. This particularly affects the proxy and exec APIs.

## Solutions from the Community

### 1. Use `ast.literal_eval()` (Most Common Workaround)

```python
import ast
# Convert the dict repr back to a Python dict
result = ast.literal_eval(log_output)
```

### 2. Use `_preload_content=False` for Raw Response

Add `_preload_content=False` to your API call to get the raw JSON response directly.

### 3. YAML-Based Job Creation

Create jobs from YAML templates instead of using the object API:

```python
import ruamel.yaml

# Load template
with open('job_template.yaml') as f:
    job = ruamel.yaml.safe_load(f)

# Modify as needed
job['spec']['template']['spec']['containers'][0]['command'] = [
    'python', '-c', f'import json; print(json.dumps({data}))'
]

# Create job
batch_v1.create_namespaced_job(namespace, job)
```

## Security Analysis of `ast.literal_eval()`

### What It Allows
- Strings, bytes, numbers, tuples, lists, dicts, sets, booleans, and None
- Only literal expressions - no function calls, attribute access, or operations

### What It Blocks
```python
# These would raise exceptions:
ast.literal_eval("__import__('os').system('rm -rf /')")  # No function calls
ast.literal_eval("{'a': lambda x: x}")  # No lambdas
ast.literal_eval("[x for x in range(10)]")  # No comprehensions
ast.literal_eval("1 + 1")  # No operators
```

### Minimal Risks
1. **DoS via large structures**: `ast.literal_eval("{'a': " * 1000000 + "1" + "}" * 1000000)`
2. **Stack overflow via nesting**: `ast.literal_eval("[" * 1000 + "]" * 1000)`

## Adversarial ML Evaluation Context

In adversarial ML evaluation, even "safe" parsing functions could be attack vectors:

1. **Crafted outputs** designed to exploit parser edge cases
2. **Resource exhaustion attacks** via nested structures
3. **Parser differential attacks** between ast.literal_eval and json.loads
4. **Information leakage** through parsing errors or timing

### Safer Approach for Adversarial Contexts

```python
import json
import resource
import signal
from contextlib import contextmanager

@contextmanager
def resource_limits(max_time=1, max_memory=100*1024*1024):  # 100MB
    """Limit execution time and memory for parsing"""
    def timeout_handler(signum, frame):
        raise TimeoutError("Parsing timeout")
    
    # Set memory limit
    resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
    
    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(max_time)
    
    try:
        yield
    finally:
        signal.alarm(0)

def parse_adversarial_output(output, max_size=10_000):
    """Parse potentially adversarial output safely"""
    # Size check
    if len(output) > max_size:
        return {"error": "Output too large", "truncated": output[:100]}
    
    # Character whitelist check
    allowed_chars = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ{}[],":\'-_.\\n\\t ')
    if not all(c in allowed_chars for c in output):
        return {"error": "Invalid characters detected"}
    
    # Try parsing with resource limits
    try:
        with resource_limits():
            # First try JSON (stricter)
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # Only try ast.literal_eval if JSON fails
                if output.strip().startswith("{") and output.strip().endswith("}"):
                    return ast.literal_eval(output)
                else:
                    return {"error": "Invalid format", "raw": output}
    except (TimeoutError, MemoryError):
        return {"error": "Resource limit exceeded"}
    except Exception as e:
        return {"error": f"Parse error: {type(e).__name__}"}
```

### Structured Output Protocol (Avoiding Parsing)

```python
def structured_output_protocol(data):
    """Use a fixed protocol instead of JSON"""
    # In the evaluated code:
    # print(f"RESULT_START:{base64.b64encode(json.dumps(result).encode()).decode()}:RESULT_END")
    
    # In the parser:
    import base64
    import re
    
    match = re.search(r'RESULT_START:([A-Za-z0-9+/=]+):RESULT_END', output)
    if match:
        try:
            encoded = match.group(1)
            decoded = base64.b64decode(encoded)
            return json.loads(decoded)
        except:
            return {"error": "Failed to decode result"}
    return {"error": "No valid result found"}
```

## Log Storage Risk Analysis

The risk already exists when:
1. **Kubernetes stores the logs** - could hit etcd storage limits
2. **Log aggregation systems** process them - could hit parser bugs
3. **Code retrieves the logs** - could hit memory limits
4. **Anyone views the logs** - kubectl logs, dashboards, etc.

### Where `literal_eval` Could Amplify Risk

- Log storage just stores the string representation
- `literal_eval` actually builds the structure in memory
- Different resource limits between storage and parsing

### Practical Approach

```python
def parse_evaluation_output(output):
    """Parse with basic safeguards, accepting that logs are already stored"""
    # Basic size sanity check
    if len(output) > 100_000:  # 100KB
        return {"error": "Output suspiciously large", "size": len(output)}
    
    try:
        # Try JSON first (cleaner)
        return json.loads(output)
    except json.JSONDecodeError:
        try:
            # Fall back to literal_eval for dict repr
            return ast.literal_eval(output)
        except Exception as e:
            # Store the error but don't re-raise
            return {
                "error": "Parse failed", 
                "type": type(e).__name__,
                "preview": output[:200]
            }
```

## Recommendations

### Short Term
Use `ast.literal_eval()` with basic size checks as a pragmatic solution.

### Long Term
1. **YAML-based job creation** for more reliable command execution
2. **Stream API with `_preload_content=False`** to get raw JSON
3. **Structured output protocols** to avoid parsing ambiguity
4. **Separate sandboxed parsing process** for adversarial contexts

### Defense in Depth for Adversarial ML
1. **Isolated namespaces** with strict resource quotas
2. **Init containers** to validate outputs before processing
3. **File-based outputs** with size validation before reading
4. **Sidecar containers** for validation with different permissions

## Conclusion

In the context of ML evaluation where arbitrary model outputs are already stored, `ast.literal_eval` doesn't meaningfully amplify risk. The fundamental attack surface exists at the log storage layer. However, for true adversarial contexts, additional hardening is warranted.