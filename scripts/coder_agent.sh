#!/bin/bash
set -euo pipefail

# Coder Agent - Flexible TDD Workflow
# This script launches Claude Code to autonomously complete tasks using TDD.
# Can work from the roadmap OR accept ad-hoc tasks.
#
# Usage:
#   ./scripts/coder_agent.sh                    # Work on next roadmap item
#   TASK="raise test coverage to 80%" ./scripts/coder_agent.sh  # Ad-hoc task
#   TARGET_PATH=/path/to/repo ./scripts/coder_agent.sh  # Work on external repo
#
# Environment Variables:
#   AGENT_ID             - Reuse specific agent by ID (optional, auto-selected if not set)
#   PHASE                - Phase hint for agent selection (e.g., "4.2" selects agent with batch 4 experience)
#   TASK                 - Ad-hoc task description (optional, overrides roadmap)
#   TARGET_PATH          - Path to target repository (default: orchestrator)
#   TARGET_NAME          - Name for logging (default: directory name)
#   TARGET_ROADMAP       - Roadmap file path (default: plans/roadmap.md)
#   TARGET_CODER_AGENT   - Coder workflow file (default: .claude/agents/coder_agent.md)
#   TARGET_IDENTITY_CONTEXT - Identity file to inject (optional)
#
# Agent Selection:
#   By default, the script reuses an existing agent from the team roster.
#   Agents are selected based on their experience with similar phases.
#   New agents are only created when no suitable agent is available.
#
# Workflow Phases:
#   0. Identity     - Claim personal name, load memory
#   1. Claim/Task   - Find roadmap work OR use TASK if provided
#   2. Analyze      - Understand requirements, plan implementation
#   3. TDD          - Write tests first, then implementation
#   4. Validate     - Run all quality gates
#   5. Document     - Update roadmap/devlog
#   6. Commit       - Stage specific files, commit with message

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=agent_common.sh
source "$SCRIPT_DIR/agent_common.sh"

# Resolve project paths
resolve_project_paths "$SCRIPT_DIR"

# Setup logging (logs go to orchestrator root for centralized monitoring)
setup_logging "coder-agent" "$ORCHESTRATOR_ROOT" "$PROJECT_NAME"

# Check prerequisites
require_claude_cli
require_file "$ROADMAP" "Roadmap"
require_file "$CODER_AGENT" "Coder agent workflow"

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting Coder Agent..."
log_info "Target Mode: $TARGET_MODE"
log_info "Project Root: $PROJECT_ROOT"
log_info "Roadmap: $ROADMAP"
log_info "Log File: $LOG_FILE"
if [[ -n "$IDENTITY_CONTEXT" ]]; then
    log_info "Identity Context: $PROJECT_ROOT/$IDENTITY_CONTEXT"
fi

log_to_file "=== Coder Agent Execution - $TIMESTAMP ==="
log_to_file "Target Mode: $TARGET_MODE"
log_to_file "Project Root: $PROJECT_ROOT"
log_to_file "Roadmap: $ROADMAP"
if [[ -n "$IDENTITY_CONTEXT" ]]; then
    log_to_file "Identity Context: $PROJECT_ROOT/$IDENTITY_CONTEXT"
fi
log_to_file ""

# Select or generate agent ID
# Priority: 1) AGENT_ID env var, 2) Agent selector, 3) Generate new
if [[ -n "${AGENT_ID:-}" ]]; then
    log_info "Using provided agent ID: $AGENT_ID"
    AGENT_MODE="provided"
