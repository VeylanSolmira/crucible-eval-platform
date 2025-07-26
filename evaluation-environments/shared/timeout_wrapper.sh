#!/bin/sh
# Timeout wrapper for evaluation execution
# Usage: timeout_wrapper.sh <timeout_seconds> <command...>

TIMEOUT=$1
shift

# Use exec to replace the shell process with timeout
# This ensures proper signal handling
exec timeout --preserve-status --signal=TERM --kill-after=5 "$TIMEOUT" "$@"