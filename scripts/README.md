# Scripts

Automation scripts for the Agentic SDLC orchestrator project.

## Available Scripts

### `autonomous_agent.sh`

**Purpose**: Launches the full autonomous development cycle with coder, tech lead, and PM agents.

**Usage**:

```bash
./scripts/autonomous_agent.sh
```

**What it does**:

The script runs **five steps** autonomously:

1. **Step 1: Coder Agent** (via `scripts.agents.coder`)
   - Claims work from `plans/roadmap.md`
   - Follows 6-phase TDD workflow
   - Implements features with tests first
   - Commits completed work

2. **Step 2: Worktree Verification**
   - Checks if coder committed all changes
   - Tech Lead investigates dirty worktree if needed

3. **Step 3: Tech Lead Audit** (via `scripts.agents.tech_lead`)
   - Runs all quality gates (tests, coverage, lint, types)
   - Generates executive summary report
   - Identifies issues and recommendations

4. **Step 4: PM Update** (via `scripts.agents.pm`)
   - Updates all documentation
   - Synchronizes roadmap status
   - Generates project status report

5. **Step 5: Requirements Compliance** (periodic)
   - Runs on Mondays or when `RUN_REQUIREMENTS_CHECK=true`
   - Generates compliance report against requirements.md

**Requirements**:

- Claude Code CLI installed (`claude` command available)
- Python virtual environment at `.venv/`
- Valid roadmap with unclaimed work streams

**Quality Gates Enforced**:

- All tests pass (`pytest tests/ -v`)
- Coverage ≥ 80% (`pytest --cov=src tests/`)
- No linting errors (`ruff check src/ tests/`)
- No type errors (`mypy src/`)

**Output**:

- Colored terminal output showing progress
- Timestamped log file in `agent-logs/{project}/`
- Updated `plans/roadmap.md` with completed work
- New entry in `docs/devlog.md`
- Reports: `docs/qa-audit.md`, `docs/pm-status.md`

**Exit Codes**:

- `0` - Success (work completed and committed)
- `1` - Error (missing dependencies, no work available, etc.)
- Other - Claude Code execution failure

### Python Agent Modules (`scripts/agents/`)

Agent launchers are now Python modules for better maintainability:

```bash
# Run directly
PYTHONPATH=. python -m scripts.agents.coder
PYTHONPATH=. python -m scripts.agents.tech_lead
PYTHONPATH=. python -m scripts.agents.pm
```

#### `agents/coder.py`

6-phase TDD workflow. Uses Sonnet model for cost efficiency.

#### `agents/tech_lead.py`

Quality audit and coder supervision. Uses Opus model for thorough analysis.

```bash
# With dead code analysis
DEAD_CODE_ANALYSIS=true PYTHONPATH=. python -m scripts.agents.tech_lead
```

#### `agents/pm.py`

Project management and documentation updates. Uses Opus model.

#### `agents/base.py`

Base class providing:
- `AgentLauncher` - Shared execution logic
- `AgentConfig` - Configuration dataclass
- Memory system prompts (clean Python, no bash escaping)
- Claude CLI invocation

### `orchestrator.py`

**Purpose**: Main CLI for orchestrator operations.

**Usage**:

```bash
python scripts/orchestrator.py status        # Show roadmap status
python scripts/orchestrator.py agents        # List known agents
python scripts/orchestrator.py dashboard     # Live monitoring
python scripts/orchestrator.py goal "..."    # Natural language goals
python scripts/orchestrator.py run 2.3       # Run specific phase
python scripts/orchestrator.py parallel 2.3 2.6  # Run in parallel
python scripts/orchestrator.py qa            # Quality audit
python scripts/orchestrator.py pm            # Project management
python scripts/orchestrator.py garden        # Unblock phases
```

### `orchestrator-mcp-server.py`

**Purpose**: MCP server providing tools for orchestrator operations.

**Usage**:

```bash
# Run directly
python scripts/orchestrator-mcp-server.py

# Or via MCP client (auto-configured in .claude/mcp-config.json)
```

**Available Tools**:

- `analyze_task(task_description)` - Extract goal, constraints, context, task type
- `decompose_task(task_description, max_depth)` - Break down into subtasks
- `design_team(task_type, subtasks, constraints)` - Design optimal agent teams
- `assign_tasks(agents, subtasks, dependencies)` - Assign tasks optimally
- `track_progress(execution_id)` - Monitor ongoing execution
- `analyze_performance(execution_id)` - Post-execution analysis
- `propose_self_improvement(performance_data)` - Generate improvement proposals

**Available Resources**:

- `orchestrator://roadmap` - Implementation roadmap
- `orchestrator://requirements` - Requirements rubric
- `orchestrator://priorities` - Feature prioritization
- `orchestrator://project-status` - Current project status

### `dead_code_analysis.sh`

**Purpose**: Detect unused code using vulture and ruff.

**Usage**:

```bash
./scripts/dead_code_analysis.sh         # Generate report
./scripts/dead_code_analysis.sh --fix   # Auto-fix unused imports
```

**Output**: `docs/dead-code-report.md`

### `agent-status.sh`

**Purpose**: Quick overview of agent activity and project status.

**Usage**:

```bash
./scripts/agent-status.sh
```

## Running Multiple Autonomous Cycles

To run multiple autonomous agent cycles:

```bash
# Run once
./scripts/autonomous_agent.sh

# Run in a loop until no work remains
while ./scripts/autonomous_agent.sh; do
    echo "Work stream completed. Starting next..."
    sleep 2
done

echo "No more work streams available."
```

## Monitoring Autonomous Execution

```bash
# Watch the devlog
watch -n 2 tail -n 20 docs/devlog.md

# Watch git commits
watch -n 2 git log --oneline -5

# Watch roadmap status
watch -n 2 grep -A 3 "Status:" plans/roadmap.md

# Quick status check
./scripts/agent-status.sh
```

## Environment Variables

| Variable                  | Purpose                    | Default                        |
| ------------------------- | -------------------------- | ------------------------------ |
| `TARGET_PATH`             | Path to target repository  | Current directory              |
| `TARGET_NAME`             | Name for logging           | Directory name                 |
| `SKIP_PM_VERIFY`          | Skip PM verification step  | false                          |
| `SKIP_TL_AUDIT`           | Skip Tech Lead audit       | false                          |
| `RUN_REQUIREMENTS_CHECK`  | Force requirements check   | false (auto on Mondays)        |
| `DEAD_CODE_ANALYSIS`      | Run dead code analysis     | false                          |

## Troubleshooting

### "Claude Code CLI not found"

Install Claude Code CLI from https://github.com/anthropics/claude-code

### "Working tree still dirty after commit attempt"

Manual intervention required:

```bash
git status
git diff
```

### "No work streams available to claim"

All work streams are either completed, blocked, or in progress. Run the PM to unblock phases:

```bash
PYTHONPATH=. python -m scripts.agents.pm
```

## Safety Notes

**The autonomous agent uses `--dangerously-skip-permissions`**

This is necessary for headless operation but means:

- The agent has full file system access
- No permission prompts will be shown
- Review code before running in production

**Safety features built-in:**

- Quality gates prevent broken code from being committed
- TDD workflow ensures tests exist before implementation
- Clear audit trail via devlog and git history
- Working tree verification

## See Also

- [Coder Agent Workflow](../.claude/agents/coder_agent.md)
- [Development Log](../docs/devlog.md)
- [Roadmap](../plans/roadmap.md)
- [AGENTS.md](./AGENTS.md) - Detailed script documentation