else
    # Try to select an existing agent using the selector
    # Extract phase from TASK or use default "1.1" for selection
    PHASE_HINT="${PHASE:-1.1}"

    # Use Python to select an agent
    SELECTED_AGENT=$(cd "$ORCHESTRATOR_ROOT" && python3 -c "
from src.core.agent_selector import get_selector
selector = get_selector()
agent = selector.select_agent('$PHASE_HINT')
if agent:
    print(agent['id'])
else:
    print('')
" 2>/dev/null || echo "")

    if [[ -n "$SELECTED_AGENT" ]]; then
        AGENT_ID="$SELECTED_AGENT"
        log_info "Reusing agent: $AGENT_ID"
        AGENT_MODE="reused"
    else
        AGENT_ID="coder-$(date +%s)"
        log_info "No available agents - creating new: $AGENT_ID"
        AGENT_MODE="new"
    fi
fi

log_to_file "Agent ID: $AGENT_ID (mode: $AGENT_MODE)"

# Check for ad-hoc task vs roadmap mode
ADHOC_TASK="${TASK:-}"
if [[ -n "$ADHOC_TASK" ]]; then
    log_info "Ad-hoc task mode: $ADHOC_TASK"
    log_to_file "Mode: Ad-hoc task"
    log_to_file "Task: $ADHOC_TASK"
else
    log_info "Roadmap mode: claiming next available work stream"
    log_to_file "Mode: Roadmap work stream"
fi

# Build the phase 1 instructions based on mode
if [[ -n "$ADHOC_TASK" ]]; then
    PHASE1_INSTRUCTIONS=">>> PHASE 1: TASK ASSIGNMENT
You have been assigned an ad-hoc task:

**TASK:** $ADHOC_TASK

This is NOT from the roadmap - it's a direct request.

1. Understand the task requirements
2. Identify what files need to be created/modified
3. Print: '>>> PHASE 1: Task Assignment - Complete (task: $ADHOC_TASK)'"
else
    PHASE1_INSTRUCTIONS=">>> PHASE 1: CLAIM WORK STREAM
1. Read plans/roadmap.md to understand the project
2. Find the next unclaimed work stream:
   - Look for Status: ⚪ Not Started
   - OR Status: 🔄 In Progress with Assigned To: -
3. Claim by editing roadmap.md:
   - Set Status to: 🔄 In Progress
   - Set Assigned To: {your_personal_name}
4. Print: '>>> PHASE 1: Claim Work Stream - Complete (claimed {phase_id})'"
fi

# Create the prompt for Claude Code
PROMPT="You are operating as an autonomous Coder Agent. Follow the workflow defined in .claude/agents/coder_agent.md exactly.

IMPORTANT: Announce each phase clearly by printing a phase marker like:
  >>> PHASE 1: Claim Work Stream - Starting
  >>> PHASE 1: Claim Work Stream - Complete
This helps with log tracking and debugging.

=== PHASE 0: IDENTITY ===
Your agent ID is: $AGENT_ID (mode: $AGENT_MODE)

Run this Python code to get your identity:
\`\`\`python
from src.core.agent_naming import get_naming, claim_agent_name

naming = get_naming()
existing_name = naming.get_name('$AGENT_ID')

if existing_name:
    # You're a returning agent - welcome back!
    my_chosen_name = existing_name
    print(f'Welcome back! I am {my_chosen_name}.')
else:
    # You're new - choose a name
    taken = naming.get_taken_names()
    print(f'Names already taken: {taken}')

    # Choose your name (any name that isn't taken)
    my_chosen_name = 'YourChosenName'  # Replace with a name you choose

    success, result = claim_agent_name('$AGENT_ID', my_chosen_name, 'coder')
    if success:
        print(f'Hello! I am {result}.')
    else:
        print(f'Could not claim: {result}')
        # Try a different name
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

=== THE 6 PHASES OF YOUR WORKFLOW ===

You MUST complete ALL 6 phases in order. Print phase markers as you go.

$PHASE1_INSTRUCTIONS

>>> PHASE 2: ANALYSIS & PLANNING
1. Read the work stream requirements carefully
2. Identify what files need to be created/modified
3. List dependencies and check if they exist
4. Plan your test strategy - what tests will you write?
5. Print: '>>> PHASE 2: Analysis & Planning - Complete'

>>> PHASE 3: TEST-DRIVEN DEVELOPMENT
FOR EACH COMPONENT:
1. Write tests FIRST in tests/
2. Run tests (they should FAIL - code doesn't exist yet)
3. Write implementation in src/
4. Run tests (they should PASS now)
5. Refactor if needed (keeping tests green)

TDD is NON-NEGOTIABLE:
- ✅ Tests BEFORE implementation
- ❌ NEVER write code before tests for new features
Print: '>>> PHASE 3: Test-Driven Development - Complete'

>>> PHASE 4: INTEGRATION & VALIDATION
Run ALL quality gates:
\`\`\`bash
# Full test suite with coverage
pytest tests/ -v --cov=src

# Check coverage (must be >= 80%)
pytest --cov=src --cov-report=term-missing tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
\`\`\`

DO NOT proceed until:
- ✅ All tests pass
- ✅ Coverage >= 80%
- ✅ No linting errors
- ✅ No type errors
Print: '>>> PHASE 4: Integration & Validation - Complete'

>>> PHASE 5: DOCUMENTATION
1. Update plans/roadmap.md - mark work stream as ✅ Complete
2. Write entry in docs/devlog.md with your personal name
3. Update any other relevant docs
Print: '>>> PHASE 5: Documentation - Complete'

>>> PHASE 6: COMMIT
1. Stage ONLY files you worked on (not git add .)
\`\`\`bash
git add src/{specific_files} tests/{specific_files}
git add plans/roadmap.md docs/devlog.md
\`\`\`
2. Write a descriptive commit message following coder_agent.md format
3. Commit the changes
Print: '>>> PHASE 6: Commit - Complete'

At the END of your session, reflect:
\`\`\`python
# Record a reflection
memory.reflect('Your honest reflection on this session')

# Save any final insights
memory.record_insight('Key learning from this session')
\`\`\`

CRITICAL REQUIREMENTS:
- Write tests BEFORE writing any implementation code (TDD)
- Do NOT commit until ALL quality gates pass:
  * All tests pass (pytest tests/ -v)
  * Coverage ≥ 80% (pytest --cov=src tests/)
  * No linting errors (ruff check src/ tests/)
  * No type errors (mypy src/)
- Only stage files you worked on (src/*, tests/*, plans/roadmap.md, docs/devlog.md)
- Write a descriptive commit message following the format in .claude/agents/coder_agent.md

If you're in roadmap mode and there are no unclaimed work streams, respond with: \"No work streams available to claim.\"

Begin now."

log_info "Executing 6-phase TDD workflow..."
log_to_file "=== CODER AGENT: 6-Phase Workflow ==="
log_to_file "Starting: $(date)"
log_to_file "Phases: 0-Identity, 1-Claim, 2-Analyze, 3-TDD, 4-Validate, 5-Document, 6-Commit"
log_to_file ""

# Coder agents use Sonnet 4.5 for cost efficiency
claude -p --model sonnet --dangerously-skip-permissions "$PROMPT" 2>&1 | tee -a "$LOG_FILE"
CODER_EXIT_CODE=${PIPESTATUS[0]}

log_to_file ""
log_to_file "Coder Agent workflow completed: $(date)"
log_to_file "Exit code: $CODER_EXIT_CODE"
log_to_file ""

if [[ $CODER_EXIT_CODE -ne 0 ]]; then
    log_error "Coder Agent failed with exit code $CODER_EXIT_CODE"
    exit $CODER_EXIT_CODE
fi

log_success "Coder Agent completed successfully!"
log_info "Check docs/devlog.md for details on what was implemented."
log_info "Full execution log: $LOG_FILE"

exit 0
