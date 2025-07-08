# Evaluation State Machine

This module provides a centralized state machine for managing evaluation lifecycle transitions across all services in the METR platform.

## Overview

The state machine ensures that evaluations can only transition between valid states, preventing issues like:
- Evaluations getting stuck in incorrect states due to out-of-order events
- Invalid state transitions (e.g., completed → running)
- Inconsistent state handling across different services

## Components

### 1. State Transition Rules (`/shared/types/evaluation-state-transitions.yaml`)
The source of truth for allowed state transitions. This YAML file defines which states can transition to which other states.

### 2. State Machine (`evaluation_state_machine.py`)
The core state machine implementation that:
- Loads transition rules from the YAML file
- Validates proposed state transitions
- Identifies terminal states (completed, failed, cancelled)
- Provides query methods for allowed transitions

### 3. Status Update Helpers (`status_updater.py`)
Shared utilities that combine state validation with actual updates:
- `validate_and_update_status()` - The main helper function used by services
- `get_valid_transitions()` - Query allowed transitions from a state
- `is_terminal_status()` - Check if a status is terminal

## Usage

### Basic State Validation
```python
from shared.state_machine import get_state_machine

state_machine = get_state_machine()
is_valid, error_msg = state_machine.validate_transition("running", "completed")
```

### Using the Shared Update Pattern
```python
from shared.state_machine import validate_and_update_status

# In your service with an HTTP client
success, error = await validate_and_update_status(
    http_client=self.client,
    storage_url="http://storage-service:8082",
    eval_id="eval-123",
    new_status="running",
    update_data={"executor_id": "exec-1"}
)

if not success:
    logger.error(f"Failed to update status: {error}")
```

## State Flow

```
submitted → queued → provisioning → running → completed
                ↓         ↓       ↘    ↓         ↓
              failed    failed     ↘ failed    (terminal)
                ↓         ↓       completed*    
            cancelled cancelled   cancelled

* provisioning → completed is allowed for fast executions that complete
  during container provisioning (temporary fix for race condition)
```

Terminal states (completed, failed, cancelled) cannot transition to any other state.

## Adding New States or Transitions

1. Edit `/shared/types/evaluation-state-transitions.yaml`
2. Add the new state and its allowed transitions
3. Update the `EvaluationStatus` enum if adding a new state
4. Test thoroughly - invalid transitions can break the platform

## Services Using This Module

- **Storage Worker** - Validates all event-based status updates
- **Storage Service** - Could validate API-based updates
- **API Service** - Could validate evaluation updates
- **Celery Worker** - Could validate task status changes
- **Executor Service** - Publishes status events (doesn't update directly)

## Known Issues

### Race Condition for Fast Executions
Under high load, very fast executions (< 100ms) can complete before the "running" event is processed, causing the "completed" event to arrive while still in "provisioning" state. 

**Temporary Fix**: Allow provisioning → completed transition
**Permanent Fix**: Implement event queue with guaranteed ordering in executor service (see [executor-event-ordering.md](/docs/architecture/executor-event-ordering.md))

## Future Enhancements

- [ ] Add transition metadata (reasons, conditions)
- [ ] Implement retry logic for certain transitions
- [ ] Add role-based permissions for manual transitions
- [ ] Support for custom validation hooks
- [ ] Event sourcing for complete state history
- [ ] Remove provisioning → completed after event ordering is fixed