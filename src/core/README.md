# Platform

Core platform implementation files.

## Contents

- `app.py` - Main platform implementation
- `platform.py` - Platform base classes (EvaluationPlatform, QueuedEvaluationPlatform)
- `components.py` - Import helper for all service components
- `requirements.txt` - Optional dependencies

## Running the Platform

```bash
cd src/platform
python app.py
```

## Testing

Tests have been moved to `/tests/test_components.py`

```bash
cd tests
python test_components.py
```

## Security Testing

Security testing scripts are in `/src/security-scanner/`:
- `run_security_demo.py`
- `safe_security_check.py`

## Demos

Demo scripts are in `/demos/`:
- `run_demo_servers.py`
