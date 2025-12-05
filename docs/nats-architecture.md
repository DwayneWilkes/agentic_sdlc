# NATS Communication Architecture

## Overview

The orchestrator uses NATS (Neural Autonomy Transport System) for all inter-agent communication. NATS provides:

- **High performance** - Millions of messages per second
- **Simplicity** - Clean pub/sub and request/reply patterns
- **Scalability** - Horizontal scaling with clustering
- **Reliability** - JetStream for persistence and replay
- **Low latency** - Sub-millisecond message delivery

## Architecture

### Subject Hierarchy

All orchestrator messages use a hierarchical subject structure:

```
orchestrator.
├── broadcast.{message_type}          # Broadcast to all agents
├── agent.{agent_id}.{message_type}   # Direct agent communication
├── team.{team_id}.{message_type}     # Team-specific channels
└── queue.{queue_name}                # Work queues for load balancing
```

### Message Types

```python
class MessageType(str, Enum):
    STATUS_UPDATE = "status_update"       # Agent status changes
    TASK_ASSIGNMENT = "task_assignment"   # New task assigned
    TASK_COMPLETE = "task_complete"       # Task finished
    TASK_FAILED = "task_failed"          # Task failed
    QUESTION = "question"                # Agent needs help
    ANSWER = "answer"                    # Response to question
    BLOCKER = "blocker"                  # Agent is blocked
    RESOURCE_REQUEST = "resource_request" # Need shared resource
    RESOURCE_RESPONSE = "resource_response" # Resource granted
    COORDINATION_REQUEST = "coordination_request" # Sync needed
    HEARTBEAT = "heartbeat"              # Agent alive signal
```

### Message Format

All messages use a standard `AgentMessage` structure:

```python
{
    "from_agent": "architect-001",
    "to_agent": "parser-dev-001",  # null for broadcast
    "message_type": "question",
    "content": {
        "question": "What format should Task.constraints use?",
        "context": {...}
    },
    "timestamp": "2025-12-05T14:30:00.000Z",
    "correlation_id": "arch-001-1733409000.123"  # For request/reply
}
```

## Communication Patterns

### 1. Broadcast (Pub/Sub)

One agent sends to all agents:

```python
# Agent broadcasts status update
await bus.broadcast(
    from_agent="architect-001",
    message_type=MessageType.STATUS_UPDATE,
    content={"status": "completed", "component": "task_model"}
)

# Other agents subscribe to broadcasts
await bus.subscribe(
    "orchestrator.broadcast.status_update",
    handle_status_update
)
```

**Use cases**:
- Status updates
- Heartbeats
- Global announcements
- Coordination requests

### 2. Direct Messaging

Point-to-point communication:

```python
# Send directly to specific agent
await bus.send_to_agent(
    from_agent="parser-dev-001",
    to_agent="architect-001",
    message_type=MessageType.QUESTION,
    content={"question": "Is Task model ready?"}
)

# Agent subscribes to its own messages
await bus.subscribe_to_agent_messages(
    "architect-001",
    handle_incoming_message
)
```

**Use cases**:
- Questions between agents
- Dependency notifications
- Specific coordination

### 3. Request/Reply

Synchronous request with timeout:

```python
# Request and wait for reply
response = await bus.request(
    from_agent="decomposer-001",
    to_agent="architect-001",
    message_type=MessageType.RESOURCE_REQUEST,
    content={"resource": "task_model_schema"},
    timeout=5.0
)

print(response.content["schema"])
```

**Use cases**:
- Query shared state
- Request permissions
- Synchronous coordination
- Resource requests

### 4. Work Queues

Load-balanced task distribution:

```python
# Create queue with 3 workers
await bus.create_work_queue(
    queue_name="test_execution",
    callback=run_test,
    num_workers=3
)

# Publish work to queue (round-robin to workers)
for test in tests:
    await bus.publish_to_queue(
        queue_name="test_execution",
        from_agent="test-coordinator",
        message_type=MessageType.TASK_ASSIGNMENT,
        content={"test": test}
    )
```

**Use cases**:
- Parallel test execution
- Distributed builds
- Load-balanced processing
- Scalable task execution

## Example: Phase 1.1 Communication Flow

### Scenario: Parser Developer needs Task model from Architect

