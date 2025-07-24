FROM python:3.11-slim

# Add non-root user
RUN useradd -m -u 1000 controller

WORKDIR /app

# Copy requirements and constraints
COPY cleanup_controller/requirements.txt .
COPY constraints.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY cleanup_controller/cleanup_controller.py .
RUN chmod +x cleanup_controller.py

# Switch to non-root user
USER controller

# Use minimal resources
ENV PYTHONUNBUFFERED=1

CMD ["python", "cleanup_controller.py"]