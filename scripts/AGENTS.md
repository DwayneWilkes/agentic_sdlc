# scripts/ - Executable Scripts

Entry points and utilities for running the orchestrator.

## Key Scripts

| Script                       | Purpose                              |
| ---------------------------- | ------------------------------------ |
| `autonomous_agent.sh`        | Run coder agent with 6-phase TDD     |
| `orchestrator.py`            | Run orchestrator with multiple modes |
| `dashboard.py`               | Monitor running agents               |
| `orchestrator-mcp-server.py` | MCP server with orchestrator tools   |

## autonomous_agent.sh

Primary way to run an autonomous coder agent:

```bash
# Run on the orchestrator's own codebase
./scripts/autonomous_agent.sh

# Run on an external repository
TARGET_PATH=/path/to/aurora \
TARGET_NAME=aurora \
./scripts/autonomous_agent.sh
```

### 6-Phase Workflow

The agent follows this workflow automatically:

1. **Phase 0: Identity** - Claim personal name, load memory
2. **Phase 1: Claim** - Find and claim unclaimed work stream
3. **Phase 2: Analyze** - Understand requirements, plan implementation
4. **Phase 3: TDD** - Write tests first, then implementation
5. **Phase 4: Validate** - Run all quality gates
6. **Phase 5: Document** - Update roadmap, write devlog
7. **Phase 6: Commit** - Stage specific files, commit with message

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `TARGET_PATH` | Path to target repository | Current directory |
| `TARGET_NAME` | Name for logging | Directory name |
| `TARGET_ROADMAP` | Roadmap file path | plans/roadmap.md |
| `TARGET_CODER_AGENT` | Coder workflow | .claude/agents/coder_agent.md |
| `TARGET_IDENTITY_CONTEXT` | Identity file to inject | None |

### Signal Handling

- `SIGTERM/SIGINT` - Graceful stop (finish current operation)
- `SIGUSR1` - Immediate stop

## orchestrator.py

Run the orchestrator with different modes:

```bash
# Run parallel agents
python scripts/orchestrator.py parallel -n 3

# Run specific phase
python scripts/orchestrator.py run 1.2

# Run all available work
python scripts/orchestrator.py batch
```

### Commands

- `parallel -n N` - Run N agents in parallel
- `run PHASE_ID` - Run specific work stream
- `batch` - Run all available work
- `status` - Show current status

## dashboard.py

Real-time monitoring of running agents:

```bash
# Interactive dashboard
python scripts/dashboard.py

# One-time status
python scripts/dashboard.py --status

# Watch mode (auto-refresh)
python scripts/dashboard.py --watch
```

Shows:

- Running agents and their status
- Claimed work streams
- Recent completions
- Agent activity

## orchestrator-mcp-server.py

Model Context Protocol server providing tools:

**Tools:**

- `analyze_task` - Parse a goal into structured task
- `decompose_task` - Break into subtasks with dependencies
- `design_team` - Create agent team for task
- `assign_tasks` - Distribute work to agents
- `track_progress` - Monitor execution
- `analyze_performance` - Post-execution analysis
- `propose_self_improvement` - Generate improvement ideas

**Resources:**

- `orchestrator://roadmap` - Current roadmap
- `orchestrator://requirements` - Requirements rubric
- `orchestrator://priorities` - Prioritization analysis
- `orchestrator://project-status` - Current status

### Running the MCP Server

Configured in `.claude/mcp-config.json` - starts automatically with Claude Code.

Manual start:

```bash
python scripts/orchestrator-mcp-server.py
```

## Log Files

All scripts write logs to `agent-logs/{project_name}/`:

```text
agent-logs/
└── agentic_sdlc/
    ├── autonomous-agent-20251205-103000.log
    ├── autonomous-agent-20251205-140000.log
    └── ...
```

Logs include:

- Phase markers (`>>> PHASE 1: Claim - Complete`)
- Quality gate results
- Git operations
- Error messages

## Related

- Orchestrator code: [src/orchestrator/](../src/orchestrator/AGENTS.md)
- Agent workflows: [.claude/agents/](../.claude/agents/)
- MCP config: `.claude/mcp-config.json`
