# Base executor image
# This matches the hardcoded python:3.11-slim currently used in executor-service
FROM python:3.11-slim

# Add metadata
LABEL maintainer="crucible-platform"
LABEL description="Base executor image for secure code evaluation"
LABEL security="restricted"

# Create non-root user for execution
RUN groupadd -r executor && useradd -r -g executor executor

# Copy timeout wrapper script
# Note: timeout command is already available in python:3.11-slim base image
COPY --chown=root:root evaluation-environments/shared/timeout_wrapper.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/timeout_wrapper.sh

# Set up minimal environment
# No pip, no apt, minimal attack surface
# The executor service handles:
# - Network isolation (--network=none)
# - Read-only filesystem (--read-only)
# - Memory limits (512MB)
# - CPU limits (0.5 CPU)
# - Temporary storage (/tmp as tmpfs)

# Set working directory
WORKDIR /app

# Switch to non-root user
USER executor

# Default command (will be overridden by executor)
CMD ["python", "-c", "print('Executor ready')"]