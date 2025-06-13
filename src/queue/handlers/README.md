# Queue Handlers

This folder is reserved for different task handler implementations when the queue service is expanded.

## Future Handler Types

1. **EvaluationHandler** - Processes code evaluation tasks
2. **BatchHandler** - Handles batch evaluation jobs
3. **PriorityHandler** - Manages priority-based task execution
4. **RetryHandler** - Handles task retries with exponential backoff
5. **DeadLetterHandler** - Processes failed tasks

## Example Implementation

```python
from abc import ABC, abstractmethod

class TaskHandler(ABC):
    @abstractmethod
    def can_handle(self, task: Dict[str, Any]) -> bool:
        """Check if this handler can process the task"""
        pass
    
    @abstractmethod
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process the task and return result"""
        pass

class EvaluationHandler(TaskHandler):
    def __init__(self, execution_engine):
        self.engine = execution_engine
    
    def can_handle(self, task: Dict[str, Any]) -> bool:
        return task.get('type') == 'evaluation'
    
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return self.engine.execute(
            code=task['code'],
            eval_id=task['id']
        )
```

Currently, task handling logic is embedded in the main TaskQueue class in `../queue.py`.
