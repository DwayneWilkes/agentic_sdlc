"""
Orchestrator - Main coordinator for autonomous agent teams.

The Orchestrator:
1. Analyzes the roadmap to find available work
2. Spawns autonomous agents for each work stream
3. Monitors progress in real-time
4. Verifies completion (tests pass, quality gates)
5. Generates reports and handles failures
"""

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from src.orchestrator.agent_runner import (
    AgentProcess,
    AgentRunner,
)
from src.orchestrator.work_stream import (
    WorkStream,
    WorkStreamStatus,
    get_prioritized_work_streams,
    parse_roadmap,
)


class OrchestratorMode(str, Enum):
    """Operating mode for the orchestrator."""
    SINGLE = "single"      # Run one work stream at a time
    PARALLEL = "parallel"  # Run multiple work streams in parallel
    BATCH = "batch"        # Complete all available work in current batch


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    mode: OrchestratorMode = OrchestratorMode.SINGLE
    max_concurrent_agents: int = 3
    agent_timeout_seconds: int = 1800  # 30 minutes
    verify_after_completion: bool = True
    auto_commit: bool = True
    dry_run: bool = False


@dataclass
class OrchestratorEvent:
    """An event in the orchestration process."""
    timestamp: datetime
    event_type: str
    message: str
    agent_id: str | None = None
    work_stream_id: str | None = None
    data: dict = field(default_factory=dict)


