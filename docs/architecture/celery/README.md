# Celery Integration Documentation

All documentation related to Celery task queue integration and migration.

## Migration Strategy
- **celery-migration-strategy.md** - Phased migration plan from custom queue to Celery
- **celery-integration-notes.md** - Integration details and considerations

## Features and Patterns
- **celery-redis-relationship.md** - How Celery uses Redis as broker
- **celery-priority-queues.md** - Priority queue implementation
- **celery-retry-logic.md** - Retry patterns and error handling
- **dead-letter-queue.md** - Handling failed tasks

## Operations
- **celery-monitoring-strategy.md** - Monitoring Celery with Flower
- **celery-status-endpoint.md** - Health check and status endpoints
- **celery-task-cancellation.md** - Task cancellation patterns