# ML Executor Image with PyTorch and Transformers
# Multi-stage build for security - build tools don't make it to final image

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install only what's needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY evaluation-environments/executor-ml/requirements.txt /tmp/

# Install ML packages
# Using --no-cache-dir to reduce image size
# Using CPU-only torch to reduce size (no CUDA)
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: Final image
FROM python:3.11-slim

# Add metadata
LABEL maintainer="crucible-platform"
LABEL description="ML executor image with PyTorch and Transformers for secure AI evaluation"
LABEL security="restricted"
LABEL ml-frameworks="pytorch,transformers"

# Create non-root user
RUN groupadd -r executor && useradd -r -g executor executor

# Copy only the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set up environment to use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/opt/venv/lib/python3.11/site-packages"

# Remove pip from the final image for security
RUN rm -rf /opt/venv/bin/pip* /opt/venv/bin/easy_install*

# Create app directory
WORKDIR /app

# Copy timeout wrapper script
COPY --chown=root:root evaluation-environments/shared/timeout_wrapper.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/timeout_wrapper.sh

# Pre-download models to avoid network access during execution
# This is commented out for now - in production you might want to pre-cache models
# RUN python -c "from transformers import AutoModel; AutoModel.from_pretrained('distilgpt2')"

# Switch to non-root user
USER executor

# Set environment variables for transformers
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache

# Default command
CMD ["python", "-c", "import torch; import transformers; print(f'ML Executor ready - PyTorch {torch.__version__}, Transformers {transformers.__version__}')"]