"""
Agent Spawner - Allows agents to spawn other agents for tasks.

STRICT HIERARCHY:
- Human/Orchestrator can spawn PM
- PM can spawn Tech Lead
- Tech Lead can spawn Coders
- Coders CANNOT spawn other Coders (must request from TL)

This enables orchestration patterns where agents delegate work
while maintaining proper chain of command.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class SpawnResult:
    """Result of spawning an agent."""
    success: bool
    agent_type: str
    task: str
    log_file: Path | None = None
    pid: int | None = None
    error: str | None = None


@dataclass
class CoderRequest:
    """A coder's request for additional help from Tech Lead."""
    requester_name: str
    reason: str
    task_description: str
    timestamp: str
    status: str = "pending"


def _spawn_agent(
    agent_module: str,
    task: str | None,
    wait: bool,
    project_root: Path | None,
    agent_type: str,
) -> SpawnResult:
    """Internal function to spawn any agent type."""
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = project_root / "agent-logs" / project_root.name
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"spawned-{agent_type}-{timestamp}.log"

    # Build environment
    env = os.environ.copy()
    if task:
        env["TASK"] = task
    env["PYTHONPATH"] = str(project_root)

    # Build command
    cmd = [sys.executable, "-m", agent_module]

    try:
        if wait:
            with open(log_file, "w") as log:
                result = subprocess.run(
                    cmd,
                    cwd=project_root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=600,
                )
            return SpawnResult(
                success=result.returncode == 0,
                agent_type=agent_type,
                task=task or "standard workflow",
                log_file=log_file,
            )
        else:
            with open(log_file, "w") as log:
                proc = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            return SpawnResult(
                success=True,
                agent_type=agent_type,
                task=task or "standard workflow",
                log_file=log_file,
                pid=proc.pid,
            )

    except subprocess.TimeoutExpired:
        return SpawnResult(
            success=False,
            agent_type=agent_type,
            task=task or "standard workflow",
            log_file=log_file,
            error=f"{agent_type} timed out after 10 minutes",
        )
    except Exception as e:
        return SpawnResult(
            success=False,
            agent_type=agent_type,
            task=task or "standard workflow",
            error=str(e),
        )


# =============================================================================
# Agent Spawn Functions (with hierarchy enforcement)
# =============================================================================


def spawn_coder(
    task: str,
    wait: bool = False,
    project_root: Path | None = None,
) -> SpawnResult:
    """
    Spawn a coder agent with a specific task.

    ONLY callable by: Tech Lead, PM (not by other Coders!)
    Coders should use request_coder_help() to ask TL for additional coders.

    Args:
        task: The task description for the coder
        wait: If True, wait for completion. If False, run in background.
        project_root: Project root directory

    Returns:
        SpawnResult with success status and details
    """
    return _spawn_agent(
        agent_module="scripts.agents.coder",
        task=task,
        wait=wait,
        project_root=project_root,
        agent_type="coder",
    )


def spawn_tech_lead(
    task: str | None = None,
    wait: bool = False,
    project_root: Path | None = None,
) -> SpawnResult:
    """
    Spawn a Tech Lead agent.

    ONLY callable by: PM

    Args:
        task: Optional specific task (default: standard audit workflow)
        wait: If True, wait for completion. If False, run in background.
        project_root: Project root directory

    Returns:
        SpawnResult with success status and details
    """
    return _spawn_agent(
        agent_module="scripts.agents.tech_lead",
        task=task,
        wait=wait,
        project_root=project_root,
        agent_type="tech_lead",
    )


def spawn_pm(
    task: str | None = None,
    wait: bool = False,
    project_root: Path | None = None,
) -> SpawnResult:
    """
    Spawn a PM agent.

    ONLY callable by: Human, Orchestrator script

    Args:
        task: Optional specific task (default: standard PM workflow)
        wait: If True, wait for completion. If False, run in background.
        project_root: Project root directory

    Returns:
        SpawnResult with success status and details
    """
    return _spawn_agent(
        agent_module="scripts.agents.pm",
        task=task,
        wait=wait,
        project_root=project_root,
        agent_type="pm",
    )


# =============================================================================
# Coder Request System (for requesting help from Tech Lead)
# =============================================================================


def request_coder_help(
    requester_name: str,
    reason: str,
    task_description: str,
    project_root: Path | None = None,
) -> CoderRequest:
    """
    Request that the Tech Lead spawn an additional coder.

    Coders should use this instead of spawn_coder() directly.
    The Tech Lead will review pending requests during their audit.

    Args:
        requester_name: Name of the coder making the request
        reason: Why additional help is needed
        task_description: What the new coder should work on

    Returns:
        CoderRequest with details
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    requests_file = project_root / "config" / "coder_requests.json"
    requests_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing requests
    if requests_file.exists():
        with open(requests_file) as f:
            requests = json.load(f)
    else:
        requests = {"pending": [], "processed": []}

    # Create new request
    request = CoderRequest(
        requester_name=requester_name,
        reason=reason,
        task_description=task_description,
        timestamp=datetime.now().isoformat(),
        status="pending",
    )

    # Add to pending
    requests["pending"].append({
        "requester_name": request.requester_name,
        "reason": request.reason,
        "task_description": request.task_description,
        "timestamp": request.timestamp,
        "status": request.status,
    })

    # Save
    with open(requests_file, "w") as f:
        json.dump(requests, f, indent=2)
        f.write("\n")

    print(f"Request submitted! Tech Lead will review: {request.reason}")
    return request


def get_pending_coder_requests(project_root: Path | None = None) -> list[dict]:
    """
    Get pending coder requests (for Tech Lead to review).

    Args:
        project_root: Project root directory

    Returns:
        List of pending request dicts
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    requests_file = project_root / "config" / "coder_requests.json"

    if not requests_file.exists():
        return []

    with open(requests_file) as f:
        requests = json.load(f)

    return requests.get("pending", [])


