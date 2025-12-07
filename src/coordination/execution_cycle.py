"""
Execution cycle management for turn-based agent execution.

Implements bounded execution cycles with:
- Configurable time budgets
- Token and API call tracking
- Checkpoint mechanism for state persistence
- Graceful termination and preemption
- Cycle history tracking
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum


class CycleStatus(str, Enum):
    """Status of an execution cycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PREEMPTED = "preempted"
    TIMEOUT = "timeout"


class CycleTerminationReason(str, Enum):
    """Reason why a cycle was terminated."""

    TASK_COMPLETED = "task_completed"
    TIMEOUT = "timeout"
    PREEMPTED = "preempted"
    BUDGET_EXCEEDED = "budget_exceeded"
    ERROR = "error"


class ExecutionDecision(str, Enum):
    """Decision about whether to continue execution."""

    CONTINUE = "continue"
    CONTINUE_WITH_WARNING = "continue_with_warning"
    TERMINATE_TIMEOUT = "terminate_timeout"
    TERMINATE_BUDGET = "terminate_budget"


@dataclass
class CycleBudgetTracker:
    """
    Tracks resource consumption during an execution cycle.

    Monitors tokens, time, and API calls against configured limits.
    """

    max_tokens: int | None = None
    max_time_seconds: int | None = None
    max_api_calls: int | None = None
    tokens_used: int = 0
    time_used_seconds: float = 0.0
    api_calls_made: int = 0

    def add_tokens(self, count: int) -> None:
        """Add tokens to usage count."""
        self.tokens_used += count

    def add_time(self, seconds: float) -> None:
        """Add time to usage count."""
        self.time_used_seconds += seconds

    def add_api_call(self) -> None:
        """Increment API call counter."""
        self.api_calls_made += 1

    def get_token_percentage(self) -> float:
        """Get percentage of token budget used."""
        if self.max_tokens is None or self.max_tokens == 0:
            return 0.0
        return (self.tokens_used / self.max_tokens) * 100.0

    def get_time_percentage(self) -> float:
        """Get percentage of time budget used."""
        if self.max_time_seconds is None or self.max_time_seconds == 0:
            return 0.0
        return (self.time_used_seconds / self.max_time_seconds) * 100.0

    def get_api_call_percentage(self) -> float:
        """Get percentage of API call budget used."""
        if self.max_api_calls is None or self.max_api_calls == 0:
            return 0.0
        return (self.api_calls_made / self.max_api_calls) * 100.0

    def is_budget_exceeded(self) -> bool:
        """Check if any budget limit has been exceeded."""
        if self.max_tokens and self.tokens_used > self.max_tokens:
            return True
        if self.max_time_seconds and self.time_used_seconds > self.max_time_seconds:
            return True
        if self.max_api_calls and self.api_calls_made > self.max_api_calls:
            return True
        return False

    def is_approaching_limit(self, threshold: float = 80.0) -> bool:
        """Check if any budget is approaching its limit (>threshold%)."""
        percentages = [
            self.get_token_percentage(),
            self.get_time_percentage(),
            self.get_api_call_percentage(),
        ]
        return any(p > threshold for p in percentages)

    def get_budget_summary(self) -> dict:
        """Get a summary of budget usage."""
        return {
            "tokens": {
                "used": self.tokens_used,
                "max": self.max_tokens,
                "percentage": self.get_token_percentage(),
            },
            "time": {
                "used": self.time_used_seconds,
                "max": self.max_time_seconds,
                "percentage": self.get_time_percentage(),
            },
            "api_calls": {
                "used": self.api_calls_made,
                "max": self.max_api_calls,
                "percentage": self.get_api_call_percentage(),
            },
        }


