"""
Agent Runner - Spawns and monitors autonomous agents.

Handles:
- Spawning agent processes (via autonomous_agent.sh)
- Monitoring agent status
- Capturing agent output
- Detecting completion/failure
"""

import subprocess
import threading
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


class AgentRunner:
    """
    Manages spawning and monitoring of autonomous agents.

    Uses the existing autonomous_agent.sh script to spawn agents,
    monitoring their output and detecting completion.
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
        agent.state = AgentState.RUNNING
        agent.started_at = datetime.now()
        self._notify_callbacks(agent)

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

        Args:
            work_stream_id: ID of the work stream (e.g., "1.2")
            on_output: Optional callback for each output line
            reuse_agent: Whether to try reusing an existing agent

        Returns:
            AgentProcess instance
        """
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
        agent.state = AgentState.RUNNING
        agent.started_at = datetime.now()
        self._notify_callbacks(agent)

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
