# Agentic SDLC - Orchestrator Agent

An autonomous orchestrator agent system that decomposes complex tasks, designs specialized subagent teams, and coordinates parallel execution with recursive self-improvement.

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Check project status
python scripts/orchestrator.py status

# Run a development phase
python scripts/orchestrator.py run 2.3
```

## What is This?

The Orchestrator Agent is a meta-agent system for general problem-solving. Give it a task, and it will:

1. Analyze and decompose the task
2. Design the right team of specialized agents
3. Execute subtasks in parallel
4. Integrate results into a final solution
5. Learn and improve from each execution

This project is being built by its own subagent team - a practical proof of the orchestrator's design.

## Current Status

### Phase 1: Foundation - COMPLETE

| Phase | Name | Agent | Status |
|-------|------|-------|--------|
| 1.1 | Core Data Models | - | Done |
| 1.2 | Task Analysis & Parser | Aria | Done |
| 1.3 | Task Decomposition Engine | Atlas | Done |
| 1.4 | Agent Role Registry | Nexus | Done |
| 10.5 | Recurrent Refinement | Sage | Done |

**Current Coverage:** 61% (target: 80%)

See [NEXT_STEPS.md](NEXT_STEPS.md) for what to work on next.

## CLI Commands

```bash
# Status and monitoring
python scripts/orchestrator.py status        # Show roadmap status
python scripts/orchestrator.py agents        # List known agents
python scripts/orchestrator.py dashboard     # Live monitoring

# Agent spawning
python scripts/orchestrator.py goal "..."    # Natural language goals
python scripts/orchestrator.py run 2.3       # Run specific phase
python scripts/orchestrator.py parallel 2.3 2.6  # Run phases in parallel

# Specialized agents
python scripts/orchestrator.py qa            # Quality audit
python scripts/orchestrator.py pm            # Project management

# Maintenance
python scripts/orchestrator.py garden        # Unblock satisfied phases
```

## Documentation

- [NEXT_STEPS.md](NEXT_STEPS.md) - Current status and immediate actions
- [CLAUDE.md](CLAUDE.md) - Full project documentation for AI assistants
- [Requirements Rubric](plans/requirements.md) - Design and evaluation criteria
- [Implementation Roadmap](plans/roadmap.md) - Development phases
- [Feature Priorities](plans/priorities.md) - Strategic analysis

## Architecture

The orchestrator follows a modular design with 15 core capability areas:

- Task Analysis & Decomposition
- Team Design & Agent Selection
- Task Assignment & Parallelization
- Coordination & Communication
- Monitoring & Progress Tracking
- Error Handling & Resilience
- Integration & Synthesis
- Self-Improvement & Meta-Learning
- And more...

See [plans/requirements.md](plans/requirements.md) for complete details.

## Active Agents

Agents build experience across sessions and retain their names:

| Name | Role | Completed Phases |
|------|------|------------------|
| Aria | coder | 1.2 |
| Atlas | coder | 1.3 |
| Nexus | coder | 1.4 |
| Sage | coder | 10.5 |

## License

TBD
