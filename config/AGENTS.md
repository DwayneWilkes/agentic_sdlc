# config/ - Configuration

Configuration files and persistent agent data.

## Contents

| Path                | Purpose                                |
| ------------------- | -------------------------------------- |
| `agent_memories/`   | Persistent memory journals             |
| `targets.yaml`      | Target repository configuration        |
| `agent_names.json`  | Agent identity and name mappings       |
| `work_history.json` | Agent work completion records          |

## targets.yaml

Defines repositories that agents can work on:

```yaml
default_target: self

targets:
  self:
    name: "Orchestrator (Self)"
    path: "."
    roadmap: "plans/roadmap.md"
  aurora:
    name: "Aurora"
    path: "/path/to/aurora-repo"
    identity_context: "config/identity/anchors.yaml"

task_intake:
  watch_proposals: true
  poll_interval_seconds: 30
```

Managed by `src/core/target_repos.py`.

## agent_names.json

Maps agent IDs to personal names:

```json
{
  "name_pools": {
    "coder": ["Aria", "Atlas", "Nova", ...],
    "orchestrator": ["Conductor", "Maestro", ...]
  },
  "assigned_names": {
    "coder-autonomous-1733409000": {
      "name": "Aria",
      "role": "coder",
      "claimed_at": "2025-12-05T10:30:00"
    }
  }
}
```

Managed by `src/core/agent_naming.py`.

## work_history.json

Tracks phases completed by each agent:

```json
{
  "agents": {
    "Aria": {
      "projects": {
        "agentic_sdlc": {
          "completed": [
            {"phase_id": "1.1", "completed_at": "..."},
            {"phase_id": "1.2", "completed_at": "..."}
          ]
        }
      }
    }
  }
}
```

Managed by `src/core/work_history.py`.

## agent_memories/

Stores agent memory journals as JSON files:

```text
agent_memories/
├── aria.json       # Memory for Aria
├── atlas.json      # Memory for Atlas
└── ...
```

Each file contains:

- Insights (learnings from mistakes and successes)
- Preferences (self-discovered working styles)
- Relationships (observations about other agents)
- Uncertainties (areas still being learned)
- Reflections (end-of-session thoughts)

Example memory entry:

```json
{
  "content": "Always activate venv before running pytest",
  "type": "insight",
  "tags": ["testing", "environment", "learned-from-mistake"],
  "created_at": "2025-12-05T10:30:00Z"
}
```

Managed by `src/core/agent_memory.py`.

## Related

- Memory system: [src/core/agent_memory.py](../src/core/AGENTS.md)
- Agent naming: [src/core/agent_naming.py](../src/core/AGENTS.md)
- Work history: [src/core/work_history.py](../src/core/AGENTS.md)
- Target repos: [src/core/target_repos.py](../src/core/AGENTS.md)
