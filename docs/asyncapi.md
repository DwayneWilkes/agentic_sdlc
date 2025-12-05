# AsyncAPI Specification

This project uses [AsyncAPI](https://www.asyncapi.com/) to document the event-driven communication between autonomous agents.

## Overview

The AsyncAPI specification (`asyncapi.yaml`) defines:

- **Message schemas** - Structure of all inter-agent messages
- **Channels** - NATS subjects and their purpose
- **Message types** - 11 different message types for coordination
- **Content schemas** - Type-specific payload structures

## Why AsyncAPI?

- **NATS-native** - Designed for message-based systems (unlike OpenAPI for HTTP)
- **Validates contracts** - Ensures agents communicate correctly
- **Auto-documentation** - Generates visual documentation
- **Type safety** - Can validate messages in tests
- **Code generation** - Can generate client code (future)

## Specification Location

```
asyncapi.yaml  # Root of project
```

## Channels (NATS Subjects)

### 1. Broadcast Channel

**Subject**: `orchestrator.broadcast.{messageType}`

**Purpose**: One-to-many communication

**Use Cases**:
- Status updates
- Heartbeats
- Global announcements

**Example**:

```python
await bus.broadcast(
    from_agent="architect-001",
    message_type=MessageType.STATUS_UPDATE,
    content={"status": "completed", "component": "task_model"}
)
```

### 2. Direct Agent Channel

**Subject**: `orchestrator.agent.{agentId}.{messageType}`

**Purpose**: Point-to-point communication

**Use Cases**:
- Questions between agents
- Dependency notifications
- Specific coordination

**Example**:

```python
await bus.send_to_agent(
    from_agent="parser-dev-001",
    to_agent="architect-001",
    message_type=MessageType.QUESTION,
    content={"question": "Is Task model ready?"}
)
```

### 3. Team Channel

**Subject**: `orchestrator.team.{teamId}.{messageType}`

**Purpose**: Team-specific communication

**Use Cases**:
- Team coordination
- Shared context
- Team announcements

**Example**:

```python
await bus.publish(
    "orchestrator.team.phase-1-1-team.status_update",
    message
)
```

### 4. Work Queue

**Subject**: `orchestrator.queue.{queueName}`

**Purpose**: Load-balanced task distribution

**Use Cases**:
- Parallel test execution
- Distributed builds
- Scalable processing

**Example**:

```python
await bus.publish_to_queue(
    queue_name="test_execution",
    from_agent="test-coordinator",
    message_type=MessageType.TASK_ASSIGNMENT,
    content={"test": "test_parser.py"}
)
```

## Message Types

The specification defines 11 message types:

| Type | Purpose | Content Schema |
|------|---------|----------------|
| `status_update` | Agent status changes | StatusUpdateContent |
| `task_assignment` | Assign task to agent | TaskAssignmentContent |
| `task_complete` | Task finished successfully | TaskCompleteContent |
| `task_failed` | Task failed | TaskFailedContent |
| `question` | Agent needs help | QuestionContent |
| `answer` | Response to question | AnswerContent |
| `blocker` | Agent is blocked | BlockerContent |
| `resource_request` | Request shared resource | ResourceRequestContent |
| `resource_response` | Resource granted | ResourceResponseContent |
| `coordination_request` | Sync needed | (generic object) |
| `heartbeat` | Agent alive signal | HeartbeatContent |

## Message Schema

All messages follow this structure:

```json
{
  "from_agent": "agent-id",
  "to_agent": "target-agent-id or null",
  "message_type": "status_update",
  "content": {
    "status": "completed",
    "work_stream": "Phase 1.1"
  },
  "timestamp": "2025-12-05T14:30:00.000Z",
  "correlation_id": "optional-request-id"
}
```

## Content Schemas

Each message type has a specific content schema:

### STATUS_UPDATE

```yaml
status: 'starting' | 'in_progress' | 'completed' | 'failed' | 'blocked'
work_stream: string (optional)
component: string (optional)
progress: number 0-100 (optional)
```

### TASK_ASSIGNMENT

```yaml
task: string (required)
description: string (optional)
deadline: ISO 8601 datetime (optional)
priority: 'low' | 'medium' | 'high' | 'critical' (optional)
dependencies: array of strings (optional)
```

### TASK_COMPLETE

```yaml
task: string (required)
status: 'success' | 'partial' (required)
output: string (optional)
files: array of strings (optional)
tests_passed: integer (optional)
coverage: number 0-100 (optional)
```

### BLOCKER

```yaml
blocker: string (required)
work_stream: string (required)
impact: 'low' | 'medium' | 'high' | 'critical' (optional)
suggested_resolution: string (optional)
```

## Using the Specification

### Validation in Tests

You can validate messages against the AsyncAPI spec in tests:

```python
import yaml
from jsonschema import validate

# Load AsyncAPI spec
with open("asyncapi.yaml") as f:
    spec = yaml.safe_load(f)

# Get schema for AgentMessage
schema = spec["components"]["schemas"]["AgentMessagePayload"]

# Validate a message
message = {
    "from_agent": "test-agent",
    "to_agent": None,
    "message_type": "status_update",
    "content": {"status": "completed"},
    "timestamp": "2025-12-05T14:30:00.000Z"
}

validate(instance=message, schema=schema)  # Raises error if invalid
```

### Generating Documentation

Generate HTML documentation from the spec:

```bash
# Install AsyncAPI generator
npm install -g @asyncapi/generator

# Generate HTML docs
ag asyncapi.yaml @asyncapi/html-template -o docs/asyncapi-html

# View docs
open docs/asyncapi-html/index.html
```

### VS Code Integration

Install the [AsyncAPI Preview](https://marketplace.visualstudio.com/items?itemName=asyncapi.asyncapi-preview) extension to:

- Preview the spec visually
- Validate syntax
- Auto-complete channels and schemas

## Message Flow Examples

### Example 1: Task Completion Flow

```
1. Architect completes Task model
   └─> BROADCAST: orchestrator.broadcast.task_complete
       {
         "from_agent": "architect-001",
         "message_type": "task_complete",
         "content": {
           "task": "Task model implementation",
           "status": "success",
           "files": ["src/models/task.py"],
           "tests_passed": 12,
           "coverage": 95
         }
       }

2. Parser Developer receives notification (subscribed to task_complete)
   └─> Starts work on TaskParser

3. Parser Developer requests Task schema
   └─> REQUEST: orchestrator.agent.architect-001.resource_request
       {
         "from_agent": "parser-dev-001",
         "to_agent": "architect-001",
         "message_type": "resource_request",
         "content": {
           "resource": "task_model_schema"
         },
         "correlation_id": "parser-dev-001-1733409000.123"
       }

4. Architect responds with schema
   └─> REPLY: orchestrator.agent.parser-dev-001.resource_response
       {
         "from_agent": "architect-001",
         "to_agent": "parser-dev-001",
         "message_type": "resource_response",
         "content": {
           "resource": "task_model_schema",
           "status": "ready",
           "api": {
             "class": "Task",
             "fields": ["goal", "constraints", "context"]
           }
         },
         "correlation_id": "parser-dev-001-1733409000.123"
       }
```

### Example 2: Blocker Resolution

```
1. Coder Agent encounters blocker
   └─> BROADCAST: orchestrator.broadcast.blocker
       {
         "from_agent": "coder-autonomous-001",
         "message_type": "blocker",
         "content": {
           "blocker": "Missing dependency: Task model",
           "work_stream": "Phase 1.2",
           "impact": "critical"
         }
       }

2. Orchestrator receives blocker notification
   └─> Checks dependency status
   └─> Sees Task model is being worked on by architect-001

3. Orchestrator sends coordination request
   └─> DIRECT: orchestrator.agent.architect-001.coordination_request
       {
         "from_agent": "orchestrator",
         "to_agent": "architect-001",
         "message_type": "coordination_request",
         "content": {
           "request": "prioritize_task_model",
           "blocked_agents": ["coder-autonomous-001"],
           "urgency": "high"
         }
       }
```

## Best Practices

### 1. Always Include Timestamps

```python
from datetime import datetime, timezone

message = AgentMessage(
    from_agent="my-agent",
    message_type=MessageType.STATUS_UPDATE,
    content={"status": "started"},
    timestamp=datetime.now(timezone.utc).isoformat()
)
```

### 2. Use Correlation IDs for Request/Reply

```python
import time

correlation_id = f"{agent_id}-{int(time.time() * 1000)}"

# Request
await bus.request(
    from_agent=agent_id,
    to_agent="target",
    message_type=MessageType.RESOURCE_REQUEST,
    content={"resource": "model"},
    correlation_id=correlation_id  # Same ID in response
)
```

### 3. Validate Content Before Sending

```python
from pydantic import BaseModel, ValidationError

class StatusUpdateContent(BaseModel):
    status: str
    work_stream: str | None = None

# Validate before sending
try:
    content = StatusUpdateContent(
        status="completed",
        work_stream="Phase 1.1"
    )
    await bus.broadcast(
        from_agent=agent_id,
        message_type=MessageType.STATUS_UPDATE,
        content=content.model_dump()
    )
except ValidationError as e:
    logger.error(f"Invalid message content: {e}")
```

### 4. Handle Message Validation Errors

```python
async def handle_message(msg: AgentMessage):
    if msg.message_type == MessageType.TASK_ASSIGNMENT:
        # Validate required fields
        if "task" not in msg.content:
            logger.error(f"Invalid TASK_ASSIGNMENT: missing 'task' field")
            await bus.broadcast(
                from_agent=agent_id,
                message_type=MessageType.TASK_FAILED,
                content={"task": "unknown", "reason": "Invalid message format"}
            )
            return

        # Process valid message
        await process_task(msg.content["task"])
```

## Updating the Specification

When adding new message types or content schemas:

1. **Update asyncapi.yaml**
   - Add new MessageType enum value
   - Define content schema under `components/schemas`
   - Update documentation

2. **Update Python code**
   - Add to `MessageType` enum in `src/coordination/nats_bus.py`
   - Create Pydantic model for content (if complex)
   - Update handlers

3. **Add tests**
   - Test message creation
   - Test validation
   - Test full message flow

4. **Regenerate docs** (if using HTML generator)

```bash
ag asyncapi.yaml @asyncapi/html-template -o docs/asyncapi-html
```

## References

- [AsyncAPI Specification](https://www.asyncapi.com/docs/specifications/latest)
- [NATS Documentation](https://docs.nats.io/)
- [Message Bus Implementation](../src/coordination/nats_bus.py)
- [NATS Architecture](./nats-architecture.md)
- [Communication Examples](../examples/nats_example.py)

## Tools

### AsyncAPI Generator

Generate docs, code, and more from the spec:

```bash
npm install -g @asyncapi/generator
ag asyncapi.yaml @asyncapi/html-template -o docs/asyncapi-html
ag asyncapi.yaml @asyncapi/markdown-template -o docs/asyncapi.md
```

### AsyncAPI Studio

Web-based editor and visualizer:

```bash
# Open in browser
npx @asyncapi/studio asyncapi.yaml
```

Or use the online version: https://studio.asyncapi.com/

### Validation

Validate the spec:

```bash
npm install -g @asyncapi/cli
asyncapi validate asyncapi.yaml
```

## See Also

- [NATS Setup Guide](./NATS_SETUP.md)
- [Coder Agent Workflow](../.claude/agents/coder_agent.md)
- [Development Strategy](../plans/subagent-development-strategy.md)
