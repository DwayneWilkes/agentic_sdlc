# scripts/ - Executable Scripts

Entry points and utilities for running the orchestrator.

## Key Scripts

| Script                       | Purpose                                    | Model   |
| ---------------------------- | ------------------------------------------ | ------- |
| `autonomous_agent.sh`        | Orchestrate: coder → Tech Lead → PM verify | -       |
| `coder_agent.sh`             | Run coder agent with 6-phase TDD           | Sonnet  |
| `pm_agent.sh`                | Project management & roadmap sync          | Opus    |
| `tech_lead.sh`               | Coder supervision & quality audits         | Opus    |
| `agent_common.sh`            | Shared utilities (colors, logging, etc.)   | -       |
| `orchestrator.py`            | Run orchestrator with multiple modes       | -       |
| `dashboard.py`               | Monitor running agents                     | -       |
| `orchestrator-mcp-server.py` | MCP server with orchestrator tools         | -       |

## Agent Scripts

### autonomous_agent.sh

Orchestration wrapper that runs the full development cycle:

1. **Step 1**: Run `coder_agent.sh` (6-phase TDD workflow)
2. **Step 2**: Handle commit cleanup if working tree is dirty
3. **Step 3**: Run PM verification for roadmap sync

```bash
# Run on the orchestrator's own codebase
./scripts/autonomous_agent.sh

# Run on an external repository
TARGET_PATH=/path/to/aurora \
TARGET_NAME=aurora \
./scripts/autonomous_agent.sh

# Skip PM verification
SKIP_PM_VERIFY=true ./scripts/autonomous_agent.sh
```

Signal handling:

- `SIGTERM/SIGINT` - Graceful stop (finish current operation)
- `SIGUSR1` - Immediate stop

### coder_agent.sh

Standalone coder agent with 6-phase TDD workflow:

```bash
# Run directly (without orchestration overhead)
./scripts/coder_agent.sh

# On external repository
TARGET_PATH=/path/to/repo ./scripts/coder_agent.sh
```

**The 6 Phases:**

| Phase | Name       | Description                               |
| ----- | ---------- | ----------------------------------------- |
| 0     | Identity   | Claim personal name, load memory          |
| 1     | Claim      | Find and claim unclaimed work stream      |
| 2     | Analyze    | Understand requirements, plan             |
| 3     | TDD        | Write tests first, then implementation    |
| 4     | Validate   | Run all quality gates                     |
| 5     | Document   | Update roadmap, write devlog              |
| 6     | Commit     | Stage specific files, commit with message |

### pm_agent.sh

Project management agent for roadmap maintenance:

```bash
./scripts/pm_agent.sh
```

Tasks:

- Run roadmap gardener (unblock phases)
- Review agent status
- Verify roadmap synchronization
- Generate status report
- Update documentation

### tech_lead.sh

Tech Lead agent for coder supervision and quality assurance:

```bash
./scripts/tech_lead.sh
```

Tasks:

- Supervise coder agents (investigate failures, call back to fix)
- Run all quality gates (tests, coverage, lint, types)
- Generate audit report
- Identify violations and remediation

### agent_common.sh

Shared library sourced by all agent scripts:

```bash
# In agent scripts:
source "$SCRIPT_DIR/agent_common.sh"
```

**Provides:**

- Color constants (`RED`, `GREEN`, `YELLOW`, `BLUE`, `NC`)
- Logging functions (`log_info`, `log_success`, `log_warning`, `log_error`, `log_to_file`)
- Common checks (`require_claude_cli`, `require_file`)
- Setup helpers (`setup_logging`, `resolve_project_paths`)
- Worktree checks (`require_clean_worktree`, `investigate_dirty_worktree`)

**require_clean_worktree:**

Checks if working tree is clean. Returns 1 if dirty.

**investigate_dirty_worktree:**

When coder leaves uncommitted changes, the Tech Lead (Opus) investigates:

- Reads coder's log for context
- Examines dirty files
- Runs quality gates
- Either commits (if complete), calls coder back (if fixable), or escalates to PM

```bash
if ! require_clean_worktree; then
    investigate_dirty_worktree "$CODER_LOG"
fi
```

## Environment Variables

| Variable                  | Purpose                    | Default                        |
| ------------------------- | -------------------------- | ------------------------------ |
| `TARGET_PATH`             | Path to target repository  | Current directory              |
| `TARGET_NAME`             | Name for logging           | Directory name                 |
| `TARGET_ROADMAP`          | Roadmap file path          | plans/roadmap.md               |
| `TARGET_CODER_AGENT`      | Coder workflow             | .claude/agents/coder_agent.md  |
| `TARGET_IDENTITY_CONTEXT` | Identity file to inject    | None                           |
| `SKIP_PM_VERIFY`          | Skip PM verification step  | false                          |

## Model Configuration

Agents use different Claude models based on task complexity:

| Agent Type       | Model       | Rationale                    |
| ---------------- | ----------- | ---------------------------- |
| Coder            | Sonnet 4.5  | Cost efficiency for TDD      |
| Tech Lead        | Opus 4.5    | Thorough analysis, reasoning |
| PM               | Opus 4.5    | Complex reasoning            |
| PM Verification  | Opus 4.5    | Cross-referencing            |

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
    ├── coder-agent-20251205-103000.log
    ├── pm-agent-20251205-140000.log
    ├── tech-lead-agent-20251205-150000.log
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
