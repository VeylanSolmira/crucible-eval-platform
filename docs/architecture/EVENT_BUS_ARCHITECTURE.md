# Event Bus Architecture

## Overview

The Event Bus implements a publish-subscribe pattern that allows components to communicate without direct dependencies on each other. This is a foundational pattern for building scalable, maintainable systems.

## Current Structure (Monolithic)

```
event-bus/
├── events.py          # The EventBus class (pub/sub infrastructure)
├── requirements.txt   # No dependencies needed (uses Python stdlib)
└── __init__.py
```

## Future Structure (Microservice)

When deployed as a standalone service, the structure would expand to:

```
event-bus/
├── events.py          # Core EventBus infrastructure
├── handlers/          # Event handler implementations
│   ├── __init__.py
│   ├── evaluation_handler.py    # Handles evaluation.* events
│   ├── queue_handler.py         # Handles queue.* events
│   └── monitoring_handler.py    # Handles monitoring.* events
├── main.py           # FastAPI service entry point
├── Dockerfile        # Container definition
└── requirements.txt  # Would need: fastapi, uvicorn, websockets
```

## Handler Pattern Example

In a microservice architecture, handlers would contain business logic:

```python
# handlers/evaluation_handler.py
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class EvaluationEventHandler:
    """Handles all evaluation-related events"""
    
    def __init__(self, event_bus, storage_client, monitoring_client):
        self.event_bus = event_bus
        self.storage = storage_client
        self.monitoring = monitoring_client
        
        # Register handlers
        event_bus.subscribe('evaluation.started', self.handle_evaluation_started)
        event_bus.subscribe('evaluation.completed', self.handle_evaluation_completed)
        event_bus.subscribe('evaluation.failed', self.handle_evaluation_failed)
    
    async def handle_evaluation_started(self, event_data: Dict[str, Any]):
        """When evaluation starts"""
        eval_id = event_data['eval_id']
        
        # Update monitoring metrics
        await self.monitoring.increment('evaluations.active')
        
        # Log for audit trail
        logger.info(f"Evaluation {eval_id} started")
        
        # Notify other services
        await self.event_bus.publish('metrics.evaluation.started', {
            'eval_id': eval_id,
            'timestamp': event_data['timestamp']
        })
    
    async def handle_evaluation_completed(self, event_data: Dict[str, Any]):
        """When evaluation completes successfully"""
        eval_id = event_data['eval_id']
        result = event_data['result']
        
        # Store results
        await self.storage.store_result(eval_id, result)
        
        # Update metrics
        await self.monitoring.decrement('evaluations.active')
        await self.monitoring.increment('evaluations.completed')
        
        # Clean up resources
        await self.event_bus.publish('cleanup.evaluation', {
            'eval_id': eval_id
        })
    
    async def handle_evaluation_failed(self, event_data: Dict[str, Any]):
        """When evaluation fails"""
        eval_id = event_data['eval_id']
        error = event_data['error']
        
        # Alert on critical failures
        if error.get('severity') == 'critical':
            await self.event_bus.publish('alert.critical', {
                'service': 'evaluation',
                'error': error
            })
        
        # Retry logic
        retry_count = event_data.get('retry_count', 0)
        if retry_count < 3:
            await self.event_bus.publish('evaluation.retry', {
                'eval_id': eval_id,
                'retry_count': retry_count + 1
            })
```

## Why Handlers are Not Needed in Monolithic Mode

In our current monolithic platform:

1. **Inline Handlers**: Components define their own event handlers when subscribing
   ```python
   # In platform code
   event_bus.subscribe('evaluation.completed', lambda event: 
       monitor.record_metric('evaluation_completed', 1))
   ```

2. **Direct Component Access**: Components can directly call each other's methods
   ```python
   # Direct call instead of event
   storage.store_result(result)
   ```

3. **Simpler Testing**: Can test components together without mocking event infrastructure

## Migration Path

To move from monolithic to microservice event handling:

1. **Extract inline handlers** to dedicated handler classes
2. **Add service clients** for cross-service communication
3. **Implement event persistence** for reliability
4. **Add WebSocket support** for real-time updates
5. **Deploy as standalone service** with its own API

## Event Naming Conventions

We use dot notation for event types:

- `evaluation.started`
- `evaluation.completed`
- `evaluation.failed`
- `queue.task.added`
- `queue.task.processed`
- `monitoring.metric.recorded`
- `storage.file.created`

This allows for:
- Wildcard subscriptions: `evaluation.*`
- Hierarchical organization
- Clear event ownership

## Benefits of Event-Driven Architecture

1. **Loose Coupling**: Components don't need to know about each other
2. **Scalability**: Easy to add new event handlers
3. **Flexibility**: Can change implementation without affecting others
4. **Auditability**: All events can be logged for audit trail
5. **Testability**: Components can be tested in isolation
6. **Migration Path**: Easy to move to external message brokers (RabbitMQ, Kafka)