#!/bin/bash
# Organize documentation into logical categories

echo "📚 Organizing documentation structure"
echo "===================================="

cd docs

# Create organized subdirectories
echo "Creating category directories..."
mkdir -p {planning,design,implementation,deployment,development,presentations}

# Move files to appropriate categories
echo "Organizing documentation by category..."

# Planning & Strategy
echo "  📋 Planning documents..."
mv 5-day-metr-submission-plan.md planning/ 2>/dev/null || echo "    Already moved"
mv mvp-technical-debt-framework.md planning/ 2>/dev/null || echo "    Already moved"
mv next-steps-upgrade-roadmap.md planning/ 2>/dev/null || echo "    Already moved"
mv iterative-buildup.md planning/ 2>/dev/null || echo "    Already moved"
mv extreme-mvp-learnings.md planning/ 2>/dev/null || echo "    Already moved"

# Design & Architecture (merge with existing architecture/)
echo "  🏗️ Design documents..."
mv architectural-patterns-exploration.md architecture/ 2>/dev/null || echo "    Already moved"
mv EVENT_ARCHITECTURE_PATTERNS.md architecture/ 2>/dev/null || echo "    Already moved"
mv EVENT_BUS_ARCHITECTURE.md architecture/ 2>/dev/null || echo "    Already moved"
mv api-design-considerations.md architecture/ 2>/dev/null || echo "    Already moved"
mv queue-worker-architecture.md architecture/ 2>/dev/null || echo "    Already moved"
mv worker-orchestrator-design.md architecture/ 2>/dev/null || echo "    Already moved"
mv real-time-updates-comparison.md architecture/ 2>/dev/null || echo "    Already moved"
mv abstraction-evolution-summary.md architecture/ 2>/dev/null || echo "    Already moved"

# Implementation Guides
echo "  🔧 Implementation guides..."
mv extreme-mvp-implementation.md implementation/ 2>/dev/null || echo "    Already moved"
mv OPENAPI_INTEGRATION.md implementation/ 2>/dev/null || echo "    Already moved"
mv redis-message-broker-notes.md implementation/ 2>/dev/null || echo "    Already moved"
mv celery-vs-sqs-comparison.md implementation/ 2>/dev/null || echo "    Already moved"

# Security & Testing
echo "  🔒 Security documents..."
mv COMPREHENSIVE_SECURITY_GUIDE.md implementation/ 2>/dev/null || echo "    Already moved"
mv adversarial-testing-requirements.md implementation/ 2>/dev/null || echo "    Already moved"
mv testing-philosophy.md implementation/ 2>/dev/null || echo "    Already moved"
mv local-testing-guidelines.md implementation/ 2>/dev/null || echo "    Already moved"

# Deployment & Operations
echo "  🚀 Deployment documents..."
mv ec2-deployment-guide.md deployment/ 2>/dev/null || echo "    Already moved"
mv gvisor-setup-guide.md deployment/ 2>/dev/null || echo "    Already moved"
mv opentofu-vs-terraform.md deployment/ 2>/dev/null || echo "    Already moved"
mv git-tagging-strategy.md deployment/ 2>/dev/null || echo "    Already moved"

# Development & Learning
echo "  📖 Development guides..."
mv typescript-learning-guide.md development/ 2>/dev/null || echo "    Already moved"
mv human-ai-collaboration.md development/ 2>/dev/null || echo "    Already moved"
mv deriving-architecture-diagram.md development/ 2>/dev/null || echo "    Already moved"

# Presentations
echo "  🎤 Presentation materials..."
mv demo-slides*.md presentations/ 2>/dev/null || echo "    Already moved"

# METR-specific
echo "  🎯 METR-specific documents..."
mkdir -p metr
mv job-description.md metr/ 2>/dev/null || echo "    Already moved"
mv question-formats.md metr/ 2>/dev/null || echo "    Already moved"

# Create index for each category
echo "Creating category indexes..."

# Main docs README
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

### [🔧 Implementation](implementation/)
- Security guide
- Testing philosophy
- Integration details

### [🚀 Deployment](deployment/)
- AWS deployment
- Infrastructure setup
- CI/CD strategies

### [📖 Development](development/)
- Learning resources
- Development guides
- Collaboration patterns

### [🎤 Presentations](presentations/)
- Demo slides
- Architecture diagrams

### [🧬 Evolution History](evolution/)
- Component evolution
- Design decisions
- Historical context

## 🚀 Quick Start

1. **Understand the project**: Read [METR Job Description](metr/job-description.md)
2. **See the plan**: Review [5-Day Submission Plan](planning/5-day-metr-submission-plan.md)
3. **Run locally**: Follow [Local Testing Guidelines](implementation/local-testing-guidelines.md)
4. **Deploy**: Use [EC2 Deployment Guide](deployment/ec2-deployment-guide.md)

## 🔑 Key Documents

- **Security**: [Comprehensive Security Guide](implementation/COMPREHENSIVE_SECURITY_GUIDE.md)
- **Architecture**: [TRACE-AI Components](architecture/architectural-patterns-exploration.md)
- **Evolution**: [How We Got Here](architecture/abstraction-evolution-summary.md)
EOF

# Planning index
cat > planning/README.md << 'EOF'
# Planning & Strategy

## Documents

- [5-Day METR Submission Plan](5-day-metr-submission-plan.md) - Implementation timeline
- [MVP Technical Debt Framework](mvp-technical-debt-framework.md) - Managing technical debt
- [Next Steps Upgrade Roadmap](next-steps-upgrade-roadmap.md) - Future enhancements
- [Iterative Buildup](iterative-buildup.md) - Development approach
- [Extreme MVP Learnings](extreme-mvp-learnings.md) - Lessons from implementation
EOF

# Architecture index
cat > architecture/README.md << 'EOF'
# Architecture & Design

## Core Architecture
- [Architectural Patterns](architectural-patterns-exploration.md) - TRACE-AI component model
- [Event Architecture Patterns](EVENT_ARCHITECTURE_PATTERNS.md) - Event-driven design
- [Event Bus Design](EVENT_BUS_ARCHITECTURE.md) - Pub/sub implementation
- [Abstraction Evolution](abstraction-evolution-summary.md) - How architecture evolved

## Service Design
- [API Design Considerations](api-design-considerations.md) - REST API patterns
- [Queue Worker Architecture](queue-worker-architecture.md) - Task processing
- [Worker Orchestrator Design](worker-orchestrator-design.md) - Job coordination
- [Real-time Updates Comparison](real-time-updates-comparison.md) - WebSocket vs polling

## Infrastructure
- [Microservice Scaffolding](microservice-scaffolding.md) - Service separation
- [Dockerfile Status](dockerfiles-status.md) - Container architecture
EOF

echo ""
echo "✅ Documentation organized!"
echo ""
echo "📋 New structure:"
echo "  docs/"
echo "  ├── README.md           (main index)"
echo "  ├── metr/              (METR-specific)"
echo "  ├── planning/          (roadmaps, strategies)"
echo "  ├── architecture/      (design docs)"
echo "  ├── implementation/    (how-to guides)"
echo "  ├── deployment/        (infrastructure)"
echo "  ├── development/       (dev resources)"
echo "  ├── presentations/     (slides, demos)"
echo "  └── evolution/         (historical)"
echo ""
echo "Each category has its own README with an index of documents."