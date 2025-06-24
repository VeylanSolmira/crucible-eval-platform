# ML Workload Support Sprint: External GPU Services Integration

## Goal: Enable Real ML Workloads like nanoGPT via External Services

### Context
- User preference: External notebook/GPU services over EC2 instances
- Focus on best pricing and minimal infrastructure management
- Leverage existing GPU providers (Colab, Paperspace, Modal, Lambda Labs, etc.)
- Support multi-hour training runs without managing hardware

### Example Target Workload: nanoGPT
```python
# Typical nanoGPT training script
import torch
from model import GPT

# Requires:
# - GPU with 8-16GB VRAM
# - 2-8 hours runtime
# - PyTorch with CUDA
# - Access to datasets (shakespeare, openwebtext)
# - Ability to save checkpoints
# - TensorBoard logging

model = GPT(vocab_size=50257, n_layer=12, n_head=12, n_embd=768)
model.to('cuda')
# ... training loop
```

## Leading External Service Options

### 1. **Modal** (Serverless GPU)
- **Pros**: Pay per second, auto-scaling, no idle costs
- **Pricing**: A10G ~$1.10/hr, T4 ~$0.59/hr
- **API**: Python-native, excellent for batch jobs
- **Integration**: Direct code execution, automatic containerization

### 2. **Paperspace Gradient** (Notebooks + Jobs)
- **Pros**: Free tier available, persistent storage included
- **Pricing**: Free P5000 (limited), A4000 $0.51/hr, A100 $3.09/hr
- **API**: REST API + SDK for job submission
- **Integration**: Notebook-first, but supports scripts

### 3. **Lambda Labs** (Dedicated Cloud)
- **Pros**: Best $/GPU-hour for A100s
- **Pricing**: A10 $0.60/hr, A100 $1.29/hr
- **API**: SSH + API for instance management
- **Integration**: More like traditional cloud, good for long runs

### 4. **Google Colab Pro+** (Managed Notebooks)
- **Pros**: Familiar interface, minimal setup
- **Pricing**: $49.99/mo for ~100 compute units
- **API**: Limited programmatic access
- **Integration**: Best for interactive work

### 5. **Replicate** (Model-as-a-Service)
- **Pros**: Zero infrastructure, version control built-in
- **Pricing**: ~$0.00055/sec for T4 ($1.98/hr)
- **API**: Excellent REST API
- **Integration**: Best for inference, supports training

## Day 1: External Service Integration Framework

### Morning (4 hours): Service Abstraction Layer
- [ ] Create unified interface for external GPU providers
  ```python
  class GPUProvider(ABC):
      @abstractmethod
      async def submit_job(self, code: str, requirements: ResourceRequirements) -> JobHandle
      
      @abstractmethod
      async def get_status(self, job_id: str) -> JobStatus
      
      @abstractmethod
      async def get_logs(self, job_id: str) -> List[str]
      
      @abstractmethod
      async def download_artifacts(self, job_id: str) -> Dict[str, bytes]
  ```

- [ ] Implement Modal provider
  ```python
  class ModalProvider(GPUProvider):
      def __init__(self):
          self.stub = modal.Stub("crucible-ml-jobs")
          
      async def submit_job(self, code: str, requirements: ResourceRequirements):
          # Convert user code to Modal function
          gpu_type = self._map_gpu_requirements(requirements)
          job = self.stub.function(
              gpu=gpu_type,
              timeout=requirements.timeout_seconds,
              secrets=[modal.Secret.from_name("crucible-storage")]
          )(self._wrap_user_code(code))
          
          return ModalJobHandle(job.object_id)
  ```

- [ ] Implement Paperspace provider
  ```python
  class PaperspaceProvider(GPUProvider):
      def __init__(self):
          self.client = gradient.JobsClient(api_key=os.environ["PAPERSPACE_API_KEY"])
          
      async def submit_job(self, code: str, requirements: ResourceRequirements):
          # Create gradient job spec
          job = await self.client.create(
              name=f"crucible-{uuid.uuid4().hex[:8]}",
              projectId=self.project_id,
              container="pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
              machineType=self._map_instance_type(requirements),
              command=self._create_job_script(code),
              workspace=self._prepare_workspace(code)
          )
          return PaperspaceJobHandle(job.id)
  ```

