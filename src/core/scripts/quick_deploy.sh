#!/bin/bash
# Quick deployment script - packages minimal files needed

echo "🚀 Quick deployment package..."

# From the metr-eval-platform directory, run:
# cd /Users/infinitespire/ai_dev/applications/metr-eval-platform
# tar czf evolution-minimal.tar.gz \
#   evolution/extreme_mvp_frontier_events.py \
#   evolution/components/*.py \
#   evolution/components/__init__.py

cd /Users/infinitespire/ai_dev/applications/metr-eval-platform
# Use --no-xattrs to exclude macOS extended attributes
tar --no-xattrs -czf evolution-minimal.tar.gz \
  evolution/extreme_mvp_frontier_events.py \
  evolution/components/

echo "✅ Minimal package created: evolution-minimal.tar.gz"
echo ""
echo "📤 Deploy with:"
echo "   scp evolution-minimal.tar.gz ubuntu@44.246.137.198:~/"
echo ""
echo "📥 On server:"
echo "   tar xzf evolution-minimal.tar.gz"
echo "   cd evolution"
echo "   python3 extreme_mvp_frontier_events.py"