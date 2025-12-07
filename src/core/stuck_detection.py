"""Stuck detection and escape strategies for the orchestrator system.

This module provides comprehensive stuck detection capabilities including retry loops,
thrashing patterns, and no-progress detection. It also implements escape strategies
to help agents recover from stuck states.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class StuckPattern(str, Enum):
    """Types of stuck patterns that can be detected."""

    RETRY_LOOP = "retry_loop"
    THRASHING = "thrashing"
    NO_PROGRESS = "no_progress"


class EscapeStrategy(str, Enum):
    """Escape strategies for recovering from stuck states."""

    REFRAME = "reframe"  # Try completely different approach
    REDUCE = "reduce"  # Simplify to minimal failing case
    RESEARCH = "research"  # Search for similar issues/solutions
    ESCALATE = "escalate"  # Ask human with full context
    HANDOFF = "handoff"  # Pass to different agent with fresh eyes


@dataclass
class ProgressSnapshot:
    """
    Captures a snapshot of progress at a point in time.

    Tracks code changes, test status, goals met, and files modified
    to enable progress detection over time windows.
    """

    timestamp: datetime
    lines_changed: int
    tests_passing: int
    tests_failing: int
    goals_met: int
    files_modified: set[str] = field(default_factory=set)


@dataclass
class StuckSignal:
    """
    Represents a detected stuck pattern.

    Contains information about the pattern type, severity, affected
    agent/task, and when it was detected.
    """

    pattern: StuckPattern
    severity: str  # "low", "medium", "high"
    description: str
    agent_id: str
    task_id: str
    detected_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class ProgressMetrics:
    """
    Tracks progress metrics over time.

    Maintains a history of progress snapshots and provides methods
    to detect progress trends and patterns.
    """

    def __init__(self) -> None:
        """Initialize the progress metrics tracker."""
        self._history: list[ProgressSnapshot] = []

    def record_progress(self, snapshot: ProgressSnapshot) -> None:
        """
        Record a progress snapshot.

        Args:
            snapshot: The progress snapshot to record
        """
        self._history.append(snapshot)

    def get_history(self) -> list[ProgressSnapshot]:
        """
        Get the full progress history.

        Returns:
            List of all recorded snapshots
        """
        return self._history.copy()

    def has_progress(self, time_window_minutes: int = 10) -> bool:
        """
        Check if progress has been made in the time window.

        Args:
            time_window_minutes: Time window to check for progress

        Returns:
            True if progress detected, False otherwise
        """
        if len(self._history) < 2:
            return False

        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_snapshots = [s for s in self._history if s.timestamp >= cutoff_time]

        if len(recent_snapshots) < 2:
            return False

        # Check for any meaningful progress
        first = recent_snapshots[0]
        last = recent_snapshots[-1]

        return (
            last.lines_changed > first.lines_changed
            or last.tests_passing > first.tests_passing
            or last.tests_failing < first.tests_failing
            or last.goals_met > first.goals_met
            or len(last.files_modified) > len(first.files_modified)
        )

    def get_tests_trend(self, lookback_count: int = 3) -> str:
        """
        Get the trend of test results.

        Args:
            lookback_count: Number of recent snapshots to analyze

        Returns:
            "improving", "degrading", or "stable"
        """
        if len(self._history) < 2:
            return "stable"

        recent = self._history[-lookback_count:]
        if len(recent) < 2:
            return "stable"

        # Calculate net test score (passing - failing)
        scores = [s.tests_passing - s.tests_failing for s in recent]

        # Check trend
        improving = all(scores[i] <= scores[i + 1] for i in range(len(scores) - 1))
        degrading = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

        if improving and scores[-1] > scores[0]:
            return "improving"
        elif degrading and scores[-1] < scores[0]:
            return "degrading"
        else:
            return "stable"


class StuckDetector:
    """
    Detects stuck patterns during agent execution.

    Monitors error patterns, action sequences, and progress metrics
    to identify when agents are stuck in retry loops, thrashing, or
    making no progress.
    """

    def __init__(self) -> None:
        """Initialize the stuck detector."""
        self._error_history: dict[tuple[str, str], list[tuple[datetime, str]]] = (
            defaultdict(list)
        )
        self._action_history: dict[tuple[str, str], list[tuple[datetime, str]]] = (
            defaultdict(list)
        )

    def record_error(self, agent_id: str, task_id: str, error_message: str) -> None:
        """
        Record an error for stuck detection.

        Args:
            agent_id: ID of the agent
            task_id: ID of the task
            error_message: The error message
        """
        key = (agent_id, task_id)
        self._error_history[key].append((datetime.now(), error_message))

    def record_action(self, agent_id: str, task_id: str, action: str) -> None:
        """
        Record an action for thrashing detection.

        Args:
            agent_id: ID of the agent
            task_id: ID of the task
            action: Description of the action taken
        """
        key = (agent_id, task_id)
        self._action_history[key].append((datetime.now(), action))

    def get_error_history(
        self, agent_id: str | None = None, task_id: str | None = None
    ) -> list[tuple[datetime, str]]:
        """
        Get error history for an agent/task.

        Args:
            agent_id: Optional agent ID filter
            task_id: Optional task ID filter

        Returns:
            List of (timestamp, error_message) tuples
        """
        if agent_id and task_id:
            return self._error_history.get((agent_id, task_id), [])
        else:
            # Return all errors if no filter
            all_errors = []
            for errors in self._error_history.values():
                all_errors.extend(errors)
            return all_errors

    def get_action_history(
        self, agent_id: str | None = None, task_id: str | None = None
    ) -> list[tuple[datetime, str]]:
        """
        Get action history for an agent/task.

        Args:
            agent_id: Optional agent ID filter
            task_id: Optional task ID filter

        Returns:
            List of (timestamp, action) tuples
        """
        if agent_id and task_id:
            return self._action_history.get((agent_id, task_id), [])
        else:
            # Return all actions if no filter
            all_actions = []
            for actions in self._action_history.values():
                all_actions.extend(actions)
            return all_actions

    def detect_retry_loop(
        self, agent_id: str, task_id: str, threshold: int = 3
    ) -> StuckSignal | None:
        """
        Detect if an agent is stuck in a retry loop.

        Args:
            agent_id: ID of the agent
            task_id: ID of the task
            threshold: Number of same errors to trigger detection

        Returns:
            StuckSignal if retry loop detected, None otherwise
        """
        errors = self.get_error_history(agent_id, task_id)
        if len(errors) < threshold:
            return None

        # Look for repeated error messages
        recent_errors = errors[-threshold:]
        error_messages = [error[1] for error in recent_errors]

        # Check if all recent errors are the same
        if len(set(error_messages)) == 1:
            return StuckSignal(
                pattern=StuckPattern.RETRY_LOOP,
                severity="high",
                description=f"Same error repeated {threshold} times: {error_messages[0]}",
                agent_id=agent_id,
                task_id=task_id,
                detected_at=datetime.now(),
                metadata={"error_count": threshold, "error_message": error_messages[0]},
            )

        return None

    def detect_thrashing(
        self, agent_id: str, task_id: str, lookback: int = 4
    ) -> StuckSignal | None:
        """
        Detect thrashing (switching approaches repeatedly).

        Args:
            agent_id: ID of the agent
            task_id: ID of the task
            lookback: Number of recent actions to check

        Returns:
            StuckSignal if thrashing detected, None otherwise
        """
        actions = self.get_action_history(agent_id, task_id)
        if len(actions) < lookback:
            return None

        recent_actions = actions[-lookback:]
        action_names = [action[1] for action in recent_actions]

        # Check for A→B→A→B pattern (or similar oscillation)
        if lookback >= 4:
            if (
                action_names[0] == action_names[2]
                and action_names[1] == action_names[3]
                and action_names[0] != action_names[1]
            ):
                return StuckSignal(
                    pattern=StuckPattern.THRASHING,
                    severity="high",
                    description=(
                        f"Thrashing detected: alternating between "
                        f"{action_names[0]} and {action_names[1]}"
                    ),
                    agent_id=agent_id,
                    task_id=task_id,
                    detected_at=datetime.now(),
                    metadata={
                        "actions": action_names,
                        "pattern": "A-B-A-B",
                    },
                )

        return None

    def detect_no_progress(
        self,
        agent_id: str,
        task_id: str,
        progress_metrics: ProgressMetrics,
        time_threshold_minutes: int = 10,
    ) -> StuckSignal | None:
        """
        Detect if no progress is being made.

        Args:
            agent_id: ID of the agent
            task_id: ID of the task
            progress_metrics: Progress metrics to analyze
            time_threshold_minutes: Time window to check

        Returns:
            StuckSignal if no progress detected, None otherwise
        """
        # Only signal if we have enough history to make a determination
        history = progress_metrics.get_history()
        if len(history) < 2:
            return None

        if not progress_metrics.has_progress(time_threshold_minutes):
            return StuckSignal(
                pattern=StuckPattern.NO_PROGRESS,
                severity="medium",
                description=f"No progress detected in {time_threshold_minutes} minutes",
                agent_id=agent_id,
                task_id=task_id,
                detected_at=datetime.now(),
                metadata={
                    "time_threshold": time_threshold_minutes,
                    "tests_trend": progress_metrics.get_tests_trend(),
                },
            )

        return None

    def is_stuck(
        self,
        agent_id: str,
        task_id: str,
        progress_metrics: ProgressMetrics | None = None,
    ) -> tuple[bool, list[StuckSignal]]:
        """
        Check if an agent is stuck using all detection methods.

        Args:
            agent_id: ID of the agent
            task_id: ID of the task
            progress_metrics: Optional progress metrics

        Returns:
            Tuple of (is_stuck, list of stuck signals)
        """
        signals: list[StuckSignal] = []

        # Check for retry loop
        retry_signal = self.detect_retry_loop(agent_id, task_id)
        if retry_signal:
            signals.append(retry_signal)

        # Check for thrashing
        thrashing_signal = self.detect_thrashing(agent_id, task_id)
        if thrashing_signal:
            signals.append(thrashing_signal)

        # Check for no progress if metrics provided
        if progress_metrics:
            no_progress_signal = self.detect_no_progress(
                agent_id, task_id, progress_metrics
            )
            if no_progress_signal:
                signals.append(no_progress_signal)

        return len(signals) > 0, signals


class EscapeStrategyEngine:
    """
    Recommends and executes escape strategies for stuck agents.

    Provides 5 escape strategies ordered by escalation level:
    1. REFRAME - Try completely different approach
    2. REDUCE - Simplify to minimal failing case
    3. RESEARCH - Search for similar issues/solutions
    4. ESCALATE - Ask human with full context
    5. HANDOFF - Pass to different agent with fresh eyes
    """

    def __init__(self) -> None:
        """Initialize the escape strategy engine."""
        self._strategies = [
            EscapeStrategy.REFRAME,
            EscapeStrategy.REDUCE,
            EscapeStrategy.RESEARCH,
            EscapeStrategy.ESCALATE,
            EscapeStrategy.HANDOFF,
        ]

    def get_available_strategies(self) -> list[EscapeStrategy]:
        """
        Get all available escape strategies.

        Returns:
            List of available strategies
        """
        return self._strategies.copy()

    def recommend_strategy(self, signal: StuckSignal) -> EscapeStrategy:
        """
        Recommend an escape strategy based on stuck signal.

        Args:
            signal: The stuck signal detected

        Returns:
            Recommended escape strategy
        """
        # Strategy mapping based on pattern and severity
        if signal.pattern == StuckPattern.RETRY_LOOP:
            return EscapeStrategy.REFRAME
        elif signal.pattern == StuckPattern.THRASHING:
            return EscapeStrategy.REDUCE
        elif signal.pattern == StuckPattern.NO_PROGRESS:
            # For no progress, try research first
            return EscapeStrategy.RESEARCH
        else:
            # Default to reframe
            return EscapeStrategy.REFRAME

    def generate_action_plan(
        self, signal: StuckSignal, strategy: EscapeStrategy
    ) -> str:
        """
        Generate an action plan for the escape strategy.

        Args:
            signal: The stuck signal
            strategy: The escape strategy to use

        Returns:
            Action plan description
        """
        if strategy == EscapeStrategy.REFRAME:
            return (
                f"REFRAME Strategy for {signal.agent_id} on {signal.task_id}:\n"
                f"Try a completely different approach to solve the problem.\n"
                f"Current issue: {signal.description}\n"
                f"Action: Step back, reconsider assumptions, and attempt a "
                f"fundamentally different solution path."
            )
        elif strategy == EscapeStrategy.REDUCE:
            return (
                f"REDUCE Strategy for {signal.agent_id} on {signal.task_id}:\n"
                f"Simplify to minimal reproducing case.\n"
                f"Current issue: {signal.description}\n"
                f"Action: Strip away complexity to isolate the core problem. "
                f"Create the smallest possible test case that demonstrates the issue."
            )
        elif strategy == EscapeStrategy.RESEARCH:
            return (
                f"RESEARCH Strategy for {signal.agent_id} on {signal.task_id}:\n"
                f"Search for similar issues and solutions.\n"
                f"Current issue: {signal.description}\n"
                f"Action: Search codebase, documentation, and external resources "
                f"for similar problems and their solutions."
            )
        elif strategy == EscapeStrategy.ESCALATE:
            return (
                f"ESCALATE Strategy for {signal.agent_id} on {signal.task_id}:\n"
                f"Request human guidance with full context.\n"
                f"Current issue: {signal.description}\n"
                f"Action: Prepare a comprehensive context summary and request human assistance. "
                f"Include: what was tried, what failed, current state, and specific questions."
            )
        elif strategy == EscapeStrategy.HANDOFF:
            return (
                f"HANDOFF Strategy for {signal.agent_id} on {signal.task_id}:\n"
                f"Pass to different agent with fresh perspective.\n"
                f"Current issue: {signal.description}\n"
                f"Action: Create a handoff document with current context and pass task "
                f"to a different agent who may approach it differently."
            )
        else:
            return f"Unknown strategy: {strategy}"

    def execute_escape_strategy(self, signal: StuckSignal) -> dict[str, Any]:
        """
        Execute an escape strategy for a stuck signal.

        Args:
            signal: The stuck signal to address

        Returns:
            Dictionary with strategy execution result
        """
        strategy = self.recommend_strategy(signal)
        action_plan = self.generate_action_plan(signal, strategy)

        return {
            "strategy": strategy.value,
            "action_plan": action_plan,
            "signal": {
                "pattern": signal.pattern.value,
                "severity": signal.severity,
                "description": signal.description,
                "agent_id": signal.agent_id,
                "task_id": signal.task_id,
                "detected_at": signal.detected_at.isoformat(),
            },
        }
