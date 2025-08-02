# Event Architecture

This document tracks which services publish and consume events in the METR platform.

## Event Types

### evaluation:submitted
- **Published by**: 
- **Consumed by**: 
- **When**: 
- **Data**: 

### evaluation:queued
- **Published by**: 
- **Consumed by**: 
- **When**: 
- **Data**: 

### evaluation:running
- **Published by**: 
- **Consumed by**: 
- **When**: 
- **Data**: 

### evaluation:completed
- **Published by**: Dispatcher (dispatcher_service/app.py)
- **Consumed by**: Storage Worker (storage_worker/app.py)
- **When**: Job succeeds with exit code 0
- **Data**: eval_id, output (logs), exit_code, metadata (job_name, completed_at, log_source)

### evaluation:failed
- **Published by**: 
- **Consumed by**: 
- **When**: 
- **Data**: 

## Services

### API Service
**Publishes**: 
**Subscribes to**: 

### Celery Worker
**Publishes**: 
**Subscribes to**: 

### Dispatcher
**Publishes**: 
**Subscribes to**: 

### Storage Worker
**Publishes**: 
**Subscribes to**: 

### Storage Service
**Publishes**: 
**Subscribes to**: 

## Notes

- Redis Pub/Sub is used for event distribution
- Events use the pattern "channel:event" (e.g., "evaluation:completed")