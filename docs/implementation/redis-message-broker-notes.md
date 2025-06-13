# Redis as a Message Broker

## What is Redis?

Redis is an in-memory **key-value store** (not a relational database). Think of it as a giant Python dictionary that lives in RAM.

**Common data structures:**
- Strings
- Lists (perfect for queues)
- Sets
- Hashes
- Sorted sets

## Redis + Celery Architecture

```python
# How Celery uses Redis as a message broker
# Redis stores tasks in lists (queues)

# When you do:
task = process_evaluation.delay(eval_id)

# Celery:
# 1. Serializes task to JSON
# 2. Pushes to Redis list: LPUSH celery {"task": "process_evaluation", "args": ["eval-123"]}
# 3. Worker pulls from list: BRPOP celery
```

**Architecture:**
```
Producer → Redis (queue) → Worker
   ↓          ↓              ↓
(task)    (stores)       (pulls)
         temporarily
```

## Why Redis for Celery?

1. **Fast message passing** - Everything in memory
2. **Built-in list operations** - Perfect for queues (LPUSH/RPOP)
3. **Pub/Sub capabilities** - For real-time task events
4. **Atomic operations** - Prevents race conditions

## The Volatility Problem

**What happens on crash:**
```
Redis process dies → All queued messages gone → Workers have nothing to process
```

### Redis Persistence Options

1. **RDB snapshots** 
   - Saves to disk every X minutes
   - Problem: Can lose last few minutes of data

2. **AOF (Append Only File)**
   - Logs every write operation
   - Problem: Slower, still can lose last second

### Production Safety Nets

```
# Use Redis for speed, but with safety nets:
1. Redis Cluster (replication)
2. Redis Sentinel (automatic failover)
3. Or... just use a persistent broker like SQS
```

## Redis vs SQS for METR

### Celery + Redis
- ✅ **Fast** - Thousands of messages/second
- ✅ **Simple** - Easy local development
- ✅ **Python-native** - Great Celery integration
- ❌ **Volatile** - Can lose messages on crash
- ❌ **More infra** - Need to manage Redis instance

### SQS
- ✅ **Always persistent** - Messages written to multiple servers
- ✅ **Never lose messages** - Even if AWS has issues
- ✅ **No infra to manage** - AWS handles replication
- ✅ **Built-in DLQ** - Failed message handling
- ❌ **Slightly slower** - Network calls vs memory
- ❌ **Less introspection** - Can't easily peek at queue state

## For METR's Use Case

Given that:
- Each evaluation could take hours
- Losing evaluation requests = angry researchers
- We need reliable task delivery over microsecond latency

**Recommendation: SQS's durability > Redis's speed**

## Alternative Message Brokers

- **RabbitMQ** - More features, AMQP protocol, more complex
- **Amazon SQS** - Managed, durable, what we're using
- **PostgreSQL** - Can work as broker (slower but persistent)
- **Kafka** - For high-throughput streaming (overkill for METR)