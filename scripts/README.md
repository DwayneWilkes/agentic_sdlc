# Scripts

Automation scripts for the Agentic SDLC orchestrator project.

## Available Scripts

### `autonomous_agent.sh`

**Purpose**: Launches Claude Code in headless mode to autonomously complete the next work stream from the roadmap using the TDD agent workflow.

**Usage**:

```bash
./scripts/autonomous_agent.sh
```

**What it does**:

The script runs **three phases** autonomously:

1. **Phase 1: TDD Workflow Execution**
   - Reads `plans/roadmap.md` and identifies next unclaimed work stream
   - Claims work and marks as "In Progress" with agent assignment
   - Follows all 6 phases from `.claude/agents/coder_agent.md`:
     - Phase 1: Claim Work Stream
     - Phase 2: Analysis & Planning
     - Phase 3: Test-Driven Development (tests first!)
     - Phase 4: Integration & Validation (quality gates)
     - Phase 5: Documentation (devlog, roadmap)
     - Phase 6: Commit (atomic, descriptive)

2. **Phase 2: Auto-Commit** (if needed)
   - Checks if working tree is dirty after Phase 1
   - Spawns another Claude Code instance to review and commit remaining changes
   - Creates descriptive commit message based on devlog and roadmap

3. **Phase 3: Roadmap Verification**
   - Verifies roadmap status is accurately updated
   - Checks if work stream is marked as "✅ Complete"
   - Updates roadmap if synchronization is needed
   - Uses Project Manager agent from `.claude/agents/project_manager.md`

**Requirements**:

- Claude Code CLI installed (`claude` command available)
- Clean working tree recommended (but not required)
- Valid roadmap with unclaimed work streams

**Quality Gates Enforced**:

- ✅ All tests pass (`pytest tests/ -v`)
- ✅ Coverage ≥ 80% (`pytest --cov=src tests/`)
- ✅ No linting errors (`ruff check src/ tests/`)
- ✅ No type errors (`mypy src/`)

**Output**:

- Colored terminal output showing progress for each phase
- Timestamped log file in `agent-logs/autonomous-agent-YYYYMMDD-HHMMSS.log`
- Updated `plans/roadmap.md` with completed work (verified in Phase 3)
- New entry in `docs/devlog.md`
- Git commit with implemented feature

**Example Output**:

```
[INFO] Starting Autonomous Agent...
[INFO] Project Root: /home/user/agentic_sdlc
[INFO] Roadmap: /home/user/agentic_sdlc/plans/roadmap.md
[INFO] Log File: /home/user/agentic_sdlc/agent-logs/autonomous-agent-20251205-143000.log
[INFO] Executing TDD workflow...
[SUCCESS] Claude Code execution completed
[INFO] Checking git working tree status...
[SUCCESS] Working tree is clean. No uncommitted changes.
[INFO] Verifying roadmap synchronization...
[SUCCESS] Roadmap verification completed
[SUCCESS] Autonomous agent completed successfully!
[INFO] Check docs/devlog.md for details on what was implemented.
[INFO] Full execution log: /home/user/agentic_sdlc/agent-logs/autonomous-agent-20251205-143000.log
```

**Exit Codes**:

- `0` - Success (work completed and committed)
- `1` - Error (missing dependencies, no work available, uncommitted changes, etc.)
- Other - Claude Code execution failure

### `qa_agent.sh`

**Purpose**: Launches Claude Code to perform a comprehensive quality audit.

**Usage**:

```bash
./scripts/qa_agent.sh
# Or via orchestrator:
python scripts/orchestrator.py qa
```

**What it does**:

- Runs all quality gates (pytest, coverage, ruff, mypy)
- Identifies violations with severity levels (Critical/Major/Minor)
- Generates `docs/qa-audit.md` with findings and recommendations
- Commits the audit report

### `pm_agent.sh`

**Purpose**: Launches Claude Code for project management and roadmap synchronization.

**Usage**:

```bash
./scripts/pm_agent.sh
# Or via orchestrator:
python scripts/orchestrator.py pm
```

**What it does**:

- Runs roadmap gardening (unblocks phases with satisfied dependencies)
- Reviews agent status and activity
- Verifies roadmap accuracy against devlog
- Generates `docs/pm-status.md` with project health summary
- Commits the status report

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
- `decompose_task(task_description, max_depth)` - Break down into subtasks with dependency graph
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

## Running Multiple Autonomous Cycles

To run multiple autonomous agent cycles (for parallel work stream completion):

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

To monitor what the autonomous agent is doing:

```bash
# In another terminal, watch the devlog
watch -n 2 tail -n 20 docs/devlog.md

# Or watch git commits
watch -n 2 git log --oneline -5

# Or watch roadmap status
watch -n 2 grep -A 3 "Status:" plans/roadmap.md
```

## Troubleshooting

### "Claude Code CLI not found"

Install Claude Code CLI:

```bash
# Follow installation instructions for your platform
# https://github.com/anthropics/claude-code
```

### "Working tree still dirty after commit attempt"

Manual intervention required. Check what's uncommitted:

```bash
git status
git diff
```

Review the changes and commit manually if needed.

### "No work streams available to claim"

All work streams are either:

- Already completed (✅)
- Blocked (🔴)
- In progress by another agent (🔄 with assignment)

Either wait for in-progress work to complete, or unblock blocked work streams.

## Development

### Adding New Scripts

1. Create script in `scripts/` directory
2. Make executable: `chmod +x scripts/your_script.sh`
3. Add documentation to this README
4. Test thoroughly before committing

### Script Conventions

- Use `#!/bin/bash` shebang
- Include `set -euo pipefail` for safety
- Add colored output for clarity
- Include helpful error messages
- Exit with appropriate exit codes
- Add usage documentation

## Safety Notes

⚠️ **The autonomous agent uses `--dangerously-skip-permissions-prompt`**

This is necessary for headless operation but means:

- The agent has full file system access
- No permission prompts will be shown
- Review code before running in production
- Consider running in a sandboxed environment for untrusted tasks

✅ **Safety features built-in:**

- Quality gates prevent broken code from being committed
- TDD workflow ensures tests exist before implementation
- Atomic commits with only relevant files
- Clear audit trail via devlog and git history
- Working tree verification before exit

## See Also

- [Coder Agent Workflow](../.claude/agents/coder_agent.md) - Complete TDD workflow documentation
- [Development Log](../docs/devlog.md) - Track completed work
- [Roadmap](../plans/roadmap.md) - View available work streams
- [NATS Architecture](../docs/nats-architecture.md) - Inter-agent communication
