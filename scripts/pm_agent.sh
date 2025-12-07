#!/bin/bash
set -euo pipefail

# PM Agent - Project Management & Roadmap Synchronization
# This script launches Claude Code to verify roadmap status and track progress.
#
# Usage:
#   ./scripts/pm_agent.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=agent_common.sh
source "$SCRIPT_DIR/agent_common.sh"

# Set project paths (PM agent only works on orchestrator itself)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
PM_AGENT="$PROJECT_ROOT/.claude/agents/project_manager.md"

# Setup logging
setup_logging "pm-agent" "$PROJECT_ROOT" "$PROJECT_NAME"

# Check prerequisites
require_claude_cli
require_file "$PM_AGENT" "PM agent workflow"

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting PM Agent..."
log_info "Project Root: $PROJECT_ROOT"
log_info "Log File: $LOG_FILE"

log_to_file "=== PM Agent Execution - $TIMESTAMP ==="
log_to_file "Project Root: $PROJECT_ROOT"
log_to_file ""

# Generate agent ID
AGENT_ID="pm-$(date +%s)"

# Create the prompt for Claude Code
PROMPT="You are operating as an autonomous Project Manager Agent. Follow the workflow defined in .claude/agents/project_manager.md exactly.

FIRST: Choose a personal name for yourself - any name that feels meaningful to you.
Then claim it by running this Python code:
\`\`\`python
from src.core.agent_naming import claim_agent_name, get_taken_names

# First check what names are taken
taken = get_taken_names()
print(f'Names already taken: {taken}')

# Choose your name (pick from orchestrator names like Conductor, Maestro, Director, Coordinator, Synergy)
my_chosen_name = 'YourChosenName'  # Replace with your chosen name

# Claim it
success, result = claim_agent_name('$AGENT_ID', my_chosen_name, 'orchestrator')
if success:
    print(f'Hello! I am {result}, your project manager.')
else:
    print(f'Could not claim name: {result}')
\`\`\`

$(get_memory_prompt pm)

Your tasks - FULL PROJECT STATUS REVIEW:

1. **Roadmap Gardening** - Run the gardener to unblock phases:
\`\`\`python
from src.orchestrator.roadmap_gardener import garden_roadmap, check_roadmap_health

# Check health
health = check_roadmap_health()
print(f'Issues found: {health.get(\"issues\", [])}')
print(f'Available for work: {health.get(\"available_for_work\", [])}')

# Garden (unblock satisfied dependencies)
results = garden_roadmap()
for unblocked in results.get('unblocked', []):
    print(f'✅ Unblocked Phase {unblocked[\"id\"]}: {unblocked[\"name\"]}')
\`\`\`

2. **Agent Status Review** - Check all known agents:
\`\`\`python
from src.core.agent_naming import get_naming

naming = get_naming()
agents = naming.list_assigned_names()

print('\\n=== Agent Status ===')
for agent_id, info in agents.items():
    name = info.get('name')
    phases = info.get('completed_phases', {})
    print(f'{name}: {phases}')
\`\`\`

3. **Roadmap Verification** - Check recent completions:
   - Read docs/devlog.md for recent work
   - Verify roadmap.md status matches
   - Update any out-of-sync entries

4. **Progress Report** - Generate a status summary:
   - Total phases: X
   - Completed: Y
   - In Progress: Z
   - Available to claim: N
   - Blockers detected: ...

5. **Create Status Report** - Write to docs/pm-status.md:
   - Project health summary
   - Agent activity
   - Blockers and recommendations
   - Next priority work

6. **Update All Documentation** - Ensure these files reflect current status:

   Core docs:
   - README.md - Current Status section, Active Agents table, CLI Commands
   - NEXT_STEPS.md - Completed phases, claimable phases, agent list
   - CLAUDE.md - Implementation Status table if needed
   - plans/roadmap.md - Status markers, completion dates

   AGENTS.md files (directory context for agents - CRITICAL to keep current):
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

   READMEs (verify these are current):
   - scripts/README.md - All scripts documented
   - docs/reviews/README.md - Review format if changed
   - agent-logs/README.md - Log format if changed
   - config/agent_memories/README.md - Memory format if changed

7. **Reflect and Save Memory** - Before committing, reflect on this session:
$(get_reflection_prompt pm)

8. Commit all changes (status report + documentation updates).

Begin now."

log_info "Executing PM workflow..."
log_to_file "=== PM Execution ==="
log_to_file "Starting: $(date)"
log_to_file ""

# PM agents use Opus 4.5 for complex reasoning
claude -p --model opus --dangerously-skip-permissions "$PROMPT" 2>&1 | tee -a "$LOG_FILE"
PM_EXIT_CODE=${PIPESTATUS[0]}

log_to_file ""
log_to_file "PM completed: $(date)"
log_to_file "Exit code: $PM_EXIT_CODE"

if [[ $PM_EXIT_CODE -ne 0 ]]; then
    log_error "PM Agent failed with exit code $PM_EXIT_CODE"
    exit $PM_EXIT_CODE
fi

log_success "PM Agent completed successfully!"
log_info "Check docs/pm-status.md for the project status report."
log_info "Full execution log: $LOG_FILE"

exit 0