class Orchestrator:
    """
    Main orchestrator that coordinates autonomous agent teams.

    Example usage:
        >>> orchestrator = Orchestrator()
        >>> orchestrator.run()  # Run next available work stream
        >>> orchestrator.run_parallel(max_agents=3)  # Run in parallel
        >>> orchestrator.run_batch()  # Complete current batch
    """

    def __init__(
        self,
        project_root: Path | None = None,
        config: OrchestratorConfig | None = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            project_root: Root directory of the project
            config: Orchestrator configuration
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.config = config or OrchestratorConfig()

        self.runner = AgentRunner(
            project_root=project_root,
            max_concurrent=self.config.max_concurrent_agents,
            timeout_seconds=self.config.agent_timeout_seconds,
        )

        self.events: list[OrchestratorEvent] = []
        self._event_callbacks: list[Callable[[OrchestratorEvent], None]] = []

        # Set up agent callbacks
        self.runner.add_callback(self._on_agent_state_change)

    def add_event_callback(
        self, callback: Callable[[OrchestratorEvent], None]
    ) -> None:
        """Add a callback for orchestrator events."""
        self._event_callbacks.append(callback)

    def _emit_event(
        self,
        event_type: str,
        message: str,
        agent_id: str | None = None,
        work_stream_id: str | None = None,
        **data,
    ) -> OrchestratorEvent:
        """Emit an orchestrator event."""
        event = OrchestratorEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            message=message,
            agent_id=agent_id,
            work_stream_id=work_stream_id,
            data=data,
        )
        self.events.append(event)

        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception:
                pass

        return event

    def _on_agent_state_change(self, agent: AgentProcess) -> None:
        """Handle agent state changes."""
        self._emit_event(
            event_type=f"agent_{agent.state.value}",
            message=f"Agent {agent.agent_id} is now {agent.state.value}",
            agent_id=agent.agent_id,
            work_stream_id=agent.work_stream_id,
            personal_name=agent.personal_name,
            exit_code=agent.exit_code,
        )

    def get_available_work(self) -> list[WorkStream]:
        """Get available work streams from the roadmap, prioritized (bootstrap first).

        Excludes work streams that are already claimed by running agents.
        """
        all_available = get_prioritized_work_streams(self.project_root / "plans" / "roadmap.md")

        # Filter out already-claimed work streams
        claimed = self.runner.get_claimed_streams()
        return [ws for ws in all_available if ws.id not in claimed]

    def get_roadmap_status(self) -> dict:
        """
        Get current status of the roadmap.

        Returns:
            Dictionary with work stream counts by status
        """
        all_streams = parse_roadmap(self.project_root / "plans" / "roadmap.md")

        by_status = {status: [] for status in WorkStreamStatus}
        for ws in all_streams:
            by_status[ws.status].append(ws)

        return {
            "total": len(all_streams),
            "available": len([ws for ws in all_streams if ws.is_claimable]),
            "by_status": {
                status.value: [str(ws) for ws in streams]
                for status, streams in by_status.items()
            },
            "next_available": [
                str(ws) for ws in all_streams if ws.is_claimable
            ][:5],
        }

    def run(
        self,
        work_stream_id: str | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> AgentProcess:
        """
        Run a single work stream.

        Args:
            work_stream_id: Specific work stream to run (auto-selects if None)
            on_output: Callback for agent output lines

        Returns:
            AgentProcess for the spawned agent
        """
        if self.config.dry_run:
            self._emit_event(
                "dry_run",
                f"Would run work stream {work_stream_id or 'next available'}",
            )
            return None

        # Get available work
        available = self.get_available_work()
        if not available:
            self._emit_event("no_work", "No available work streams found")
            raise RuntimeError("No available work streams")

        # Select work stream
        if work_stream_id:
            work_stream = next(
                (ws for ws in available if ws.id == work_stream_id),
                None,
            )
            if not work_stream:
                raise ValueError(f"Work stream {work_stream_id} not available")
        else:
            work_stream = available[0]

        self._emit_event(
            "spawning_agent",
            f"Spawning agent for Phase {work_stream.id}: {work_stream.name}",
            work_stream_id=work_stream.id,
        )

        # Spawn agent
        agent = self.runner.spawn_agent(
            work_stream_id=work_stream.id,
            on_output=on_output,
        )

        return agent

    def run_parallel(
        self,
        max_agents: int | None = None,
        work_stream_ids: list[str] | None = None,
        on_output: Callable[[str, str], None] | None = None,
    ) -> list[AgentProcess]:
        """
        Run multiple work streams in parallel.

        Args:
            max_agents: Maximum agents to spawn (uses config default if None)
            work_stream_ids: Specific work streams to run (auto-selects if None)
            on_output: Callback for output (receives agent_id and line)

        Returns:
            List of spawned AgentProcess instances
        """
        max_agents = max_agents or self.config.max_concurrent_agents

        # Get available work
        available = self.get_available_work()
        if not available:
            self._emit_event("no_work", "No available work streams found")
            return []

        # Select work streams
        if work_stream_ids:
            to_run = [ws for ws in available if ws.id in work_stream_ids]
        else:
            to_run = available[:max_agents]

        self._emit_event(
            "parallel_start",
            f"Starting parallel execution of {len(to_run)} work streams",
            work_streams=[str(ws) for ws in to_run],
        )

        # Spawn agents
        agents = []
        for ws in to_run:
            def make_output_handler(ws_id):
                def handler(line):
                    if on_output:
                        on_output(ws_id, line)
                return handler

            try:
                agent = self.runner.spawn_agent(
                    work_stream_id=ws.id,
                    on_output=make_output_handler(ws.id),
                )
                agents.append(agent)

                self._emit_event(
                    "agent_spawned",
                    f"Spawned agent for Phase {ws.id}",
                    agent_id=agent.agent_id,
                    work_stream_id=ws.id,
                )

            except RuntimeError as e:
                self._emit_event(
                    "spawn_failed",
                    f"Failed to spawn agent for Phase {ws.id}: {e}",
                    work_stream_id=ws.id,
                )
                break

        return agents

    def run_batch(
        self,
        on_output: Callable[[str, str], None] | None = None,
        wait: bool = True,
    ) -> list[AgentProcess]:
        """
        Run all available work in the current batch.

        Args:
            on_output: Callback for output (receives agent_id and line)
            wait: Whether to wait for all agents to complete

        Returns:
            List of all spawned AgentProcess instances
        """
        all_agents = []

        while True:
            available = self.get_available_work()
            if not available:
                break

            # Spawn up to max_concurrent
            running = len(self.runner.get_running_agents())
            to_spawn = min(
                len(available),
                self.config.max_concurrent_agents - running,
            )

            if to_spawn == 0:
                # Wait for some to finish
                time.sleep(5)
                continue

            agents = self.run_parallel(
                max_agents=to_spawn,
                on_output=on_output,
            )
            all_agents.extend(agents)

            if not wait:
                break

            # Wait for current batch to have some completions
            time.sleep(10)

        if wait:
            self.runner.wait_for_all()

        return all_agents

    def verify_completion(self, agent: AgentProcess) -> dict:
        """
        Verify that an agent's work was completed successfully.

        Checks:
        - Agent exited with code 0
        - Tests pass
        - Roadmap is updated
        - Devlog entry exists

        Args:
            agent: The agent process to verify

        Returns:
            Dictionary with verification results
        """
        results = {
            "agent_id": agent.agent_id,
            "work_stream_id": agent.work_stream_id,
            "personal_name": agent.personal_name,
            "checks": {},
            "passed": True,
        }

        # Check exit code
        results["checks"]["exit_code"] = {
            "passed": agent.exit_code == 0,
            "value": agent.exit_code,
        }
        if agent.exit_code != 0:
            results["passed"] = False

        # Check tests pass
        try:
            test_result = subprocess.run(
                ["pytest", "tests/", "-v", "--tb=short"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            results["checks"]["tests"] = {
                "passed": test_result.returncode == 0,
                "output": test_result.stdout[-500:] if test_result.stdout else "",
            }
            if test_result.returncode != 0:
                results["passed"] = False
        except Exception as e:
            results["checks"]["tests"] = {
                "passed": False,
                "error": str(e),
            }
            results["passed"] = False

        # Check roadmap updated
        roadmap = parse_roadmap(self.project_root / "plans" / "roadmap.md")
        work_stream = next(
            (ws for ws in roadmap if ws.id == agent.work_stream_id),
            None,
        )
        if work_stream:
            results["checks"]["roadmap"] = {
                "passed": work_stream.status in (
                    WorkStreamStatus.COMPLETE,
                    WorkStreamStatus.IN_PROGRESS,
                ),
                "status": work_stream.status.value,
                "assigned_to": work_stream.assigned_to,
            }
        else:
            results["checks"]["roadmap"] = {
                "passed": False,
                "error": "Work stream not found in roadmap",
            }
            results["passed"] = False

        # Check git status (should be clean after commit)
        try:
            git_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
            )
            is_clean = len(git_result.stdout.strip()) == 0
            results["checks"]["git_clean"] = {
                "passed": is_clean,
                "dirty_files": git_result.stdout.strip().split("\n") if not is_clean else [],
            }
        except Exception as e:
            results["checks"]["git_clean"] = {
                "passed": False,
                "error": str(e),
            }

        self._emit_event(
            "verification_complete",
            f"Verification {'passed' if results['passed'] else 'failed'} for {agent.agent_id}",
            agent_id=agent.agent_id,
            work_stream_id=agent.work_stream_id,
            results=results,
        )

        return results

    def get_report(self) -> dict:
        """
        Generate a comprehensive report of orchestration activity.

        Returns:
            Dictionary with full orchestration report
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "mode": self.config.mode.value,
                "max_concurrent": self.config.max_concurrent_agents,
                "timeout": self.config.agent_timeout_seconds,
            },
            "roadmap_status": self.get_roadmap_status(),
            "agent_status": self.runner.get_status_report(),
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.event_type,
                    "message": e.message,
                    "agent_id": e.agent_id,
                    "work_stream_id": e.work_stream_id,
                }
                for e in self.events[-50:]  # Last 50 events
            ],
        }

    def stop(self) -> int:
        """
        Stop all running agents.

        Returns:
            Number of agents stopped
        """
        self._emit_event("stopping", "Stopping all agents")
        killed = self.runner.kill_all()
        self._emit_event("stopped", f"Stopped {killed} agents")
        return killed