### Afternoon (4 hours): Cost Optimization Engine
- [ ] Implement provider selection logic
  ```python
  class ProviderSelector:
      def select_optimal_provider(
          self, 
          requirements: ResourceRequirements,
          constraints: UserConstraints
      ) -> GPUProvider:
          # Factor in:
          # - Current spot prices
          # - Queue times
          # - User's remaining credits
          # - Job duration estimates
          # - Geographic restrictions
          
          if requirements.duration_hours < 1 and requirements.gpu_memory < 16:
              return ModalProvider()  # Best for short bursts
          elif requirements.interactive:
              return ColabProvider()  # Best for notebooks
          elif requirements.duration_hours > 24:
              return LambdaLabsProvider()  # Best for long runs
          else:
              return PaperspaceProvider()  # Good balance
  ```

- [ ] Create cost estimation service
  ```python
  class CostEstimator:
      def estimate_job_cost(
          self,
          provider: str,
          gpu_type: str,
          duration_hours: float
      ) -> CostEstimate:
          rates = {
              "modal": {"t4": 0.59, "a10g": 1.10, "a100": 2.78},
              "paperspace": {"a4000": 0.51, "a6000": 0.79, "a100": 3.09},
              "lambda": {"a10": 0.60, "a100": 1.29},
          }
          
          base_cost = rates[provider][gpu_type] * duration_hours
          
          # Add storage, egress, and other costs
          storage_cost = self._estimate_storage_cost(duration_hours)
          network_cost = self._estimate_network_cost(provider)
          
          return CostEstimate(
              compute=base_cost,
              storage=storage_cost,
              network=network_cost,
              total=base_cost + storage_cost + network_cost
          )
  ```

## Day 2: Frontend Service Selection

### Morning (4 hours): Provider Selection UI
- [ ] Create service comparison component
  ```typescript
  interface ServiceOption {
    provider: string
    gpu_type: string
    hourly_rate: number
    availability: 'immediate' | 'queued' | 'unavailable'
    features: string[]
    estimated_total_cost: number
  }
  
  export function ServiceSelector({ 
    code, 
    estimatedDuration,
    onSelect 
  }: ServiceSelectorProps) {
    const options = useServiceOptions(code, estimatedDuration)
    
    return (
      <div className="service-grid">
        {options.map(option => (
          <ServiceCard 
            key={option.provider}
            option={option}
            recommended={option.provider === options[0].provider}
            onSelect={() => onSelect(option)}
          />
        ))}
      </div>
    )
  }
  ```

- [ ] Add requirements detection
  ```typescript
  function detectRequirements(code: string): ResourceRequirements {
    const requirements: ResourceRequirements = {
      gpu_memory: 8,  // Default
      duration_hours: 1,
      framework: 'pytorch',
      interactive: false
    }
    
    // Detect GPU memory needs
    if (code.includes('GPT') && code.includes('n_layer=12')) {
      requirements.gpu_memory = 16
    }
    if (code.includes('13B') || code.includes('large')) {
      requirements.gpu_memory = 24
    }
    
    // Detect duration from comments or training loops
    const epochMatch = code.match(/epochs?\s*=\s*(\d+)/)
    if (epochMatch) {
      requirements.duration_hours = parseInt(epochMatch[1]) * 0.1 // Rough estimate
    }
    
    return requirements
  }
  ```

### Afternoon (4 hours): Job Monitoring Dashboard
- [ ] Create unified job tracking
  ```typescript
  interface ExternalJob {
    id: string
    provider: string
    status: 'queued' | 'provisioning' | 'running' | 'completed' | 'failed'
    progress?: {
      epoch?: number
      total_epochs?: number
      loss?: number
      eta_seconds?: number
    }
    logs: string[]
    cost_so_far: number
  }
  
  export function JobMonitor({ jobId }: { jobId: string }) {
    const job = useExternalJob(jobId)
    const logs = useJobLogs(jobId)
    
    return (
      <div className="job-monitor">
        <StatusHeader job={job} />
        <ProgressChart progress={job.progress} />
        <LogViewer logs={logs} />
        <CostMeter current={job.cost_so_far} estimated={job.estimated_total} />
      </div>
    )
  }
  ```

