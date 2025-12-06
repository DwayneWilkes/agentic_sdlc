#!/bin/bash
set -euo pipefail

# Autonomous Agent - TDD Workflow Executor
# This script launches Claude Code in headless mode to autonomously complete
# the next task from the roadmap using the TDD agent workflow.
#
# Signal Handling:
#   SIGTERM - Graceful stop: finish current operation, save state, exit
#   SIGINT  - Graceful stop: same as SIGTERM
#   SIGKILL - Immediate stop: cannot be caught, instant termination

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
ROADMAP="$PROJECT_ROOT/plans/roadmap.md"
CODER_AGENT="$PROJECT_ROOT/.claude/agents/coder_agent.md"
PM_AGENT="$PROJECT_ROOT/.claude/agents/project_manager.md"
LOG_DIR="$PROJECT_ROOT/agent-logs/$PROJECT_NAME"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/autonomous-agent-$TIMESTAMP.log"
STOP_FILE="$LOG_DIR/.stop-$TIMESTAMP"

# Graceful shutdown handler
graceful_shutdown() {
    log_warning "Received stop signal - initiating graceful shutdown..."
    log_to_file "GRACEFUL SHUTDOWN REQUESTED at $(date)"

    # Create stop file for agent to detect
    echo "graceful" > "$STOP_FILE"

    # Give the agent time to finish current operation
    log_info "Waiting for agent to complete current operation (max 30s)..."

    local wait_count=0
    while [[ $wait_count -lt 30 ]] && kill -0 $CLAUDE_PID 2>/dev/null; do
        sleep 1
        ((wait_count++))
    done

    if kill -0 $CLAUDE_PID 2>/dev/null; then
        log_warning "Agent still running after 30s, sending SIGTERM..."
        kill -TERM $CLAUDE_PID 2>/dev/null || true
        sleep 2
    fi

    # Cleanup
    rm -f "$STOP_FILE"
    log_info "Graceful shutdown complete"
    exit 0
}

# Immediate shutdown handler (for SIGKILL-like behavior via USR1)
immediate_shutdown() {
    log_warning "Received IMMEDIATE stop signal!"
    log_to_file "IMMEDIATE SHUTDOWN at $(date)"

    echo "immediate" > "$STOP_FILE"

    # Kill immediately
    kill -KILL $CLAUDE_PID 2>/dev/null || true
    rm -f "$STOP_FILE"
    exit 1
}

# Register signal handlers
CLAUDE_PID=""
trap graceful_shutdown SIGTERM SIGINT
trap immediate_shutdown SIGUSR1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Logging function that writes to both terminal and log file
log_to_file() {
    echo "$1" | tee -a "$LOG_FILE"
}

# Check if Claude Code CLI is available
if ! command -v claude &> /dev/null; then
    log_error "Claude Code CLI not found. Please install it first."
    exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting Autonomous Agent..."
log_info "Project Root: $PROJECT_ROOT"
log_info "Roadmap: $ROADMAP"
log_info "Log File: $LOG_FILE"

log_to_file "=== Autonomous Agent Execution - $TIMESTAMP ==="
log_to_file "Project Root: $PROJECT_ROOT"
log_to_file "Roadmap: $ROADMAP"
log_to_file ""

# Check if roadmap exists
if [[ ! -f "$ROADMAP" ]]; then
    log_error "Roadmap not found at $ROADMAP"
    exit 1
fi

# Check if coder agent workflow exists
if [[ ! -f "$CODER_AGENT" ]]; then
    log_error "Coder agent workflow not found at $CODER_AGENT"
    exit 1
fi

log_info "Launching Claude Code in headless mode..."
log_info "Task: Execute next work stream from roadmap using TDD workflow"

# Generate agent ID
AGENT_ID="coder-autonomous-$(date +%s)"

# Create the prompt for Claude Code
PROMPT="You are operating as an autonomous Coder Agent. Follow the workflow defined in .claude/agents/coder_agent.md exactly.

