# ML Workload Support Sprint: Running Real AI Training Jobs

## Goal: Enable Real ML Workloads like nanoGPT on Crucible Platform

### Context
- We have GPU infrastructure documented in [`infrastructure/terraform/GPU_SETUP.md`](../../infrastructure/terraform/GPU_SETUP.md)
- Instance types available: g4dn.xlarge ($0.526/hr), g5.2xlarge ($2.012/hr), etc.
- Current platform runs CPU-only containers with 512MB RAM limits
- Need to support multi-hour training runs with GPU access

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

## Day 1: Resource Detection & Backend Support

### Morning (4 hours): Dynamic Resource Configuration
- [ ] Create resource requirement detection
  - [ ] Parse imports to detect GPU needs (torch.cuda, tensorflow)
  - [ ] Analyze code for memory patterns (large arrays, model sizes)
  - [ ] Estimate runtime from code complexity
  - [ ] Suggest appropriate resource tier
- [ ] Implement resource tiers in backend
  - [ ] CPU_SMALL: Current default (512MB, 30s timeout)
  - [ ] CPU_LARGE: 4GB RAM, 10min timeout
  - [ ] GPU_SMALL: g4dn.xlarge, 16GB VRAM, 2hr timeout
  - [ ] GPU_MEDIUM: g4dn.2xlarge, 16GB VRAM, 8hr timeout
  - [ ] GPU_LARGE: g5.2xlarge, 24GB VRAM, 24hr timeout
- [ ] Update Docker executor for GPU support
  - [ ] Add `--gpus all` flag for GPU containers
  - [ ] Use NVIDIA runtime when available
  - [ ] Mount /dev/nvidia* devices
  - [ ] Set appropriate CUDA environment variables

### Afternoon (4 hours): Container Image Management
- [ ] Create GPU-enabled container images
  - [ ] Base image: pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime
  - [ ] Add common ML libraries (transformers, datasets, wandb)
  - [ ] Include Jupyter kernel for notebook-style execution
  - [ ] Pre-download common models to reduce startup time
- [ ] Implement image selection logic
  ```python
  def select_container_image(code: str, resource_tier: str) -> str:
      if 'torch' in code and resource_tier.startswith('GPU'):
          return 'crucible/ml-pytorch-gpu:latest'
      elif 'tensorflow' in code and resource_tier.startswith('GPU'):
          return 'crucible/ml-tensorflow-gpu:latest'
      else:
          return 'crucible/python:3.11-slim'
  ```
- [ ] Container registry management
  - [ ] Push GPU images to ECR
  - [ ] Implement image caching on GPU instances
  - [ ] Version management for ML frameworks

## Day 2: Frontend Resource Selection

### Morning (4 hours): Resource Selection UI
- [ ] Add resource tier selector to submission form
  ```typescript
  interface ResourceTier {
    id: string
    name: string
    description: string
    cpu: string
    memory: string
    gpu?: string
    maxRuntime: string
    costPerHour: number
  }
  ```
- [ ] Create resource recommendation component
  - [ ] "Detected GPU usage - recommend GPU_SMALL tier"
  - [ ] Show estimated cost for selected runtime
  - [ ] Warning for expensive options
  - [ ] Comparison table of tiers
- [ ] Add advanced configuration panel
  - [ ] Custom timeout override
  - [ ] Memory limit override
  - [ ] GPU memory limit
  - [ ] Environment variable injection
- [ ] Implement cost calculator
  - [ ] Real-time cost estimation
  - [ ] Budget alerts
  - [ ] Usage history tracking

### Afternoon (4 hours): Progress Monitoring for Long Jobs
- [ ] Enhanced progress tracking
  - [ ] Training epoch progress
  - [ ] Loss/metric graphs (parse from stdout)
  - [ ] GPU utilization graphs
  - [ ] Memory usage over time
- [ ] Checkpoint management UI
  - [ ] List saved checkpoints
  - [ ] Download checkpoint files
  - [ ] Resume from checkpoint
  - [ ] Auto-save on timeout
- [ ] Log streaming improvements
  - [ ] Structured log parsing (detect epochs, loss values)
  - [ ] TensorBoard integration
  - [ ] Collapsible log sections
  - [ ] Search within logs

