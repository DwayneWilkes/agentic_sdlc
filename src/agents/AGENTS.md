# src/agents/ - Agent Implementations

Specialized agent implementations for different roles.

## Current State

**Placeholder** - Agent logic is currently embedded in prompts rather than code.

Agents are executed via Claude CLI with role-specific prompts constructed
by the orchestrator. Reserved for future implementations:

- Custom agent logic beyond prompts
- Specialized tools per agent type
- Agent-specific state management
- Role-specific behaviors

## Planned Agent Types

From `core/role_registry.py`:

| Role                | Purpose                      |
| ------------------- | ---------------------------- |
| `software_engineer` | Write and modify code        |
| `architect`         | Design systems and APIs      |
| `qa_engineer`       | Test and verify quality      |
| `researcher`        | Investigate and analyze      |
| `technical_writer`  | Documentation                |
| `devops`            | Infrastructure / deployment  |

## Current Execution Model

Agents are currently "prompt-only" - the AgentRunner constructs a prompt with:

- Role description
- Task assignment
- Context (memory, previous work)
- Constraints

And executes via:

```bash
claude --print "You are a {role}. {task}..."
```

## Future Direction

As the orchestrator matures, agents may become more autonomous with:

- Persistent state
- Tool use policies
- Learning from feedback
- Inter-agent protocols

## Related

- Execution: [orchestrator/agent_runner.py](../orchestrator/AGENTS.md)
- Roles: [core/role_registry.py](../core/AGENTS.md)
- Memory: [core/agent_memory.py](../core/AGENTS.md)
