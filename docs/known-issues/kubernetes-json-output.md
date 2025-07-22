# Known Issue: Kubernetes API Single JSON Output

## Problem

When creating Kubernetes jobs via the Python API, if your code has only a single `print(json.dumps(...))` statement, the output will be converted to Python dict representation with single quotes instead of proper JSON with double quotes.

### Example

Your code:
```python
import json
data = {"result": "success", "value": 42}
print(json.dumps(data))
```

Expected output:
```json
{"result": "success", "value": 42}
```

Actual output:
```python
{'result': 'success', 'value': 42}
```

## Root Cause

This appears to be a bug in how the Kubernetes Python client handles command execution. It only affects single-line JSON outputs created via the API (not kubectl).

## Workarounds

### 1. Add a Suffix (Recommended)

Add any additional output after your JSON:

```python
import json
data = {"result": "success", "value": 42}
print(json.dumps(data))
print("# Complete")  # This prevents the conversion
```

### 2. Use the Evaluation Utils

We provide a utility function that handles this automatically:

```python
from evaluation_utils import output_json

data = {"result": "success", "value": 42}
output_json(data)  # Handles the workaround internally
```

### 3. Add a Prefix

```python
import json
data = {"result": "success", "value": 42}
print("JSON:" + json.dumps(data))
```

Then parse it as:
```python
if output.startswith("JSON:"):
    data = json.loads(output[5:])
```

### 4. For Test Code

If you're writing tests that expect JSON output, handle both formats:

```python
try:
    data = json.loads(output)
except json.JSONDecodeError:
    # Handle K8s API bug
    import ast
    data = ast.literal_eval(output)
```

## When This Happens

- ✅ Only affects single `print(json.dumps(...))` statements
- ✅ Only when jobs are created via Kubernetes Python API
- ❌ Does NOT affect kubectl apply
- ❌ Does NOT affect multiple print statements
- ❌ Does NOT affect non-JSON output

## Status

This is a known issue with the Kubernetes Python client. We've implemented workarounds but are monitoring for an upstream fix.