## Day 3: Storage & Data Management

### Morning (4 hours): Persistent Storage
- [ ] Implement workspace storage
  - [ ] S3 bucket per user/project
  - [ ] Mount as volume in containers
  - [ ] 100GB default quota
  - [ ] Automatic cleanup after 30 days
- [ ] Dataset management
  - [ ] Common datasets pre-cached (MNIST, CIFAR, etc.)
  - [ ] Custom dataset upload (up to 10GB)
  - [ ] Dataset versioning
  - [ ] Shared dataset library
- [ ] Output artifact handling
  - [ ] Auto-save models to S3
  - [ ] Generate shareable links
  - [ ] Model card generation
  - [ ] Training report export

### Afternoon (4 hours): Integration with ML Tools
- [ ] Weights & Biases integration
  - [ ] Auto-inject W&B API key
  - [ ] Link to W&B dashboard
  - [ ] Capture system metrics
  - [ ] Run comparison tools
- [ ] TensorBoard support
  - [ ] Proxy TensorBoard through nginx
  - [ ] Auto-start for detected logs
  - [ ] Multi-run comparison
  - [ ] Export visualizations
- [ ] MLflow compatibility
  - [ ] Track experiments
  - [ ] Model registry integration
  - [ ] Metric comparison
  - [ ] Artifact storage

## Day 4: GPU Infrastructure & Scheduling

### Morning (4 hours): GPU Instance Management
- [ ] Implement GPU instance pool
  - [ ] Pre-warm instances for common tiers
  - [ ] Auto-scale based on queue depth
  - [ ] Spot instance management
  - [ ] Cost optimization logic
- [ ] Job scheduling system
  - [ ] Queue prioritization (FIFO, priority, fair-share)
  - [ ] Resource reservation
  - [ ] Preemption for high-priority jobs
  - [ ] Multi-GPU job support
- [ ] Instance health monitoring
  - [ ] GPU health checks
  - [ ] Automatic instance replacement
  - [ ] Driver version validation
  - [ ] CUDA compatibility checks

### Afternoon (4 hours): Cost Management
- [ ] Implement cost controls
  - [ ] Per-user budgets
  - [ ] Project allocations
  - [ ] Automatic job termination at budget limit
  - [ ] Cost alerts via email/Slack
- [ ] Usage reporting
  - [ ] Daily/weekly/monthly reports
  - [ ] Cost breakdown by resource type
  - [ ] Optimization recommendations
  - [ ] Chargeback/showback support
- [ ] Spot instance optimization
  - [ ] Automatic fallback to on-demand
  - [ ] Checkpointing before interruption
  - [ ] Price-aware scheduling
  - [ ] Multi-region support

## Day 5: Example Workloads & Documentation

### Morning (4 hours): nanoGPT Integration
- [ ] Create nanoGPT template
  ```python
  # Pre-configured nanoGPT training template
  # - Shakespeare dataset pre-loaded
  # - Optimal hyperparameters for g4dn.xlarge
  # - Checkpoint every 1000 steps
  # - TensorBoard logging enabled
  ```
- [ ] Implement common ML templates
  - [ ] Image classification (ResNet on CIFAR-10)
  - [ ] Text generation (GPT-2 fine-tuning)
  - [ ] Diffusion model training
  - [ ] BERT fine-tuning
- [ ] Benchmark suite
  - [ ] Performance baselines for each GPU tier
  - [ ] Cost/performance optimization guide
  - [ ] Scaling recommendations
  - [ ] Framework comparisons

### Afternoon (4 hours): Documentation & Examples
- [ ] Create ML researcher guide
  - [ ] Getting started with GPU jobs
  - [ ] Cost optimization tips
  - [ ] Common pitfalls and solutions
  - [ ] Migration from Colab/local
- [ ] API documentation for ML workflows
  - [ ] Programmatic job submission
  - [ ] Result retrieval
  - [ ] Checkpoint management
  - [ ] Metrics extraction
- [ ] Integration examples
  - [ ] CI/CD for model training
  - [ ] Hyperparameter sweeps
  - [ ] A/B testing models
  - [ ] Production deployment pipeline

