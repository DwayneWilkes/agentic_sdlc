"""
Agent Status Monitor - Phase 6.1

Provides real-time monitoring of agent states and resource consumption.

Features:
1. Track agent states (idle, working, blocked, completed, failed)
2. Monitor resource consumption (time, tokens, API calls, memory)
3. Detect stuck agents (no progress for threshold time)
4. Status snapshots and history tracking
5. Thread-safe for concurrent updates

Usage:
    monitor = AgentStatusMonitor(stuck_threshold_seconds=120)

    # Update status
    monitor.update_status("agent-1", AgentStatus.WORKING, current_task="Build X")

    # Record resources
    monitor.record_resource_usage("agent-1", tokens=1500, api_calls=3)

    # Check status
    snapshot = monitor.get_status("agent-1")

    # Detect stuck agents
    stuck = monitor.detect_stuck_agents()
"""

import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from src.models.enums import AgentStatus


@dataclass
class AgentResourceMetrics:
    """Resource consumption metrics for an agent."""

    time_seconds: float = 0.0
    tokens: int = 0
    api_calls: int = 0
    memory_mb: float = 0.0


@dataclass
class AgentStatusSnapshot:
    """Snapshot of an agent's current status."""

    agent_id: str
    status: AgentStatus
    current_task: str | None
    last_update: datetime
    resources: AgentResourceMetrics
    last_progress: datetime | None = None


@dataclass
class StuckAgentDetection:
    """Information about a stuck agent."""

    agent_id: str
    status: AgentStatus
    current_task: str | None
    last_progress: datetime
    seconds_stuck: float


