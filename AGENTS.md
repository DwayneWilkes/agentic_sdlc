# Agentic SDLC - Agent Context

> This file provides context for LLM agents working on this codebase.

## Project Purpose

This is an **Orchestrator Agent** system - a meta-agent that:

- Decomposes complex tasks into work streams
- Designs specialized teams of subagents
- Coordinates parallel execution
- Tracks work history and agent experience
- Supports multi-repository orchestration
- Recursively self-improves

## Quick Orientation

| Directory                          | Purpose                               |
| ---------------------------------- | ------------------------------------- |
| [src/](src/AGENTS.md)              | Source code - start here              |
| [plans/](plans/AGENTS.md)          | Requirements, roadmap, design docs    |
| [tests/](tests/AGENTS.md)          | Test suite mirroring src/             |
| [scripts/](scripts/AGENTS.md)      | Executable scripts and MCP server     |
| [docs/](docs/AGENTS.md)            | Architecture docs and guides          |
| [config/](config/AGENTS.md)        | Configuration, memories, targets      |
| [.claude/agents/](.claude/agents/) | Agent workflow definitions            |

## Key Documents

- **[requirements.md](plans/requirements.md)** - The orchestrator "rubric" (15 capability areas)
- **[roadmap.md](plans/roadmap.md)** - Implementation phases with status
- **[priorities.md](plans/priorities.md)** - Feature prioritization rationale
- **[CLAUDE.md](CLAUDE.md)** - Full project documentation for humans

## Agent Workflows

Autonomous agents follow these workflows:

| Agent | Workflow File | Purpose |
|-------|--------------|---------|
| Coder | [coder_agent.md](.claude/agents/coder_agent.md) | Claim work, TDD, commit |
| PM | [project_manager.md](.claude/agents/project_manager.md) | Roadmap verification |
| Tech Lead | [tech_lead.md](.claude/agents/tech_lead.md) | Coder supervision, quality audits |
| Orchestrator | [orchestrator_agent.md](.claude/agents/orchestrator_agent.md) | Team coordination |

### 6-Phase Coder Workflow

Coder agents follow this workflow for each work stream:

1. **Claim** - Find and claim an unclaimed work stream from roadmap
2. **Analyze** - Understand requirements, plan implementation
3. **TDD** - Write tests first, then implementation
4. **Validate** - Run all quality gates (tests, coverage, lint, types)
5. **Document** - Update roadmap, write devlog entry
6. **Commit** - Stage specific files, descriptive commit message

## Current Implementation Status

**Batch 1 Complete (100%)** - Foundation phases done.
**Overall: ~25% complete** - Core working, many advanced features TODO.

### What Works

- Task parsing and decomposition with dependency graphs
- Team composition based on task type
- Agent execution via Claude CLI with 6-phase workflow
- Agent memory (persistent journal) and personal naming
- Work history tracking per agent/project
- NATS message bus (defined, patterns documented)
- Roadmap gardening (auto-unblock phases when dependencies met)
- Multi-repo support (target repositories via config/targets.yaml)
- Dashboard for monitoring agents

### What's Missing

- Full parallel execution coordination
- Error handling and recovery workflows
- Output integration/synthesis
- Self-improvement loop
- Resource management

## Architecture Pattern

```text
User Goal
    ↓
GoalInterpreter → TaskParser → TaskDecomposer → TeamComposer → AgentRunner
    ↓                 ↓              ↓               ↓              ↓
 Interpreted      ParsedTask    DAG of          Team of        Execution
   Goal                        Subtasks         Agents         Results
```

## Agent Identity System

Agents have personal names and persistent memory:

```python
from src.core.agent_naming import claim_agent_name
from src.core.agent_memory import get_memory

# Claim a personal name
name = claim_agent_name("agent-123", role="coder")  # e.g., "Aria"

# Access memory
memory = get_memory(name)
memory.record_insight("Always check dependencies before coding")
```

Names persist across sessions. Memory includes insights, preferences, relationships.

## Multi-Repo Support

Agents can work on external repositories:

```python
from src.core.target_repos import get_target

# Get target configuration
target = get_target("aurora")  # External repo
print(f"Roadmap: {target.get_roadmap_path()}")
```

Configure targets in `config/targets.yaml`.

## Development Conventions

1. **Tests first** - Every module has corresponding tests in `tests/`
2. **Type hints** - All functions have type annotations
3. **Docstrings** - Public functions document purpose, args, returns
4. **Feature branches** - Self-improvement and risky changes use branches
5. **6-phase workflow** - Claim → Analyze → TDD → Validate → Document → Commit

## Running Things

```bash
# Activate venv
source .venv/bin/activate

# Run tests
pytest tests/

# Start NATS (for coordination)
docker-compose up -d nats

# Run autonomous agent
./scripts/autonomous_agent.sh

# Run with parallel agents
python scripts/orchestrator.py parallel -n 3

# Monitor agents
python scripts/dashboard.py
```

## Quality Gates

All code must pass before commit:

- `pytest tests/ -v` - All tests pass
- `pytest --cov=src tests/` - Coverage ≥ 80%
- `ruff check src/ tests/` - No linting errors
- `mypy src/` - No type errors

## Related Files

- [CLAUDE.md](CLAUDE.md) - Detailed project documentation
- [nats-architecture.md](docs/nats-architecture.md) - Inter-agent comms
- [subagent-development-strategy.md](plans/subagent-development-strategy.md) - Building with agents
- [targets.yaml](config/targets.yaml) - Multi-repo configuration
