# src/models/ - Data Models

Core data structures used throughout the orchestrator system.

## Files

| File        | Purpose                             |
| ----------- | ----------------------------------- |
| `task.py`   | Task and ParsedTask dataclasses     |
| `agent.py`  | Agent dataclass with capabilities   |
| `team.py`   | Team dataclass grouping agents      |
| `enums.py`  | TaskType, AgentState, other enums   |

## Key Classes

### Task / ParsedTask

```python
@dataclass
class ParsedTask:
    goal: str
    task_type: TaskType
    constraints: list[str]
    context: dict
    subtasks: list[str]  # After decomposition
```

### Agent

```python
@dataclass
class Agent:
    id: str
    name: str  # Human-friendly name from agent_naming
    role: str
    capabilities: list[str]
    state: AgentState
```

### Team

```python
@dataclass
class Team:
    id: str
    agents: list[Agent]
    task_assignments: dict[str, str]  # agent_id -> task_id
```

## Related

- Created by: [core/task_parser.py](../core/AGENTS.md)
- Used by: [orchestrator/agent_runner.py](../orchestrator/AGENTS.md)
- Enums defined in `enums.py` include `TaskType` (SOFTWARE, RESEARCH, ANALYSIS, etc.)
