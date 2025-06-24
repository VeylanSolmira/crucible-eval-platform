# Running the Crucible Evaluation Platform

The platform is a Python application with `app.py` as the main entry point.

## Quick Start

From the project root:

```bash
# Direct execution
python app.py --help

# As a module
python -m app

# If installed with pip
crucible --help
```

## Options

- `--engine [subprocess|docker|gvisor]` - Choose execution engine
- `--port PORT` - Web server port (default: 8080)
- `--test` - Run component tests
- `--unsafe` - Allow subprocess engine (dangerous!)

## Project Structure

```
crucible-evaluation-platform/
├── app.py              # Main entry point
├── src/                # Source code
│   ├── core/          # Core platform classes
│   ├── api/           # API component
│   ├── execution_engine/  # Execution engines
│   └── ...            # Other components
├── tests/             # Test files
├── docs/              # Documentation
└── pyproject.toml     # Python package configuration
```

This is a standard Python application structure where:
- `app.py` at the root is the main executable
- `src/` contains all the library code
- The application can be run directly or installed as a package
