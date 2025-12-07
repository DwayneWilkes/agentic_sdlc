# src/ - Source Code

All production code for the Orchestrator Agent system.

## Module Overview

| Module                                          | Purpose      | Status   |
| ----------------------------------------------- | ------------ | -------- |
| [models/](models/AGENTS.md)                     | Data classes | Complete |
| [core/](core/AGENTS.md)                         | Core logic   | Mostly   |
| [orchestrator/](orchestrator/AGENTS.md)         | Runtime      | Partial  |
| [coordination/](coordination/AGENTS.md)         | NATS bus     | Defined  |
| [agents/](agents/AGENTS.md)                     | Agent impls  | Stub     |
| [self_improvement/](self_improvement/AGENTS.md) | Meta-learn   | TODO     |

## Data Flow

```text
1. Goal string → core/task_parser.py → ParsedTask
2. ParsedTask → core/task_decomposer.py → DAG of subtasks
3. Subtasks → core/team_composer.py → Team of agents
4. Team → orchestrator/agent_runner.py → Execution
5. Results → (future: integration/synthesis)
```

## Import Structure

```python
from src.models import Task, Agent, Team, TaskType
from src.core import TaskParser, TaskDecomposer, TeamComposer
from src.orchestrator import AgentRunner, Orchestrator
from src.coordination import NATSMessageBus
```

## Key Patterns

- **Dataclasses with validation** - Models use `@dataclass` with type hints
- **Protocol-based interfaces** - Loose coupling via Python protocols
- **Async-ready** - NATS bus and runner support async operations
