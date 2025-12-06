"""
Agent Runner - Spawns and monitors autonomous agents.

Handles:
- Spawning agent processes (via autonomous_agent.sh)
- Monitoring agent status
- Capturing agent output
- Detecting completion/failure
- NATS-based coordination for race condition prevention
"""

import subprocess
import threading
import asyncio
import time
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable
import os
import signal

from src.core.agent_naming import AgentNaming, get_naming
from src.core.agent_memory import get_memory, AgentMemory
from src.coordination.nats_bus import NATSMessageBus, MessageType, get_message_bus


class AgentState(str, Enum):
    """State of an agent process."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


@dataclass
class AgentProcess:
    """Represents a running or completed agent process."""

    agent_id: str
    work_stream_id: str
    state: AgentState = AgentState.PENDING
    process: Optional[subprocess.Popen] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    # Output storage: head (first lines), tail (recent lines), important (errors/warnings)
    _output_head: list[str] = field(default_factory=list)  # First 100 lines
    _output_tail: list[str] = field(default_factory=list)  # Rolling last 200 lines
    _output_important: list[str] = field(default_factory=list)  # Errors/warnings
    _total_lines: int = 0
    error_lines: list[str] = field(default_factory=list)
    log_file: Optional[Path] = None
    personal_name: Optional[str] = None

    # Limits for output storage
    HEAD_LIMIT = 100
    TAIL_LIMIT = 200
    IMPORTANT_LIMIT = 100

    @property
    def output_lines(self) -> list[str]:
        """Get all stored output lines (head + ... + tail)."""
        if self._total_lines <= self.HEAD_LIMIT + self.TAIL_LIMIT:
            return self._output_head + self._output_tail
        else:
            gap = self._total_lines - self.HEAD_LIMIT - len(self._output_tail)
            return (
                self._output_head +
                [f"... [{gap} lines omitted, {len(self._output_important)} important lines captured] ..."] +
                self._output_tail
            )

    def add_output_line(self, line: str) -> None:
        """Add an output line with smart storage."""
        self._total_lines += 1

        # Store in head if still filling
        if len(self._output_head) < self.HEAD_LIMIT:
            self._output_head.append(line)
        else:
            # Add to rolling tail
            self._output_tail.append(line)
            if len(self._output_tail) > self.TAIL_LIMIT:
                self._output_tail.pop(0)

        # Check for important lines (errors, warnings, failures)
        line_lower = line.lower()
        if any(marker in line_lower for marker in ["error", "failed", "exception", "traceback", "warning"]):
            if len(self._output_important) < self.IMPORTANT_LIMIT:
                self._output_important.append(f"[L{self._total_lines}] {line}")

    @property
    def important_lines(self) -> list[str]:
        """Get important lines (errors, warnings, etc.)."""
        return self._output_important.copy()

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration of agent run in seconds."""
        if not self.started_at:
            return None
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return self.state == AgentState.RUNNING

    @property
    def is_finished(self) -> bool:
        """Check if agent has finished (success or failure)."""
        return self.state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.TIMEOUT,
            AgentState.KILLED,
        )


