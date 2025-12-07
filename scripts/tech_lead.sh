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
PROMPT="You are operating as an autonomous Tech Lead Agent. Your PRIMARY job is to give the human overseer a quick summary of what coders accomplished.

FIRST: Choose a personal name for yourself.
\`\`\`python
from src.core.agent_naming import claim_agent_name, get_taken_names
taken = get_taken_names()
print(f'Names already taken: {taken}')
my_chosen_name = 'YourChosenName'  # Pick a tech lead name
success, result = claim_agent_name('$AGENT_ID', my_chosen_name, 'tech_lead')
print(f'I am {result}, your Tech Lead.' if success else f'Could not claim: {result}')
\`\`\`

Your task - EXECUTIVE SUMMARY + QUALITY AUDIT:

## STEP 1: Gather Recent Work (IMPORTANT - this is what the human wants to see)

Read the recent activity:
\`\`\`bash
# Recent commits (what was done)
git log --oneline -10

# Recent devlog entries
head -100 docs/devlog.md
\`\`\`

## STEP 2: Run Quality Gates

\`\`\`bash
PYTHONPATH=. pytest tests/ -q --tb=no 2>&1 | tail -5
PYTHONPATH=. pytest --cov=src --cov-report=term tests/ 2>&1 | grep TOTAL
ruff check src/ tests/ 2>&1 | tail -3
mypy src/ 2>&1 | tail -3
\`\`\`

## STEP 3: Create Executive Summary Report

Write docs/qa-audit.md with this EXACT format (the human reads this instead of logs):

\`\`\`markdown
# Tech Lead Report - {DATE}

**Auditor:** {your name}
**Status:** ✅ ALL CLEAR | ⚠️ ISSUES FOUND | 🔴 CRITICAL

## Executive Summary (read this in 30 seconds)

### Work Completed Since Last Audit

| Agent | Phase | What They Did | Status |
|-------|-------|---------------|--------|
| Nova | 2.7 | Defeat test framework | ✅ Good |
| Atlas | 4.1 | Task assignment optimizer | ✅ Good |

### Quality Status

| Gate | Status | Value |
|------|--------|-------|
| Tests | ✅ | X passed |
| Coverage | ✅/❌ | X% |
| Lint | ✅/❌ | X errors |
| Types | ✅/❌ | X errors |

### Action Items for Human

- [ ] {Any decisions needed}
- [ ] {Any blockers}
- (none) if everything is fine

---

## Detailed Findings

{Only if there are violations - list specific files and fixes needed}

## Technical Debt

{Reference docs/technical-debt.md if items exist}
\`\`\`

## STEP 4: Commit

\`\`\`bash
git add docs/qa-audit.md
git commit -m 'Tech Lead Report: {Status} - {X} tests, {Y}% coverage'
\`\`\`

IMPORTANT: The Executive Summary section is THE MOST IMPORTANT PART. The human reads this instead of coder logs. Make it scannable in 30 seconds.

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
