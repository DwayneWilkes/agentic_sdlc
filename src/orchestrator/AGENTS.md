# src/orchestrator/ - Orchestrator Runtime

Runtime coordination, execution, and monitoring of agent teams.

## Files

| File                  | Purpose                         | Status   |
| --------------------- | ------------------------------- | -------- |
| `orchestrator.py`     | Main coordinator class          | Complete |
| `agent_runner.py`     | Execute agents via Claude CLI   | Complete |
| `dashboard.py`        | Real-time progress display      | Complete |
| `goal_interpreter.py` | Interpret goals into plans      | Complete |
| `roadmap_gardener.py` | Auto-unblock roadmap phases     | Complete |
| `work_stream.py`      | Parse and prioritize work       | Complete |

## Key Classes

### Orchestrator

Top-level coordinator that ties everything together:

- Receives goals from user
- Delegates to parser, decomposer, composer
- Manages agent execution (sequential, parallel, batch)
- Verifies work completion
- Supports multi-repo orchestration via target_id

### AgentRunner

Executes agents using Claude CLI:

- Spawns Claude processes with prompts
- Monitors execution status
- Captures output
- Handles timeouts and failures
- Supports agent reuse with context
- Multi-repo support via target_id

```python
# Spawn for external repository
agent = runner.spawn_agent(
    work_stream=work_stream,
    target_id="aurora"  # External repo
)
```

### Dashboard

Terminal-based progress visualization:

- Real-time agent status
- Claimed work streams from roadmap
- Task completion tracking
- Agent activity detection

### RoadmapGardener

Maintains roadmap.md automatically:

- Detects completed phases
- Unblocks dependent phases when dependencies met
- Updates status markers
- Health checks for roadmap consistency

### GoalInterpreter

Translates user goals into work:

- Matches goals to work streams
- Identifies relevant phases
- Provides recommendations

### WorkStream

Parses roadmap into structured work:

- Status tracking (Not Started, In Progress, Complete, Blocked)
- Dependency resolution
- Priority ordering
- Bootstrap phase identification

## Execution Flow

```text
Orchestrator.run(goal)
    → GoalInterpreter.interpret(goal)
    → Find matching work streams
    → AgentRunner.spawn_agent(work_stream, target_id)
        → Construct prompt with 6-phase workflow
        → Spawn Claude CLI process
        → Pass TARGET_* environment variables
        → Monitor progress
        → Collect results
    → Verify completion (quality gates)
    → (Future) Synthesize outputs
```

## Agent Execution

Agents are run via the Claude CLI:

```bash
claude -p --dangerously-skip-permissions "$PROMPT"
```

The runner manages:

- Prompt construction with context
- Working directory setup (per target)
- Output capture
- Error handling
- Environment variables for multi-repo support

### Multi-Repo Execution

When target_id is specified, the runner:

1. Loads target config from `config/targets.yaml`
2. Sets working directory to target path
3. Passes TARGET_* environment variables
4. Uses target's roadmap, coder_agent, etc.

## Agent Workflows

Agents follow workflows defined in `.claude/agents/`:

- `coder_agent.md` - 6-phase TDD workflow
- `project_manager.md` - Roadmap verification
- `qa_agent.md` - Quality gate audits
- `orchestrator_agent.md` - Team coordination

## Related

- Uses: [core/](../core/AGENTS.md) for parsing/decomposition
- Uses: [models/](../models/AGENTS.md) for data structures
- Uses: [coordination/](../coordination/AGENTS.md) for NATS messaging
- Entry point: [scripts/autonomous_agent.sh](../../scripts/AGENTS.md)
- Agent workflows: [.claude/agents/](../../.claude/agents/)