- [ ] Implement log parsing for progress
  ```typescript
  function parseTrainingProgress(logs: string[]): TrainingProgress {
    const progress: TrainingProgress = {}
    
    // Parse epoch information
    const epochRegex = /Epoch\s+(\d+)\/(\d+)/
    const lossRegex = /loss:\s*([\d.]+)/
    
    for (const line of logs) {
      const epochMatch = line.match(epochRegex)
      if (epochMatch) {
        progress.current_epoch = parseInt(epochMatch[1])
        progress.total_epochs = parseInt(epochMatch[2])
      }
      
      const lossMatch = line.match(lossRegex)
      if (lossMatch) {
        progress.loss = parseFloat(lossMatch[1])
      }
    }
    
    return progress
  }
  ```

## Day 3: Storage & Artifact Management

### Morning (4 hours): Unified Storage Layer
- [ ] Implement cross-provider storage
  ```python
  class UnifiedStorage:
      def __init__(self):
          self.s3_client = boto3.client('s3')
          self.bucket = "crucible-ml-artifacts"
          
      async def prepare_job_storage(self, job_id: str, provider: str) -> StorageConfig:
          # Create job-specific prefix
          prefix = f"jobs/{job_id}/"
          
          # Generate pre-signed URLs for provider access
          if provider == "modal":
              # Modal can use S3 directly with credentials
              return StorageConfig(
                  type="s3",
                  bucket=self.bucket,
                  prefix=prefix,
                  credentials=self._get_temp_credentials(prefix)
              )
          elif provider == "paperspace":
              # Paperspace needs data in their storage
              return await self._sync_to_gradient_storage(prefix)
          elif provider == "lambda":
              # Lambda Labs uses persistent volumes
              return await self._prepare_lambda_volume(prefix)
              
      async def collect_artifacts(self, job_id: str, provider: str) -> Dict[str, str]:
          # Collect outputs from provider-specific storage
          # Consolidate in S3
          # Return S3 URLs for all artifacts
  ```

- [ ] Create dataset management system
  ```python
  class DatasetManager:
      COMMON_DATASETS = {
          "shakespeare": "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt",
          "openwebtext": "s3://crucible-datasets/openwebtext-sample.tar.gz",
          "cifar10": "torchvision.datasets.CIFAR10",
      }
      
      async def prepare_dataset(self, name: str, provider: str) -> DatasetConfig:
          if name in self.COMMON_DATASETS:
              # Use pre-cached version on provider
              return await self._get_provider_dataset_path(name, provider)
          else:
              # Upload custom dataset to provider
              return await self._upload_custom_dataset(name, provider)
  ```

### Afternoon (4 hours): Checkpoint & Resume System
- [ ] Implement checkpoint management
  ```python
  class CheckpointManager:
      async def save_checkpoint(
          self, 
          job_id: str, 
          checkpoint_data: bytes,
          metadata: Dict[str, Any]
      ):
          # Save to S3 with metadata
          key = f"checkpoints/{job_id}/step_{metadata['step']}.pt"
          await self.s3_client.put_object(
              Bucket=self.bucket,
              Key=key,
              Body=checkpoint_data,
              Metadata={
                  'epoch': str(metadata.get('epoch', 0)),
                  'loss': str(metadata.get('loss', 0)),
                  'timestamp': datetime.utcnow().isoformat()
              }
          )
          
      async def list_checkpoints(self, job_id: str) -> List[Checkpoint]:
          # List all checkpoints for a job
          # Include metadata for UI display
          
      async def prepare_resume_job(
          self, 
          original_job_id: str,
          checkpoint_id: str,
          provider: str
      ) -> ResumeConfig:
          # Download checkpoint
          # Prepare for provider-specific resume
          # Return configuration for resumed job
  ```

## Day 4: Provider-Specific Optimizations

### Morning (4 hours): Modal Optimizations
- [ ] Implement Modal-specific features
  ```python
  class ModalOptimizer:
      def optimize_for_modal(self, user_code: str) -> str:
          # Add Modal-specific optimizations
          template = """
  import modal
  
  stub = modal.Stub("crucible-job-{job_id}")
  
  # Pre-download models and datasets at build time
  image = (
      modal.Image.debian_slim()
      .pip_install("torch", "transformers", "datasets")
      .run_function(download_datasets, secrets=[modal.Secret.from_name("hf-token")])
  )
  
  @stub.function(
      gpu="a10g",
      timeout=86400,
      image=image,
      secrets=[modal.Secret.from_name("crucible-storage")],
      _allow_background=True  # Don't block on completion
  )
  def train():
      {user_code}
      
      # Auto-save results to S3
      save_results_to_s3()
  
  if __name__ == "__main__":
      train.remote()
  """
          return template.format(user_code=user_code, job_id=uuid.uuid4().hex)
  ```

