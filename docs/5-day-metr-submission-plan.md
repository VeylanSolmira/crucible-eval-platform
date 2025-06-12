# 5-Day METR Submission Development Plan

## Goal
Create an impressive demonstration of the Crucible Evaluation Platform that showcases:
1. **Deep understanding of AI safety challenges**
2. **Strong platform engineering skills**
3. **Security-first mindset**
4. **Clear communication of technical decisions**

## What METR Will Look For
- **Security Architecture**: Multiple isolation layers, defense-in-depth
- **Real Implementation**: Working code, not just diagrams
- **Safety Mindset**: Understanding of AI evaluation risks
- **Production Thinking**: Scalability, monitoring, reliability
- **Clear Documentation**: Explaining the "why" behind decisions

## Day 1: Foundation & Core Security (8-10 hours)

### Morning (4 hours)
1. **Fix SSH Security** (30 min) ✅
   ```bash
   # Edit infrastructure/terraform/ec2.tf
   # Uncomment key_pair resource (lines 55-58)
   # Add your public key
   # Change CIDR to your IP: cidr_blocks = ["YOUR_IP/32"]
   tofu apply
   ```

2. **Deploy Evolution Series** (2 hours) ✅ (Partial - Skipped individual file tests)
   ```bash
   # Copy all evolution files to EC2
   scp evolution/*.py ubuntu@44.246.137.198:~/  # ✅ Used evolution-minimal.tar.gz instead
   
   # SSH in and test each version
   ssh ubuntu@44.246.137.198
   python3 extreme_mvp.py  # Verify it works  # ⏭️ Skipped
   python3 extreme_mvp_docker.py  # Test Docker isolation  # ⏭️ Skipped
   # ✅ Went directly to extreme_mvp_frontier_events.py
   ```

3. **Verify gVisor** (1.5 hours) ✅
   ```bash
   # Test gVisor is working
   docker run --runtime=runsc hello-world  # ✅ Confirmed working
   
   # Deploy gVisor version
   python3 extreme_mvp_gvisor.py
   ```

### Afternoon (4-6 hours)
4. **Connect Lambda to SQS** (3 hours)
   - Update Lambda to actually enqueue evaluations
   - Create basic SQS worker on EC2
   - Test end-to-end flow

5. **Document Security Decisions** (1 hour) ⚡ (Partial)
   - ✅ Created `COMPREHENSIVE_SECURITY_GUIDE.md`
   - ✅ Documented all security layers and decisions
   - ✅ Added extensive security checklist with ratings
   - ⏸️ Review and update based on implementation progress

### Day 1 Deliverables
- ✅ Secure EC2 access
- ✅ Working evolution demos
- ✅ gVisor runtime verified
- ✅ Basic queue processing
- ✅ Created modular component architecture (extreme_mvp_frontier_events.py)

## Day 2: Monitoring & Observability (8-10 hours)

### Morning (4 hours)
1. **Deploy Monitoring Version** (2 hours)
   ```bash
   # Deploy SSE version
   python3 extreme_mvp_monitoring_v3.py
   
   # Add systemd service for auto-start
   sudo systemctl enable evaluation-platform
   ```

2. **Add CloudWatch Integration** (2 hours)
   - Custom metrics for evaluation status
   - Log aggregation
   - Basic alerting

### Afternoon (4-6 hours)
3. **Create Safety Test Suite** (3 hours)
   - Network escape attempts
   - Resource exhaustion tests
   - File system probing
   - Show these FAIL safely

4. **Add Monitoring Dashboard** (2 hours)
   - Simple HTML dashboard showing:
     - Current evaluations
     - Resource usage
     - Safety violations

### Day 2 Deliverables
- ✅ Real-time monitoring working
- ✅ Safety test suite demonstrating containment
- ✅ CloudWatch metrics flowing
- ✅ Basic dashboard

## Day 3: Professional Frontend (10-12 hours)

### Morning (5 hours)
1. **React Frontend Setup** (2 hours)
   ```bash
   cd frontend
   npm create vite@latest metr-dashboard -- --template react-ts
   npm install @mui/material @emotion/react @emotion/styled
   npm install socket.io-client axios
   ```

2. **Core Components** (3 hours)
   - Evaluation submission form
   - Real-time status display
   - Log viewer with syntax highlighting
   - Safety alert notifications

### Afternoon (5-7 hours)
3. **WebSocket Integration** (3 hours)
   - Connect to backend SSE/WebSocket
   - Live evaluation updates
   - Resource usage graphs

4. **Polish UI/UX** (2 hours)
   - METR-inspired clean design
   - Responsive layout
   - Loading states
   - Error handling

### Day 3 Deliverables
- ✅ Professional React frontend
- ✅ Real-time updates working
- ✅ Clean, intuitive UI
- ✅ Mobile responsive

## Day 4: Advanced Safety & Demo Scenarios (10-12 hours)

