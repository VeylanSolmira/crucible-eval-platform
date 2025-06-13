# Reference Implementation History

This folder contains the evolutionary history of the Crucible platform, showing the progression from a simple unsafe prototype to a production-ready system.

## Purpose

These files serve as:
1. **Educational artifacts** - Learn from the evolution process
2. **Design documentation** - Each file represents specific design decisions
3. **Code archaeology** - Understand why current architecture exists
4. **Alternative approaches** - Different solutions to similar problems

## ⚠️ Important Notes

- These files are **NOT** meant for production use
- They are **HISTORICAL REFERENCES** only
- The current implementation is in `../platform/`
- Some early versions (especially `extreme_mvp.py`) are **UNSAFE**

## Evolution Timeline

See [Evolution Tree](../../docs/extreme-mvp/evolution-tree.md) for the complete evolution map.

### Key Milestones

1. **extreme_mvp.py** - Original unsafe prototype (subprocess execution)
2. **extreme_mvp_docker.py** - First safety attempt with containers
3. **extreme_mvp_testable.py** - Introduction of testing philosophy
4. **extreme_mvp_monitoring.py** - Added observability
5. **extreme_mvp_queue.py** - Concurrent execution support
6. **extreme_mvp_gvisor.py** - Production-grade security
7. **extreme_mvp_modular.py** - Fully modular architecture

## Demo Files

The `demo/` subfolder contains examples of how individual components work:
- Component isolation demonstrations
- API usage examples
- Frontend variations
- Storage integration patterns

## Why Keep This?

1. **Learning Resource**: Shows progression from naive to sophisticated
2. **Design Rationale**: Documents why certain choices were made
3. **Interview Prep**: Can discuss evolution and trade-offs
4. **Refactoring Guide**: Shows what NOT to do and why

## Current Implementation

The active, production-ready code is at:
- **Monolithic**: `../platform/app.py`
- **Components**: Various service directories (`../execution-engine/`, etc.)

## Future

When the platform fully migrates to microservices, this reference folder will serve as a historical record of the monolithic era.