@dataclass
class ExecutionCycle:
    """
    Represents a single execution cycle for an agent.

    A cycle is a bounded time period during which an agent works on a task.
    """

    cycle_id: str
    agent_id: str
    task_id: str
    start_time: datetime
    duration_seconds: int
    status: CycleStatus = CycleStatus.PENDING
    budget_tracker: CycleBudgetTracker = field(default_factory=CycleBudgetTracker)
    end_time: datetime | None = None
    termination_reason: CycleTerminationReason | None = None
    metadata: dict = field(default_factory=dict)

    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since cycle start."""
        now = datetime.now(UTC)
        delta = now - self.start_time
        return delta.total_seconds()

    def remaining_seconds(self) -> float:
        """Calculate remaining time in cycle."""
        elapsed = self.elapsed_seconds()
        return max(0.0, self.duration_seconds - elapsed)

    def is_expired(self) -> bool:
        """Check if cycle has exceeded its duration."""
        return self.elapsed_seconds() > self.duration_seconds

    def should_checkpoint(self) -> bool:
        """
        Check if it's time to checkpoint.

        Checkpoints at 50% mark (mid-cycle) and at end.
        """
        elapsed = self.elapsed_seconds()
        progress = elapsed / self.duration_seconds

        # Checkpoint at 50% mark
        if 0.48 <= progress <= 0.52:
            return True

        # Checkpoint near end (95%+)
        if progress >= 0.95:
            return True

        return False

    def to_json(self) -> str:
        """Serialize cycle to JSON."""
        data = asdict(self)
        # Convert datetime to ISO format
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ExecutionCycle":
        """Deserialize cycle from JSON."""
        data = json.loads(json_str)
        # Convert ISO format to datetime
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            data["end_time"] = datetime.fromisoformat(data["end_time"])

        # Reconstruct budget tracker
        budget_data = data.get("budget_tracker", {})
        data["budget_tracker"] = CycleBudgetTracker(**budget_data)

        # Convert status enum
        if isinstance(data.get("status"), str):
            data["status"] = CycleStatus(data["status"])

        # Convert termination reason enum
        if isinstance(data.get("termination_reason"), str):
            data["termination_reason"] = CycleTerminationReason(data["termination_reason"])

        return cls(**data)


@dataclass
class CycleCheckpoint:
    """
    Represents a checkpoint snapshot of cycle state.

    Checkpoints enable resuming work after interruption.
    """

    cycle_id: str
    timestamp: datetime
    state_snapshot: dict
    progress_metrics: dict
    files_changed: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize checkpoint to JSON."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "CycleCheckpoint":
        """Deserialize checkpoint from JSON."""
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class ExecutionCycleManager:
    """
    Manages execution cycles for agents.

    Handles cycle creation, checkpointing, termination, and history.
    """

    def __init__(
        self,
        default_duration_seconds: int = 1800,  # 30 minutes
        checkpoint_interval_seconds: int = 900,  # 15 minutes
    ):
        """
        Initialize cycle manager.

        Args:
            default_duration_seconds: Default cycle duration (30 min)
            checkpoint_interval_seconds: How often to checkpoint (15 min)
        """
        self.default_duration_seconds = default_duration_seconds
        self.checkpoint_interval_seconds = checkpoint_interval_seconds
        self._active_cycles: dict[str, ExecutionCycle] = {}
        self._cycle_history: dict[str, list[ExecutionCycle]] = {}  # agent_id -> cycles
        self._checkpoints: dict[str, list[CycleCheckpoint]] = {}  # cycle_id -> checkpoints
        self._cycle_counter = 0

    def start_cycle(
        self,
        agent_id: str,
        task_id: str,
        duration_seconds: int | None = None,
        max_tokens: int | None = None,
        max_api_calls: int | None = None,
        resume_from_checkpoint: CycleCheckpoint | None = None,
    ) -> ExecutionCycle:
        """
        Start a new execution cycle.

        Args:
            agent_id: ID of agent running this cycle
            task_id: ID of task being worked on
            duration_seconds: Cycle duration (uses default if None)
            max_tokens: Token budget limit
            max_api_calls: API call budget limit
            resume_from_checkpoint: Optional checkpoint to resume from

        Returns:
            Started ExecutionCycle
        """
        self._cycle_counter += 1
        cycle_id = f"cycle-{agent_id}-{self._cycle_counter}"

        duration = duration_seconds or self.default_duration_seconds

        budget_tracker = CycleBudgetTracker(
            max_tokens=max_tokens,
            max_time_seconds=duration,
            max_api_calls=max_api_calls,
        )

        cycle = ExecutionCycle(
            cycle_id=cycle_id,
            agent_id=agent_id,
            task_id=task_id,
            start_time=datetime.now(UTC),
            duration_seconds=duration,
            status=CycleStatus.RUNNING,
            budget_tracker=budget_tracker,
        )

        # If resuming, add metadata
        if resume_from_checkpoint:
            cycle.metadata["resumed_from"] = resume_from_checkpoint.cycle_id
            cycle.metadata["resume_state"] = resume_from_checkpoint.state_snapshot

        self._active_cycles[cycle_id] = cycle

        # Initialize history if needed
        if agent_id not in self._cycle_history:
            self._cycle_history[agent_id] = []

        return cycle

    def save_checkpoint(
        self,
        cycle_id: str,
        state_snapshot: dict,
        progress_metrics: dict,
        files_changed: list[str] | None = None,
    ) -> CycleCheckpoint:
        """
        Save a checkpoint for a cycle.

        Args:
            cycle_id: ID of cycle to checkpoint
            state_snapshot: Current execution state
            progress_metrics: Progress measurements
            files_changed: Files modified so far

        Returns:
            Created CycleCheckpoint
        """
        cycle = self._active_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"No active cycle with ID {cycle_id}")

        checkpoint = CycleCheckpoint(
            cycle_id=cycle_id,
            timestamp=datetime.now(UTC),
            state_snapshot=state_snapshot,
            progress_metrics=progress_metrics,
            files_changed=files_changed or [],
        )

        if cycle_id not in self._checkpoints:
            self._checkpoints[cycle_id] = []

        self._checkpoints[cycle_id].append(checkpoint)

        return checkpoint

    def load_latest_checkpoint(self, cycle_id: str) -> CycleCheckpoint | None:
        """
        Load the most recent checkpoint for a cycle.

        Args:
            cycle_id: ID of cycle

        Returns:
            Latest CycleCheckpoint or None
        """
        checkpoints = self._checkpoints.get(cycle_id, [])
        if not checkpoints:
            return None

        return checkpoints[-1]

    def get_cycle(self, cycle_id: str) -> ExecutionCycle | None:
        """Get a cycle by ID (active or from history)."""
        # Check active cycles first
        if cycle_id in self._active_cycles:
            return self._active_cycles[cycle_id]

        # Search history
        for cycles in self._cycle_history.values():
            for cycle in cycles:
                if cycle.cycle_id == cycle_id:
                    return cycle

        return None

    def complete_cycle(
        self,
        cycle_id: str,
        termination_reason: CycleTerminationReason,
    ) -> None:
        """
        Mark a cycle as completed.

        Args:
            cycle_id: ID of cycle to complete
            termination_reason: Why the cycle ended
        """
        cycle = self._active_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"No active cycle with ID {cycle_id}")

        cycle.status = CycleStatus.COMPLETED
        cycle.end_time = datetime.now(UTC)
        cycle.termination_reason = termination_reason

        # Move to history
        self._cycle_history.setdefault(cycle.agent_id, []).append(cycle)
        del self._active_cycles[cycle_id]

    def graceful_terminate(
        self,
        cycle_id: str,
        state_snapshot: dict,
        progress_metrics: dict,
        files_changed: list[str] | None = None,
    ) -> CycleCheckpoint:
        """
        Gracefully terminate a cycle, saving state first.

        Args:
            cycle_id: ID of cycle to terminate
            state_snapshot: Final execution state
            progress_metrics: Final progress measurements
            files_changed: Files modified

        Returns:
            Final CycleCheckpoint
        """
        # Save final checkpoint
        checkpoint = self.save_checkpoint(
            cycle_id=cycle_id,
            state_snapshot=state_snapshot,
            progress_metrics=progress_metrics,
            files_changed=files_changed,
        )

        # Complete the cycle
        self.complete_cycle(
            cycle_id=cycle_id,
            termination_reason=CycleTerminationReason.TASK_COMPLETED,
        )

        return checkpoint

    def preempt_cycle(
        self,
        cycle_id: str,
        reason: str,
        state_snapshot: dict,
        progress_metrics: dict | None = None,
    ) -> CycleCheckpoint:
        """
        Preempt a cycle for higher-priority work.

        Args:
            cycle_id: ID of cycle to preempt
            reason: Reason for preemption
            state_snapshot: Current execution state
            progress_metrics: Current progress measurements

        Returns:
            CycleCheckpoint with saved state
        """
        cycle = self._active_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"No active cycle with ID {cycle_id}")

        # Save checkpoint before preempting
        checkpoint = self.save_checkpoint(
            cycle_id=cycle_id,
            state_snapshot=state_snapshot,
            progress_metrics=progress_metrics or {},
        )

        # Mark as preempted
        cycle.status = CycleStatus.PREEMPTED
        cycle.end_time = datetime.now(UTC)
        cycle.termination_reason = CycleTerminationReason.PREEMPTED
        cycle.metadata["preemption_reason"] = reason

        # Move to history
        self._cycle_history.setdefault(cycle.agent_id, []).append(cycle)
        del self._active_cycles[cycle_id]

        return checkpoint

    def check_cycle_status(self, cycle_id: str) -> ExecutionDecision:
        """
        Check cycle status and determine if it should continue.

        Args:
            cycle_id: ID of cycle to check

        Returns:
            ExecutionDecision on whether to continue
        """
        cycle = self._active_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"No active cycle with ID {cycle_id}")

        # Check if expired
        if cycle.is_expired():
            # Auto-terminate on timeout
            cycle.status = CycleStatus.TIMEOUT
            cycle.end_time = datetime.now(UTC)
            cycle.termination_reason = CycleTerminationReason.TIMEOUT
            self._cycle_history.setdefault(cycle.agent_id, []).append(cycle)
            del self._active_cycles[cycle_id]
            return ExecutionDecision.TERMINATE_TIMEOUT

        # Check if budget exceeded
        if cycle.budget_tracker.is_budget_exceeded():
            return ExecutionDecision.TERMINATE_BUDGET

        # Check if approaching limits
        if cycle.budget_tracker.is_approaching_limit():
            return ExecutionDecision.CONTINUE_WITH_WARNING

        return ExecutionDecision.CONTINUE

    def track_token_usage(self, cycle_id: str, tokens: int) -> None:
        """Track token usage for a cycle."""
        cycle = self._active_cycles.get(cycle_id)
        if cycle:
            cycle.budget_tracker.add_tokens(tokens)

    def track_api_call(self, cycle_id: str) -> None:
        """Track an API call for a cycle."""
        cycle = self._active_cycles.get(cycle_id)
        if cycle:
            cycle.budget_tracker.add_api_call()

    def get_agent_cycle_history(self, agent_id: str) -> list[ExecutionCycle]:
        """
        Get cycle history for an agent.

        Args:
            agent_id: ID of agent

        Returns:
            List of all cycles (completed + active, oldest to newest)
        """
        # Get completed cycles from history
        history = self._cycle_history.get(agent_id, []).copy()

        # Add any active cycles for this agent
        for cycle in self._active_cycles.values():
            if cycle.agent_id == agent_id:
                history.append(cycle)

        return history

    def get_active_cycles(self) -> list[ExecutionCycle]:
        """Get all currently active cycles."""
        return list(self._active_cycles.values())
