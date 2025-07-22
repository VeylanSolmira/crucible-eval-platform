# Kubernetes API JSON Output Issue

## Problem
Jobs created via Kubernetes Python API produce Python dict representation (single quotes) instead of proper JSON (double quotes), while manual YAML jobs work correctly.

## Investigation Strategy

### Test Different Command Formats

1. **Original format (like dispatcher)**
   ```python
   command=["python", "-u", "-c", "import json\ndata = {'test': 'api'}\nprint(json.dumps(data))"]
   ```
   - Tests the exact format dispatcher uses

2. **Using /bin/sh -c wrapper**
   ```python
   command=["/bin/sh", "-c", "python -c \"import json; print(json.dumps({'test': 'api'}))\""]
   ```
   - Tests if shell wrapper affects output
   - May help with escaping issues

3. **Simple hello test**
   ```python
   command=["python", "-c", "print('hello')"]
   ```
   - Baseline test to ensure basic output works

4. **Direct JSON without intermediate variable**
   ```python
   command=["python", "-c", "import json; print(json.dumps({'test': 'direct'}))"]
   ```
   - Tests if variable assignment affects output

5. **Write to file to bypass stdout**
   ```python
   command=["python", "-c", "import json; open('/tmp/out.json','w').write(json.dumps({'test': 'file'})); print(open('/tmp/out.json').read())"]
   ```
   - Tests if stdout handling is the issue

## Potential Root Causes

1. **Shell escaping issues** - K8s API might be double-escaping quotes
2. **Python's repr() being called** - Something in job creation causes repr output
3. **Container entrypoint interference** - Base image might affect command execution
4. **Kubernetes logging layer** - Log retrieval API might transform output

## Next Steps

- Run test_k8s_api_job.py with all command format variations
- Identify which formats produce correct JSON vs dict repr
- Apply successful format to dispatcher service
- If all fail, investigate Kubernetes client library source code