# METR Evaluation Platform - Component Upgrade Roadmap

## Current State
You've successfully deployed basic AWS infrastructure with OpenTofu:
- ✅ EC2 instance (t2.micro) with Docker/gVisor setup
- ✅ API Gateway + Lambda for evaluation submission
- ✅ SQS queues (main + DLQ)
- ✅ Security groups (⚠️ SSH open to 0.0.0.0/0)

## Immediate Security Tasks
### 🔴 Priority 1: SSH Security
1. **Configure SSH Key Pair**
   - Uncomment lines 55-58 in `ec2.tf`
   - Add your public key: `~/.ssh/id_rsa.pub`
   - Redeploy with `tofu apply`

2. **Restrict SSH Access** (Choose one):
   - Option A: Your IP only - `cidr_blocks = ["YOUR_IP/32"]`
   - Option B: Use AWS Systems Manager Session Manager
   - Option C: Set up VPN/Bastion host

## Component Upgrade Paths

### 1. Execution Engine Evolution
**Current**: EC2 with Docker installed

**Level 1 → 2**: Deploy Extreme MVP
```bash
# SSH into instance and run
scp src/platform/extreme_mvp.py ubuntu@44.246.137.198:~/
ssh ubuntu@44.246.137.198
python3 extreme_mvp.py
```

**Level 2 → 3**: Add Docker Isolation
```bash
# Deploy Docker version
scp src/platform/extreme_mvp_docker.py ubuntu@44.246.137.198:~/
python3 extreme_mvp_docker.py
```

**Level 3 → 4**: Add Monitoring
```bash
# Deploy monitoring version with SSE
scp src/platform/extreme_mvp_monitoring_v3.py ubuntu@44.246.137.198:~/
python3 extreme_mvp_monitoring_v3.py
```

**Level 4 → 5**: Add Queue
```bash
# Deploy queue version
scp src/platform/extreme_mvp_queue.py ubuntu@44.246.137.198:~/
python3 extreme_mvp_queue.py
```

**Level 5 → 6**: Production Safety (gVisor)
```bash
# gVisor already installed via user_data
scp src/platform/extreme_mvp_gvisor.py ubuntu@44.246.137.198:~/
python3 extreme_mvp_gvisor.py
```

### 2. API Evolution
**Current**: Lambda function (basic)

**Next Steps**:
1. **Connect Lambda to SQS** - Make it actually queue evaluations
2. **Add validation** - Check Python syntax before queuing
3. **Add authentication** - API keys or JWT
4. **Rate limiting** - Prevent abuse
5. **Migrate to FastAPI** - If need WebSocket/SSE

### 3. Queue System Evolution
**Current**: SQS created but not connected

**Next Steps**:
1. **Wire Lambda → SQS** - Actually use the queue
2. **Create worker** - Process messages from queue
3. **Add DLQ handling** - Process failed evaluations
4. **Add visibility** - CloudWatch metrics
5. **Consider Celery** - If need complex workflows

### 4. Frontend Evolution
**Current**: None (just embedded HTML in Python)

**Next Steps**:
1. **Deploy React starter** - Basic submission form
2. **Add real-time updates** - SSE/WebSocket client
3. **Add authentication UI** - Login/logout
4. **Build dashboard** - Queue status, results
5. **Add visualizations** - Charts, metrics

### 5. Monitoring Evolution
**Current**: Basic CloudWatch

**Next Steps**:
1. **Add application metrics** - Custom CloudWatch metrics
2. **Deploy Prometheus** - On EC2 or separate instance
3. **Add Grafana** - Visualization dashboards
4. **Set up alerts** - SNS for critical events
5. **Add distributed tracing** - X-Ray or Jaeger

### 6. Storage Evolution
**Current**: None

**Next Steps**:
1. **Add S3 bucket** - Store evaluation results
2. **Add RDS PostgreSQL** - Evaluation metadata
3. **Add caching layer** - ElastiCache Redis
4. **Add backup strategy** - Automated snapshots
5. **Add data lifecycle** - Archive old results

### 7. Security Evolution
**Current**: Basic Docker isolation

**Next Steps**:
1. **Enable gVisor** - Already installed, need to use
2. **Add network policies** - Restrict container traffic
3. **Add secrets management** - AWS Secrets Manager
4. **Add audit logging** - CloudTrail + custom
5. **Add WAF** - Protect API Gateway

### 8. Infrastructure Evolution
**Current**: Single EC2 instance

**Next Steps**:
1. **Add ALB** - Load balancer for multiple instances
2. **Add Auto Scaling** - Handle load spikes
3. **Move to ECS** - Container orchestration
4. **Migrate to EKS** - Full Kubernetes
5. **Multi-region** - DR and global presence

## Recommended Learning Path

### Week 1: Security & Basic Functionality
1. Fix SSH security (Day 1)
2. Deploy extreme MVP progression (Days 2-3)
3. Connect Lambda to SQS (Days 4-5)

### Week 2: Real Platform Features
1. Create SQS worker (Days 1-2)
2. Add basic React frontend (Days 3-4)
3. Add S3 storage (Day 5)

### Week 3: Production Readiness
1. Add monitoring/metrics (Days 1-2)
2. Add authentication (Days 3-4)
3. Load testing & optimization (Day 5)
4. **Nice to have**: Set up Docker dev/prod parity (see [Docker Dev/Prod Parity Guide](../development/docker-dev-prod-parity.md))

### Week 4: Advanced Features
1. Move to ECS/EKS (Days 1-3)
2. Add advanced security (Days 4-5)

## Quick Experiments (1-2 hours each)

1. **Test gVisor isolation**:
   ```bash
   docker run --runtime=runsc python:3.11-slim python -c "print('Hello from gVisor!')"
   ```

2. **Test SQS manually**:
   ```bash
   aws sqs send-message --queue-url YOUR_QUEUE_URL --message-body "test"
   aws sqs receive-message --queue-url YOUR_QUEUE_URL
   ```

3. **Deploy simple frontend**:
   ```bash
   # On EC2 instance
   python3 -m http.server 8001
   # Create index.html with evaluation form
   ```

4. **Test Lambda locally**:
   ```bash
   # Use SAM CLI
   sam local start-api
   ```

## Architecture Decision Records (ADRs)

Document each decision:
1. Why you chose this path
2. What alternatives you considered
3. What trade-offs you accepted
4. When you might reconsider

Example: "Chose SQS over Celery because managed service requires less operational overhead for MVP. Will reconsider when we need complex task dependencies."

## Interview Talking Points

For each upgrade, be ready to discuss:
1. **Why this order?** - Risk mitigation, user value, learning
2. **Security considerations** - What threats each level addresses
3. **Scalability path** - How each piece enables growth
4. **Cost implications** - AWS pricing at each level
5. **Operational complexity** - What monitoring/maintenance needed

## Next Immediate Action

**Recommended**: Fix SSH security first, then deploy the extreme MVP series on your EC2 instance. This gives you:
1. Secure access to your infrastructure
2. Working code to demonstrate
3. Clear evolution story for interviews
4. Hands-on experience with the security challenges