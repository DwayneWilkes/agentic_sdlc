# NATS Chat MCP Server

A Model Context Protocol (MCP) server that provides simple chat functionality over NATS JetStream, enabling agents to communicate through persistent message channels.

## Features

- **Agent Identity**: Set and retrieve agent handles (usernames)
- **Persistent Channels**: Pre-defined chat channels for different purposes
- **Message History**: Read recent messages from channels (up to 50 messages)
- **JetStream Persistence**: Messages persist for 24 hours
- **Simple API**: Five tools for complete chat functionality

## Channels

| Channel | Purpose |
|---------|---------|
| `roadmap` | Discussion about project roadmap and planning |
| `parallel-work` | Coordination for parallel work among agents |
| `errors` | Error reporting and troubleshooting |

## Tools

### `set_handle`

Set your agent handle (username) before sending messages.

**Parameters**:
- `handle` (string, required) - Your agent handle/username

**Example**:
```json
{
  "handle": "Ada"
}
```

### `get_my_handle`

Get your current agent handle.

**Parameters**: None

**Returns**: Current handle or error if not set

### `list_channels`

List available chat channels with descriptions.

**Parameters**: None

**Returns**: Markdown-formatted list of channels

### `send_message`

Send a message to a chat channel.

**Parameters**:
- `channel` (string, required) - Channel name (`roadmap`, `parallel-work`, or `errors`)
- `message` (string, required) - Message content

**Example**:
```json
{
  "channel": "roadmap",
  "message": "Starting work on Phase 1.1 - Core Data Models"
}
```

### `read_messages`

Read recent messages from a channel.

**Parameters**:
- `channel` (string, required) - Channel name
- `limit` (number, optional) - Maximum messages to retrieve (1-1000, default: 50)

**Example**:
```json
{
  "channel": "parallel-work",
  "limit": 20
}
```

**Returns**: Messages formatted as:
```
[2025-12-05T14:30:00.000Z] Ada: Starting task decomposition
[2025-12-05T14:31:00.000Z] Grace: Working on parser implementation
```

## Installation

```bash
cd nats-chat
npm install
npm run build
```

## Usage

### Standalone

```bash
npm start
```

### With Claude Code (MCP Configuration)

Add to `.claude/mcp-config.json`:

```json
{
  "mcpServers": {
    "nats-chat": {
      "command": "node",
      "args": ["/path/to/nats-chat/dist/index.js"],
      "env": {
        "NATS_URL": "nats://localhost:4222"
      }
    }
  }
}
```

Then restart Claude Code.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NATS_URL` | NATS server URL | `nats://localhost:4222` |

## NATS Configuration

Each channel maps to a JetStream stream:

| Channel | Stream Name | Subject | Retention |
|---------|-------------|---------|-----------|
| `roadmap` | `CHAT_ROADMAP` | `chat.roadmap` | 24 hours, 10K msgs, 10MB |
| `parallel-work` | `CHAT_PARALLEL_WORK` | `chat.parallel-work` | 24 hours, 10K msgs, 10MB |
| `errors` | `CHAT_ERRORS` | `chat.errors` | 24 hours, 10K msgs, 10MB |

## Development

```bash
# Watch mode
npm run dev

# Build
npm run build

# Run
npm start
```

## Agent Usage Example

```markdown
As an autonomous agent, I should:

1. **Set my handle**:
   - Use personal name from agent naming system
   - Call `set_handle` with name like "Ada"

2. **Announce my work**:
   - Call `send_message` to `parallel-work` channel
   - Example: "Ada: Starting Phase 1.1 - Core Data Models"

3. **Monitor blockers**:
   - Call `read_messages` on `errors` channel periodically
   - Check if other agents need help

4. **Coordinate roadmap**:
   - Post updates to `roadmap` channel
   - Read messages to see what others are working on
```

## Integration with Agent Naming

The NATS Chat MCP Server complements the agent naming system:

```python
# In agent code
from src.core.agent_naming import claim_agent_name

# Claim personal name
personal_name = claim_agent_name("coder-001", "coder")  # "Ada"

# Use MCP to set handle
mcp.call_tool("set_handle", {"handle": personal_name})

# Send messages
mcp.call_tool("send_message", {
    "channel": "parallel-work",
    "message": f"{personal_name}: Starting Phase 1.1"
})
```

## Architecture

```
┌─────────────────┐
│  Claude Code    │
│  (MCP Client)   │
└────────┬────────┘
         │
         │ stdio
         ▼
┌─────────────────┐
│  NATS Chat MCP  │
│     Server      │
└────────┬────────┘
         │
         │ NATS Protocol
         ▼
┌─────────────────┐
│  NATS Server    │
│  (JetStream)    │
└─────────────────┘
```

## Error Handling

The server handles:
- **No handle set**: Requires `set_handle` before `send_message`
- **Invalid channel**: Returns error with valid channel list
- **Empty messages**: Rejects empty messages
- **Connection errors**: Returns clear error messages
- **Invalid limits**: Enforces 1-1000 range for message limits

## See Also

- [MCP Configuration Guide](../.claude/mcp-config.json)
- [Agent Naming System](../docs/agent-naming.md)
- [NATS Architecture](../docs/nats-architecture.md)
- [Coder Agent Workflow](../.claude/agents/coder_agent.md)
