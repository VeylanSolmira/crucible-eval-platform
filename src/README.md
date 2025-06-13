# Source Code Structure

This directory contains the Crucible Evaluation Platform source code.

## Quick Start

```bash
cd core
python app.py --help
```

## Directory Structure

- `core/` - The monolithic platform (current implementation)
- `execution_engine/` - Code execution components
- `event_bus/` - Event coordination system
- `security_scanner/` - Security testing framework
- `shared/` - Shared utilities and base classes
- `lambda/` - AWS Lambda functions
- `mvp_evolution/` - Historical implementation progression
- `future_services/` - Services planned for future development

For detailed architecture documentation, see `/docs/architecture/`

## Docker Compose

The `docker-compose.yml.example` file shows how the platform could be deployed as microservices in the future. Currently, the platform runs as a monolith from the `core/` directory.

To run the current monolithic version:
```bash
cd core
python app.py
```

The docker-compose example is for future reference when migrating to microservices.
