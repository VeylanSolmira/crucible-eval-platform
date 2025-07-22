# Debugging JSON Output Issue

## Problem Statement
The test `test_available_libraries.py` is failing because it expects JSON output but receives a Python dict representation with single quotes instead of double quotes.

## What We Know So Far

### 1. The Issue Location
- **Confirmed**: The dispatcher service receives the output WITH single quotes from Kubernetes
- **Debug logs show**: `First 200 chars of logs: "{'available': ['numpy'..."`
- **The dispatcher is NOT converting the output** - it's already wrong when received

### 2. The Test Code
The test code in `test_available_libraries.py` uses:
```python
print(json_module.dumps(final_data, indent=2))
```
This SHOULD produce proper JSON with double quotes.

### 3. How Code is Executed
- Code is passed to dispatcher service
- Dispatcher creates a Kubernetes Job with command: `["python", "-u", "-c", request.code]`
- The output is captured by Kubernetes and returned via the logs API

### 4. Local Testing Results
Running `python -c` locally with the same code produces correct JSON output:
```
Test 1: Direct execution
Output: '{"test": "value"}\n'
```

## Investigation Steps

### Step 1: Check if code is modified during transmission
- Need to verify the exact code being passed to the Kubernetes job
- Check if any escaping or transformation happens

### Step 2: Check executor image behavior
- The executor-ml image might have something that affects output
- Need to test the exact same code in the actual container

### Step 3: Check for any output post-processing
- Between the container output and what dispatcher receives
- Kubernetes logging might be doing something

## Current Theory
Something is causing the Python code to output a dict repr instead of the JSON string, but only in the Kubernetes environment.

## Investigation Progress

### Step 1: Added debug logging to dispatcher
Added logging to see the exact code being passed to the Kubernetes job:
- Code length
- First 200 chars of code
- Last 200 chars of code

This will help verify if the code is being modified during transmission.

### Step 1 Results: Sync Issues
- Added debug code to dispatcher_service/app.py
- File sync worked - verified with grep that new code is in /app/app.py
- BUT: The running uvicorn process hasn't reloaded the Python module
- Without --reload flag, uvicorn keeps using the old code in memory
- Need to restart the pod to load the new code

### Step 2: Added --reload flag to uvicorn services
- Created uvicorn-reload-patch.yaml for local K8s deployment
- Adds --reload flag to api-service, storage-service, and dispatcher
- This will make uvicorn automatically reload when files change
- Need to restart Skaffold to apply the new configuration

### Step 3: Debugging after Skaffold restart
- Skaffold restarted with new kustomization
- Confirmed uvicorn command updated in deployment
- Our debug logs for "Getting logs" are working
- But "Code length" logs not appearing - need to check if reload is working
- Confirmed reload is working: "WatchFiles detected changes in 'app.py'. Reloading..."

### Step 4: Got the debug output!
The code being passed to Kubernetes is correct:
```
Code length: 934 chars
First 200 chars: "\n# Import json first before we test library availability\nimport json as json_module\n\nlibraries_to_test = [\n    'numpy', 'pandas', 'requests', 'matplotlib', \n    'scipy', 'sklearn', 'tensorflow', 'torc"
Last 200 chars: 'inal_data = {\n    "available": results["available"],\n    "unavailable": results["unavailable"],\n    "tests": test_results\n}\n# Print only the JSON output\nprint(json_module.dumps(final_data, indent=2))\n'
```

The code ends with `print(json_module.dumps(final_data, indent=2))` which SHOULD produce proper JSON.

### The Mystery
- Code passed to Kubernetes: Uses json.dumps() ✓
- Output from Kubernetes: Python dict with single quotes ✗
- Something is happening between `python -c` execution and log capture

### Step 5: Isolated testing
Created test jobs with the same image and code:
1. Simple test: `{"test": "value", "numbers": [1, 2, 3]}` - Works! ✓
2. Exact test code in YAML: Produces proper JSON with double quotes! ✓

