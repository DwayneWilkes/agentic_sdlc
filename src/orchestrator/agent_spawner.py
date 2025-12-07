"""
Agent Spawner - Allows agents to spawn other agents for tasks.

STRICT HIERARCHY:
- Human/Orchestrator can spawn PM
- PM can spawn Tech Lead
- Tech Lead can spawn Coders
- Coders CANNOT spawn other Coders (must request from TL)

COFFEE BREAKS:
- Agents notify TL when going on break after completing work
- Agents on break are "available" not "busy" - can be recalled
- Breaks are for knowledge sharing and relationship building
- No need to spawn new agents if existing ones are on break

This enables orchestration patterns where agents delegate work
while maintaining proper chain of command.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Literal


class AgentStatus(str, Enum):
    """Agent availability status."""
    WORKING = "working"      # Currently executing a task
    ON_BREAK = "on_break"    # On coffee break (can be recalled)
    AVAILABLE = "available"  # Ready for new work


# Fair break durations by role (in SECONDS)
# Digital employees operate at token speeds - a 5-minute task is like an 8-hour human day
# So 30-120 second breaks are proportionally fair (like a 10-30 min human break)
BREAK_DURATIONS_SECONDS = {
    "coder": 60,      # 1 minute - quick sync after completing a phase
    "tech_lead": 90,  # 1.5 minutes - review discussions with team
    "pm": 120,        # 2 minutes - strategic overview
    "default": 60,    # Default for any role
}


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


# =============================================================================
# Coffee Break System - Agent Status & Availability
# =============================================================================


def _get_status_file(project_root: Path | None = None) -> Path:
    """Get the path to the agent status file."""
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent
    status_file = project_root / "config" / "agent_status.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)
    return status_file


def _load_status(project_root: Path | None = None) -> dict:
    """Load agent status from file."""
    status_file = _get_status_file(project_root)
    if status_file.exists():
        with open(status_file) as f:
            return json.load(f)
    return {"agents": {}, "breaks": []}


def _save_status(status: dict, project_root: Path | None = None) -> None:
    """Save agent status to file."""
    status_file = _get_status_file(project_root)
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)
        f.write("\n")


def _get_break_duration_seconds(agent_name: str, project_root: Path | None = None) -> int:
    """Get the fair break duration in seconds for an agent based on their role."""
    from src.core.agent_naming import get_naming

    naming = get_naming()
    agent_id = naming.get_agent_id(agent_name)
    if agent_id:
        entry = naming.config["assigned_names"].get(agent_id, {})
        role = entry.get("role", "default")
        return BREAK_DURATIONS_SECONDS.get(role, BREAK_DURATIONS_SECONDS["default"])
    return BREAK_DURATIONS_SECONDS["default"]


def notify_going_on_break(
    agent_name: str,
    break_partners: list[str] | None = None,
    topic: str | None = None,
    duration_seconds: int | None = None,
    project_root: Path | None = None,
) -> dict:
    """
    Notify that an agent is going on a coffee break.

    Agents on break are AVAILABLE, not busy - they can be recalled for new work.
    Breaks are for knowledge sharing and relationship building.
    Breaks have fair durations based on role (coders: 60s, TL: 90s, PM: 120s).

    Args:
        agent_name: Name of the agent going on break
        break_partners: Other agents joining the break (optional)
        topic: Topic for discussion (optional)
        duration_seconds: Override default duration in seconds (optional)
        project_root: Project root directory

    Returns:
        Dict with break_id, participants, and scheduled_end
    """
    status = _load_status(project_root)
    break_id = f"break-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{agent_name}"

    # Calculate break duration in seconds (use role-based default if not specified)
    if duration_seconds is None:
        duration_seconds = _get_break_duration_seconds(agent_name, project_root)

    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration_seconds)

    # Update agent status
    status["agents"][agent_name] = {
        "status": AgentStatus.ON_BREAK.value,
        "break_id": break_id,
        "started_at": start_time.isoformat(),
        "scheduled_end": end_time.isoformat(),
        "duration_seconds": duration_seconds,
    }

    # Update partners' status too
    partners = break_partners or []
    for partner in partners:
        partner_duration = _get_break_duration_seconds(partner, project_root)
        partner_end = start_time + timedelta(seconds=partner_duration)
        status["agents"][partner] = {
            "status": AgentStatus.ON_BREAK.value,
            "break_id": break_id,
            "started_at": start_time.isoformat(),
            "scheduled_end": partner_end.isoformat(),
            "duration_seconds": partner_duration,
        }

    # Record the break session
    break_record = {
        "break_id": break_id,
        "initiator": agent_name,
        "participants": [agent_name] + partners,
        "topic": topic or "General knowledge sharing",
        "started_at": start_time.isoformat(),
        "scheduled_end": end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "ended_at": None,
        "recalled": False,
    }
    status["breaks"].append(break_record)

    _save_status(status, project_root)

    print(f"☕ {agent_name} is going on a {duration_seconds}-second break" +
          (f" with {', '.join(partners)}" if partners else ""))
    if topic:
        print(f"   Topic: {topic}")
    print(f"   Scheduled end: {end_time.strftime('%H:%M:%S')}")

    return {
        "break_id": break_id,
        "participants": break_record["participants"],
        "duration_seconds": duration_seconds,
        "scheduled_end": end_time.isoformat(),
    }


def recall_from_break(
    agent_name: str,
    task_description: str,
    project_root: Path | None = None,
) -> bool:
    """
    Recall an agent from their coffee break for a new task.

    The agent can finish their current conversation but should wrap up promptly.

    Args:
        agent_name: Name of the agent to recall
        task_description: Brief description of why they're needed
        project_root: Project root directory

    Returns:
        True if agent was on break and recalled, False otherwise
    """
    status = _load_status(project_root)

    agent_status = status["agents"].get(agent_name, {})
    if agent_status.get("status") != AgentStatus.ON_BREAK.value:
        return False

    # Find and update the break record
    break_id = agent_status.get("break_id")
    for break_record in status["breaks"]:
        if break_record["break_id"] == break_id and not break_record["ended_at"]:
            break_record["recalled"] = True
            break_record["recall_reason"] = task_description
            break_record["recall_time"] = datetime.now().isoformat()
            break

    # Update agent status to available
    status["agents"][agent_name] = {
        "status": AgentStatus.AVAILABLE.value,
        "updated_at": datetime.now().isoformat(),
        "last_break_id": break_id,
    }

    _save_status(status, project_root)

    print(f"📢 Recalling {agent_name} from break: {task_description}")
    return True


def end_break(
    agent_name: str,
    summary: str | None = None,
    project_root: Path | None = None,
) -> None:
    """
    End a coffee break naturally (not recalled).

    Args:
        agent_name: Name of the agent ending their break
        summary: Optional summary of what was discussed
        project_root: Project root directory
    """
    status = _load_status(project_root)

    agent_status = status["agents"].get(agent_name, {})
    break_id = agent_status.get("break_id")

    # Find and update the break record
    for break_record in status["breaks"]:
        if break_record["break_id"] == break_id and not break_record["ended_at"]:
            break_record["ended_at"] = datetime.now().isoformat()
            if summary:
                break_record["summary"] = summary
            break

    # Update agent status
    status["agents"][agent_name] = {
        "status": AgentStatus.AVAILABLE.value,
        "updated_at": datetime.now().isoformat(),
        "last_break_id": break_id,
    }

    _save_status(status, project_root)
    print(f"✅ {agent_name} is back from break")


def _check_expired_breaks(project_root: Path | None = None) -> list[str]:
    """
    Check for and auto-end expired breaks.

    Returns:
        List of agent names whose breaks were auto-ended
    """
    status = _load_status(project_root)
    now = datetime.now()
    auto_ended = []

    for name, info in list(status["agents"].items()):
        if info.get("status") == AgentStatus.ON_BREAK.value:
            scheduled_end = info.get("scheduled_end")
            if scheduled_end:
                end_time = datetime.fromisoformat(scheduled_end)
                if now > end_time:
                    # Break has expired - auto-end it
                    status["agents"][name] = {
                        "status": AgentStatus.AVAILABLE.value,
                        "updated_at": now.isoformat(),
                        "last_break_id": info.get("break_id"),
                        "auto_ended": True,
                    }
                    auto_ended.append(name)

                    # Update the break record
                    break_id = info.get("break_id")
                    for break_record in status["breaks"]:
                        if break_record["break_id"] == break_id and not break_record["ended_at"]:
                            break_record["ended_at"] = now.isoformat()
                            break_record["auto_ended"] = True
                            break

    if auto_ended:
        _save_status(status, project_root)
        for name in auto_ended:
            print(f"⏰ {name}'s break time ended (auto-returned to available)")

    return auto_ended


def get_agents_on_break(project_root: Path | None = None) -> list[dict]:
    """
    Get list of agents currently on break.

    Also auto-ends any expired breaks before returning the list.

    Returns:
        List of dicts with agent info and break details including:
        - name: Agent name
        - break_id: Break session ID
        - started_at: When break started
        - scheduled_end: When break is scheduled to end
        - duration_seconds: Break duration in seconds
        - time_remaining_seconds: Seconds remaining (negative if overtime)
    """
    # First, check for and auto-end any expired breaks
    _check_expired_breaks(project_root)

    status = _load_status(project_root)
    now = datetime.now()
    on_break = []

    for name, info in status["agents"].items():
        if info.get("status") == AgentStatus.ON_BREAK.value:
            scheduled_end = info.get("scheduled_end")
            time_remaining = None
            if scheduled_end:
                end_time = datetime.fromisoformat(scheduled_end)
                time_remaining = int((end_time - now).total_seconds())

            on_break.append({
                "name": name,
                "break_id": info.get("break_id"),
                "started_at": info.get("started_at"),
                "scheduled_end": scheduled_end,
                "duration_seconds": info.get("duration_seconds"),
                "time_remaining_seconds": time_remaining,
            })

    return on_break


def get_available_agents(role: str | None = None, project_root: Path | None = None) -> list[str]:
    """
    Get list of available agents (not working, including those on break).

    Agents on break ARE available - they can be recalled for work.
    This function also auto-ends any expired breaks before checking.

    Args:
        role: Optional role filter (uses agent_naming to check)
        project_root: Project root directory

    Returns:
        List of agent names that are available
    """
    # First, check for and auto-end any expired breaks
    _check_expired_breaks(project_root)

    status = _load_status(project_root)

    # Get all agents not marked as WORKING
    available = []
    for name, info in status["agents"].items():
        if info.get("status") != AgentStatus.WORKING.value:
            available.append(name)

    # If role filter specified, check against agent_naming
    if role:
        from src.core.agent_naming import get_agents_by_role
        role_agents = {a["name"] for a in get_agents_by_role(role)}
        available = [a for a in available if a in role_agents]

    return available


def set_agent_working(agent_name: str, task: str, project_root: Path | None = None) -> None:
    """
    Mark an agent as working on a task.

    Args:
        agent_name: Name of the agent
        task: Description of the task
        project_root: Project root directory
    """
    status = _load_status(project_root)

    status["agents"][agent_name] = {
        "status": AgentStatus.WORKING.value,
        "task": task,
        "started_at": datetime.now().isoformat(),
    }

    _save_status(status, project_root)


def set_agent_available(agent_name: str, project_root: Path | None = None) -> None:
    """
    Mark an agent as available for new work.

    Args:
        agent_name: Name of the agent
        project_root: Project root directory
    """
    status = _load_status(project_root)

    status["agents"][agent_name] = {
        "status": AgentStatus.AVAILABLE.value,
        "updated_at": datetime.now().isoformat(),
    }

    _save_status(status, project_root)
