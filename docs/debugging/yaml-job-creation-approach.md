# YAML-Based Job Creation Approach

## Current Problem
When creating Kubernetes jobs using the Python client's object API (V1Job, V1Container, etc.), the command execution produces Python dict representation instead of JSON output.

## YAML-Based Solution

Instead of using Python objects, create jobs from YAML templates:

### 1. Create a Job Template

```yaml
# job_template.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: __JOB_NAME__
  namespace: crucible
  labels:
    app: evaluation
    eval-id: __EVAL_ID__
    created-by: dispatcher
  annotations:
    eval-id: __EVAL_ID__
    created-at: __CREATED_AT__
spec:
  ttlSecondsAfterFinished: 300
  activeDeadlineSeconds: __TIMEOUT__
  backoffLimit: 0
  template:
    metadata:
      labels:
        app: evaluation
        eval-id: __EVAL_ID__
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: evaluation
        image: __EXECUTOR_IMAGE__
        imagePullPolicy: IfNotPresent
        command: ["python", "-u", "-c", "__CODE__"]
        env:
        - name: EVAL_ID
          value: __EVAL_ID__
        - name: PYTHONUNBUFFERED
          value: "1"
        resources:
          limits:
            memory: __MEMORY_LIMIT__
            cpu: __CPU_LIMIT__
          requests:
            memory: 128Mi
            cpu: 100m
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop: ["ALL"]
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 100Mi
```

### 2. Modified Dispatcher Code

```python
import yaml
import base64
from string import Template

# Load template once at startup
with open('job_template.yaml') as f:
    JOB_TEMPLATE = f.read()

@app.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    """Create a Kubernetes Job using YAML template."""
    
    # Generate job name
    eval_id_safe = request.eval_id.replace('_', '-')[:20]
    job_name = f"eval-{eval_id_safe}-{uuid.uuid4().hex[:8]}"
    
    # Fill in the template
    job_yaml = JOB_TEMPLATE.replace('__JOB_NAME__', job_name)
    job_yaml = job_yaml.replace('__EVAL_ID__', request.eval_id)
    job_yaml = job_yaml.replace('__CREATED_AT__', datetime.utcnow().isoformat())
    job_yaml = job_yaml.replace('__TIMEOUT__', str(request.timeout))
    job_yaml = job_yaml.replace('__EXECUTOR_IMAGE__', EXECUTOR_IMAGE)
    job_yaml = job_yaml.replace('__MEMORY_LIMIT__', request.memory_limit)
    job_yaml = job_yaml.replace('__CPU_LIMIT__', request.cpu_limit)
    
    # Escape the code properly for YAML
    # Option 1: Base64 encode to avoid escaping issues
    encoded_code = base64.b64encode(request.code.encode()).decode()
    job_yaml = job_yaml.replace('__CODE__', f"$(echo {encoded_code} | base64 -d)")
    
    # Or Option 2: Use proper YAML escaping
    # escaped_code = yaml.dump(request.code)[:-1]  # Remove trailing newline
    # job_yaml = job_yaml.replace('"__CODE__"', escaped_code)
    
    # Parse YAML to dict
    job_dict = yaml.safe_load(job_yaml)
    
    try:
        # Create job from dict (not from objects)
        created_job = batch_v1.create_namespaced_job(
            namespace=KUBERNETES_NAMESPACE,
            body=job_dict  # Pass dict directly, not V1Job object
        )
        
        logger.info(f"Successfully created job {job_name}")
        
        return ExecuteResponse(
            eval_id=request.eval_id,
            job_name=job_name,
            status="created",
            message="Job created successfully"
        )
```

### 3. Alternative: Dynamic YAML Generation

```python
def create_job_yaml(request: ExecuteRequest, job_name: str) -> dict:
    """Generate job YAML dynamically without template."""
    
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": KUBERNETES_NAMESPACE,
            "labels": {
                "app": "evaluation",
                "eval-id": request.eval_id,
                "created-by": "dispatcher"
            },
            "annotations": {
                "eval-id": request.eval_id,
                "created-at": datetime.utcnow().isoformat()
            }
        },
        "spec": {
            "ttlSecondsAfterFinished": JOB_CLEANUP_TTL,
            "activeDeadlineSeconds": request.timeout,
            "backoffLimit": 0,
            "template": {
                "metadata": {
                    "labels": {
                        "app": "evaluation",
                        "eval-id": request.eval_id
                    }
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [{
                        "name": "evaluation",
                        "image": EXECUTOR_IMAGE,
                        "imagePullPolicy": "IfNotPresent",
                        "command": ["python", "-u", "-c", request.code],
                        "env": [
                            {"name": "EVAL_ID", "value": request.eval_id},
                            {"name": "PYTHONUNBUFFERED", "value": "1"}
                        ],
                        "resources": {
                            "limits": {
                                "memory": request.memory_limit,
                                "cpu": request.cpu_limit
                            },
                            "requests": {
                                "memory": "128Mi",
                                "cpu": "100m"
                            }
                        }
                    }],
                    "volumes": [{
                        "name": "tmp",
                        "emptyDir": {"sizeLimit": "100Mi"}
                    }]
                }
            }
        }
    }
```

## Key Differences

### Current Approach (V1Job objects):
- Uses `client.V1Job()`, `client.V1Container()`, etc.
- Python client serializes these objects
- Something in the serialization causes dict repr output

### YAML Approach:
- Creates plain dict/YAML structure
- Passes dict directly to `create_namespaced_job(body=job_dict)`
- Bypasses whatever serialization issue causes dict repr

## Benefits of YAML Approach

1. **Matches kubectl behavior** - More likely to produce same output as manual YAML
2. **Easier debugging** - Can dump exact YAML being sent
3. **Template flexibility** - Easy to version and modify templates
4. **Less code** - No need for verbose V1* object construction

## Implementation Path

1. Test with minimal job first
2. Verify it produces proper JSON output
3. Migrate dispatcher to use YAML approach
4. Keep V1Job approach as fallback if needed