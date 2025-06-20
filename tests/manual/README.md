# Manual Test Utilities

This directory contains manual test scripts for validating various aspects of the platform.

## Test Scripts

### test_db_flow.py
Tests the complete evaluation flow through the API, including:
- Normal evaluation submission and retrieval
- Large output handling with truncation verification
- Storage persistence checking

```bash
# Test against local server
python test_db_flow.py

# Test against different server
python test_db_flow.py --api-url http://localhost:8080
```

### test_storage_direct.py
Directly examines the storage backend without going through the API:
- Lists stored evaluations
- Verifies truncation metadata
- Checks event storage
- Provides storage statistics

```bash
# Test file storage
python test_storage_direct.py --storage-type file

# Test database storage
DATABASE_URL=postgresql://crucible:changeme@localhost:5432/crucible \
python test_storage_direct.py --storage-type database
```

## Running Tests

1. Start the platform:
```bash
# With file storage
python app.py

# With database storage
DATABASE_URL=postgresql://crucible:changeme@localhost:5432/crucible python app.py
```

2. Run the tests:
```bash
cd tests/manual
python test_db_flow.py
python test_storage_direct.py
```

## What to Look For

### Truncation Testing
When testing large outputs, verify:
- `output_truncated: True` for outputs > 1MB
- `output_size` shows the actual size in bytes
- `output` field contains only the first 1KB preview

### Storage Consistency
- Evaluations appear in both API and direct storage queries
- Event logs are properly associated with evaluations
- Metadata fields are preserved correctly

## Adding New Tests

When adding new manual tests:
1. Follow the naming pattern: `test_<feature>.py`
2. Include clear documentation in the script header
3. Support command-line arguments for flexibility
4. Provide example output in comments