### Morning (5 hours)
1. **Multi-Layer Security Demo** (3 hours)
   Create evaluation scenarios that show:
   - Docker isolation (filesystem)
   - Network policies (no egress)
   - Resource limits (CPU/memory)
   - gVisor protection (syscall filtering)

2. **Kubernetes Manifests** (2 hours)
   - Even if not deployed, show production thinking
   - Network policies
   - Pod security policies
   - Resource quotas

### Afternoon (5-7 hours)
3. **Create Attack Scenarios** (4 hours)
   Build demo evaluations that try to:
   - Exfiltrate data (blocked by network policy)
   - Exhaust resources (killed by limits)
   - Escape container (blocked by gVisor)
   - Hide capabilities (detected by monitoring)

4. **Performance Testing** (2 hours)
   - Load test with concurrent evaluations
   - Document scaling limits
   - Show queue handling overload

### Optional Enhancement: Private Subnet Migration (2-3 hours)
If ahead of schedule, migrate to production-grade networking:

```bash
# Deploy Session Manager infrastructure
cd infrastructure/terraform
cp session-manager-setup.tf.example session-manager-setup.tf
tofu apply

# Access without SSH:
aws ssm start-session --target i-xxxxx
```

**Benefits to highlight:**
- Zero network attack surface (no SSH)
- Complete audit trail via CloudTrail
- Production-ready architecture
- Shows advanced AWS security knowledge

**Implementation includes:**
- VPC with public/private subnets
- NAT Gateway for controlled egress
- Session Manager for access
- No public IPs or SSH keys

This demonstrates to METR that you understand:
- Defense in depth principles
- Production vs development trade-offs
- Modern cloud security practices
- How to prevent AI models from network attacks

### Day 4 Deliverables
- ✅ Compelling safety demonstrations
- ✅ Production-ready K8s configs
- ✅ Performance benchmarks
- ✅ Attack scenario results
- ✅ (Optional) Private subnet architecture

## Day 5: Polish & Presentation (8-10 hours)

### Morning (4 hours)
1. **Comprehensive Documentation** (2 hours)
   - Update README with clear setup instructions
   - Architecture decisions with TRACE-AI rationale
   - Security architecture deep-dive
   - API documentation

2. **Demo Video** (2 hours)
   - 5-minute walkthrough showing:
     - Submitting an evaluation
     - Real-time monitoring
     - Safety features in action
     - Architecture overview

### Afternoon (4-6 hours)
3. **Code Cleanup** (2 hours)
   - Remove debug code
   - Add meaningful comments
   - Ensure consistent style
   - Run linters

4. **Interview Prep Package** (2 hours)
   Create `INTERVIEW_NOTES.md` with:
   - Key architectural decisions
   - Trade-offs made and why
   - Future improvements roadmap
   - Answers to likely questions

### Day 5 Deliverables
- ✅ Polished, professional codebase
- ✅ Comprehensive documentation
- ✅ Demo video
- ✅ Interview talking points

## Minimum Viable Submission (If Time Constrained)

If you can't complete everything, prioritize:

### Must Have (3 days)
1. **Working gVisor isolation** - Shows you understand the core safety requirement
2. **Evolution demos** - Shows iterative thinking and learning
3. **Basic monitoring** - Shows observability mindset
4. **Clear documentation** - Shows communication skills

### Nice to Have (2 days)
1. React frontend (can use embedded HTML)
2. Kubernetes manifests (can be theoretical)
3. Performance testing
4. Video demo

## What Makes This Impressive

1. **It Actually Works** - Not just theory, real running code
2. **Security Depth** - Multiple layers, each explained
3. **Evolution Story** - Shows how you think and learn
4. **Production Thinking** - Monitoring, scaling, operations
5. **AI Safety Focus** - Understands the unique challenges

## Key Talking Points for METR

1. **"I built this to explore how to safely evaluate potentially dangerous AI"**
   - Shows alignment with their mission

2. **"The evolution approach mirrors how I think about architecture"**
   - Start simple, learn, improve based on real needs

3. **"Each security layer addresses a specific threat model"**
   - Docker: filesystem isolation
   - Network policies: data exfiltration
   - gVisor: kernel exploitation
   - Monitoring: behavioral anomalies

4. **"I chose boring technology for critical paths"**
   - Python/Docker/Kubernetes are proven
   - Innovation in composition, not components

5. **"This is designed to be maintainable by a team"**
   - Clear abstractions
   - Comprehensive tests
   - Good documentation

## Daily Checklist

### End of Each Day
- [ ] Commit code with meaningful messages
- [ ] Update documentation
- [ ] Test everything still works
- [ ] Note what you learned
- [ ] Prepare next day's plan

### Before Submission
- [ ] All tests pass
- [ ] Documentation is complete
- [ ] Demo video is recorded
- [ ] Code is clean and commented
- [ ] You can explain every decision

## Remember
METR cares more about **thoughtful engineering** than feature count. A well-documented, security-focused MVP with clear reasoning beats a feature-rich but poorly explained system.