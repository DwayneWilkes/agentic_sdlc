# src/coordination/ - Inter-Agent Communication

NATS-based message bus for agent coordination and communication.

## Files

| File           | Purpose                   | Status           |
| -------------- | ------------------------- | ---------------- |
| `nats_bus.py`  | NATSMessageBus impl       | Defined, unwired |

## Current State

The NATS message bus is **implemented but not yet integrated** into the
main execution flow. Agents currently run independently.

## NATSMessageBus

Provides four communication patterns:

### 1. Broadcast

Send messages to all agents:

```python
await bus.broadcast("status_update", {"phase": "starting"})
```

### 2. Direct Messaging

Send to a specific agent:

```python
await bus.send_to_agent(agent_id, "task_assignment", payload)
```

### 3. Request/Reply

Synchronous query with timeout:

```python
response = await bus.request(agent_id, "get_status", timeout=5.0)
```

### 4. Work Queues

Load-balanced task distribution:

```python
await bus.publish_to_queue("tasks", task_payload)
# Multiple workers compete to process
```

## Subject Hierarchy

```text
orchestrator.
├── broadcast.{message_type}     # All agents
├── agent.{agent_id}.{type}      # Direct to agent
├── team.{team_id}.{type}        # Team channel
└── queue.{queue_name}           # Work queues
```

## Integration Plan

Per roadmap Phase 4.x:

1. Wire NATS into AgentRunner
2. Enable real-time status updates
3. Add coordination protocols
4. Support dynamic task reassignment

## Related

- Architecture: [docs/nats-architecture.md](../../docs/nats-architecture.md)
- Docker setup: [docker-compose.yaml](../../docker-compose.yaml) (nats service)
- Examples: [examples/nats_example.py](../../examples/nats_example.py)
