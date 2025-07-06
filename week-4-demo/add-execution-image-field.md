# Task: Add Execution Image Field to Evaluations Database

## Overview
Add a new field to the evaluations database table to track which Docker image was used to execute the code. This will support multiple execution environments with different security profiles and dependency sets.

## Background
As we implement more sophisticated security controls, we'll need multiple Docker images with different permission sets:
- `crucible-executor-basic`: Standard Python environment
- `crucible-executor-restricted`: No network access, limited filesystem
- `crucible-executor-ml`: Includes ML libraries (numpy, pandas, etc.)
- `crucible-executor-web`: Allows web requests for scraping tasks

## Implementation Steps

### 1. Database Migration
Add a new column to the evaluations table:
```sql
ALTER TABLE evaluations ADD COLUMN execution_image VARCHAR(255);
```

The field should:
- Be nullable initially (for backward compatibility)
- Store the full image name with tag (e.g., `crucible-executor-basic:v1.2.3`)
- Be indexed for efficient filtering

### 2. Update Storage Models
Update the SQLAlchemy model in `storage/models/evaluation.py`:
```python
execution_image = Column(String(255), nullable=True, index=True)
```

### 3. Update API Contracts
- Add `execution_image` to `EvaluationResponse` in the OpenAPI spec
- Update the storage service to save and return this field

### 4. Executor Integration
- Modify executors to report which image they're using
- Pass this information through the evaluation pipeline

### 5. Frontend Display
- Show the execution image in the execution monitor
- Add filtering by execution image in the evaluations list

## Benefits
1. **Security Auditing**: Track which environment ran each piece of code
2. **Debugging**: Understand environment-specific failures
3. **Compliance**: Demonstrate appropriate isolation for different code types
4. **Performance**: Route evaluations to optimized images

## Future Enhancements
- Auto-select execution image based on code analysis
- Resource limits per image type
- Image version management and deprecation
- Security scanning integration

## Notes
- Consider storing additional metadata about the image (memory limits, CPU limits, network policies)
- May want to normalize this into a separate `execution_images` table if we need to store more image metadata