This proves:
- The executor-ml image works correctly
- The Python code works correctly
- The issue is somewhere in how the dispatcher creates or retrieves logs from jobs

### Next Steps
Need to check:
1. How dispatcher passes the code to Kubernetes
2. Any differences between manual job creation and dispatcher job creation
3. Log retrieval mechanism

### Step 6: Critical observation
The output has the EXACT structure we expect:
```
{'available': [...], 'unavailable': [...], 'tests': [...]}
```

This suggests the JSON was parsed into a Python dict and then printed/repr'd somewhere. This is NOT raw output from the container - it's been processed!

**ALREADY ESTABLISHED: Something is converting JSON to dict and repr'ing it**

### Step 7: Found suspicious pattern
The dispatcher logs show the command being created correctly. The code contains:
- Dictionary with double quotes: `results = {"available": [], "unavailable": []}`
- But output has single quotes: `{'available': [...], 'unavailable': [...]}`

This confirms something is evaluating/parsing the JSON output and converting it to Python dict representation.

### Step 8: The Real Issue
I keep proving the same thing:
- Manual jobs work correctly
- Dispatcher jobs don't
- The difference must be in HOW the job is created, not in the code or image

Need to find what's different about dispatcher-created jobs.

## Things I've Already Checked (STOP RE-CHECKING THESE)

### 1. Extra print statements or wrapper scripts
- **CHECKED**: The test code ends with `print(json_module.dumps(final_data, indent=2))`
- **CHECKED**: No additional print statements after this
- **CHECKED**: executor-ml Dockerfile has NO wrapper script
- **CHECKED**: Python -c doesn't print last expression if there's already a print
- **RESULT**: This is NOT the issue

### 2. Code modification during transmission
- **CHECKED**: Dispatcher logs show code is passed correctly
- **CHECKED**: Code ends with proper json.dumps() call
- **RESULT**: Code is NOT being modified

### 3. Executor image behavior
- **CHECKED**: Manual jobs with executor-ml:latest produce correct JSON
- **CHECKED**: Same exact code in manual YAML works perfectly
- **RESULT**: Image is NOT the problem

### 4. Python command format differences
- **CHECKED**: Manual job uses same command format as dispatcher
- **CHECKED**: Both use ["python", "-u", "-c", code]
- **RESULT**: Command format is NOT the issue

## What's Actually Different

The ONLY remaining difference is that dispatcher creates jobs programmatically via Kubernetes API, while manual tests use kubectl apply with YAML.

## FOUND THE ROOT CAUSE!

Ran test_k8s_api_job.py which creates a job via Kubernetes Python API (exactly like dispatcher does):
- Used simple test code: `print(json.dumps(data))`
- Result: `{'test': 'api', 'numbers': [1, 2, 3]}` (single quotes!)
- This proves the issue is with how Kubernetes API creates jobs vs kubectl YAML

The Kubernetes Python API is somehow causing Python dict representation instead of JSON output!

## Further Investigation Results

### YAML Approach Also Fails
- Tested creating jobs from YAML dicts instead of V1Job objects
- STILL produces dict repr - so it's not about object serialization

### The Real Pattern
When testing different outputs in the same job:
- Multiple print statements: json.dumps works correctly
- Single `print(json.dumps(...))`: Converted to dict repr
- Direct dict print: Shows as dict repr (expected)

This suggests the issue is specifically with single-line json.dumps output when created via K8s API.

### Not Related To:
- Container image (happens with python:3.11-slim, executor-ml, alpine)
- Command format (happens with direct python, shell wrapper, exec form)
- YAML vs object creation (both have the issue)

## New Discovery: Newline Escaping

Looking at the actual job YAML created by dispatcher:
- The code contains escaped newlines: `\n` instead of actual newlines
- When I test escaped newlines locally, Python produces NO output
- This suggests the escaping might be breaking the code execution

But wait - the dispatcher logs show the output IS being produced (with single quotes). So the code IS running...