- [ ] Create Paperspace job templates
  ```python
  class PaperspaceOptimizer:
      def create_gradient_job_spec(self, user_code: str, requirements: ResourceRequirements):
          # Optimize for Gradient's job system
          return {
              "name": f"crucible-{uuid.uuid4().hex[:8]}",
              "projectId": self.project_id,
              "container": self._select_optimal_container(requirements),
              "machineType": self._select_machine_type(requirements),
              "command": "python /workspace/train.py",
              "workspace": {
                  "type": "git",
                  "uri": self._prepare_git_workspace(user_code)
              },
              "artifactDirectory": "/artifacts",
              "clusterId": self._select_cluster(requirements)  # Use private cluster for better pricing
          }
  ```

### Afternoon (4 hours): Notebook Integration
- [ ] Implement Colab integration
  ```python
  class ColabIntegration:
      def generate_colab_notebook(self, code: str, requirements: ResourceRequirements) -> str:
          # Generate .ipynb file
          notebook = {
              "cells": [
                  {
                      "cell_type": "markdown",
                      "source": ["# Crucible ML Job\n", "Auto-generated notebook"]
                  },
                  {
                      "cell_type": "code",
                      "source": [
                          "# Mount Google Drive for persistence\n",
                          "from google.colab import drive\n",
                          "drive.mount('/content/drive')\n",
                          "\n",
                          "# Install requirements\n",
                          "!pip install -q torch transformers datasets wandb"
                      ]
                  },
                  {
                      "cell_type": "code",
                      "source": [
                          "# Configure GPU\n",
                          "import torch\n",
                          "device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')\n",
                          "print(f'Using device: {device}')\n",
                          "if device.type == 'cuda':\n",
                          "    print(f'GPU: {torch.cuda.get_device_name()}')"
                      ]
                  },
                  {
                      "cell_type": "code",
                      "source": self._split_code_into_cells(code)
                  }
              ]
          }
          
          # Save to temporary file and generate shareable link
          return self._upload_to_colab(notebook)
  ```

- [ ] Create notebook execution monitoring
  ```python
  class NotebookMonitor:
      async def monitor_colab_execution(self, notebook_id: str):
          # Poll Colab API for execution status
          # Extract outputs and progress
          # Handle disconnections and session timeouts
  ```

## Day 5: Example Workloads & Documentation

### Morning (4 hours): nanoGPT on Each Provider
- [ ] Create provider-specific nanoGPT templates
  ```python
  # Modal template
  MODAL_NANOGPT = """
  @stub.function(gpu="a10g", timeout=7200)
  def train_nanogpt():
      from nanoGPT.model import GPT
      from nanoGPT.train import train
      
      # Configuration optimized for A10G (24GB)
      config = {
          'batch_size': 12,
          'block_size': 1024,
          'n_layer': 12,
          'n_head': 12,
          'n_embd': 768,
          'dropout': 0.0,
          'learning_rate': 6e-4,
          'max_iters': 5000,
          'eval_interval': 500,
          'eval_iters': 200,
      }
      
      # Train with automatic checkpointing
      train(config, checkpoint_callback=save_to_s3)
  """
  
  # Paperspace template
  PAPERSPACE_NANOGPT = """
  # gradient.yml
  name: nanoGPT-training
  container: pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime
  machineType: A4000
  command: |
    git clone https://github.com/karpathy/nanoGPT.git
    cd nanoGPT
    python train.py --config shakespeare_char --device cuda
  """
  
  # Colab template
  COLAB_NANOGPT = """
  # Auto-generated Colab notebook cells
  !git clone https://github.com/karpathy/nanoGPT.git
  %cd nanoGPT
  !pip install -r requirements.txt
  
  # Run training with Colab-specific optimizations
  !python train.py --config shakespeare_char --compile False
  """
  ```

