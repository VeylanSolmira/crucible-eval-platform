# Core Module (formerly platform)

This folder was renamed from `platform/` to `core/` to:

1. **Avoid naming conflicts** with Python's built-in `platform` module
2. **Better reflect its purpose** as the transitional monolithic core
3. **Indicate it's temporary** - code here will migrate to service folders

## What's in core/

- `app.py` - Main entry point
- `platform.py` - Base classes (EvaluationPlatform, etc.)
- `components.py` - Import helper for all services

## Running

From project root:
```bash
python -m src.core.extreme_mvp_frontier_events
# or
python -m src.core
```

## Future

As we complete the microservices migration, code will move from here to the appropriate service folders.