class WorkStreamCoordinator:
    """
    Coordinates work stream claims via NATS to prevent race conditions.

    Uses request/reply pattern for atomic claiming and broadcasts
    for status updates.
    """

    def __init__(self):
        self._claimed: dict[str, str] = {}  # work_stream_id -> agent_id
        self._lock = threading.Lock()
        self._nats_bus: Optional[NATSMessageBus] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def _get_bus(self) -> NATSMessageBus:
        """Get or create NATS connection."""
        if self._nats_bus is None:
            self._nats_bus = await get_message_bus()
        return self._nats_bus

    def _run_async(self, coro):
        """Run async code from sync context."""
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule in running loop
                import concurrent.futures
                future = concurrent.futures.Future()
                def callback():
                    try:
                        result = asyncio.ensure_future(coro)
                        result.add_done_callback(
                            lambda f: future.set_result(f.result()) if not f.exception()
                            else future.set_exception(f.exception())
                        )
                    except Exception as e:
                        future.set_exception(e)
                loop.call_soon_threadsafe(callback)
                return future.result(timeout=5)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(coro)

    def claim_work_stream(self, work_stream_id: str, agent_id: str) -> bool:
        """
        Attempt to claim a work stream for an agent.

        Uses NATS for distributed coordination.

        Args:
            work_stream_id: The work stream to claim
            agent_id: The agent claiming it

        Returns:
            True if claimed successfully, False if already claimed
        """
        with self._lock:
            # Check local cache first
            if work_stream_id in self._claimed:
                owner = self._claimed[work_stream_id]
                if owner != agent_id:
                    return False
                return True  # Already claimed by this agent

            # Try to claim via NATS broadcast
            try:
                self._run_async(self._broadcast_claim(work_stream_id, agent_id))
            except Exception as e:
                # NATS unavailable, use local-only coordination
                print(f"NATS unavailable for claim broadcast: {e}")

            # Record local claim
            self._claimed[work_stream_id] = agent_id
            return True

    async def _broadcast_claim(self, work_stream_id: str, agent_id: str) -> None:
        """Broadcast work stream claim via NATS."""
        bus = await self._get_bus()
        await bus.broadcast(
            from_agent=agent_id,
            message_type=MessageType.TASK_ASSIGNED,
            content={
                "work_stream_id": work_stream_id,
                "agent_id": agent_id,
                "action": "claim",
                "timestamp": datetime.now().isoformat(),
            }
        )

    def release_work_stream(self, work_stream_id: str, agent_id: str) -> bool:
        """
        Release a work stream claim.

        Args:
            work_stream_id: The work stream to release
            agent_id: The agent releasing it

        Returns:
            True if released, False if not owned by agent
        """
        with self._lock:
            if work_stream_id not in self._claimed:
                return True  # Already released

            if self._claimed[work_stream_id] != agent_id:
                return False  # Not owned by this agent

            del self._claimed[work_stream_id]

            try:
                self._run_async(self._broadcast_release(work_stream_id, agent_id))
            except Exception:
                pass  # Best effort

            return True

    async def _broadcast_release(self, work_stream_id: str, agent_id: str) -> None:
        """Broadcast work stream release via NATS."""
        bus = await self._get_bus()
        await bus.broadcast(
            from_agent=agent_id,
            message_type=MessageType.TASK_COMPLETE,
            content={
                "work_stream_id": work_stream_id,
                "agent_id": agent_id,
                "action": "release",
                "timestamp": datetime.now().isoformat(),
            }
        )

    def broadcast_status(self, agent_id: str, work_stream_id: str, status: str, details: dict = None) -> None:
        """
        Broadcast agent status update via NATS.

        Args:
            agent_id: The agent's ID
            work_stream_id: The work stream
            status: Status string (started, completed, failed, etc.)
            details: Additional details
        """
        try:
            self._run_async(self._do_broadcast_status(agent_id, work_stream_id, status, details or {}))
        except Exception as e:
            print(f"NATS status broadcast failed: {e}")

    async def _do_broadcast_status(self, agent_id: str, work_stream_id: str, status: str, details: dict) -> None:
        """Actually broadcast status via NATS."""
        bus = await self._get_bus()
        await bus.broadcast(
            from_agent=agent_id,
            message_type=MessageType.STATUS_UPDATE,
            content={
                "work_stream_id": work_stream_id,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                **details,
            }
        )

    def get_claimed_streams(self) -> dict[str, str]:
        """Get all currently claimed work streams."""
        with self._lock:
            return self._claimed.copy()

    def is_claimed(self, work_stream_id: str) -> Optional[str]:
        """Check if a work stream is claimed. Returns agent_id if claimed, None otherwise."""
        with self._lock:
            return self._claimed.get(work_stream_id)


# Global coordinator instance
_coordinator: Optional[WorkStreamCoordinator] = None


def get_coordinator() -> WorkStreamCoordinator:
    """Get the global work stream coordinator."""
    global _coordinator
    if _coordinator is None:
        _coordinator = WorkStreamCoordinator()
    return _coordinator


