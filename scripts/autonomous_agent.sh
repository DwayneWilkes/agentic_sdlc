#!/bin/bash
set -euo pipefail

# Autonomous Agent - Orchestrated Workflow
# This script orchestrates the full autonomous development cycle:
#   1. Run coder agent (6-phase TDD workflow) - Python: scripts.agents.coder
#   2. Verify clean worktree (Tech Lead investigates if dirty)
#   3. Run Tech Lead quality audit - Python: scripts.agents.tech_lead
#   4. Run PM documentation update - Python: scripts.agents.pm
#   5. Requirements compliance check (periodic - Mondays or RUN_REQUIREMENTS_CHECK=true)
#
# The orchestrator is responsible for requirements.md governance.
# Agent launchers are Python modules in scripts/agents/ for maintainability.
#
# Hierarchy: Orchestrator (bash) → PM → Tech Lead → Coders (all Python)
#
# Signal Handling:
#   SIGTERM - Graceful stop: finish current operation, save state, exit
#   SIGINT  - Graceful stop: same as SIGTERM
#   SIGUSR1 - Immediate stop: kill child process immediately
#
# Usage:
#   ./scripts/autonomous_agent.sh                    # Work on orchestrator itself
#   TARGET_PATH=/path/to/repo ./scripts/autonomous_agent.sh  # Work on external repo
#
# Environment Variables:
#   TARGET_PATH          - Path to target repository (default: orchestrator)
#   TARGET_NAME          - Name for logging (default: directory name)
#   TARGET_ROADMAP       - Roadmap file path (default: plans/roadmap.md)
#   SKIP_PM_VERIFY       - Skip PM verification step (default: false)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=agent_common.sh
source "$SCRIPT_DIR/agent_common.sh"

# Resolve project paths
resolve_project_paths "$SCRIPT_DIR"

# Setup logging (logs go to orchestrator root for centralized monitoring)
setup_logging "autonomous-agent" "$ORCHESTRATOR_ROOT" "$PROJECT_NAME"

# Track child process for signal handling
CHILD_PID=""
STOP_FILE="$LOG_DIR/.stop-$TIMESTAMP"

# Graceful shutdown handler
graceful_shutdown() {
    log_warning "Received stop signal - initiating graceful shutdown..."
    log_to_file "GRACEFUL SHUTDOWN REQUESTED at $(date)"

    # Create stop file for agent to detect
    echo "graceful" > "$STOP_FILE"

    # Give the child time to finish current operation
    log_info "Waiting for agent to complete current operation (max 30s)..."

    local wait_count=0
    while [[ $wait_count -lt 30 ]] && [[ -n "$CHILD_PID" ]] && kill -0 "$CHILD_PID" 2>/dev/null; do
        sleep 1
        ((wait_count++))
    done

    if [[ -n "$CHILD_PID" ]] && kill -0 "$CHILD_PID" 2>/dev/null; then
        log_warning "Agent still running after 30s, sending SIGTERM..."
        kill -TERM "$CHILD_PID" 2>/dev/null || true
        sleep 2
    fi

    # Cleanup
    rm -f "$STOP_FILE"
    log_info "Graceful shutdown complete"
    exit 0
}

# Immediate shutdown handler
immediate_shutdown() {
    log_warning "Received IMMEDIATE stop signal!"
    log_to_file "IMMEDIATE SHUTDOWN at $(date)"

    echo "immediate" > "$STOP_FILE"

    # Kill immediately
    if [[ -n "$CHILD_PID" ]]; then
        kill -KILL "$CHILD_PID" 2>/dev/null || true
    fi
    rm -f "$STOP_FILE"
    exit 1
}

# Register signal handlers
trap graceful_shutdown SIGTERM SIGINT
trap immediate_shutdown SIGUSR1

# Check prerequisites
require_claude_cli

# Change to project root
cd "$PROJECT_ROOT"

log_info "Starting Autonomous Agent Orchestration..."
log_info "Target Mode: $TARGET_MODE"
log_info "Project Root: $PROJECT_ROOT"
log_info "Log File: $LOG_FILE"

log_to_file "=== Autonomous Agent Orchestration - $TIMESTAMP ==="
log_to_file "Target Mode: $TARGET_MODE"
log_to_file "Project Root: $PROJECT_ROOT"
log_to_file ""

# ==============================================================================
# STEP 1: Run Coder Agent
# ==============================================================================
log_info "Step 1/5: Running Coder Agent..."
log_to_file "=== STEP 1: Coder Agent ==="
log_to_file "Starting: $(date)"
log_to_file ""

# Export environment for child script
export TARGET_PATH TARGET_NAME TARGET_ROADMAP TARGET_CODER_AGENT TARGET_IDENTITY_CONTEXT

# Run coder agent (Python version)
PYTHONPATH="$ORCHESTRATOR_ROOT" "$ORCHESTRATOR_ROOT/.venv/bin/python" -m scripts.agents.coder 2>&1 | tee -a "$LOG_FILE" &
CHILD_PID=$!

# Wait for coder to complete
wait $CHILD_PID
CODER_EXIT_CODE=$?
CHILD_PID=""

log_to_file ""
log_to_file "Coder Agent completed: $(date)"
log_to_file "Exit code: $CODER_EXIT_CODE"
log_to_file ""

