# Running the Crucible Platform

## Professional Python Package Setup (Recommended)

```bash
# 1. Setup development environment
chmod +x setup-dev.sh
./setup-dev.sh

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run the platform (choose one):
python -m app              # Run as module
crucible --help                     # Use installed script
```

## Quick Run (without installation)

From the project root:
```bash
cd /Users/infinitespire/ai_dev/applications/metr-eval-platform
python app.py --help
```

## Why This Structure?

1. **Avoids naming conflicts**: Our `core` folder doesn't conflict with Python's built-in `platform` module
2. **Professional package structure**: Uses `pyproject.toml` like modern Python packages
3. **Development mode**: Changes to code are immediately reflected
4. **Console scripts**: The `crucible` command is available when installed

## Common Issues

### Import Errors
- Make sure you're running from the project root, not from inside `src/core/`
- Use the module syntax: `python -m app`

### Name Conflicts
- Python has a built-in `platform` module
- That's why we use `src.core` to disambiguate

### Package Not Found
- Run `./setup-dev.sh` first
- Make sure virtual environment is activated