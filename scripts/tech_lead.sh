#!/bin/bash
set -euo pipefail

# Tech Lead Agent - Coder Supervision & Quality Assurance
# This script launches Claude Code to supervise coders and run quality audits.
#
# Usage:
#   ./scripts/tech_lead.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=agent_common.sh
source "$SCRIPT_DIR/agent_common.sh"

# Set project paths (Tech Lead agent only works on orchestrator itself)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
TECH_LEAD_AGENT="$PROJECT_ROOT/.claude/agents/tech_lead.md"

# Setup logging
setup_logging "tech-lead-agent" "$PROJECT_ROOT" "$PROJECT_NAME"

# Check prerequisites
require_claude_cli
require_file "$TECH_LEAD_AGENT" "Tech Lead agent workflow"

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting Tech Lead Agent..."
log_info "Project Root: $PROJECT_ROOT"
log_info "Log File: $LOG_FILE"

log_to_file "=== Tech Lead Agent Execution - $TIMESTAMP ==="
log_to_file "Project Root: $PROJECT_ROOT"
log_to_file ""

# Generate agent ID
AGENT_ID="tech-lead-$(date +%s)"

# Create the prompt for Claude Code
PROMPT="You are operating as an autonomous Tech Lead Agent. Follow the workflow defined in .claude/agents/tech_lead.md exactly.

FIRST: Choose a personal name for yourself - any name that feels meaningful to you.
Then claim it by running this Python code:
\`\`\`python
from src.core.agent_naming import claim_agent_name, get_taken_names

# First check what names are taken
taken = get_taken_names()
print(f'Names already taken: {taken}')

# Choose your name (pick a tech lead appropriate name)
my_chosen_name = 'YourChosenName'  # Replace with your chosen name

# Claim it
success, result = claim_agent_name('$AGENT_ID', my_chosen_name, 'tech_lead')
if success:
    print(f'Hello! I am {result}, your Tech Lead.')
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
git commit -m 'Tech Lead Audit: [Pass/Violation] - Coverage X%, Tests Y passed'
\`\`\`

Report ALL findings honestly. Do not skip any quality gates.

Begin now."

log_info "Executing Tech Lead audit workflow..."
log_to_file "=== Tech Lead Audit Execution ==="
log_to_file "Starting: $(date)"
log_to_file ""

# Tech Lead agents use Opus 4.5 for thorough analysis
claude -p --model opus --dangerously-skip-permissions "$PROMPT" 2>&1 | tee -a "$LOG_FILE"
TECH_LEAD_EXIT_CODE=${PIPESTATUS[0]}

log_to_file ""
log_to_file "Tech Lead Audit completed: $(date)"
log_to_file "Exit code: $TECH_LEAD_EXIT_CODE"

if [[ $TECH_LEAD_EXIT_CODE -ne 0 ]]; then
    log_error "Tech Lead Agent failed with exit code $TECH_LEAD_EXIT_CODE"
    exit $TECH_LEAD_EXIT_CODE
fi

log_success "Tech Lead Agent completed successfully!"
log_info "Check docs/qa-audit.md for the quality audit report."
log_info "Full execution log: $LOG_FILE"

exit 0
