# Event Architecture Patterns: Orchestration vs Component-Based

## Overview

When implementing event-driven architecture, there are two primary patterns for how components interact with the event system:

1. **Orchestration-Based Events** - Components remain unaware of events; orchestrator handles event wiring
2. **Component-Based Events** - Components directly publish/subscribe to events

Both are valid architectural choices with different tradeoffs.

## Pattern 1: Orchestration-Based Events (Current Implementation)

This is what we've implemented in `extreme_mvp_frontier_events.py`.

### How It Works

```python
# Components remain simple and event-unaware
class Platform:
    def evaluate(self, code: str) -> Dict[str, Any]:
        result = self.engine.execute(code)
        return result  # Just returns result, doesn't publish events

class Storage:
    def store(self, eval_id: str, result: Dict[str, Any]):
        # Direct method call, no event subscription
        self._write_to_disk(eval_id, result)

# Orchestrator wires everything together
def main():
    event_bus = EventBus()
    platform = Platform(engine)
    storage = Storage()
    
    # Orchestrator creates the event handlers
    def handle_evaluation_completed(event):
        eval_id = event['data']['eval_id']
        result = event['data']['result']
        storage.store(eval_id, result)  # Orchestrator calls storage
    
    event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, handle_evaluation_completed)
    
    # Orchestrator publishes events on behalf of components
    result = platform.evaluate(code)
    event_bus.publish(EventTypes.EVALUATION_COMPLETED, {
        "eval_id": eval_id,
        "result": result
    })
```

### Advantages

1. **Simpler Components**
   - Components don't need to know about EventBus
   - Easier to test in isolation
   - Can be used with or without events

2. **Gradual Migration**
   - Can add events without changing existing components
   - Mix event-driven and direct calls as needed
   - Lower risk refactoring

3. **Flexibility**
   - Orchestrator can transform/filter events
   - Easy to add cross-cutting concerns
   - Can change event flow without touching components

4. **Backward Compatibility**
   - Existing code continues to work
   - No breaking changes to component APIs
   - Can support multiple orchestration strategies

### Disadvantages

1. **Coupling in Orchestrator**
   - Orchestrator knows about all components
   - Event flow logic scattered in main/orchestrator
   - Harder to understand component interactions

2. **Less Autonomy**
   - Components can't evolve their events independently
   - Need orchestrator changes for new events
   - Components less self-contained

3. **Testing Complexity**
   - Integration tests need full orchestration
   - Harder to test event flows in isolation
   - Mock complexity in orchestrator

## Pattern 2: Component-Based Events (Full Refactor)

This is what we started to implement in the cancelled `extreme_mvp_frontier_events_full.py`.

### How It Works

```python
# Components are event-aware and autonomous
class EventDrivenPlatform:
    def __init__(self, engine: Engine, event_bus: EventBus):
        self.engine = engine
        self.event_bus = event_bus
    
    def evaluate(self, code: str) -> str:
        eval_id = generate_id()
        
        # Platform publishes its own events
        self.event_bus.publish(EventTypes.EVALUATION_STARTED, {
            "eval_id": eval_id,
            "code": code
        })
        
        result = self.engine.execute(code)
        
        # Platform publishes completion
        self.event_bus.publish(EventTypes.EVALUATION_COMPLETED, {
            "eval_id": eval_id,
            "result": result
        })
        
        return eval_id

class EventDrivenStorage:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
        # Storage subscribes to events it cares about
        event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, self._on_completed)
        event_bus.subscribe(EventTypes.EVALUATION_FAILED, self._on_failed)
    
    def _on_completed(self, event: Dict[str, Any]):
        # Storage handles its own event processing
        eval_id = event['data']['eval_id']
        result = event['data']['result']
        self._write_to_disk(eval_id, result)
        
        # Can publish its own events
        self.event_bus.publish(EventTypes.STORAGE_SAVED, {
            "eval_id": eval_id,
            "path": f"storage/{eval_id}.json"
        })

# Orchestrator just wires components, doesn't handle events
def main():
    event_bus = EventBus()
    platform = EventDrivenPlatform(engine, event_bus)
    storage = EventDrivenStorage(event_bus)  # Self-subscribes
    monitor = EventDrivenMonitor(event_bus)  # Self-subscribes
    
    # That's it! Components handle their own events
```

### Advantages

1. **True Loose Coupling**
   - Components only know about events, not each other
   - Can add/remove components without changing others
   - Clear component boundaries

2. **Component Autonomy**
   - Components control their own events
   - Self-contained behavior
   - Easier to understand individual components

3. **Scalability**
   - Components can be deployed separately
   - Natural microservice boundaries
   - Event bus can be external (Redis, Kafka)

4. **Extensibility**
   - New components just subscribe to events
   - No orchestrator changes needed
   - Plugin-style architecture

### Disadvantages

1. **Component Complexity**
   - Every component needs EventBus dependency
   - More code in each component
   - Event handling logic distributed

2. **Testing Overhead**
   - Components require EventBus for testing
   - Need to test event publishing/subscribing
   - More mocking required

3. **Debugging Difficulty**
   - Event flow harder to trace
   - No central place to see all interactions
   - Potential for event loops/storms

4. **All-or-Nothing**
   - Hard to partially adopt
   - Requires refactoring all components
   - Breaking changes to APIs

## Recommendation for METR Platform

The **current orchestration-based approach is the right choice** for this project because:

1. **Faster Development** - We can add events without refactoring components
2. **Lower Risk** - Components continue to work as before
3. **Easier Testing** - Components can be tested without EventBus
4. **Gradual Evolution** - Can move to component-based later if needed
5. **METR Timeline** - Fits the 5-day delivery schedule

## Migration Path

If you want to eventually move to component-based events:

```python
# Step 1: Current orchestration-based (DONE)
event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, 
                   lambda e: storage.store(e['data']['eval_id'], e['data']['result']))

# Step 2: Add event awareness to components (FUTURE)
class EventAwareStorage(Storage):
    def __init__(self, event_bus: EventBus = None):
        super().__init__()
        if event_bus:
            event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, self._handle_completed)
    
    def _handle_completed(self, event):
        self.store(event['data']['eval_id'], event['data']['result'])

# Step 3: Components publish their own events (FUTURE)
class EventPublishingPlatform(Platform):
    def evaluate(self, code: str):
        result = super().evaluate(code)
        if self.event_bus:
            self.event_bus.publish(EventTypes.EVALUATION_COMPLETED, {...})
        return result
```

## Code Examples in Our Project

### Current Implementation (Orchestration-Based)
See: `/evolution/extreme_mvp_frontier_events.py` lines 94-110

### Proposed Full Refactor (Component-Based)
See: The cancelled `extreme_mvp_frontier_events_full.py` attempt

## Summary

Both patterns are valid. The orchestration-based approach we've implemented provides most of the benefits of event-driven architecture (loose coupling, extensibility, observability) without the complexity of refactoring all components. This is a pragmatic choice that delivers value quickly while keeping the door open for future evolution.