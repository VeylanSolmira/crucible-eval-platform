# Celery vs SQS Comparison for METR

## Quick Summary

**Use SQS for MVP** - Simpler operations, built-in durability, less infrastructure
**Consider Celery later if** - You need complex workflows, task chaining, or advanced monitoring

## Detailed Comparison

### Celery + Redis/RabbitMQ

**Pros:**
- **Task introspection** - Check task state directly (`task.state`, `task.result`)
- **Complex workflows** - Task chaining, groups, chords
- **Python-native** - Decorators, natural Python feel
- **Rich monitoring** - Flower dashboard for task visibility
- **Flexible routing** - Multiple queues, priority routing
- **Real-time events** - Task progress updates

**Cons:**
- **Infrastructure overhead** - Must run and maintain Redis/RabbitMQ
- **Volatility risk** (with Redis) - Can lose messages on crash
- **More complex setup** - Broker, backend, worker configuration
- **Scaling challenges** - Need to scale broker and workers separately

**Example:**
```python
# Celery task with chaining
@celery.task
def process_evaluation(eval_id):
    return {"status": "processed", "eval_id": eval_id}

@celery.task
def notify_user(result):
    send_email(result['eval_id'])

# Chain tasks
(process_evaluation.s(eval_id) | notify_user.s()).apply_async()
```

### AWS SQS

**Pros:**
- **Zero infrastructure** - AWS manages everything
- **Built-in durability** - Messages replicated across AZs
- **Simple scaling** - Automatic scaling with demand
- **DLQ included** - Failed message handling out of the box
- **Cost effective** - Pay per message, no idle costs
- **IAM integration** - AWS-native security

**Cons:**
- **Limited introspection** - Can't easily check message state
- **No complex workflows** - Just simple queue operations
- **AWS lock-in** - Tied to AWS ecosystem
- **Network latency** - Slightly slower than in-memory Redis
- **Less flexibility** - Fewer features than Celery

**Example:**
```python
# SQS simple task
sqs.send_message(
    QueueUrl=QUEUE_URL,
    MessageBody=json.dumps({
        'evaluation_id': eval_id,
        'action': 'process'
    })
)
```

## Decision Matrix

| Requirement | Celery | SQS | Winner |
|------------|--------|-----|---------|
| Simple task dispatch | ✓ | ✓ | Tie |
| Zero infrastructure | ✗ | ✓ | SQS |
| Message durability | ✓/✗ | ✓ | SQS |
| Complex workflows | ✓ | ✗ | Celery |
| Task monitoring | ✓ | ✗ | Celery |
| Quick MVP setup | ✗ | ✓ | SQS |
| Cost for low volume | ✗ | ✓ | SQS |
| Python integration | ✓ | ✓ | Tie |

## For METR's Use Case

### MVP Phase (Current)
**Choose SQS because:**
- Simple evaluation dispatch (no complex workflows)
- Reliability is critical (can't lose eval requests)
- Want to minimize operational overhead
- Already using AWS (Lambda, etc.)

### Future Growth
**Consider Celery when:**
- Need multi-step evaluation pipelines
- Want real-time progress updates
- Require advanced task routing
- Have dedicated ops team

## Migration Path

Starting with SQS doesn't lock you in:

```python
# Abstract queue interface
class QueueInterface:
    def send_task(self, task_data): pass
    def receive_task(self): pass

class SQSQueue(QueueInterface):
    def send_task(self, task_data):
        sqs.send_message(...)

class CeleryQueue(QueueInterface):
    def send_task(self, task_data):
        celery_task.delay(...)
```

This abstraction makes switching queue backends easier later.

## Key Insight

The queue choice is less important than getting the abstraction right. Both can work for METR - choose based on operational complexity tolerance.