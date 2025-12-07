"""
Attention Schema - Phase 10.3 (AST-1)

Provides attention tracking, drift detection, budget management, and priority signals
for autonomous agents. Part of the Attention Schema Theory implementation.

Features:
1. Model current attention state (primary, secondary, background focus)
2. Track attention history and focus duration
3. Detect attention drift with severity classification
4. Implement deliberate attention redirection
5. Add attention budget per subtask
6. Create attention priority signals
7. Implement attention persistence (save/restore state)

Usage:
    schema = AttentionSchema()
    schema.set_focus("Fix authentication bug", budget_minutes=30.0)
    schema.add_secondary_focus("Understand OAuth flow")

    # Detect drift
    drift = schema.track_drift("Refactor entire auth module")
    if drift.severity == DriftSeverity.HIGH:
        schema.redirect_attention("Fix authentication bug", reason="Scope creep")

    # Check budget and signals
    budget = schema.check_budget()
    signals = schema.get_priority_signals()
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class DriftSeverity(str, Enum):
    """Severity levels for attention drift."""

    LOW = "low"  # Minor, related tangent
    MEDIUM = "medium"  # Moderate scope change
    HIGH = "high"  # Major scope creep


class BudgetStatus(str, Enum):
    """Status of attention budget consumption."""

    UNDER = "under"  # Using less than 50% of budget
    ON_TRACK = "on_track"  # Using 50-100% of budget
    OVER = "over"  # Exceeded budget


class PriorityLevel(str, Enum):
    """Priority levels for signals and threads."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def value_numeric(self) -> int:
        """Get numeric value for ordering (higher = more important)."""
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}[self.value]


class SignalType(str, Enum):
    """Types of attention priority signals."""

    TIME_LIMIT = "time_limit"
    DRIFT_DETECTED = "drift_detected"
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_WARNING = "budget_warning"


@dataclass(frozen=True)
class AttentionDriftEvent:
    """Records a single attention drift event."""

    from_focus: str
    to_focus: str
    drift_time: datetime
    severity: DriftSeverity


@dataclass
class AttentionBudget:
    """Tracks time budget for current focus."""

    subtask_id: str
    allocated_minutes: float
    consumed_minutes: float
    budget_status: BudgetStatus


@dataclass(frozen=True)
class AttentionPrioritySignal:
    """Priority signal for attention management."""

    signal_type: SignalType
    priority: PriorityLevel
    message: str
    action_recommended: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AttentionState:
    """Snapshot of current attention state."""

    primary_focus: str | None
    secondary_focus: list[str]
    background_threads: list[str]
    focus_duration: timedelta
    started_at: datetime | None


@dataclass
class PendingThread:
    """A pending thread with priority."""

    description: str
    priority: PriorityLevel
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AttentionHistoryEntry:
    """Entry in attention history."""

    focus: str
    started_at: datetime
    ended_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


