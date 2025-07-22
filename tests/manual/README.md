# Manual Test Scripts

This directory contains manual test scripts for debugging and development purposes. These scripts are not part of the automated test suite but are useful for:

1. **Debugging specific issues**
2. **Testing individual components in isolation**
3. **Experimenting with new features**
4. **Reproducing reported bugs**

## Directory Organization

### kubernetes-api-issue/
Contains all scripts related to diagnosing and fixing the Kubernetes API JSON output issue where Python's `repr()` was being used instead of proper JSON formatting:

- **Investigation Scripts**:
  - `test_k8s_api_job.py` - Tests job creation via K8s Python API
  - `test_k8s_api_specific.py` - Specific API behavior tests
  - `test_k8s_logs.py` - Log retrieval testing
  - `test_json_output.py` - JSON output formatting tests
  - `test_yaml_job_creation.py` - YAML-based job creation approach
  - `test_job_inspection.py` - Job status and output inspection

- **Command Format Testing**:
  - `test-command-formats.py` - Different command execution formats
  - `test-newline-escaping.py` - Newline and escaping behavior
  - `test-print-behavior.py` - Python print behavior in Kubernetes context
  - `test_python_invocation.py` - Python invocation methods
  - `test_single_output.py` - Single output conversion hypothesis

- **Workarounds**:
  - `test_prefix_suffix_workaround.py` - Prefix/suffix workaround validation

- **YAML Manifests**:
  - `test-dispatcher-style.yaml` - Dispatcher-style job manifest
  - `test-exact-code.yaml` - Exact code execution manifest
  - `test-json-job.yaml` - JSON output job manifest

**Key Finding**: When Python code has only `print(json.dumps(...))` as output, the Kubernetes Python API somehow converts it to dict repr. This doesn't happen with manual kubectl apply.

### storage-testing/
Contains scripts for testing storage backends and database flows:

- `test_db_flow.py` - Tests the complete evaluation flow through the API:
  - Normal evaluation submission and retrieval
  - Large output handling with truncation verification
  - Storage persistence checking

- `test_storage_direct.py` - Directly examines the storage backend:
  - Lists stored evaluations
  - Verifies truncation metadata
  - Checks event storage
  - Provides storage statistics

## Usage

Most scripts can be run directly with Python:

```bash
# Kubernetes API issue scripts
python tests/manual/kubernetes-api-issue/test_k8s_api_job.py

# Storage testing
python tests/manual/storage-testing/test_db_flow.py --api-url http://localhost:8080

# With database storage
DATABASE_URL=postgresql://crucible:changeme@localhost:5432/crucible \
python tests/manual/storage-testing/test_storage_direct.py --storage-type database
```

Some scripts may require specific environment setup or running services. Check the script comments for requirements.

## Running Platform for Testing

1. Start the platform:
```bash
# With file storage
python app.py

# With database storage
DATABASE_URL=postgresql://crucible:changeme@localhost:5432/crucible python app.py

# With Kubernetes
skaffold dev
```

2. Run the specific test scripts based on what you're investigating

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

### Kubernetes API Issues
- JSON output format (proper JSON vs Python dict repr)
- Command execution behavior
- Log retrieval consistency

## Adding New Tests

When adding new manual tests:
1. Follow the naming pattern: `test_<feature>.py`
2. Place in the appropriate subdirectory based on the issue area
3. Include clear documentation in the script header
4. Support command-line arguments for flexibility
5. Provide example output in comments
6. Document any key findings or workarounds discovered