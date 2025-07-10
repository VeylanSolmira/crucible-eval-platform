# Monitoring Infrastructure

This directory contains all observability and monitoring tools for the Crucible platform, supporting both operational monitoring and researcher-centered analytics.

## Directory Structure

```
/monitoring/
├── flower/              # Celery task monitoring (replaceable)
│   ├── Dockerfile
│   └── requirements.txt
├── prometheus/          # Metrics collection (future)
│   ├── prometheus.yml
│   └── rules/
├── grafana/             # Dashboards (future)
│   ├── dashboards/
│   └── datasources/
├── researcher-tools/    # Custom monitoring for ML/AI workloads
│   ├── gpu-monitor/     # GPU utilization tracking
│   ├── model-metrics/   # Model performance tracking
│   └── experiment-tracker/
└── README.md           # Explains the monitoring strategy
```

## Monitoring Philosophy

We maintain a dual monitoring approach:

### 1. Operational Monitoring (DevOps/SRE Focus)
- **Flower**: Real-time Celery task queue monitoring
- **Prometheus**: Time-series metrics collection
- **Grafana**: Visualization and alerting
- **Focus**: System health, performance, reliability

### 2. Researcher-Centered Monitoring (Data Science/ML Focus)
- **Experiment Tracking**: Track model training runs and hyperparameters
- **Resource Utilization**: GPU/CPU usage per experiment
- **Model Performance**: Inference latencies, accuracy metrics
- **Dataset Versioning**: Track data lineage
- **Compute Cost Tracking**: Resource usage → cost attribution

## Current Status

- ✅ **Flower**: Containerized for Celery monitoring
- 🚧 **Prometheus/Grafana**: Planned for production
- 📋 **Researcher Tools**: Design phase

## Why Separate Directory?

1. **Modularity**: Each monitoring tool is independently replaceable
2. **Clear Ownership**: Ops tools vs researcher tools
3. **Deployment Flexibility**: Can deploy monitoring stack separately
4. **Technology Agnostic**: Easy to swap Flower for alternatives

## Getting Started

### Running Flower
```bash
# Build the Flower image
docker build -t crucible-monitoring/flower monitoring/flower/

# Run standalone (for testing)
docker run -p 5555:5555 \
  -e CELERY_BROKER_URL=redis://redis:6379/0 \
  -e FLOWER_BASIC_AUTH=admin:changeme \
  crucible-monitoring/flower
```

### Future Integration
Each monitoring component will be added to the main docker-compose.yml or deployed separately in Kubernetes with appropriate service discovery and ingress rules.