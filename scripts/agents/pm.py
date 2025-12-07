"""PM Agent - Project Management & Roadmap Synchronization.

This agent manages the roadmap, tracks progress, and updates documentation.

Usage:
    python -m scripts.agents.pm
"""

import sys
from pathlib import Path

from scripts.agents.base import AgentConfig, AgentLauncher, get_project_root


class PMLauncher(AgentLauncher):
    """Launcher for the PM agent."""

    def __init__(self, config: AgentConfig):
        config.agent_type = "pm"
        config.model = "opus"  # PM uses Opus for complex reasoning
        super().__init__(config)

    def get_agent_description(self) -> str:
        return "project management workflow"

    def build_prompt(self) -> str:
        """Build the full PM agent prompt."""
        return f'''You are operating as an autonomous Project Manager Agent. Follow the workflow defined in .claude/agents/project_manager.md exactly.

{self.get_naming_prompt("orchestrator")}

{self.get_memory_prompt()}

Your tasks - FULL PROJECT STATUS REVIEW:

## 1. Roadmap Gardening - Run the gardener to unblock phases:

```python
from src.orchestrator.roadmap_gardener import garden_roadmap, check_roadmap_health

# Check health
health = check_roadmap_health()
print(f'Issues found: {{health.get("issues", [])}}')
print(f'Available for work: {{health.get("available_for_work", [])}}')

# Garden (unblock satisfied dependencies)
results = garden_roadmap()
for unblocked in results.get('unblocked', []):
    print(f'Unblocked Phase {{unblocked["id"]}}: {{unblocked["name"]}}')
```

## 2. Agent Status Review - Check all known agents:

```python
from src.core.agent_naming import get_naming

naming = get_naming()
agents = naming.list_assigned_names()

print('\\n=== Agent Status ===')
for agent_id, info in agents.items():
    name = info.get('name')
    phases = info.get('completed_phases', {{}})
    print(f'{{name}}: {{phases}}')
```

## 3. Roadmap Verification - Check recent completions:
- Read docs/devlog.md for recent work
- Verify roadmap.md status matches
- Update any out-of-sync entries

## 4. Progress Report - Generate a status summary:
- Total phases: X
- Completed: Y
- In Progress: Z
- Available to claim: N
- Blockers detected: ...

## 5. Spawn Tech Lead for Quality Audit (if needed):

If there are quality concerns or it's been a while since the last audit:
```python
from src.orchestrator.agent_spawner import spawn_tech_lead

# Spawn Tech Lead for quality audit
print("Spawning Tech Lead for quality audit...")
result = spawn_tech_lead(wait=False)
if result.success:
    print(f"Tech Lead spawned! Log: {{result.log_file}}")
else:
    print(f"Failed to spawn: {{result.error}}")
```

## 6. Create Status Report - Write to docs/pm-status.md:
- Project health summary
- Agent activity
- Blockers and recommendations
- Next priority work
- Spawned agents (if any)

## 7. Update All Documentation - Ensure these files reflect current status:

**Core docs:**
- README.md - Current Status section, Active Agents table, CLI Commands
- NEXT_STEPS.md - Completed phases, claimable phases, agent list
- CLAUDE.md - Implementation Status table if needed
- plans/roadmap.md - Status markers, completion dates

**AGENTS.md files (directory context for agents - CRITICAL to keep current):**
- AGENTS.md (root) - Project overview, key files, getting started
- src/AGENTS.md - Source code structure, module responsibilities
- src/core/AGENTS.md - Core utilities, agent naming, task decomposition
- src/models/AGENTS.md - Data models (Task, Agent, Team)
- src/agents/AGENTS.md - Agent implementations
- src/coordination/AGENTS.md - NATS, handoffs, conflict resolution
- src/orchestrator/AGENTS.md - Orchestration logic, roadmap gardening
- src/self_improvement/AGENTS.md - Meta-learning, self-modification
- tests/AGENTS.md - Test structure, running tests
- scripts/AGENTS.md - Available scripts, usage
- config/AGENTS.md - Configuration files, agent memories
- docs/AGENTS.md - Documentation structure
- plans/AGENTS.md - Roadmap, requirements, priorities

**READMEs (verify these are current):**
- scripts/README.md - All scripts documented
- docs/reviews/README.md - Review format if changed
- agent-logs/README.md - Log format if changed
- config/agent_memories/README.md - Memory format if changed

## 8. Reflect and Save Memory - Before committing:

{self.get_reflection_prompt()}

## 9. Commit all changes (status report + documentation updates).

Begin now.'''


def main() -> int:
    """Main entry point."""
    project_root = get_project_root()

    config = AgentConfig(
        agent_type="pm",
        model="opus",
        project_root=project_root,
    )

    agent = PMLauncher(config)
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