def process_coder_request(
    request_index: int,
    approved: bool,
    project_root: Path | None = None,
) -> SpawnResult | None:
    """
    Tech Lead processes a coder request (approve or deny).

    Args:
        request_index: Index of the request in pending list
        approved: Whether to approve and spawn a coder
        project_root: Project root directory

    Returns:
        SpawnResult if approved, None if denied
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    requests_file = project_root / "config" / "coder_requests.json"

    if not requests_file.exists():
        return None

    with open(requests_file) as f:
        requests = json.load(f)

    pending = requests.get("pending", [])
    if request_index >= len(pending):
        return None

    request = pending.pop(request_index)
    request["status"] = "approved" if approved else "denied"
    request["processed_at"] = datetime.now().isoformat()
    requests["processed"].append(request)

    # Save updated requests
    with open(requests_file, "w") as f:
        json.dump(requests, f, indent=2)
        f.write("\n")

    # If approved, spawn the coder
    if approved:
        return spawn_coder(
            task=request["task_description"],
            wait=False,
            project_root=project_root,
        )

    return None


# =============================================================================
# Convenience Functions for Common Patterns
# =============================================================================


def spawn_coders_for_coverage(
    assignments: list[dict],
    wait: bool = False,
    project_root: Path | None = None,
) -> list[SpawnResult]:
    """
    Spawn multiple coders for coverage tasks.

    ONLY callable by: Tech Lead

    Args:
        assignments: List of dicts with 'file', 'coverage', 'priority' keys
        wait: If True, run sequentially. If False, run in parallel.
        project_root: Project root directory

    Returns:
        List of SpawnResults
    """
    results = []

    for assignment in assignments:
        file_path = assignment.get("file", "unknown")
        coverage = assignment.get("coverage", 0)
        priority = assignment.get("priority", "MEDIUM")

        task = f"""COVERAGE TASK: Write tests for {file_path}

Current coverage: {coverage}%
Target: 80%+
Priority: {priority}

Instructions:
1. Read {file_path} to understand the code
2. Check existing tests in tests/ for this module
3. Write comprehensive tests covering:
   - All public functions/methods
   - Edge cases and error conditions
   - Integration with dependencies
4. Run tests to verify they pass
5. Check coverage improved to 80%+
6. Commit with message "Tests: Improve coverage for {file_path}"

Focus on this ONE file. Do not modify the source code, only add tests.

IMPORTANT: If you need help from another coder, use request_coder_help() - do NOT spawn coders directly!
"""

        result = spawn_coder(
            task=task,
            wait=wait,
            project_root=project_root,
        )
        results.append(result)

    return results


def get_coverage_gaps(min_coverage: int = 80) -> list[dict]:
    """
    Get files below coverage threshold.

    Returns:
        List of dicts with file, coverage, priority
    """
    project_root = Path(__file__).parent.parent.parent

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "--cov=src", "--cov-report=term",
                "tests/", "-q", "--tb=no"
            ],
            cwd=project_root,
            env={**os.environ, "PYTHONPATH": str(project_root)},
            capture_output=True,
            text=True,
            timeout=120,
        )

        gaps = []
        for line in result.stdout.split("\n"):
            if line.startswith("src/") and "%" in line:
                parts = line.split()
                if len(parts) >= 4:
                    file_path = parts[0]
                    try:
                        coverage = int(parts[3].rstrip("%"))
                        if coverage < min_coverage:
                            # Determine priority
                            if "orchestrator" in file_path:
                                priority = "CRITICAL"
                            elif coverage == 0:
                                priority = "HIGH"
                            elif coverage < 50:
                                priority = "MEDIUM"
                            else:
                                priority = "LOW"

                            gaps.append({
                                "file": file_path,
                                "coverage": coverage,
                                "priority": priority,
                            })
                    except ValueError:
                        continue

        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        gaps.sort(key=lambda x: (priority_order.get(x["priority"], 99), x["coverage"]))

        return gaps

    except Exception as e:
        print(f"Error getting coverage gaps: {e}")
        return []


def run_full_cycle(wait: bool = True, project_root: Path | None = None) -> dict:
    """
    Run the full autonomous cycle: Coder → Tech Lead → PM

    This is what the autonomous_agent.sh script does, but callable from Python.

    Args:
        wait: If True, run each step sequentially
        project_root: Project root directory

    Returns:
        Dict with results from each stage
    """
    results = {}

    # Step 1: Run coder
    print("Step 1: Running coder agent...")
    results["coder"] = spawn_coder(
        task="",  # Use roadmap
        wait=wait,
        project_root=project_root,
    )

    if not results["coder"].success:
        print(f"Coder failed: {results['coder'].error}")
        return results

    # Step 2: Run tech lead
    print("Step 2: Running tech lead agent...")
    results["tech_lead"] = spawn_tech_lead(
        wait=wait,
        project_root=project_root,
    )

    if not results["tech_lead"].success:
        print(f"Tech Lead failed: {results['tech_lead'].error}")
        return results

    # Step 3: Run PM
    print("Step 3: Running PM agent...")
    results["pm"] = spawn_pm(
        wait=wait,
        project_root=project_root,
    )

    return results