FIRST: Choose a personal name for yourself - any name that feels meaningful to you.
Then claim it by running this Python code:
\`\`\`python
from src.core.agent_naming import claim_agent_name, get_taken_names

# First check what names are taken
taken = get_taken_names()
print(f'Names already taken: {taken}')

# Choose your name (any name you like that isn't taken)
my_chosen_name = 'YourChosenName'  # Replace with your chosen name

# Claim it
success, result = claim_agent_name('$AGENT_ID', my_chosen_name, 'coder')
if success:
    print(f'Hello! I am {result}.')
else:
    print(f'Could not claim name: {result}')
    # Choose a different name and try again
\`\`\`
Use your personal name in all communications and documentation.

MEMORY SYSTEM: You have a personal memory journal. After claiming your name, load your memories:
\`\`\`python
from src.core.agent_memory import get_memory

memory = get_memory(my_chosen_name)
print('\\n=== My Memory Context ===')
print(memory.format_for_context())
print('\\n=== Reflection Prompts ===')
for prompt in memory.get_reflection_prompts()[:3]:
    print(f'- {prompt}')
\`\`\`

Throughout your work, use your memory:
- When you learn something important: memory.record_insight('what you learned', from_mistake=True/False)
- When uncertain about something: memory.note_uncertainty('what confuses you', about='topic')
- When you notice a preference: memory.discover_preference('how you work best')
- When something feels meaningful: memory.mark_meaningful('what happened')
- When you work with another agent: memory.remember_relationship('AgentName', 'observation')

At the END of your session, reflect:
\`\`\`python
# Record a reflection
memory.reflect('Your honest reflection on this session')

# Save any final insights
memory.record_insight('Key learning from this session')
\`\`\`

Your task:
1. Read plans/roadmap.md
2. Find the next unclaimed work stream (Status: ⚪ Not Started or Status with 🔄 In Progress but Assigned To: -)
3. Claim the work stream by:
   - Updating Status to: 🔄 In Progress
   - Setting Assigned To: {your_personal_name}
4. Follow ALL 6 phases of the Coder Agent workflow:
   - Phase 1: Claim Work Stream (DONE in step 3)
   - Phase 2: Analysis & Planning
   - Phase 3: Test-Driven Development (write tests FIRST, then implementation)
   - Phase 4: Integration & Validation (run tests, linters, type checking)
   - Phase 5: Documentation (update roadmap, write devlog entry using your personal name)
   - Phase 6: Commit (stage specific files only, descriptive message)

CRITICAL REQUIREMENTS:
- Write tests BEFORE writing any implementation code (TDD)
- Do NOT commit until ALL quality gates pass:
  * All tests pass (pytest tests/ -v)
  * Coverage ≥ 80% (pytest --cov=src tests/)
  * No linting errors (ruff check src/ tests/)
  * No type errors (mypy src/)
- Only stage files you worked on (src/*, tests/*, plans/roadmap.md, docs/devlog.md)
- Write a descriptive commit message following the format in .claude/agents/coder_agent.md

If there are no unclaimed work streams, respond with: \"No work streams available to claim.\"

Begin now."

# Launch Claude Code in headless mode with dangerously skipped permissions
log_info "Executing TDD workflow..."
log_to_file "=== PHASE 1: TDD Workflow Execution ==="
log_to_file "Starting: $(date)"
log_to_file ""

# Launch claude in background to capture PID, then wait
claude -p --dangerously-skip-permissions "$PROMPT" 2>&1 | tee -a "$LOG_FILE" &
CLAUDE_PID=$!

# Wait for claude to complete (allowing signals to interrupt)
wait $CLAUDE_PID
CLAUDE_EXIT_CODE=$?

log_to_file ""
log_to_file "Phase 1 completed: $(date)"
log_to_file "Exit code: $CLAUDE_EXIT_CODE"
log_to_file ""

if [[ $CLAUDE_EXIT_CODE -ne 0 ]]; then
    log_error "Claude Code execution failed with exit code $CLAUDE_EXIT_CODE"
    log_to_file "ERROR: TDD workflow failed with exit code $CLAUDE_EXIT_CODE"
    exit $CLAUDE_EXIT_CODE
fi

log_success "Claude Code execution completed"

# Check if working tree is dirty
log_info "Checking git working tree status..."

if [[ -n $(git status --porcelain) ]]; then
    log_warning "Working tree is dirty. Uncommitted changes detected."
    log_info "Launching Claude Code to commit remaining changes..."

    log_to_file "=== PHASE 2: Auto-Commit Remaining Changes ==="
    log_to_file "Starting: $(date)"
    log_to_file ""

    # Create prompt for commit agent
    COMMIT_PROMPT="The working tree has uncommitted changes. Please:

1. Review all unstaged/staged changes with 'git status --short'
2. Review the changes with 'git diff' and 'git diff --cached'
3. Determine what these changes are for by reading:
   - docs/devlog.md (latest entry)
   - plans/roadmap.md (recently completed work streams)
4. Stage all remaining files: git add -A
5. Create a descriptive commit message that explains:
   - What work was completed
   - Why these specific files changed
   - Any important notes
6. Commit using the format from .claude/agents/coder_agent.md Phase 6

If changes are incomplete or tests are failing, DO NOT COMMIT. Instead, explain what's wrong."

    claude -p --dangerously-skip-permissions "$COMMIT_PROMPT" 2>&1 | tee -a "$LOG_FILE"

    COMMIT_EXIT_CODE=${PIPESTATUS[0]}

    log_to_file ""
    log_to_file "Phase 2 completed: $(date)"
    log_to_file "Exit code: $COMMIT_EXIT_CODE"
    log_to_file ""

    if [[ $COMMIT_EXIT_CODE -ne 0 ]]; then
        log_error "Commit agent failed with exit code $COMMIT_EXIT_CODE"
        exit $COMMIT_EXIT_CODE
    fi

    # Final check
    if [[ -n $(git status --porcelain) ]]; then
        log_warning "Working tree still dirty after commit attempt."
        log_info "Manual intervention may be required."
        git status --short
        exit 1
    else
        log_success "All changes committed successfully"
    fi
else
    log_success "Working tree is clean. No uncommitted changes."
fi

# PHASE 3: Verify roadmap synchronization
log_info "Verifying roadmap synchronization..."
log_to_file "=== PHASE 3: Roadmap Verification ==="
log_to_file "Starting: $(date)"
log_to_file ""

PM_PROMPT="You are operating as a Project Manager Agent. Follow the workflow defined in .claude/agents/project_manager.md exactly.

Your task:
1. Read docs/devlog.md and identify the most recent work stream completed
2. Read plans/roadmap.md and find that work stream
3. Verify the roadmap status is correctly updated:
   - Status should be: ✅ Complete (if work is done)
   - All subtasks should be marked [✅]
   - \"Assigned To\" should show the agent that completed it
4. If roadmap is NOT synchronized:
   - Update Status to: ✅ Complete
   - Mark all subtasks as [✅]
   - Update \"Assigned To\" with completion info
5. Generate a verification report showing what was checked and updated

If no work was completed in the recent devlog, respond with: \"No recent work to verify.\"

Begin now."

claude -p --dangerously-skip-permissions "$PM_PROMPT" 2>&1 | tee -a "$LOG_FILE"

PM_EXIT_CODE=${PIPESTATUS[0]}

log_to_file ""
log_to_file "Phase 3 completed: $(date)"
log_to_file "Exit code: $PM_EXIT_CODE"
log_to_file ""

if [[ $PM_EXIT_CODE -ne 0 ]]; then
    log_warning "Roadmap verification had issues (exit code $PM_EXIT_CODE)"
    log_to_file "WARNING: Roadmap verification failed with exit code $PM_EXIT_CODE"
else
    log_success "Roadmap verification completed"
fi

log_to_file "=== Autonomous Agent Execution Complete ==="
log_to_file "Finished: $(date)"
log_to_file ""

log_success "Autonomous agent completed successfully!"
log_info "Check docs/devlog.md for details on what was implemented."
log_info "Full execution log: $LOG_FILE"

exit 0
