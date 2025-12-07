#!/bin/bash
# agent_common.sh - Shared utilities for agent scripts
#
# Usage: source "$(dirname "${BASH_SOURCE[0]}")/agent_common.sh"
#
# Provides:
#   - Color constants (RED, GREEN, YELLOW, BLUE, NC)
#   - Logging functions (log_info, log_success, log_warning, log_error, log_to_file)
#   - Common checks (require_claude_cli, require_file)
#   - Log directory setup (setup_logging)
#   - Project path resolution (resolve_project_paths)
#   - Worktree checks (require_clean_worktree, investigate_dirty_worktree)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Log to both terminal and file (requires LOG_FILE to be set)
log_to_file() {
    if [[ -n "${LOG_FILE:-}" ]]; then
        echo "$1" | tee -a "$LOG_FILE"
    else
        echo "$1"
    fi
}

# Check if Claude Code CLI is available
require_claude_cli() {
    if ! command -v claude &> /dev/null; then
        log_error "Claude Code CLI not found. Please install it first."
        exit 1
    fi
}

# Check if a required file exists
require_file() {
    local file_path="$1"
    local description="${2:-File}"
    if [[ ! -f "$file_path" ]]; then
        log_error "$description not found at $file_path"
        exit 1
    fi
}

# Setup logging directory and file
# Usage: setup_logging "agent-name" "$PROJECT_ROOT"
# Sets: LOG_DIR, LOG_FILE, TIMESTAMP
setup_logging() {
    local agent_name="$1"
    local log_root="${2:-$PROJECT_ROOT}"
    local project_name="${3:-$(basename "$log_root")}"

    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    LOG_DIR="$log_root/agent-logs/$project_name"
    LOG_FILE="$LOG_DIR/$agent_name-$TIMESTAMP.log"

    mkdir -p "$LOG_DIR"

    export TIMESTAMP LOG_DIR LOG_FILE
}

# Resolve project paths from environment or defaults
# Usage: resolve_project_paths
# Sets: PROJECT_ROOT, PROJECT_NAME, TARGET_MODE, and various path variables
resolve_project_paths() {
    local script_dir="$1"
    local orchestrator_root="$(cd "$script_dir/.." && pwd)"

    if [[ -n "${TARGET_PATH:-}" ]]; then
        PROJECT_ROOT="$TARGET_PATH"
        PROJECT_NAME="${TARGET_NAME:-$(basename "$PROJECT_ROOT")}"
        ROADMAP="$PROJECT_ROOT/${TARGET_ROADMAP:-plans/roadmap.md}"
        CODER_AGENT="$PROJECT_ROOT/${TARGET_CODER_AGENT:-.claude/agents/coder_agent.md}"
        PM_AGENT="$PROJECT_ROOT/${TARGET_PM_AGENT:-.claude/agents/project_manager.md}"
        CONVENTIONS="$PROJECT_ROOT/${TARGET_CONVENTIONS:-CLAUDE.md}"
        IDENTITY_CONTEXT="${TARGET_IDENTITY_CONTEXT:-}"
        TARGET_MODE="external"
    else
        PROJECT_ROOT="$orchestrator_root"
        PROJECT_NAME="$(basename "$PROJECT_ROOT")"
        ROADMAP="$PROJECT_ROOT/plans/roadmap.md"
        CODER_AGENT="$PROJECT_ROOT/.claude/agents/coder_agent.md"
        PM_AGENT="$PROJECT_ROOT/.claude/agents/project_manager.md"
        CONVENTIONS="$PROJECT_ROOT/CLAUDE.md"
        IDENTITY_CONTEXT=""
        TARGET_MODE="self"
    fi

    export PROJECT_ROOT PROJECT_NAME ROADMAP CODER_AGENT PM_AGENT CONVENTIONS IDENTITY_CONTEXT TARGET_MODE
    export ORCHESTRATOR_ROOT="$orchestrator_root"
}

# Check that working tree is clean (no uncommitted changes)
# Usage: require_clean_worktree
# Returns: 0 if clean, 1 if dirty (with error message)
require_clean_worktree() {
    if [[ -z $(git status --porcelain) ]]; then
        log_success "Working tree is clean."
        return 0
    fi

    log_warning "Working tree is dirty. Uncommitted changes detected:"
    git status --short
    log_to_file "WARNING: Uncommitted changes detected"
    log_to_file "$(git status --short)"
    return 1
}

# Investigate dirty worktree - called when coder fails to commit
# The Tech Lead investigates and either commits, calls the coder back, or escalates.
# Usage: investigate_dirty_worktree "$LOG_FILE"
# Returns: 0 if resolved, 1 if needs human intervention
investigate_dirty_worktree() {
    local coder_log="${1:-}"

    log_info "Tech Lead investigating uncommitted changes..."
    log_to_file "=== Tech Lead Investigation ==="
    log_to_file "Starting: $(date)"
    log_to_file ""

    local log_context=""
    if [[ -n "$coder_log" && -f "$coder_log" ]]; then
        log_context="The coder agent's log is at: $coder_log
Review the last ~100 lines to understand what happened."
    fi

    local investigate_prompt="You are the Tech Lead. A coder agent left uncommitted changes. Investigate and resolve.

DIRTY FILES:
$(git status --short)

$log_context

INVESTIGATION STEPS:
1. Examine the uncommitted files with 'git diff' and 'git diff --cached'
2. Check docs/devlog.md for what work was attempted
3. Check plans/roadmap.md for the claimed work stream
4. Run quality gates to assess completion:
   - pytest tests/ -v
   - ruff check src/ tests/
   - mypy src/

DECISION MATRIX:
| Situation | Action |
|-----------|--------|
| Work complete, gates pass | Commit the changes yourself |
| Work incomplete, minor issues | Call coder back to finish (see below) |
| Work incomplete, major issues | Leave uncommitted, report for PM review |
| Coder misunderstood task | Leave uncommitted, report for PM review |

TO CALL CODER BACK (if work is incomplete but fixable):
Run this command to spawn the coder to fix their work:

claude -p --model sonnet --dangerously-skip-permissions \"
You previously worked on a task but left uncommitted changes.

PROBLEM:
\$(git status --short)

QUALITY GATE RESULTS:
\$(pytest tests/ -v 2>&1 | tail -30)

YOUR TASK:
1. Fix any failing tests
2. Ensure all quality gates pass (pytest, ruff, mypy)
3. Commit your changes with a descriptive message

Do not leave uncommitted changes.
\"

After calling the coder back, verify the worktree is clean.

Be thorough. Report your findings and actions taken."

    # Tech Lead uses Opus for investigation (complex reasoning)
    claude -p --model opus --dangerously-skip-permissions "$investigate_prompt" 2>&1 | tee -a "$LOG_FILE"
    local exit_code=${PIPESTATUS[0]}

    log_to_file ""
    log_to_file "Tech Lead investigation completed: $(date)"
    log_to_file "Exit code: $exit_code"
    log_to_file ""

    if [[ $exit_code -ne 0 ]]; then
        log_error "Tech Lead investigation failed with exit code $exit_code"
        return 1
    fi

    # Check if worktree is now clean
    if [[ -z $(git status --porcelain) ]]; then
        log_success "Tech Lead resolved - changes committed."
        return 0
    else
        log_warning "Tech Lead investigation complete - changes left for PM/human review."
        git status --short
        return 1
    fi
}
