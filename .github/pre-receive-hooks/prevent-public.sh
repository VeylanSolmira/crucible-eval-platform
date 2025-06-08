#!/bin/bash
# Pre-receive hook to prevent repository from being made public
# This would need to be installed on the GitHub server (GitHub Enterprise only)

echo "⚠️  WARNING: This repository contains sensitive interview preparation materials."
echo "⚠️  Making this repository public is strongly discouraged."
echo "⚠️  If you must make it public, please remove all interview-related content first."

# For GitHub Enterprise, you could reject the push here
# exit 1