## Implementation Details

### Backend Changes
```python
# evaluation_service.py
class ResourceTier(Enum):
    CPU_SMALL = {
        "memory": "512Mi",
        "cpu": "0.5",
        "timeout": 30,
        "cost_per_hour": 0.02
    }
    GPU_SMALL = {
        "memory": "16Gi", 
        "cpu": "4",
        "gpu": "1",
        "timeout": 7200,
        "cost_per_hour": 0.526,
        "instance_type": "g4dn.xlarge"
    }

async def create_ml_container(code: str, tier: ResourceTier):
    if tier.value.get("gpu"):
        return await docker_client.containers.run(
            image="crucible/ml-pytorch-gpu:latest",
            command=["python", "-c", code],
            device_requests=[
                docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
            ],
            environment={
                "CUDA_VISIBLE_DEVICES": "0",
                "PYTHONUNBUFFERED": "1"
            },
            mem_limit=tier.value["memory"],
            nano_cpus=int(float(tier.value["cpu"]) * 1e9),
            volumes={
                f"/mnt/workspace/{user_id}": {"bind": "/workspace", "mode": "rw"}
            }
        )
```

### Frontend Changes
```typescript
// ResourceSelector.tsx
export function ResourceSelector({ 
  code, 
  onSelect 
}: { 
  code: string, 
  onSelect: (tier: ResourceTier) => void 
}) {
  const recommendation = useResourceRecommendation(code);
  
  return (
    <div className="resource-selector">
      <Alert>
        {recommendation && (
          <p>Detected {recommendation.reason}. Recommended: {recommendation.tier}</p>
        )}
      </Alert>
      
      <RadioGroup onChange={onSelect}>
        {RESOURCE_TIERS.map(tier => (
          <Radio key={tier.id} value={tier}>
            <div className="tier-option">
              <h4>{tier.name}</h4>
              <p>{tier.description}</p>
              <div className="tier-specs">
                <span>CPU: {tier.cpu}</span>
                <span>Memory: {tier.memory}</span>
                {tier.gpu && <span>GPU: {tier.gpu}</span>}
                <span>Max Runtime: {tier.maxRuntime}</span>
              </div>
              <div className="tier-cost">
                ${tier.costPerHour}/hour
              </div>
            </div>
          </Radio>
        ))}
      </RadioGroup>
    </div>
  );
}
```

## MVP for ML Workloads (3 days)

If we want to quickly support nanoGPT:

### Day 1: Minimal GPU Support
- [ ] Add GPU_SMALL tier to backend
- [ ] Create pytorch-gpu container image
- [ ] Update executor for GPU flag
- [ ] Basic GPU detection in frontend

### Day 2: Storage & Monitoring
- [ ] S3 workspace mounting
- [ ] Extended timeout support (2+ hours)
- [ ] Basic progress tracking
- [ ] Checkpoint download

### Day 3: nanoGPT Template
- [ ] Pre-configured nanoGPT example
- [ ] Cost calculator
- [ ] Documentation
- [ ] Test run with Shakespeare

## Success Criteria

1. **Can run nanoGPT training to completion**
   - 2-hour training job succeeds
   - Checkpoints are saved
   - Can resume from checkpoint

2. **Researchers find it easier than local setup**
   - No CUDA installation issues
   - Datasets pre-available
   - Results easily shareable

3. **Cost-effective compared to Colab Pro**
   - Clear cost visibility
   - Spot instance savings
   - Only pay for actual usage

4. **Integrates with existing workflows**
   - Git integration
   - CI/CD compatibility
   - Standard ML tools work

## Key References

- [GPU Instance Types & Pricing](../../infrastructure/terraform/GPU_SETUP.md)
- [Current Executor Implementation](../../executor-service/app.py)
- [Docker GPU Support](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/user-guide.html)
- [nanoGPT Requirements](https://github.com/karpathy/nanoGPT)

## Next Steps After This Sprint

1. **Multi-node training support** (distributed PyTorch)
2. **Model serving integration** (deploy trained models)
3. **AutoML capabilities** (hyperparameter search)
4. **Federation support** (privacy-preserving training)