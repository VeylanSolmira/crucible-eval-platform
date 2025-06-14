#!/bin/bash
# Clean up monitoring structure

echo "🧹 Cleaning up monitoring structure"
echo "==================================="

cd src/monitoring

# 1. Remove the duplicate/broken collectors and exporters folders
echo "Removing incomplete modularization attempts..."
rm -rf collectors/ exporters/
echo "  ✓ Removed collectors/ and exporters/ folders"

# 2. Add a note to monitoring.py about future modularization
echo "Adding modularization note to monitoring.py..."
cat > monitoring_header.py << 'EOF'
"""
Monitoring services for evaluation tracking.
These can evolve into full observability platforms.

NOTE: Currently monolithic by design. See docs/architecture/when-to-modularize.md

Future modularization structure:
- collectors/     # Metric collection (CPU, memory, GPU, custom)
- exporters/      # Export to monitoring systems (Prometheus, CloudWatch)
- aggregators/    # Metric aggregation and processing
- storage/        # Time-series data storage

TODO: Consider modularizing when:
- Adding Prometheus/Grafana integration
- Need specialized metric collectors
- Supporting multiple export formats
"""
EOF

# Combine header with rest of file (skip first 4 lines)
tail -n +5 monitoring.py > monitoring_temp.py
cat monitoring_header.py monitoring_temp.py > monitoring.py
rm monitoring_header.py monitoring_temp.py

echo ""
echo "✅ Monitoring cleanup complete!"
echo ""
echo "Summary:"
echo "  - Removed incomplete collectors/ and exporters/ folders"
echo "  - Added modularization documentation reference"
echo "  - Documented future structure for observability platform"
echo ""
echo "The monitoring implementation remains in monitoring.py for the MVP."