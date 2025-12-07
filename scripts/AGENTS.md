# scripts/ - Executable Scripts

Entry points and utilities for running the orchestrator.

## Key Scripts

| Script                       | Purpose                                    | Model   |
| ---------------------------- | ------------------------------------------ | ------- |
| `autonomous_agent.sh`        | Orchestrate: coder → Tech Lead → PM verify | -       |
| `agents/coder.py`            | Run coder agent with 6-phase TDD           | Sonnet  |
| `agents/pm.py`               | Project management & roadmap sync          | Opus    |
| `agents/tech_lead.py`        | Coder supervision & quality audits         | Opus    |
| `agent_common.sh`            | Shared utilities (colors, logging, etc.)   | -       |
| `orchestrator.py`            | Run orchestrator with multiple modes       | -       |
| `dashboard.py`               | Monitor running agents                     | -       |
| `orchestrator-mcp-server.py` | MCP server with orchestrator tools         | -       |

## Agent Scripts

### autonomous_agent.sh

Orchestration wrapper that runs the full development cycle:

1. **Step 1**: Run coder agent (6-phase TDD workflow) via `scripts.agents.coder`
2. **Step 2**: Verify clean worktree (Tech Lead investigates if dirty)
3. **Step 3**: Run Tech Lead quality audit via `scripts.agents.tech_lead`
4. **Step 4**: Run PM documentation update via `scripts.agents.pm`
5. **Step 5**: Requirements compliance check (periodic)

```bash
# Run on the orchestrator's own codebase
./scripts/autonomous_agent.sh

# Run on an external repository
TARGET_PATH=/path/to/aurora \
TARGET_NAME=aurora \
./scripts/autonomous_agent.sh

# Skip PM verification
SKIP_PM_VERIFY=true ./scripts/autonomous_agent.sh

# Force requirements check
RUN_REQUIREMENTS_CHECK=true ./scripts/autonomous_agent.sh
```

Signal handling:

- `SIGTERM/SIGINT` - Graceful stop (finish current operation)
- `SIGUSR1` - Immediate stop

### Python Agent Modules (scripts/agents/)

Agent launchers are Python modules for better maintainability:

```bash
# Run agents directly (or via autonomous_agent.sh)
PYTHONPATH=. python -m scripts.agents.coder
PYTHONPATH=. python -m scripts.agents.tech_lead
PYTHONPATH=. python -m scripts.agents.pm
```

#### agents/coder.py

6-phase TDD workflow for implementing roadmap items:

```bash
# Work on next roadmap item
PYTHONPATH=. python -m scripts.agents.coder

# On external repository
TARGET_PATH=/path/to/repo PYTHONPATH=. python -m scripts.agents.coder
```

**The 6 Phases:**

| Phase | Name       | Description                               |
| ----- | ---------- | ----------------------------------------- |
| 0     | Identity   | Claim personal name, load memory          |
| 1     | Claim/Task | Claim roadmap work OR use TASK if set     |
| 2     | Analyze    | Understand requirements, plan             |
| 3     | TDD        | Write tests first, then implementation    |
| 4     | Validate   | Run all quality gates                     |
| 5     | Document   | Update roadmap, write devlog              |
| 6     | Commit     | Stage specific files, commit with message |

#### agents/pm.py

Project management agent for roadmap maintenance:

```bash
PYTHONPATH=. python -m scripts.agents.pm
```

Tasks:

- Run roadmap gardener (unblock phases)
- Review agent status
- Verify roadmap synchronization
- Generate status report
- Update all AGENTS.md documentation files

#### agents/tech_lead.py

Tech Lead agent for coder supervision and quality assurance:

```bash
PYTHONPATH=. python -m scripts.agents.tech_lead

# With dead code analysis
DEAD_CODE_ANALYSIS=true PYTHONPATH=. python -m scripts.agents.tech_lead
```

Tasks:

- Supervise coder agents (investigate failures, call back to fix)
- Run all quality gates (tests, coverage, lint, types)
- Generate audit report (docs/qa-audit.md)
- Identify violations and remediation

#### agents/base.py

Base class for all agent launchers providing:

- `AgentLauncher` - Base class with logging, prompt building, execution
- `AgentConfig` - Configuration dataclass
- Memory system prompts (no more bash escape hell!)
- Claude CLI invocation

### agent_common.sh

Shared library sourced by the orchestrator:

```bash
# In autonomous_agent.sh:
source "$SCRIPT_DIR/agent_common.sh"
```

**Provides:**

- Color constants (`RED`, `GREEN`, `YELLOW`, `BLUE`, `NC`)
- Logging functions (`log_info`, `log_success`, `log_warning`, `log_error`, `log_to_file`)
- Common checks (`require_claude_cli`, `require_file`)
- Setup helpers (`setup_logging`, `resolve_project_paths`)
- Worktree checks (`require_clean_worktree`, `investigate_dirty_worktree`)

## Environment Variables

| Variable                  | Purpose                    | Default                        |
| ------------------------- | -------------------------- | ------------------------------ |
| `TASK`                    | Ad-hoc task for coder      | None (use roadmap)             |
| `TARGET_PATH`             | Path to target repository  | Current directory              |
| `TARGET_NAME`             | Name for logging           | Directory name                 |
| `TARGET_ROADMAP`          | Roadmap file path          | plans/roadmap.md               |
| `TARGET_CODER_AGENT`      | Coder workflow             | .claude/agents/coder_agent.md  |
| `TARGET_IDENTITY_CONTEXT` | Identity file to inject    | None                           |
| `SKIP_PM_VERIFY`          | Skip PM verification step  | false                          |
| `SKIP_TL_AUDIT`           | Skip Tech Lead audit       | false                          |
| `RUN_REQUIREMENTS_CHECK`  | Force requirements check   | false (auto on Mondays)        |
| `DEAD_CODE_ANALYSIS`      | Run dead code analysis     | false                          |

## Model Configuration

Agents use different Claude models based on task complexity:

| Agent Type       | Model       | Rationale                    |
| ---------------- | ----------- | ---------------------------- |
| Coder            | Sonnet 4.5  | Cost efficiency for TDD      |
| Tech Lead        | Opus 4.5    | Thorough analysis, reasoning |
| PM               | Opus 4.5    | Complex reasoning            |

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
    ├── tech_lead-agent-20251205-150000.log
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
