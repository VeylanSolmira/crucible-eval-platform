# Demo Scripts

This folder contains scripts specifically designed for demonstrating platform capabilities during presentations and demos.

## ⚠️ Important Note

These scripts are **NOT** intended for general use. They include:
- Resource exhaustion tests
- Error triggering examples  
- Security boundary tests
- Performance stress tests

## Available Demo Scripts

### memory-exhaustion.py
Demonstrates memory limit enforcement by attempting to:
- Allocate 500MB (succeeds, near the 512MB limit)
- Allocate 2GB (fails, exceeds limit)
- Shows OOM kill behavior (container terminated)

### cpu-exhaustion.py
Demonstrates CPU limit enforcement by:
- Spawning multiple CPU-intensive processes
- Shows CPU throttling (limited to 0.5 cores)
- Processes are throttled, not killed
- Clean demonstration of cgroup CPU limits

### Usage

These scripts should only be run during controlled demonstrations to show:
1. Platform resilience
2. Resource limit enforcement
3. Error handling capabilities
4. Security boundaries

## Why Separate from User Templates?

The `/frontend/lib/templates/` folder contains helpful starter code for users.
This `/templates/demos/` folder contains potentially problematic code that:
- Could consume excessive resources
- Is designed to trigger errors
- Tests platform boundaries
- Would not be helpful as user starter code

## Adding New Demo Scripts

When adding new demo scripts:
1. Clearly comment the purpose
2. Include warnings about resource usage
3. Ensure they demonstrate a specific platform capability
4. Never include actually malicious code