class AgentStatusMonitor:
    """
    Monitor agent states and resource consumption in real-time.

    Thread-safe implementation for concurrent agent updates.
    """

    def __init__(
        self, stuck_threshold_seconds: float = 120.0, max_history_per_agent: int = 100
    ):
        """
        Initialize the agent status monitor.

        Args:
            stuck_threshold_seconds: Time threshold for stuck detection
            max_history_per_agent: Maximum history entries to keep per agent
        """
        self.stuck_threshold_seconds = stuck_threshold_seconds
        self.max_history_per_agent = max_history_per_agent

        # Thread safety
        self._lock = threading.RLock()

        # Current status tracking
        self._statuses: dict[str, AgentStatusSnapshot] = {}

        # History tracking
        self._history: dict[str, list[AgentStatusSnapshot]] = defaultdict(list)

        # Track when agent started current state (for time calculation)
        self._state_start_times: dict[str, datetime] = {}

    def update_status(
        self,
        agent_id: str,
        status: AgentStatus,
        current_task: str | None = None,
    ) -> None:
        """
        Update an agent's status.

        Args:
            agent_id: Unique agent identifier
            status: New agent status
            current_task: Optional task description
        """
        with self._lock:
            now = datetime.now()

            # Get existing snapshot or create new one
            if agent_id in self._statuses:
                existing = self._statuses[agent_id]
                resources = existing.resources
                last_progress = existing.last_progress

                # Update time for previous state
                if agent_id in self._state_start_times:
                    elapsed = (now - self._state_start_times[agent_id]).total_seconds()
                    resources.time_seconds += elapsed
            else:
                resources = AgentResourceMetrics()
                last_progress = None

            # Create new snapshot
            snapshot = AgentStatusSnapshot(
                agent_id=agent_id,
                status=status,
                current_task=current_task,
                last_update=now,
                resources=resources,
                last_progress=last_progress or now,
            )

            # Update current status
            self._statuses[agent_id] = snapshot

            # Track state start time
            self._state_start_times[agent_id] = now

            # Add to history
            self._add_to_history(agent_id, snapshot)

    def record_resource_usage(
        self,
        agent_id: str,
        tokens: int = 0,
        api_calls: int = 0,
        memory_mb: float = 0.0,
    ) -> None:
        """
        Record resource consumption for an agent.

        Args:
            agent_id: Unique agent identifier
            tokens: Number of tokens consumed
            api_calls: Number of API calls made
            memory_mb: Memory used in megabytes
        """
        with self._lock:
            if agent_id not in self._statuses:
                # Create initial snapshot if doesn't exist
                self.update_status(agent_id, AgentStatus.IDLE)

            snapshot = self._statuses[agent_id]
            snapshot.resources.tokens += tokens
            snapshot.resources.api_calls += api_calls
            snapshot.resources.memory_mb += memory_mb

    def record_progress(self, agent_id: str, progress_note: str | None = None) -> None:
        """
        Record that an agent made progress.

        This resets the stuck detection timer.

        Args:
            agent_id: Unique agent identifier
            progress_note: Optional note about the progress
        """
        with self._lock:
            if agent_id not in self._statuses:
                return

            snapshot = self._statuses[agent_id]
            snapshot.last_progress = datetime.now()

    def get_status(self, agent_id: str) -> AgentStatusSnapshot | None:
        """
        Get current status snapshot for an agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Current status snapshot, or None if not tracked
        """
        with self._lock:
            if agent_id not in self._statuses:
                return None

            # Update time before returning
            snapshot = self._statuses[agent_id]
            if agent_id in self._state_start_times:
                now = datetime.now()
                elapsed = (now - self._state_start_times[agent_id]).total_seconds()
                # Create new snapshot with updated time
                updated_resources = AgentResourceMetrics(
                    time_seconds=snapshot.resources.time_seconds + elapsed,
                    tokens=snapshot.resources.tokens,
                    api_calls=snapshot.resources.api_calls,
                    memory_mb=snapshot.resources.memory_mb,
                )
                return AgentStatusSnapshot(
                    agent_id=snapshot.agent_id,
                    status=snapshot.status,
                    current_task=snapshot.current_task,
                    last_update=snapshot.last_update,
                    resources=updated_resources,
                    last_progress=snapshot.last_progress,
                )

            return snapshot

    def get_all_statuses(self) -> list[AgentStatusSnapshot]:
        """
        Get status snapshots for all tracked agents.

        Returns:
            List of status snapshots
        """
        with self._lock:
            result = []
            for agent_id in self._statuses.keys():
                snapshot = self.get_status(agent_id)
                if snapshot is not None:
                    result.append(snapshot)
            return result

    def get_agents_by_status(self, status: AgentStatus) -> list[AgentStatusSnapshot]:
        """
        Get agents filtered by status.

        Args:
            status: Status to filter by

        Returns:
            List of matching agent snapshots
        """
        with self._lock:
            return [s for s in self.get_all_statuses() if s.status == status]

    def detect_stuck_agents(self) -> list[StuckAgentDetection]:
        """
        Detect agents that haven't made progress within threshold.

        Only considers agents in WORKING or BLOCKED states.

        Returns:
            List of stuck agent detections
        """
        with self._lock:
            now = datetime.now()
            stuck: list[StuckAgentDetection] = []

            for agent_id, snapshot in self._statuses.items():
                # Only check working/blocked agents
                if snapshot.status not in (AgentStatus.WORKING, AgentStatus.BLOCKED):
                    continue

                # Check time since last progress
                if snapshot.last_progress is None:
                    continue

                seconds_stuck = (now - snapshot.last_progress).total_seconds()
                if seconds_stuck >= self.stuck_threshold_seconds:
                    stuck.append(
                        StuckAgentDetection(
                            agent_id=agent_id,
                            status=snapshot.status,
                            current_task=snapshot.current_task,
                            last_progress=snapshot.last_progress,
                            seconds_stuck=seconds_stuck,
                        )
                    )

            return stuck

    def get_status_history(self, agent_id: str) -> list[AgentStatusSnapshot]:
        """
        Get status history for an agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            List of historical status snapshots (chronological order)
        """
        with self._lock:
            return list(self._history.get(agent_id, []))

    def remove_agent(self, agent_id: str) -> None:
        """
        Remove an agent from tracking.

        Args:
            agent_id: Unique agent identifier
        """
        with self._lock:
            self._statuses.pop(agent_id, None)
            self._history.pop(agent_id, None)
            self._state_start_times.pop(agent_id, None)

    def _add_to_history(self, agent_id: str, snapshot: AgentStatusSnapshot) -> None:
        """
        Add a snapshot to agent's history.

        Maintains max history size by removing oldest entries.

        Args:
            agent_id: Unique agent identifier
            snapshot: Status snapshot to add
        """
        # Create a copy to avoid mutation issues
        history_snapshot = AgentStatusSnapshot(
            agent_id=snapshot.agent_id,
            status=snapshot.status,
            current_task=snapshot.current_task,
            last_update=snapshot.last_update,
            resources=AgentResourceMetrics(
                time_seconds=snapshot.resources.time_seconds,
                tokens=snapshot.resources.tokens,
                api_calls=snapshot.resources.api_calls,
                memory_mb=snapshot.resources.memory_mb,
            ),
            last_progress=snapshot.last_progress,
        )

        self._history[agent_id].append(history_snapshot)

        # Trim if exceeds max
        if len(self._history[agent_id]) > self.max_history_per_agent:
            self._history[agent_id] = self._history[agent_id][-self.max_history_per_agent :]


# =============================================================================
# Singleton and Convenience Functions
# =============================================================================

_monitor_instance: AgentStatusMonitor | None = None


def get_agent_status_monitor(
    stuck_threshold_seconds: float = 120.0,
) -> AgentStatusMonitor:
    """Get the singleton agent status monitor."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AgentStatusMonitor(
            stuck_threshold_seconds=stuck_threshold_seconds
        )
    return _monitor_instance


def update_agent_status(
    agent_id: str, status: AgentStatus, current_task: str | None = None
) -> None:
    """Convenience function to update agent status."""
    get_agent_status_monitor().update_status(agent_id, status, current_task)


def record_agent_resources(
    agent_id: str,
    tokens: int = 0,
    api_calls: int = 0,
    memory_mb: float = 0.0,
) -> None:
    """Convenience function to record resource usage."""
    get_agent_status_monitor().record_resource_usage(agent_id, tokens, api_calls, memory_mb)


def record_agent_progress(agent_id: str, progress_note: str | None = None) -> None:
    """Convenience function to record progress."""
    get_agent_status_monitor().record_progress(agent_id, progress_note)


def get_stuck_agents() -> list[StuckAgentDetection]:
    """Convenience function to detect stuck agents."""
    return get_agent_status_monitor().detect_stuck_agents()
