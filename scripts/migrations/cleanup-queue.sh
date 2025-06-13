#!/bin/bash
# Clean up queue folder structure

echo "🧹 Cleaning up queue folder"
echo "==========================="

cd src/queue

# 1. Remove duplicate base.py in handlers
echo "Removing duplicate handlers/base.py..."
rm -f handlers/base.py
echo "  ✓ Removed handlers/base.py (duplicate of queue.py)"

# 2. Check if handlers folder is empty and handle it
if [ -z "$(ls -A handlers 2>/dev/null)" ]; then
    echo "Adding README to explain handlers folder..."
    cat > handlers/README.md << 'EOF'
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
EOF
    echo "  ✓ Added handlers/README.md"
fi

# 3. Add comment to queue.py about future modularization
echo "Adding modularization note to queue.py..."
cat > queue_header.py << 'EOF'
"""
Task queue for concurrent evaluation processing.
Can evolve into a distributed job queue with Redis/RabbitMQ/SQS.

NOTE: Currently monolithic. When expanding, consider:
- handlers/ - Different task handler types
- backends/ - Redis, RabbitMQ, SQS implementations
- workers/ - Worker pool management
"""
EOF

# Get the rest of queue.py (skip first 4 lines)
tail -n +5 queue.py > queue_temp.py
cat queue_header.py queue_temp.py > queue.py
rm queue_header.py queue_temp.py

echo "  ✓ Added modularization note"

echo ""
echo "✅ Queue cleanup complete!"
echo ""
echo "Summary:"
echo "  - Removed duplicate handlers/base.py"
echo "  - Added README explaining future handler architecture"
echo "  - Added modularization note to queue.py"
echo ""
echo "The handlers/ folder is preserved for future task handler implementations."