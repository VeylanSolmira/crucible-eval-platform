#!/bin/bash
# Move documentation from /src to appropriate locations

echo "📚 Reorganizing documentation from /src"
echo "======================================"

# Create architecture docs directory
mkdir -p docs/architecture

# Move src-level documentation
echo "Moving documentation files..."

# DOCKERFILES.md - architecture documentation
if [ -f "src/DOCKERFILES.md" ]; then
    echo "  - Moving DOCKERFILES.md to docs/architecture/"
    mv src/DOCKERFILES.md docs/architecture/dockerfiles-status.md
fi

# MAIN_PY_FILES.md - architecture documentation
if [ -f "src/MAIN_PY_FILES.md" ]; then
    echo "  - Moving MAIN_PY_FILES.md to docs/architecture/"
    mv src/MAIN_PY_FILES.md docs/architecture/microservice-scaffolding.md
fi

# src/README.md - should describe the source structure
if [ -f "src/README.md" ]; then
    echo "  - Checking src/README.md content..."
    # This one might be okay if it describes the source structure
    # Let's update it to be more focused
    cat > src/README.md << 'EOF'
# Source Code Structure

This directory contains the Crucible Evaluation Platform source code.

## Quick Start

```bash
cd platform
python extreme_mvp_frontier_events.py --help
```

## Directory Structure

- `platform/` - The monolithic platform (current implementation)
- `execution-engine/` - Code execution components
- `event-bus/` - Event coordination system
- `security-scanner/` - Security testing framework
- `shared/` - Shared utilities and base classes
- `lambda/` - AWS Lambda functions
- `reference/` - Historical implementations
- `future-services/` - Services planned for future development

For detailed architecture documentation, see `/docs/architecture/`
EOF
    echo "  - Updated src/README.md to be concise"
fi

# EVOLUTION_TREE.md - belongs with reference implementations
if [ -f "src/reference/EVOLUTION_TREE.md" ]; then
    echo "  - EVOLUTION_TREE.md is correctly placed in reference/"
fi

# EVENT_BUS_ARCHITECTURE.md if it exists
if [ -f "src/event-bus/EVENT_BUS_ARCHITECTURE.md" ]; then
    echo "  - Moving EVENT_BUS_ARCHITECTURE.md to docs/architecture/"
    mv src/event-bus/EVENT_BUS_ARCHITECTURE.md docs/architecture/event-bus-design.md
fi

# Create an index for architecture docs
echo "Creating architecture documentation index..."
cat > docs/architecture/README.md << 'EOF'
# Architecture Documentation

This directory contains architectural decisions and design documentation for the Crucible platform.

## Documents

### Platform Architecture
- [Source Code Structure](../../src/README.md) - Overview of `/src` directory
- [Event Bus Design](event-bus-design.md) - Event-driven architecture patterns
- [Microservice Scaffolding](microservice-scaffolding.md) - How components become services
- [Dockerfile Status](dockerfiles-status.md) - Current state of containerization

### Design Decisions
- [Component Architecture](../architectural-patterns-exploration.md) - TRACE-AI components
- [Security Architecture](../COMPREHENSIVE_SECURITY_GUIDE.md) - Multi-layer security
- [Evolution Summary](../evolution/abstraction-evolution-summary.md) - How we got here

### Migration Paths
- [Monolith to Microservices](microservice-scaffolding.md) - Future service separation
- [Real-time Updates Evolution](../evolution/real-time-updates-evolution.md) - Polling to WebSockets
- [Next Steps Roadmap](../next-steps-upgrade-roadmap.md) - Platform evolution

## Key Principles

1. **Start Simple**: Monolithic first, microservices when needed
2. **Clear Boundaries**: Each component has a single responsibility  
3. **Event-Driven**: Loose coupling through events
4. **Security First**: Multiple isolation layers
5. **Migration Ready**: Clear path to scale

See the [5-Day METR Plan](../5-day-metr-submission-plan.md) for implementation timeline.
EOF

echo ""
echo "✅ Documentation reorganized!"
echo ""
echo "📋 Summary:"
echo "  - Architecture docs moved to docs/architecture/"
echo "  - src/README.md updated to focus on source structure"
echo "  - Created architecture documentation index"
echo ""
echo "Documentation is now properly organized:"
echo "  - /docs - All documentation"
echo "  - /src - Only source code (with minimal README)"
echo "  - Service directories - No docs, just code"