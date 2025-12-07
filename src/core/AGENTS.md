# src/core/ - Core Orchestration Logic

The brain of the orchestrator - parsing, decomposition, team design.

## Files

| File                   | Purpose                          | Status   |
| ---------------------- | -------------------------------- | -------- |
| `task_parser.py`       | Parse goals into ParsedTask      | Complete |
| `task_decomposer.py`   | Break tasks into subtask DAGs    | Complete |
| `team_composer.py`     | Design agent teams               | Complete |
| `role_registry.py`     | Available agent roles            | Complete |
| `agent_memory.py`      | Persistent memory journal        | Complete |
| `agent_naming.py`      | Human-friendly agent names       | Complete |
| `work_history.py`      | Track work history               | Complete |
| `recurrent_refiner.py` | Iterative output refinement      | Complete |
| `target_repos.py`      | Target repository configuration  | Complete |

## Key Classes

### TaskParser

Extracts structured information from natural language goals:

- Goal identification
- Task type classification (SOFTWARE, RESEARCH, etc.)
- Constraint extraction
- Context gathering

### TaskDecomposer

Creates dependency graphs of subtasks:

- Recursive decomposition
- Dependency detection
- Parallelization opportunities
- Returns DAG structure

### TeamComposer

Designs teams based on task requirements:

- Role selection from registry
- Capability matching
- Team size optimization
- Agent assignment

### AgentMemory

Persistent memory for agents across sessions:

- Journal entries (observations, decisions, learnings)
- Memory retrieval by relevance
- Cross-session continuity

### AgentNaming

Human-friendly names for agents:

- Consistent naming per agent ID
- Personality-appropriate names
- Memorable identifiers

### WorkHistory

Tracks work completed by agents across projects:

- Phase completion records per agent/project
- Query by agent name or project
- Separated from identity (agent_naming)

### TargetRepository / TargetManager

Multi-repository support:

- Define external codebases to work on
- Path resolution for roadmap, devlog, etc.
- Identity context injection
- Configured via `config/targets.yaml`

## Data Flow

```text
"Build a REST API"
    → TaskParser.parse()
    → ParsedTask(type=SOFTWARE, constraints=[...])
    → TaskDecomposer.decompose()
    → [Subtask1, Subtask2, ...] with dependencies
    → TeamComposer.compose()
    → Team(agents=[SWE, Architect, QA])
```

## Related

- Uses models from: [models/](../models/AGENTS.md)
- Called by: [orchestrator/](../orchestrator/AGENTS.md)
- Role definitions: `role_registry.py` contains all available agent roles
