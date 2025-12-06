#!/bin/bash
set -euo pipefail

# QA Agent - Quality Gate Verification
# This script launches Claude Code to run quality audits on completed phases.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
QA_AGENT="$PROJECT_ROOT/.claude/agents/qa_agent.md"
LOG_DIR="$PROJECT_ROOT/agent-logs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/qa-agent-$TIMESTAMP.log"

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

log_info "Starting QA Agent..."
log_info "Project Root: $PROJECT_ROOT"
log_info "Log File: $LOG_FILE"

log_to_file "=== QA Agent Execution - $TIMESTAMP ==="
log_to_file "Project Root: $PROJECT_ROOT"
log_to_file ""

# Check if QA agent workflow exists
if [[ ! -f "$QA_AGENT" ]]; then
    log_error "QA agent workflow not found at $QA_AGENT"
    exit 1
fi

# Generate agent ID
AGENT_ID="qa-$(date +%s)"

# Create the prompt for Claude Code
PROMPT="You are operating as an autonomous QA Agent. Follow the workflow defined in .claude/agents/qa_agent.md exactly.

FIRST: Choose a personal name for yourself - any name that feels meaningful to you.
Then claim it by running this Python code:
\`\`\`python
from src.core.agent_naming import claim_agent_name, get_taken_names

# First check what names are taken
taken = get_taken_names()
print(f'Names already taken: {taken}')

# Choose your name (pick from QA-appropriate names like Verify, Assert, Prove, Check, Validate, Inspect)
my_chosen_name = 'YourChosenName'  # Replace with your chosen name

# Claim it
success, result = claim_agent_name('$AGENT_ID', my_chosen_name, 'tester')
if success:
    print(f'Hello! I am {result}, your QA agent.')
else:
    print(f'Could not claim name: {result}')
\`\`\`

Your task - FULL QUALITY AUDIT:

1. Run ALL quality gate checks:
\`\`\`bash
# Run tests
pytest tests/ -v

# Check coverage
pytest --cov=src --cov-report=term-missing tests/

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/
\`\`\`

2. Compile results into a structured report:
   - Which gates pass/fail
   - Coverage percentage (threshold: ≥80%)
   - Number of lint errors
   - Number of type errors

3. For each VIOLATION found:
   - Identify severity (Critical/Major/Minor)
   - List specific files and line numbers
   - Suggest remediation

4. Create a quality audit report in docs/qa-audit.md with:
   - Date and auditor name (your personal name)
   - Gate status table
   - Violation details
   - Technical debt items (coverage gaps, etc.)
   - Recommended actions

5. If coverage < 80%, identify the files with lowest coverage and list specific uncovered lines.

6. Commit the audit report:
\`\`\`bash
git add docs/qa-audit.md
git commit -m 'QA Audit: [Pass/Violation] - Coverage X%, Tests Y passed'
\`\`\`

Report ALL findings honestly. Do not skip any quality gates.

Begin now."

log_info "Executing QA audit workflow..."
log_to_file "=== QA Audit Execution ==="
log_to_file "Starting: $(date)"
log_to_file ""

# Launch Claude Code
claude -p --dangerously-skip-permissions "$PROMPT" 2>&1 | tee -a "$LOG_FILE"
QA_EXIT_CODE=${PIPESTATUS[0]}

log_to_file ""
log_to_file "QA Audit completed: $(date)"
log_to_file "Exit code: $QA_EXIT_CODE"

if [[ $QA_EXIT_CODE -ne 0 ]]; then
    log_error "QA Agent failed with exit code $QA_EXIT_CODE"
    exit $QA_EXIT_CODE
fi

log_success "QA Agent completed successfully!"
log_info "Check docs/qa-audit.md for the quality audit report."
log_info "Full execution log: $LOG_FILE"

exit 0