if [[ $CODER_EXIT_CODE -ne 0 ]]; then
    log_error "Coder Agent failed with exit code $CODER_EXIT_CODE"
    log_to_file "ERROR: Coder Agent failed with exit code $CODER_EXIT_CODE"
    exit $CODER_EXIT_CODE
fi

log_success "Coder Agent completed"

# ==============================================================================
# STEP 2: Verify Clean Worktree (or investigate if dirty)
# ==============================================================================
log_info "Step 2/5: Verifying coder committed all changes..."

if ! require_clean_worktree; then
    log_info "Handing off to Tech Lead to investigate dirty worktree..."

    # Pass the coder's log file for context
    CODER_LOG="$LOG_DIR/coder-agent-$TIMESTAMP.log"
    if ! investigate_dirty_worktree "$CODER_LOG"; then
        log_error "Tech Lead could not resolve. PM/human review required."
        exit 1
    fi
fi

# ==============================================================================
# STEP 3: Tech Lead Quality Audit (ALWAYS runs)
# ==============================================================================
if [[ "${SKIP_TL_AUDIT:-}" == "true" ]]; then
    log_info "Step 3/5: Skipping TL audit (SKIP_TL_AUDIT=true)"
else
    log_info "Step 3/5: Running Tech Lead quality audit..."
    log_to_file "=== STEP 3: Tech Lead Quality Audit ==="
    log_to_file "Starting: $(date)"
    log_to_file ""

    # Run the full Tech Lead agent (Python version)
    if [[ -f "$ORCHESTRATOR_ROOT/scripts/agents/tech_lead.py" ]]; then
        PYTHONPATH="$ORCHESTRATOR_ROOT" "$ORCHESTRATOR_ROOT/.venv/bin/python" -m scripts.agents.tech_lead 2>&1 | tee -a "$LOG_FILE" &
        CHILD_PID=$!
        wait $CHILD_PID
        TL_EXIT_CODE=$?
        CHILD_PID=""

        log_to_file ""
        log_to_file "Tech Lead audit completed: $(date)"
        log_to_file "Exit code: $TL_EXIT_CODE"
        log_to_file ""

        if [[ $TL_EXIT_CODE -ne 0 ]]; then
            log_warning "Tech Lead audit had issues (exit code $TL_EXIT_CODE)"
            log_to_file "WARNING: Tech Lead audit failed with exit code $TL_EXIT_CODE"
        else
            log_success "Tech Lead audit completed"
        fi
    else
        log_warning "Tech Lead agent not found"
    fi
fi

# ==============================================================================
# STEP 4: PM Full Documentation Update (ALWAYS runs)
# ==============================================================================
if [[ "${SKIP_PM_VERIFY:-}" == "true" ]]; then
    log_info "Step 4/5: Skipping PM update (SKIP_PM_VERIFY=true)"
else
    log_info "Step 4/5: Running PM for full documentation update..."
    log_to_file "=== STEP 4: PM Documentation Update ==="
    log_to_file "Starting: $(date)"
    log_to_file ""

    # Run the full PM agent (Python version)
    if [[ -f "$ORCHESTRATOR_ROOT/scripts/agents/pm.py" ]]; then
        PYTHONPATH="$ORCHESTRATOR_ROOT" "$ORCHESTRATOR_ROOT/.venv/bin/python" -m scripts.agents.pm 2>&1 | tee -a "$LOG_FILE" &
        CHILD_PID=$!
        wait $CHILD_PID
        PM_EXIT_CODE=$?
        CHILD_PID=""

        log_to_file ""
        log_to_file "PM update completed: $(date)"
        log_to_file "Exit code: $PM_EXIT_CODE"
        log_to_file ""

        if [[ $PM_EXIT_CODE -ne 0 ]]; then
            log_warning "PM update had issues (exit code $PM_EXIT_CODE)"
            log_to_file "WARNING: PM update failed with exit code $PM_EXIT_CODE"
        else
            log_success "PM documentation update completed"
        fi
    else
        log_warning "PM agent not found"
    fi
fi

# ==============================================================================
# STEP 5: Orchestrator Requirements Compliance (periodic)
# ==============================================================================
if [[ "${RUN_REQUIREMENTS_CHECK:-}" == "true" ]] || [[ $(date +%u) == "1" ]]; then
    # Run on Mondays or when explicitly requested
    log_info "Step 5/5: Running requirements compliance check..."
    log_to_file "=== STEP 5: Requirements Compliance Check ==="
    log_to_file "Starting: $(date)"
    log_to_file ""

    # Generate requirements compliance report
    if PYTHONPATH="$PROJECT_ROOT" "$PROJECT_ROOT/.venv/bin/python" -c "from src.orchestrator.requirements_compliance import generate_compliance_report, save_compliance_report; report = generate_compliance_report(); save_compliance_report(report)" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Requirements compliance report generated"
        log_info "Check docs/requirements-compliance.md for the compliance report."
    else
        log_warning "Requirements compliance check had issues"
    fi
    log_to_file ""
else
    log_info "Step 5/5: Skipping requirements check (run on Mondays or set RUN_REQUIREMENTS_CHECK=true)"
fi

# ==============================================================================
# Complete
# ==============================================================================
log_to_file "=== Autonomous Agent Orchestration Complete ==="
log_to_file "Finished: $(date)"
log_to_file ""

log_success "Autonomous agent completed successfully!"
log_info "Check docs/devlog.md for details on what was implemented."
log_info "Full execution log: $LOG_FILE"

exit 0