class AttentionSchema:
    """
    Main attention tracking and management system.

    Implements Attention Schema Theory (AST-1) for agent self-awareness
    of focus, drift, and attention allocation.

    Thread-safe for concurrent updates.
    """

    def __init__(self) -> None:
        """Initialize the attention schema."""
        self._lock = threading.RLock()

        # Current state
        self._primary_focus: str | None = None
        self._focus_started_at: datetime | None = None
        self._budget_minutes: float = 0.0
        self._secondary_focus: list[str] = []
        self._background_threads: list[str] = []

        # Pending threads with priority
        self._pending_threads: list[PendingThread] = []

        # History
        self._drift_history: list[AttentionDriftEvent] = []
        self._attention_history: list[AttentionHistoryEntry] = []

    def set_focus(self, task: str, budget_minutes: float) -> None:
        """
        Set primary focus with time budget.

        Args:
            task: Task description
            budget_minutes: Allocated time budget in minutes

        Raises:
            ValueError: If task is empty or budget is negative
        """
        if not task or not task.strip():
            raise ValueError("Task name cannot be empty")
        if budget_minutes < 0:
            raise ValueError("Budget cannot be negative")

        with self._lock:
            # Record previous focus in history if exists
            if self._primary_focus and self._focus_started_at:
                self._attention_history.append(
                    AttentionHistoryEntry(
                        focus=self._primary_focus,
                        started_at=self._focus_started_at,
                        ended_at=datetime.now(),
                    )
                )

            self._primary_focus = task
            self._focus_started_at = datetime.now()
            self._budget_minutes = budget_minutes

    def add_secondary_focus(self, task: str) -> None:
        """Add a secondary focus (related subtask)."""
        with self._lock:
            if task not in self._secondary_focus:
                self._secondary_focus.append(task)

    def add_background_thread(self, thread: str) -> None:
        """Add a background thread (pending item)."""
        with self._lock:
            if thread not in self._background_threads:
                self._background_threads.append(thread)

    def track_drift(self, new_focus: str) -> AttentionDriftEvent:
        """
        Track attention drift from current focus.

        Args:
            new_focus: What attention has drifted to

        Returns:
            AttentionDriftEvent with severity classification
        """
        with self._lock:
            if not self._primary_focus:
                # No primary focus set, treat as low severity
                severity = DriftSeverity.LOW
                from_focus = ""
            else:
                from_focus = self._primary_focus
                severity = self._classify_drift_severity(from_focus, new_focus)

            drift_event = AttentionDriftEvent(
                from_focus=from_focus,
                to_focus=new_focus,
                drift_time=datetime.now(),
                severity=severity,
            )

            self._drift_history.append(drift_event)

            # Update current focus to the drifted task
            self._primary_focus = new_focus
            self._focus_started_at = datetime.now()

            return drift_event

    def _classify_drift_severity(self, from_focus: str, to_focus: str) -> DriftSeverity:
        """
        Classify drift severity based on task similarity.

        Uses simple heuristics:
        - HIGH: Very different tasks (few common words)
        - MEDIUM: Moderately related tasks
        - LOW: Similar/related tasks (many common words)
        """
        from_words = set(from_focus.lower().split())
        to_words = set(to_focus.lower().split())

        # Calculate similarity (Jaccard index)
        if not from_words or not to_words:
            return DriftSeverity.LOW

        intersection = from_words & to_words
        union = from_words | to_words
        similarity = len(intersection) / len(union)

        if similarity > 0.3:
            return DriftSeverity.LOW
        elif similarity > 0.1:
            return DriftSeverity.MEDIUM
        else:
            return DriftSeverity.HIGH

    def check_budget(self) -> AttentionBudget:
        """
        Check current attention budget status.

        Returns:
            AttentionBudget with current consumption
        """
        with self._lock:
            if not self._primary_focus or not self._focus_started_at:
                return AttentionBudget(
                    subtask_id="",
                    allocated_minutes=0.0,
                    consumed_minutes=0.0,
                    budget_status=BudgetStatus.UNDER,
                )

            consumed_seconds = (datetime.now() - self._focus_started_at).total_seconds()
            consumed_minutes = consumed_seconds / 60.0

            # Determine status
            if self._budget_minutes == 0:
                status = BudgetStatus.OVER
            else:
                usage_ratio = consumed_minutes / self._budget_minutes
                if usage_ratio <= 0.5:
                    status = BudgetStatus.UNDER
                elif usage_ratio <= 1.0:
                    status = BudgetStatus.ON_TRACK
                else:
                    status = BudgetStatus.OVER

            return AttentionBudget(
                subtask_id=self._primary_focus,
                allocated_minutes=self._budget_minutes,
                consumed_minutes=consumed_minutes,
                budget_status=status,
            )

    def get_priority_signals(self) -> list[AttentionPrioritySignal]:
        """
        Get current attention priority signals.

        Returns signals for:
        - Budget exceeded/warning
        - Drift detected
        - Time limits approaching

        Sorted by priority (CRITICAL first).
        """
        signals = []

        with self._lock:
            budget = self.check_budget()

            # Budget signals
            if budget.budget_status == BudgetStatus.OVER:
                consumed = budget.consumed_minutes
                allocated = budget.allocated_minutes
                signals.append(
                    AttentionPrioritySignal(
                        signal_type=SignalType.BUDGET_EXCEEDED,
                        priority=PriorityLevel.HIGH,
                        message=f"Budget exceeded: {consumed:.1f}/{allocated:.1f} min",
                        action_recommended="Consider wrapping up or extending budget",
                    )
                )
            elif (
                budget.budget_status == BudgetStatus.ON_TRACK
                and budget.consumed_minutes / budget.allocated_minutes > 0.8
            ):
                consumed = budget.consumed_minutes
                allocated = budget.allocated_minutes
                signals.append(
                    AttentionPrioritySignal(
                        signal_type=SignalType.BUDGET_WARNING,
                        priority=PriorityLevel.MEDIUM,
                        message=f"Budget warning: {consumed:.1f}/{allocated:.1f} min",
                        action_recommended="Start wrapping up current focus",
                    )
                )

            # Drift signals (check recent drifts)
            recent_drifts = self._drift_history[-5:] if self._drift_history else []
            for drift in recent_drifts:
                if drift.severity == DriftSeverity.HIGH:
                    msg = f"High-severity drift: {drift.from_focus} -> {drift.to_focus}"
                    signals.append(
                        AttentionPrioritySignal(
                            signal_type=SignalType.DRIFT_DETECTED,
                            priority=PriorityLevel.HIGH,
                            message=msg,
                            action_recommended="Return to original task or explicitly redirect",
                        )
                    )
                elif drift.severity == DriftSeverity.MEDIUM:
                    msg = (
                        f"Medium-severity drift: {drift.from_focus} -> {drift.to_focus}"
                    )
                    signals.append(
                        AttentionPrioritySignal(
                            signal_type=SignalType.DRIFT_DETECTED,
                            priority=PriorityLevel.MEDIUM,
                            message=msg,
                            action_recommended="Consider if this drift is intentional",
                        )
                    )

        # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW)
        signals.sort(key=lambda s: s.priority.value_numeric, reverse=True)
        return signals

    def redirect_attention(self, to_task: str, reason: str) -> None:
        """
        Deliberately redirect attention with documented reason.

        Args:
            to_task: New task to focus on
            reason: Why the redirect is happening
        """
        with self._lock:
            # Record current focus in history with redirect reason
            if self._primary_focus and self._focus_started_at:
                self._attention_history.append(
                    AttentionHistoryEntry(
                        focus=self._primary_focus,
                        started_at=self._focus_started_at,
                        ended_at=datetime.now(),
                        metadata={"redirect_reason": reason, "redirected_to": to_task},
                    )
                )

            # Set new focus (keeping same budget or resetting to 0 if none)
            self._primary_focus = to_task
            self._focus_started_at = datetime.now()

    def persist_thread(self, thread: str, priority: PriorityLevel = PriorityLevel.MEDIUM) -> None:
        """
        Persist a pending thread for later attention.

        Args:
            thread: Thread description
            priority: Priority level for this thread
        """
        with self._lock:
            self._pending_threads.append(
                PendingThread(description=thread, priority=priority)
            )
            # Also add to background threads for state tracking
            if thread not in self._background_threads:
                self._background_threads.append(thread)

    def get_pending_threads(self, ordered: bool = False) -> list[str]:
        """
        Get all pending threads.

        Args:
            ordered: If True, return ordered by priority (CRITICAL first)

        Returns:
            List of thread descriptions
        """
        with self._lock:
            threads = self._pending_threads.copy()

            if ordered:
                threads.sort(key=lambda t: t.priority.value_numeric, reverse=True)

            return [t.description for t in threads]

    def get_attention_state(self) -> AttentionState:
        """
        Get current attention state snapshot.

        Returns:
            AttentionState with current focus, duration, and threads
        """
        with self._lock:
            if self._focus_started_at:
                duration = datetime.now() - self._focus_started_at
            else:
                duration = timedelta(0)

            return AttentionState(
                primary_focus=self._primary_focus,
                secondary_focus=self._secondary_focus.copy(),
                background_threads=self._background_threads.copy(),
                focus_duration=duration,
                started_at=self._focus_started_at,
            )

    def get_drift_history(self) -> list[AttentionDriftEvent]:
        """Get all drift events in chronological order."""
        with self._lock:
            return self._drift_history.copy()

    def get_attention_history(self) -> list[AttentionHistoryEntry]:
        """Get full attention history."""
        with self._lock:
            return self._attention_history.copy()

    def save_state(self) -> dict[str, Any]:
        """
        Save current attention state for persistence.

        Returns:
            Serializable state dictionary
        """
        with self._lock:
            started_at_iso = (
                self._focus_started_at.isoformat() if self._focus_started_at else None
            )
            return {
                "primary_focus": self._primary_focus,
                "focus_started_at": started_at_iso,
                "budget_minutes": self._budget_minutes,
                "secondary_focus": self._secondary_focus.copy(),
                "background_threads": self._background_threads.copy(),
                "pending_threads": [
                    {
                        "description": t.description,
                        "priority": t.priority.value,
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in self._pending_threads
                ],
            }

    def restore_state(self, state: dict[str, Any]) -> None:
        """
        Restore attention state from saved data.

        Args:
            state: Previously saved state dictionary
        """
        with self._lock:
            self._primary_focus = state.get("primary_focus")
            focus_started_str = state.get("focus_started_at")
            self._focus_started_at = (
                datetime.fromisoformat(focus_started_str) if focus_started_str else None
            )
            self._budget_minutes = state.get("budget_minutes", 0.0)
            self._secondary_focus = state.get("secondary_focus", [])
            self._background_threads = state.get("background_threads", [])

            # Restore pending threads
            self._pending_threads = [
                PendingThread(
                    description=t["description"],
                    priority=PriorityLevel(t["priority"]),
                    created_at=datetime.fromisoformat(t["created_at"]),
                )
                for t in state.get("pending_threads", [])
            ]