### Afternoon (4 hours): Documentation & Best Practices
- [ ] Create provider comparison guide
  ```markdown
  ## External GPU Provider Comparison
  
  | Provider | Best For | GPU Options | Pricing | Pros | Cons |
  |----------|----------|-------------|---------|------|------|
  | Modal | Short jobs (<2hr) | T4, A10G, A100 | $/second | No idle time, auto-scaling | Cold starts |
  | Paperspace | Medium jobs (2-24hr) | A4000-A100 | $/hour | Persistent storage, notebooks | Queue times |
  | Lambda | Long jobs (>24hr) | A10, A100, H100 | $/hour | Best A100 pricing | Less automation |
  | Colab Pro+ | Interactive | T4, V100, A100 | $50/month | Familiar, free tier | Session limits |
  | Replicate | API serving | T4, A10 | $/second | Zero setup | Higher cost |
  ```

- [ ] Create migration guides
  - From local GPU to external service
  - From EC2 to managed platforms
  - From notebooks to production jobs

- [ ] Cost optimization playbook
  - When to use spot/preemptible instances
  - Batching strategies
  - Checkpoint frequency optimization
  - Multi-provider arbitrage

## Implementation Summary

### Backend Changes
```python
# evaluation_service.py
class ExternalGPUEvaluator:
    def __init__(self):
        self.providers = {
            'modal': ModalProvider(),
            'paperspace': PaperspaceProvider(),
            'lambda': LambdaLabsProvider(),
            'colab': ColabProvider(),
        }
        self.selector = ProviderSelector()
        self.storage = UnifiedStorage()
        
    async def submit_ml_job(self, request: MLJobRequest) -> MLJobResponse:
        # Detect requirements from code
        requirements = detect_requirements(request.code)
        
        # Select optimal provider
        provider = self.selector.select_optimal(requirements, request.constraints)
        
        # Prepare storage
        storage_config = await self.storage.prepare_job_storage(job_id, provider.name)
        
        # Submit job
        job_handle = await provider.submit_job(
            code=request.code,
            requirements=requirements,
            storage=storage_config
        )
        
        return MLJobResponse(
            job_id=job_handle.id,
            provider=provider.name,
            estimated_cost=provider.estimate_cost(requirements),
            status_url=f"/api/ml-jobs/{job_handle.id}/status"
        )
```

### Frontend Changes
```typescript
// MLJobSubmission.tsx
export function MLJobSubmission() {
  const [code, setCode] = useState(NANOGPT_TEMPLATE)
  const [requirements, setRequirements] = useState<Requirements>()
  const [selectedProvider, setSelectedProvider] = useState<string>()
  
  // Auto-detect requirements as user types
  useEffect(() => {
    const detected = detectRequirements(code)
    setRequirements(detected)
  }, [code])
  
  const handleSubmit = async () => {
    const response = await fetch('/api/ml-jobs', {
      method: 'POST',
      body: JSON.stringify({
        code,
        provider: selectedProvider,
        requirements
      })
    })
    
    const job = await response.json()
    navigate(`/ml-jobs/${job.job_id}`)
  }
  
  return (
    <div className="ml-job-submission">
      <CodeEditor value={code} onChange={setCode} />
      <RequirementsDisplay requirements={requirements} />
      <ProviderSelector 
        requirements={requirements}
        onSelect={setSelectedProvider}
      />
      <CostEstimate 
        provider={selectedProvider}
        requirements={requirements}
      />
      <button onClick={handleSubmit}>Submit ML Job</button>
    </div>
  )
}
```

## Success Criteria

1. **Can run nanoGPT on 3+ external providers**
   - Modal, Paperspace, and Lambda minimum
   - <5 minute setup time
   - Automatic dataset handling

2. **Cost transparency**
   - Real-time cost tracking
   - Provider comparison before submission
   - Budget alerts

3. **Better than local setup**
   - No CUDA installation
   - No GPU availability issues
   - Easier sharing of results

4. **Seamless experience**
   - One-click submission
   - Unified monitoring
   - Consistent artifact storage

## MVP Path (2 days)

If we want quick external GPU support:

### Day 1: Modal Integration Only
- [ ] Basic Modal provider
- [ ] Simple job submission
- [ ] Cost estimation
- [ ] Log streaming

### Day 2: Frontend & Testing
- [ ] Job submission UI
- [ ] Progress monitoring
- [ ] nanoGPT template
- [ ] End-to-end test

This gets us GPU support without infrastructure management!