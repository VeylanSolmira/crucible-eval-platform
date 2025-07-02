# When to Modularize: A Decision Framework

## Overview

This document provides guidance on when to break monolithic code into modular components, using the execution engines as a case study.

## Current State: Execution Engines

The execution engines are currently in a single file (`execution.py`, ~400 lines) containing:
- `ExecutionEngine` (base class)
- `SubprocessEngine` (unsafe, dev only)
- `DockerEngine` (containerized)
- `GVisorEngine` (production security)

## When to Keep Monolithic

Keep code in a single file when:

1. **File size is manageable** (< 500-700 lines)
2. **Components share significant code** (utilities, patterns)
3. **You're in MVP/prototype phase**
4. **Team is small** (< 5 developers)
5. **Components are tightly related** (always used together)

## When to Modularize

Consider splitting when you hit **2 or more** of these triggers:

### 📏 Size Triggers
- [ ] File exceeds 1000 lines
- [ ] Any single class exceeds 300 lines
- [ ] More than 5 major classes/components
- [ ] IDE performance degrades

### 🔧 Complexity Triggers
- [ ] Different components need different dependencies
- [ ] Components have conflicting requirements
- [ ] Testing becomes unwieldy (> 500 lines of tests)
- [ ] Circular dependency risks

### 👥 Team Triggers
- [ ] Multiple developers frequently conflict on the file
- [ ] Different teams own different components
- [ ] Need to assign code ownership
- [ ] Component expertise is specialized

### 🚀 Scale Triggers
- [ ] Components need independent deployment
- [ ] Different scaling requirements
- [ ] Different update frequencies
- [ ] Different security contexts

### 🏗️ Architecture Triggers
- [ ] Moving to microservices
- [ ] Need plugin architecture
- [ ] External teams need specific components
- [ ] Components become separate PyPI packages

## Execution Engines: Future Modularization Plan

### Phase 1: Current (Monolithic) ✅
```
execution.py
├── ExecutionEngine (base)
├── SubprocessEngine
├── DockerEngine
└── GVisorEngine
```

### Phase 2: Modular (When triggered)
```
engines/
├── __init__.py
├── base.py          # ExecutionEngine base class
├── subprocess.py    # SubprocessEngine
├── docker.py        # DockerEngine  
├── gvisor.py        # GVisorEngine
├── firecracker.py   # Future: AWS Firecracker
├── kata.py          # Future: Kata Containers
└── tests/
    ├── test_subprocess.py
    ├── test_docker.py
    └── test_gvisor.py
```

### Phase 3: Microservices (If needed)
```
execution-service/
├── api/             # REST/gRPC interface
├── engines/         # Engine implementations
├── scheduler/       # Job scheduling
├── security/        # Security policies
└── monitoring/      # Metrics & logging
```

## Modularization Checklist

Before modularizing, ensure you have:

- [ ] **Clear interfaces** - Well-defined base classes/protocols
- [ ] **Minimal coupling** - Components can work independently
- [ ] **Test coverage** - Tests to verify nothing breaks
- [ ] **Documentation** - Clear docs for each module
- [ ] **Migration plan** - How to update imports/dependencies

## Anti-patterns to Avoid

1. **Premature modularization** - Splitting too early adds complexity
2. **Over-modularization** - One class per file is usually too much
3. **Circular dependencies** - Plan module boundaries carefully
4. **Shared state** - Modules should be independent
5. **Breaking changes** - Maintain backward compatibility

## Example: When Execution Engines Should Split

The engines should be modularized when:

1. **Adding Firecracker/Kata** - Going from 4 to 6+ engine types
2. **Cloud-specific engines** - AWS/GCP/Azure specific implementations
3. **Language-specific handling** - Python/Node/Go need different setups
4. **Complex configuration** - Each engine needs 100+ lines of config
5. **Separate deployment** - Engines run as independent services

## Decision Record

| Component | Current State | Modularize When | Notes |
|-----------|--------------|-----------------|-------|
| Execution Engines | Monolithic (~400 lines) | 5+ engines or 1000+ lines | Clean abstraction exists |
| Web Frontend | Already modular | - | Good separation |
| Storage | Monolithic (~200 lines) | Adding cloud storage | S3/GCS/Azure different |
| Monitoring | Monolithic (~150 lines) | Adding Prometheus/Grafana | Different protocols |

## Remember

> "Duplication is far cheaper than the wrong abstraction" - Sandi Metz

Start monolithic, extract modules when the pain of the monolith exceeds the cost of modularization.