#!/bin/bash
set -euo pipefail

# PM Agent - Project Management & Roadmap Synchronization
# This script launches Claude Code to verify roadmap status and track progress.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PM_AGENT="$PROJECT_ROOT/.claude/agents/project_manager.md"
LOG_DIR="$PROJECT_ROOT/agent-logs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/pm-agent-$TIMESTAMP.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_to_file() { echo "$1" | tee -a "$LOG_FILE"; }

# Check if Claude Code CLI is available
if ! command -v claude &> /dev/null; then
    log_error "Claude Code CLI not found. Please install it first."
    exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting PM Agent..."
log_info "Project Root: $PROJECT_ROOT"
log_info "Log File: $LOG_FILE"

log_to_file "=== PM Agent Execution - $TIMESTAMP ==="
log_to_file "Project Root: $PROJECT_ROOT"
log_to_file ""

# Check if PM agent workflow exists
if [[ ! -f "$PM_AGENT" ]]; then
    log_error "PM agent workflow not found at $PM_AGENT"
    exit 1
fi

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
   - README.md - Update Current Status section with completed phases
   - NEXT_STEPS.md - Update completed phases, active agents, claimable phases
   - CLAUDE.md - Update Implementation Status table if needed
   - scripts/README.md - Verify new scripts are documented

7. Commit all changes (status report + documentation updates).

Begin now."

log_info "Executing PM workflow..."
log_to_file "=== PM Execution ==="
log_to_file "Starting: $(date)"
log_to_file ""

# Launch Claude Code
claude -p --dangerously-skip-permissions "$PROMPT" 2>&1 | tee -a "$LOG_FILE"
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