```python
# 1. Parser Developer requests Task model
response = await bus.request(
    from_agent="parser-dev-001",
    to_agent="architect-001",
    message_type=MessageType.RESOURCE_REQUEST,
    content={
        "resource": "task_model",
        "reason": "Need to implement TaskParser"
    },
    timeout=10.0
)

# 2. Architect responds with model info
# (automatically handled by NATS request/reply)
# Response contains:
{
    "resource": "task_model",
    "status": "ready",
    "location": "src/models/task.py",
    "api": {
        "class": "Task",
        "fields": ["goal", "constraints", "context", "task_type"],
        "methods": ["to_dict", "from_dict"]
    }
}

# 3. Parser Developer broadcasts completion
await bus.broadcast(
    from_agent="parser-dev-001",
    message_type=MessageType.TASK_COMPLETE,
    content={
        "task": "TaskParser implementation",
        "output": "src/core/task_parser.py",
        "tests": "tests/test_task_parser.py",
        "coverage": "92%"
    }
)

# 4. Decomposer (waiting on Parser) receives notification
# and can now start its work
```

## Integration with Orchestrator

### Agent Lifecycle

Every agent follows this communication pattern:

```python
async def agent_lifecycle():
    # 1. Connect to NATS
    bus = await get_message_bus()

    # 2. Subscribe to messages
    await bus.subscribe_to_agent_messages(
        agent_id="my-agent-001",
        callback=handle_message
    )

    # 3. Send heartbeat
    async def heartbeat_loop():
        while True:
            await bus.broadcast(
                from_agent="my-agent-001",
                message_type=MessageType.HEARTBEAT,
                content={"status": "alive"}
            )
            await asyncio.sleep(30)

    asyncio.create_task(heartbeat_loop())

    # 4. Do work and communicate
    await do_work()

    # 5. Cleanup
    await bus.disconnect()
```

### Orchestrator Monitoring

The orchestrator monitors all agents via NATS:

```python
# Subscribe to all status updates
await bus.subscribe(
    "orchestrator.broadcast.status_update",
    update_agent_status
)

# Subscribe to all failures
await bus.subscribe(
    "orchestrator.broadcast.task_failed",
    handle_task_failure
)

# Subscribe to all blockers
await bus.subscribe(
    "orchestrator.broadcast.blocker",
    resolve_blocker
)
```

## Running NATS

### Local Development

```bash
# Start NATS with Docker Compose
docker-compose up -d nats

# Verify NATS is running
curl http://localhost:8222/varz

# View NATS monitoring UI
open http://localhost:8222
```

### Production

```bash
# NATS cluster with JetStream
docker-compose up -d --scale nats=3
```

## Performance Characteristics

- **Latency**: ~0.5ms per message (local)
- **Throughput**: 1M+ messages/sec per node
- **Pub/Sub**: O(1) routing to subscribers
- **Request/Reply**: Single RTT (~1ms)
- **Queue Groups**: Automatic load balancing

## Best Practices

### 1. Use Appropriate Patterns

- **Broadcast**: Status updates, announcements
- **Direct**: Questions, specific coordination
- **Request/Reply**: Synchronous queries, permissions
- **Queue**: Parallel work distribution

### 2. Handle Timeouts

```python
try:
    response = await bus.request(..., timeout=5.0)
except TimeoutError:
    # Agent might be down, use fallback
    await handle_timeout()
```

### 3. Implement Heartbeats

```python
# Send heartbeat every 30s
# Orchestrator marks agents dead if no heartbeat for 90s
```

### 4. Use Correlation IDs

```python
# For debugging message flows
correlation_id = f"{agent_id}-{timestamp}-{request_id}"
```

### 5. Structure Subjects

```python
# Good: orchestrator.agent.arch-001.question
# Bad: arch-001.question
```

## Comparison to Alternatives

| Feature | NATS | Redis | RabbitMQ | Kafka |
|---------|------|-------|----------|-------|
| Latency | 0.5ms | 1-2ms | 5-10ms | 10-50ms |
| Throughput | 10M/s | 1M/s | 100K/s | 1M/s |
| Complexity | Low | Medium | High | Very High |
| Persistence | JetStream | Pub/Sub | Durable | Built-in |
| Clustering | Native | Sentinel | Native | Native |
| Use Case | Agent comms | Cache+msgs | Enterprise | Event streams |

**Why NATS?**
- Simplest to deploy and operate
- Lowest latency for agent communication
- Built-in request/reply (no custom protocol)
- Excellent Python support (nats-py)
- Scales horizontally with minimal config

## References

- [NATS Documentation](https://docs.nats.io/)
- [nats-py Client](https://github.com/nats-io/nats.py)
- [JetStream Guide](https://docs.nats.io/nats-concepts/jetstream)
- [NATS Monitoring](https://docs.nats.io/running-a-nats-service/nats_admin/monitoring)
