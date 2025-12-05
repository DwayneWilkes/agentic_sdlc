#!/bin/bash
set -euo pipefail

# Autonomous Agent - TDD Workflow Executor
# This script launches Claude Code in headless mode to autonomously complete
# the next task from the roadmap using the TDD agent workflow.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROADMAP="$PROJECT_ROOT/plans/roadmap.md"
CODER_AGENT="$PROJECT_ROOT/.claude/agents/coder_agent.md"

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

# Check if Claude Code CLI is available
if ! command -v claude &> /dev/null; then
    log_error "Claude Code CLI not found. Please install it first."
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting Autonomous Agent..."
log_info "Project Root: $PROJECT_ROOT"
log_info "Roadmap: $ROADMAP"

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

# Create the prompt for Claude Code
PROMPT="You are operating as an autonomous Coder Agent. Follow the workflow defined in .claude/agents/coder_agent.md exactly.

Your task:
1. Read plans/roadmap.md
2. Find the next unclaimed work stream (Status: ⚪ Not Started or Status with 🔄 In Progress but Assigned To: -)
3. Claim the work stream by:
   - Updating Status to: 🔄 In Progress
   - Setting Assigned To: coder-autonomous-$(date +%s)
4. Follow ALL 6 phases of the Coder Agent workflow:
   - Phase 1: Claim Work Stream (DONE in step 3)
   - Phase 2: Analysis & Planning
   - Phase 3: Test-Driven Development (write tests FIRST, then implementation)
   - Phase 4: Integration & Validation (run tests, linters, type checking)
   - Phase 5: Documentation (update roadmap, write devlog entry)
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
claude --dangerously-skip-permissions-prompt "$PROMPT"

CLAUDE_EXIT_CODE=$?

if [[ $CLAUDE_EXIT_CODE -ne 0 ]]; then
    log_error "Claude Code execution failed with exit code $CLAUDE_EXIT_CODE"
    exit $CLAUDE_EXIT_CODE
fi

log_success "Claude Code execution completed"

# Check if working tree is dirty
log_info "Checking git working tree status..."

if [[ -n $(git status --porcelain) ]]; then
    log_warning "Working tree is dirty. Uncommitted changes detected."
    log_info "Launching Claude Code to commit remaining changes..."

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

    claude --dangerously-skip-permissions-prompt "$COMMIT_PROMPT"

    COMMIT_EXIT_CODE=$?

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

log_success "Autonomous agent completed successfully!"
log_info "Check docs/devlog.md for details on what was implemented."

exit 0
