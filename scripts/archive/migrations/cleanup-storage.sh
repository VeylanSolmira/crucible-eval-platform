#!/bin/bash
# Clean up storage structure

echo "🧹 Cleaning up storage structure"
echo "================================"

cd src/storage

# 1. Remove duplicate base.py in backends
echo "Removing duplicate backends/base.py..."
rm -f backends/base.py
echo "  ✓ Removed backends/base.py (duplicate of storage.py)"

# 2. Add README to backends folder explaining the structure
echo "Adding documentation to backends folder..."
cat > backends/README.md << 'EOF'
# Storage Backends

This directory contains placeholder structures for different storage backend implementations.

## Current Backends (Placeholders)

### demo_storage/
Initial demo storage layout - simple file-based storage for prototyping.

### events_storage/
Event-focused storage optimized for time-series event data.

### frontier_storage/
Production-ready storage with advanced features like:
- Sharding by evaluation ID
- Compression for large results
- Metadata indexing
- Archival policies

## Directory Structure

Each backend follows the same pattern:
```
backend_name/
├── evaluations/    # Evaluation results
├── events/         # Time-series events
└── metadata/       # Indexes and metadata
```

## Future Backends

When implementing actual backends, consider:

1. **S3Backend** - AWS S3 with lifecycle policies
2. **PostgreSQLBackend** - JSONB storage with indexing
3. **MongoDBBackend** - Document store for complex queries
4. **RedisBackend** - Hot cache for recent evaluations
5. **HybridBackend** - Combines multiple backends

## Implementation Guide

To add a new backend:

1. Create a new class inheriting from `StorageService`
2. Implement all abstract methods
3. Add backend-specific configuration
4. Include appropriate tests
5. Document performance characteristics

Example:
```python
class S3StorageBackend(StorageService):
    def __init__(self, bucket_name: str, region: str):
        self.s3_client = boto3.client('s3', region_name=region)
        self.bucket = bucket_name
    
    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        key = f"evaluations/{eval_id}/result.json"
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(data)
        )
        return True
```

Currently, all storage implementations are in `../storage.py`.
EOF

# 3. Check if the empty directories have any purpose
echo "Checking backend directories..."
for backend in demo_storage events_storage frontier_storage; do
    if [ -d "backends/$backend" ]; then
        # Count files (excluding directories)
        file_count=$(find "backends/$backend" -type f | wc -l)
        if [ $file_count -eq 0 ]; then
            echo "  - $backend: empty placeholder"
            # Add a .gitkeep to preserve the directory structure
            touch "backends/$backend/evaluations/.gitkeep"
            touch "backends/$backend/events/.gitkeep"
            touch "backends/$backend/metadata/.gitkeep"
        fi
    fi
done

echo ""
echo "✅ Storage cleanup complete!"
echo ""
echo "Summary:"
echo "  - Removed duplicate backends/base.py"
echo "  - Added README explaining backend structure"
echo "  - Added .gitkeep files to preserve directory structure"
echo ""
echo "The backends/ folder structure is preserved as a template for future"
echo "storage backend implementations (S3, PostgreSQL, MongoDB, etc.)."