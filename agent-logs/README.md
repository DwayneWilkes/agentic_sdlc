# Agent Logs

This directory contains execution logs from autonomous agent runs, organized by project.

## Purpose

Logs provide a complete audit trail of autonomous agent operations, including:

- TDD workflow execution output
- Auto-commit operations
- Roadmap verification results
- Error messages and debugging information
- Timestamps for each phase

## Directory Structure

Logs are organized by project name:

```text
agent-logs/
├── {project_name}/
│   ├── autonomous-agent-YYYYMMDD-HHMMSS.log
│   ├── qa-agent-YYYYMMDD-HHMMSS.log
│   └── pm-agent-YYYYMMDD-HHMMSS.log
└── README.md
```

Example: `agent-logs/agentic_sdlc/autonomous-agent-20251205-143000.log`

## Log Structure

Each log contains three phases:

```
=== Autonomous Agent Execution - YYYYMMDD-HHMMSS ===
Project Root: /path/to/project
Roadmap: /path/to/roadmap.md

=== PHASE 1: TDD Workflow Execution ===
Starting: Thu Dec  5 14:30:00 UTC 2025

[Claude Code output...]

Phase 1 completed: Thu Dec  5 14:45:00 UTC 2025
Exit code: 0

=== PHASE 2: Auto-Commit Remaining Changes ===
Starting: Thu Dec  5 14:45:00 UTC 2025

[Commit agent output...]

Phase 2 completed: Thu Dec  5 14:46:00 UTC 2025
Exit code: 0

=== PHASE 3: Roadmap Verification ===
Starting: Thu Dec  5 14:46:00 UTC 2025

[Project manager agent output...]

Phase 3 completed: Thu Dec  5 14:47:00 UTC 2025
Exit code: 0

=== Autonomous Agent Execution Complete ===
Finished: Thu Dec  5 14:47:00 UTC 2025
```

## Usage

### View Latest Log

```bash
# List project log directories
ls agent-logs/

# List logs for a project by most recent
ls -lt agent-logs/agentic_sdlc/

# View latest log for a project
tail -f agent-logs/agentic_sdlc/autonomous-agent-*.log | head -n 1
```

### Search Logs

```bash
# Find errors across all projects
grep -r "ERROR" agent-logs/

# Find errors in specific project
grep -r "ERROR" agent-logs/agentic_sdlc/

# Find specific work stream
grep -r "Phase 1.1" agent-logs/agentic_sdlc/

# Check exit codes
grep -r "Exit code:" agent-logs/
```

### Debug Failed Runs

If an autonomous agent run fails:

1. Check the most recent log file
2. Look for "ERROR:" messages
3. Check exit codes (non-zero indicates failure)
4. Review the output from each phase
5. Examine git status and working tree state

```bash
# Find failed runs across all projects
grep -rl "Exit code: [^0]" agent-logs/

# Find failed runs in specific project
grep -l "Exit code: [^0]" agent-logs/agentic_sdlc/*.log
```

## Log Retention

Logs are:

- **Ignored by git** (see [.gitignore](.gitignore))
- **Organized by project** for easy cleanup
- **Kept indefinitely** on local system
- **Manually cleaned** when disk space is needed

To clean old logs:

```bash
# Remove logs older than 30 days (all projects)
find agent-logs/ -name "*.log" -mtime +30 -delete

# Remove all logs for a specific project
rm -rf agent-logs/agentic_sdlc/

# Remove all logs (all projects)
find agent-logs/ -name "*.log" -delete
```

## Troubleshooting

### No Logs Generated

If logs aren't being created:
- Check `agent-logs/` directory exists: `ls agent-logs/`
- Check permissions: `ls -ld agent-logs/`
- Check `autonomous_agent.sh` has execute permission: `ls -l scripts/autonomous_agent.sh`

### Incomplete Logs

If logs are incomplete or cut off:
- Check disk space: `df -h`
- Check for errors in script execution
- Verify `tee` command is working: `echo "test" | tee -a agent-logs/test.log`

## See Also

- [Autonomous Agent Script](../scripts/autonomous_agent.sh) - Script that generates logs
- [Scripts README](../scripts/README.md) - Usage documentation
- [Coder Agent Workflow](../.claude/agents/coder_agent.md) - Phase 1 workflow
- [Project Manager Agent](../.claude/agents/project_manager.md) - Phase 3 workflow