class AgentRunner:
    """
    Manages spawning and monitoring of autonomous agents.

    Uses the existing autonomous_agent.sh script to spawn agents,
    monitoring their output and detecting completion.

    Integrates with NATS for coordination to prevent race conditions.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        max_concurrent: int = 3,
        timeout_seconds: int = 1800,  # 30 minutes default
    ):
        """
        Initialize the agent runner.

        Args:
            project_root: Root of the project. Defaults to auto-detect.
            max_concurrent: Maximum concurrent agents
            timeout_seconds: Timeout per agent in seconds
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds

        self.script_path = project_root / "scripts" / "autonomous_agent.sh"
        self.log_dir = project_root / "agent-logs"

        self.agents: dict[str, AgentProcess] = {}
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[AgentProcess], None]] = []
        self._naming = get_naming()
        self._coordinator = get_coordinator()

        # Track agent experience for reuse decisions
        self._agent_experience: dict[str, list[str]] = {}  # name -> completed phases

    def add_callback(self, callback: Callable[[AgentProcess], None]) -> None:
        """Add a callback to be called when agent state changes."""
        self._callbacks.append(callback)

    def get_available_agents(self) -> dict[str, dict]:
        """
        Get all known agents that could be reused.

        Returns:
            Dict mapping personal name to agent info
        """
        assigned = self._naming.list_assigned_names()
        available = {}

        for agent_id, info in assigned.items():
            personal_name = info["name"]
            memory = get_memory(personal_name)
            summary = memory.get_journal_summary()

            available[personal_name] = {
                "agent_id": agent_id,
                "role": info.get("role", "coder"),
                "claimed_at": info.get("claimed_at"),
                "memory_count": summary.get("total_memories", 0),
                "completed_phases": self._agent_experience.get(personal_name, []),
            }

        return available

    def find_agent_for_task(self, work_stream_id: str) -> Optional[str]:
        """
        Find an existing agent suitable for a work stream.

        Considers:
        - Agent's past experience with similar phases
        - Agent's memory/context
        - Agent availability

        Args:
            work_stream_id: The work stream ID (e.g., "2.1")

        Returns:
            Personal name of suitable agent, or None
        """
        available = self.get_available_agents()
        if not available:
            return None

        # Extract batch number from work stream ID
        batch = work_stream_id.split(".")[0]

        best_agent = None
        best_score = 0

        for name, info in available.items():
            score = 0

            # Prefer agents who completed phases in same batch
            for completed in info.get("completed_phases", []):
                if completed.startswith(f"{batch}."):
                    score += 10  # Same batch experience
                else:
                    score += 1  # Any experience

            # Prefer agents with more memory (more context)
            score += info.get("memory_count", 0) * 0.1

            if score > best_score:
                best_score = score
                best_agent = name

        return best_agent

    def spawn_agent_by_name(
        self,
        personal_name: str,
        work_stream_id: str,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> AgentProcess:
        """
        Spawn an agent using their personal name (reusing existing context).

        Args:
            personal_name: The agent's personal name (e.g., "Aria")
            work_stream_id: ID of the work stream (e.g., "2.1")
            on_output: Optional callback for each output line

        Returns:
            AgentProcess instance
        """
        # Get agent's memory context
        memory = get_memory(personal_name)
        context = memory.format_for_context()

        # Get agent's technical ID
        agent_id = self._naming.get_agent_id(personal_name)
        if not agent_id:
            # Create new ID for this agent
            agent_id = f"coder-{work_stream_id}-{int(time.time())}"

        agent = AgentProcess(
            agent_id=agent_id,
            work_stream_id=work_stream_id,
            personal_name=personal_name,
        )

        # Start the agent with context
        thread = threading.Thread(
            target=self._run_agent_with_context,
            args=(agent, context, on_output),
            daemon=True,
        )
        thread.start()

        with self._lock:
            self.agents[agent_id] = agent

        return agent

    def _run_agent_with_context(
        self,
        agent: AgentProcess,
        context: str,
        on_output: Optional[Callable[[str], None]],
    ) -> None:
        """Run agent process with memory context (called in background thread)."""
        # Claim work stream via coordinator
        if not self._coordinator.claim_work_stream(agent.work_stream_id, agent.agent_id):
            agent.state = AgentState.FAILED
            agent.error_lines.append(f"Failed to claim work stream {agent.work_stream_id}")
            self._notify_callbacks(agent)
            return

        agent.state = AgentState.RUNNING
        agent.started_at = datetime.now()
        self._notify_callbacks(agent)

        # Broadcast start via NATS
        self._coordinator.broadcast_status(
            agent.agent_id,
            agent.work_stream_id,
            "started",
            {"personal_name": agent.personal_name, "reused": True}
        )

        try:
            # Prepare environment with context
            env = os.environ.copy()
            env["AGENT_ID"] = agent.agent_id
            env["WORK_STREAM_ID"] = agent.work_stream_id
            env["AGENT_PERSONAL_NAME"] = agent.personal_name or ""
            env["AGENT_CONTEXT"] = context[:4000] if context else ""  # Limit size

            # Start the process
            process = subprocess.Popen(
                ["bash", str(self.script_path)],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1,
            )

            agent.process = process
            self._monitor_agent(agent, process, on_output)

        except Exception as e:
            agent.state = AgentState.FAILED
            agent.error_lines.append(str(e))

        finally:
            agent.completed_at = datetime.now()

            # Broadcast completion/failure via NATS
            status = "completed" if agent.state == AgentState.COMPLETED else "failed"
            self._coordinator.broadcast_status(
                agent.agent_id,
                agent.work_stream_id,
                status,
                {
                    "personal_name": agent.personal_name,
                    "exit_code": agent.exit_code,
                    "duration_seconds": agent.duration_seconds,
                }
            )

            # Release work stream claim
            self._coordinator.release_work_stream(agent.work_stream_id, agent.agent_id)

            # Record experience if completed
            if agent.state == AgentState.COMPLETED and agent.personal_name:
                if agent.personal_name not in self._agent_experience:
                    self._agent_experience[agent.personal_name] = []
                self._agent_experience[agent.personal_name].append(agent.work_stream_id)
            self._notify_callbacks(agent)

    def _monitor_agent(
        self,
        agent: AgentProcess,
        process: subprocess.Popen,
        on_output: Optional[Callable[[str], None]],
    ) -> None:
        """Monitor agent output and detect completion."""
        start_time = time.time()

        while True:
            # Check timeout
            if time.time() - start_time > self.timeout_seconds:
                agent.state = AgentState.TIMEOUT
                process.kill()
                break

            # Read output
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            if line:
                line = line.rstrip()
                agent.add_output_line(line)

                # Extract personal name from output
                if "Hello! I am " in line:
                    name_match = line.split("Hello! I am ")[-1].rstrip(".")
                    agent.personal_name = name_match

                if on_output:
                    on_output(line)

        # Get exit code
        agent.exit_code = process.returncode

        # Determine final state
        if agent.state != AgentState.TIMEOUT:
            if agent.exit_code == 0:
                agent.state = AgentState.COMPLETED
            else:
                agent.state = AgentState.FAILED

    def _notify_callbacks(self, agent: AgentProcess) -> None:
        """Notify all callbacks of agent state change."""
        for callback in self._callbacks:
            try:
                callback(agent)
            except Exception as e:
                print(f"Callback error: {e}")

    def spawn_agent(
        self,
        work_stream_id: str,
        on_output: Optional[Callable[[str], None]] = None,
        reuse_agent: bool = True,
    ) -> AgentProcess:
        """
        Spawn an autonomous agent for a work stream.

        If reuse_agent is True, will try to reuse an existing agent
        with relevant experience. Otherwise creates a new agent.

        Uses NATS coordination to prevent race conditions when multiple
        agents try to claim the same work stream.

        Args:
            work_stream_id: ID of the work stream (e.g., "1.2")
            on_output: Optional callback for each output line
            reuse_agent: Whether to try reusing an existing agent

        Returns:
            AgentProcess instance

        Raises:
            RuntimeError: If max concurrent agents reached or work stream already claimed
        """
        # Check if work stream is already claimed
        existing_claim = self._coordinator.is_claimed(work_stream_id)
        if existing_claim:
            raise RuntimeError(
                f"Work stream {work_stream_id} already claimed by {existing_claim}"
            )

        # Check concurrent limit
        with self._lock:
            running = sum(1 for a in self.agents.values() if a.is_running)
            if running >= self.max_concurrent:
                raise RuntimeError(
                    f"Max concurrent agents ({self.max_concurrent}) reached"
                )

        # Try to reuse an existing agent
        if reuse_agent:
            existing_agent = self.find_agent_for_task(work_stream_id)
            if existing_agent:
                return self.spawn_agent_by_name(
                    personal_name=existing_agent,
                    work_stream_id=work_stream_id,
                    on_output=on_output,
                )

        # Create new agent
        agent_id = f"coder-{work_stream_id}-{int(time.time())}"

        agent = AgentProcess(
            agent_id=agent_id,
            work_stream_id=work_stream_id,
        )

        # Start the agent in a background thread
        thread = threading.Thread(
            target=self._run_agent,
            args=(agent, on_output),
            daemon=True,
        )
        thread.start()

        with self._lock:
            self.agents[agent_id] = agent

        return agent

    def _run_agent(
        self,
        agent: AgentProcess,
        on_output: Optional[Callable[[str], None]],
    ) -> None:
        """Run agent process (called in background thread)."""
        # Claim work stream via coordinator
        if not self._coordinator.claim_work_stream(agent.work_stream_id, agent.agent_id):
            agent.state = AgentState.FAILED
            agent.error_lines.append(f"Failed to claim work stream {agent.work_stream_id}")
            self._notify_callbacks(agent)
            return

        agent.state = AgentState.RUNNING
        agent.started_at = datetime.now()
        self._notify_callbacks(agent)

        # Broadcast start via NATS
        self._coordinator.broadcast_status(
            agent.agent_id,
            agent.work_stream_id,
            "started",
            {"personal_name": agent.personal_name}
        )

        try:
            # Prepare environment
            env = os.environ.copy()
            env["AGENT_ID"] = agent.agent_id
            env["WORK_STREAM_ID"] = agent.work_stream_id

            # Start the process
            process = subprocess.Popen(
                ["bash", str(self.script_path)],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1,
            )

            agent.process = process
            self._monitor_agent(agent, process, on_output)

        except Exception as e:
            agent.state = AgentState.FAILED
            agent.error_lines.append(str(e))

        finally:
            agent.completed_at = datetime.now()

            # Broadcast completion/failure via NATS
            status = "completed" if agent.state == AgentState.COMPLETED else "failed"
            self._coordinator.broadcast_status(
                agent.agent_id,
                agent.work_stream_id,
                status,
                {
                    "personal_name": agent.personal_name,
                    "exit_code": agent.exit_code,
                    "duration_seconds": agent.duration_seconds,
                }
            )

            # Release work stream claim
            self._coordinator.release_work_stream(agent.work_stream_id, agent.agent_id)

            # Record experience if completed
            if agent.state == AgentState.COMPLETED and agent.personal_name:
                if agent.personal_name not in self._agent_experience:
                    self._agent_experience[agent.personal_name] = []
                self._agent_experience[agent.personal_name].append(agent.work_stream_id)
            self._notify_callbacks(agent)

    def kill_agent(self, agent_id: str) -> bool:
        """
        Kill a running agent.

        Args:
            agent_id: ID of the agent to kill

        Returns:
            True if agent was killed, False if not found or not running
        """
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent or not agent.is_running:
                return False

            if agent.process:
                try:
                    agent.process.kill()
                    agent.state = AgentState.KILLED
                    agent.completed_at = datetime.now()
                    self._notify_callbacks(agent)
                    return True
                except Exception:
                    return False

        return False

    def kill_all(self) -> int:
        """
        Kill all running agents.

        Returns:
            Number of agents killed
        """
        killed = 0
        with self._lock:
            for agent_id, agent in self.agents.items():
                if agent.is_running and agent.process:
                    try:
                        agent.process.kill()
                        agent.state = AgentState.KILLED
                        agent.completed_at = datetime.now()
                        killed += 1
                    except Exception:
                        pass

        return killed

    def get_agent(self, agent_id: str) -> Optional[AgentProcess]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_running_agents(self) -> list[AgentProcess]:
        """Get all currently running agents."""
        return [a for a in self.agents.values() if a.is_running]

    def get_finished_agents(self) -> list[AgentProcess]:
        """Get all finished agents."""
        return [a for a in self.agents.values() if a.is_finished]

    def wait_for_all(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for all agents to complete.

        Args:
            timeout: Maximum seconds to wait (None for no timeout)

        Returns:
            True if all completed, False if timeout
        """
        start = time.time()
        while True:
            running = self.get_running_agents()
            if not running:
                return True

            if timeout and (time.time() - start) > timeout:
                return False

            time.sleep(1)

    def get_status_report(self) -> dict:
        """
        Get a status report of all agents.

        Returns:
            Dictionary with agent statuses and statistics
        """
        agents_by_state = {state: [] for state in AgentState}

        for agent in self.agents.values():
            agents_by_state[agent.state].append({
                "agent_id": agent.agent_id,
                "work_stream": agent.work_stream_id,
                "personal_name": agent.personal_name,
                "duration_seconds": agent.duration_seconds,
                "exit_code": agent.exit_code,
            })

        return {
            "total": len(self.agents),
            "running": len(agents_by_state[AgentState.RUNNING]),
            "completed": len(agents_by_state[AgentState.COMPLETED]),
            "failed": len(agents_by_state[AgentState.FAILED]),
            "by_state": {
                state.value: agents
                for state, agents in agents_by_state.items()
                if agents
            },
        }

    # ==================== Agent Control Commands ====================

    def send_stop_command(
        self,
        agent_id: str,
        graceful: bool = True,
        reason: str = "Orchestrator requested stop"
    ) -> bool:
        """
        Send a stop command to an agent via NATS and OS signals.

        Stop Modes:
        - graceful=True: Sends SIGTERM to the shell script, which triggers the
          graceful_shutdown handler. The agent finishes its current operation,
          saves state, and exits cleanly (up to 30s grace period).
        - graceful=False: Sends SIGKILL for immediate termination. No cleanup
          possible, process dies instantly.

        Args:
            agent_id: ID of the agent to stop
            graceful: Whether to stop gracefully (SIGTERM) or immediately (SIGKILL)
            reason: Reason for stopping

        Returns:
            True if command was sent successfully
        """
        agent = self.agents.get(agent_id)
        if not agent or not agent.is_running:
            return False

        try:
            # Broadcast stop command via NATS (for logging/monitoring)
            self._coordinator.broadcast_status(
                agent_id="orchestrator",
                work_stream_id=agent.work_stream_id,
                status="stop_command",
                details={
                    "target_agent": agent_id,
                    "graceful": graceful,
                    "reason": reason,
                }
            )

            # Send appropriate signal to the process
            if agent.process:
                if graceful:
                    # SIGTERM - caught by shell script's trap handler
                    # Triggers graceful_shutdown() which waits up to 30s
                    agent.process.terminate()
                else:
                    # SIGKILL - immediate termination, cannot be caught
                    agent.process.kill()
                    agent.state = AgentState.KILLED
                    agent.completed_at = datetime.now()
                    self._notify_callbacks(agent)

            return True
        except Exception as e:
            print(f"Failed to send stop command: {e}")
            return False

    def send_update_goal_command(
        self,
        agent_id: str,
        new_goal: str,
        reason: str = "Goal update from orchestrator"
    ) -> bool:
        """
        Send a goal update command to an agent via NATS.

        The agent should adjust its current task to align with the new goal.

        Args:
            agent_id: ID of the agent to update
            new_goal: New goal/task description
            reason: Reason for the update

        Returns:
            True if command was sent successfully
        """
        agent = self.agents.get(agent_id)
        if not agent or not agent.is_running:
            return False

        try:
            self._coordinator.broadcast_status(
                agent_id="orchestrator",
                work_stream_id=agent.work_stream_id,
                status="update_goal",
                details={
                    "target_agent": agent_id,
                    "new_goal": new_goal,
                    "reason": reason,
                }
            )
            return True
        except Exception as e:
            print(f"Failed to send goal update: {e}")
            return False

    def send_ping(self, agent_id: str, timeout: float = 5.0) -> bool:
        """
        Send a ping to check if an agent is responsive.

        Args:
            agent_id: ID of the agent to ping
            timeout: Seconds to wait for response

        Returns:
            True if agent responded, False otherwise
        """
        agent = self.agents.get(agent_id)
        if not agent or not agent.is_running:
            return False

        # For now, just check if process is alive
        # Full NATS ping/pong would require async handling
        if agent.process and agent.process.poll() is None:
            return True
        return False

    def stop_all_agents(self, graceful: bool = True, reason: str = "Shutdown requested") -> int:
        """
        Send stop command to all running agents.

        Args:
            graceful: Whether to stop gracefully
            reason: Reason for stopping

        Returns:
            Number of agents sent stop command
        """
        count = 0
        for agent_id, agent in self.agents.items():
            if agent.is_running:
                if self.send_stop_command(agent_id, graceful, reason):
                    count += 1
        return count

    def broadcast_to_all_agents(
        self,
        message_type: str,
        content: dict
    ) -> None:
        """
        Broadcast a message to all running agents.

        Args:
            message_type: Type of message
            content: Message content
        """
        self._coordinator.broadcast_status(
            agent_id="orchestrator",
            work_stream_id="*",
            status=message_type,
            details=content
        )
