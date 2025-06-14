#!/bin/bash
# Create security documentation folder and move relevant docs

echo "🔒 Creating security documentation folder"
echo "========================================"

cd docs

# Create security directory
echo "Creating security directory..."
mkdir -p security

# Move security-specific documents
echo "Moving security documents..."

# From implementation/
if [ -f "implementation/COMPREHENSIVE_SECURITY_GUIDE.md" ]; then
    echo "  - Moving COMPREHENSIVE_SECURITY_GUIDE.md"
    mv implementation/COMPREHENSIVE_SECURITY_GUIDE.md security/
fi

if [ -f "implementation/adversarial-testing-requirements.md" ]; then
    echo "  - Moving adversarial-testing-requirements.md"
    mv implementation/adversarial-testing-requirements.md security/
fi

# From architecture/
if [ -f "architecture/CONTAINER_SECURITY_REPORT.md" ]; then
    echo "  - Moving CONTAINER_SECURITY_REPORT.md"
    mv architecture/CONTAINER_SECURITY_REPORT.md security/
fi

# From deployment/
if [ -f "deployment/gvisor-setup-guide.md" ]; then
    echo "  - Moving gvisor-setup-guide.md"
    mv deployment/gvisor-setup-guide.md security/
fi

# Create security documentation index
echo "Creating security documentation index..."
cat > security/README.md << 'EOF'
# Security Documentation

This directory contains all security-related documentation for the Crucible Evaluation Platform.

## Core Security Documents

### 🛡️ Security Architecture
- [Comprehensive Security Guide](COMPREHENSIVE_SECURITY_GUIDE.md) - Multi-layer security architecture
- [Container Security Report](CONTAINER_SECURITY_REPORT.md) - Container isolation assessment

### 🔍 Testing & Validation
- [Adversarial Testing Requirements](adversarial-testing-requirements.md) - Security testing framework
- [gVisor Setup Guide](gvisor-setup-guide.md) - Kernel-level container isolation

## Security Layers

### 1. Container Isolation
- **gVisor**: User-space kernel for container isolation
- **Resource Limits**: CPU, memory, and I/O constraints
- **Seccomp Profiles**: System call filtering

### 2. Network Security
- **Network Policies**: Kubernetes-level isolation
- **Egress Control**: Preventing unauthorized connections
- **Service Mesh**: mTLS between services

### 3. Filesystem Security
- **Read-only Containers**: Immutable runtime
- **Volume Restrictions**: Limited persistent storage
- **Temporary Filesystems**: Ephemeral workspace

### 4. Process Security
- **Non-root Users**: Principle of least privilege
- **Capability Dropping**: Minimal Linux capabilities
- **PID Namespace**: Process isolation

## Security Checklist

- [ ] Enable gVisor runtime for untrusted code
- [ ] Configure resource limits (CPU, memory, disk)
- [ ] Set up network policies for isolation
- [ ] Enable audit logging for all actions
- [ ] Implement file system restrictions
- [ ] Drop unnecessary capabilities
- [ ] Use read-only root filesystem
- [ ] Enable security scanning in CI/CD

## Related Documentation

- [Platform Architecture](../architecture/PLATFORM_ARCHITECTURE.md)
- [Deployment Guide](../deployment/ec2-deployment-guide.md)
- [Testing Philosophy](../implementation/testing-philosophy.md)
EOF

# Update main docs README
echo "Updating main documentation index..."
cat > README.md << 'EOF'
# Crucible Platform Documentation

## 📁 Documentation Structure

### [🎯 METR Application](metr/)
- Job description and requirements
- Expected question formats
- **Start here:** [5-Day Submission Plan](planning/5-day-metr-submission-plan.md)

### [📋 Planning & Strategy](planning/)
- Development roadmaps
- MVP framework
- Lessons learned

### [🏗️ Architecture & Design](architecture/)
- System architecture
- Component design  
- Event-driven patterns

### [🔒 Security](security/)
- Comprehensive security guide
- Container isolation strategies
- Adversarial testing framework
- gVisor setup and configuration

### [🔧 Implementation](implementation/)
- Integration guides
- Testing philosophy
- Local development

### [🚀 Deployment](deployment/)
- AWS deployment
- Infrastructure setup
- CI/CD strategies

### [📖 Development](development/)
- Learning resources
- Development guides
- Collaboration patterns

### [📚 Knowledge Base](knowledge/)
- General programming guides
- Design patterns
- Best practices

### [🎤 Presentations](presentations/)
- Demo slides
- Architecture diagrams

### [🧬 Extreme MVP History](extreme-mvp/)
- Initial implementation journey
- Design decisions
- Historical context

## 🚀 Quick Start

1. **Understand the project**: Read [METR Job Description](metr/job-description.md)
2. **Review security**: Check [Comprehensive Security Guide](security/COMPREHENSIVE_SECURITY_GUIDE.md)
3. **See the plan**: Review [5-Day Submission Plan](planning/5-day-metr-submission-plan.md)
4. **Run locally**: Follow [Local Testing Guidelines](implementation/local-testing-guidelines.md)
5. **Deploy**: Use [EC2 Deployment Guide](deployment/ec2-deployment-guide.md)

## 🔑 Key Documents

- **Security**: [Comprehensive Security Guide](security/COMPREHENSIVE_SECURITY_GUIDE.md)
- **Architecture**: [Platform Architecture](architecture/PLATFORM_ARCHITECTURE.md)
- **Evolution**: [How We Got Here](extreme-mvp/README.md)
- **Testing**: [Adversarial Testing](security/adversarial-testing-requirements.md)
EOF

echo ""
echo "✅ Security documentation folder created!"
echo ""
echo "📋 Security docs now organized in docs/security/:"
echo "  - COMPREHENSIVE_SECURITY_GUIDE.md"
echo "  - CONTAINER_SECURITY_REPORT.md"
echo "  - adversarial-testing-requirements.md"
echo "  - gvisor-setup-guide.md"
echo ""
echo "The main documentation index has been updated to include the security section."