"""
Agent Metrics Tracking - Measure velocity, quality, and collaboration.

Tracks three categories of metrics:
1. Velocity - Phases completed, tasks per session
2. Quality - Test coverage, lint errors, type errors
3. Collaboration - Coffee breaks, help requests, tool uses

Based on plans/subagent-development-strategy.md success metrics.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class MetricType(str, Enum):
    """Types of metrics tracked."""

    # Velocity
    PHASE_COMPLETED = "phase_completed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    SESSION_DURATION = "session_duration"

    # Quality
    TEST_COVERAGE = "test_coverage"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    LINT_ERRORS = "lint_errors"
    TYPE_ERRORS = "type_errors"

    # Collaboration
    COFFEE_BREAK = "coffee_break"
    HELP_REQUESTED = "help_requested"
    HELP_PROVIDED = "help_provided"
    TOOL_CREATED = "tool_created"
    TOOL_USED = "tool_used"
    KNOWLEDGE_SHARED = "knowledge_shared"


@dataclass
class MetricEntry:
    """A single metric entry."""

    metric_type: MetricType
    agent_name: str
    value: float | int | str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_type": self.metric_type.value,
            "agent_name": self.agent_name,
            "value": self.value,
            "timestamp": self.timestamp,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetricEntry":
        """Create from dictionary."""
        return cls(
            metric_type=MetricType(data["metric_type"]),
            agent_name=data["agent_name"],
            value=data["value"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            context=data.get("context", {}),
        )


class MetricsTracker:
    """
    Track and analyze agent metrics.

    Usage:
        tracker = MetricsTracker()
        tracker.record_phase_completed("Nova", "2.1", coverage=85.5)
        tracker.record_quality("Nova", test_coverage=85.5, lint_errors=0)
        summary = tracker.get_agent_summary("Nova")
    """

    def __init__(self, metrics_file: Path | None = None):
        """
        Initialize metrics tracker.

        Args:
            metrics_file: Path to metrics JSON file. Defaults to config/metrics.json
        """
        if metrics_file is None:
            project_root = Path(__file__).parent.parent.parent
            metrics_file = project_root / "config" / "metrics.json"

        self.metrics_file = metrics_file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        """Load metrics from file."""
        if self.metrics_file.exists():
            with open(self.metrics_file) as f:
                data: dict[str, Any] = json.load(f)
                return data
        return {"entries": [], "summaries": {}}

    def _save(self) -> None:
        """Save metrics to file."""
        with open(self.metrics_file, "w") as f:
            json.dump(self._data, f, indent=2)
            f.write("\n")

    def record(self, entry: MetricEntry) -> None:
        """
        Record a metric entry.

        Args:
            entry: The metric entry to record
        """
        self._data["entries"].append(entry.to_dict())
        self._save()

    # -------------------------------------------------------------------------
    # Velocity Metrics
    # -------------------------------------------------------------------------

    def record_phase_completed(
        self,
        agent_name: str,
        phase_id: str,
        coverage: float | None = None,
        tests_added: int | None = None,
    ) -> None:
        """
        Record that an agent completed a phase.

        Args:
            agent_name: Name of the agent
            phase_id: Phase identifier (e.g., "2.1")
            coverage: Test coverage percentage (optional)
            tests_added: Number of tests added (optional)
        """
        context: dict[str, Any] = {"phase_id": phase_id}
        if coverage is not None:
            context["coverage"] = coverage
        if tests_added is not None:
            context["tests_added"] = tests_added

        self.record(
            MetricEntry(
                metric_type=MetricType.PHASE_COMPLETED,
                agent_name=agent_name,
                value=phase_id,
                context=context,
            )
        )

    def record_task_started(self, agent_name: str, task_description: str) -> None:
        """Record that an agent started a task."""
        self.record(
            MetricEntry(
                metric_type=MetricType.TASK_STARTED,
                agent_name=agent_name,
                value=task_description,
            )
        )

    def record_task_completed(
        self,
        agent_name: str,
        task_description: str,
        duration_minutes: float | None = None,
    ) -> None:
        """Record that an agent completed a task."""
        context = {}
        if duration_minutes is not None:
            context["duration_minutes"] = duration_minutes

        self.record(
            MetricEntry(
                metric_type=MetricType.TASK_COMPLETED,
                agent_name=agent_name,
                value=task_description,
                context=context,
            )
        )

    # -------------------------------------------------------------------------
    # Quality Metrics
    # -------------------------------------------------------------------------

    def record_quality(
        self,
        agent_name: str,
        test_coverage: float | None = None,
        tests_passed: int | None = None,
        tests_failed: int | None = None,
        lint_errors: int | None = None,
        type_errors: int | None = None,
    ) -> None:
        """
        Record quality metrics from a session.

        Args:
            agent_name: Name of the agent
            test_coverage: Coverage percentage (0-100)
            tests_passed: Number of passing tests
            tests_failed: Number of failing tests
            lint_errors: Number of lint errors
            type_errors: Number of type errors
        """
        if test_coverage is not None:
            self.record(
                MetricEntry(
                    metric_type=MetricType.TEST_COVERAGE,
                    agent_name=agent_name,
                    value=test_coverage,
                )
            )

        if tests_passed is not None:
            self.record(
                MetricEntry(
                    metric_type=MetricType.TESTS_PASSED,
                    agent_name=agent_name,
                    value=tests_passed,
                )
            )

        if tests_failed is not None:
            self.record(
                MetricEntry(
                    metric_type=MetricType.TESTS_FAILED,
                    agent_name=agent_name,
                    value=tests_failed,
                )
            )

        if lint_errors is not None:
            self.record(
                MetricEntry(
                    metric_type=MetricType.LINT_ERRORS,
                    agent_name=agent_name,
                    value=lint_errors,
                )
            )

        if type_errors is not None:
            self.record(
                MetricEntry(
                    metric_type=MetricType.TYPE_ERRORS,
                    agent_name=agent_name,
                    value=type_errors,
                )
            )

    # -------------------------------------------------------------------------
    # Collaboration Metrics
    # -------------------------------------------------------------------------

    def record_coffee_break(
        self,
        agent_name: str,
        partners: list[str],
        topic: str | None = None,
        duration_minutes: float | None = None,
    ) -> None:
        """Record a coffee break session."""
        context: dict[str, Any] = {"partners": partners}
        if topic:
            context["topic"] = topic
        if duration_minutes is not None:
            context["duration_minutes"] = duration_minutes

        self.record(
            MetricEntry(
                metric_type=MetricType.COFFEE_BREAK,
                agent_name=agent_name,
                value=len(partners) + 1,  # Total participants
                context=context,
            )
        )

    def record_help_requested(
        self, agent_name: str, reason: str, approved: bool | None = None
    ) -> None:
        """Record that an agent requested help."""
        context: dict[str, Any] = {"reason": reason}
        if approved is not None:
            context["approved"] = approved

        self.record(
            MetricEntry(
                metric_type=MetricType.HELP_REQUESTED,
                agent_name=agent_name,
                value=reason,
                context=context,
            )
        )

    def record_help_provided(self, agent_name: str, helped_agent: str, task: str) -> None:
        """Record that an agent provided help to another."""
        self.record(
            MetricEntry(
                metric_type=MetricType.HELP_PROVIDED,
                agent_name=agent_name,
                value=task,
                context={"helped_agent": helped_agent},
            )
        )

    def record_knowledge_shared(self, agent_name: str, topic: str, recipients: list[str]) -> None:
        """Record knowledge sharing (teaching, war stories, etc.)."""
        self.record(
            MetricEntry(
                metric_type=MetricType.KNOWLEDGE_SHARED,
                agent_name=agent_name,
                value=topic,
                context={"recipients": recipients},
            )
        )

    # -------------------------------------------------------------------------
    # Queries and Summaries
    # -------------------------------------------------------------------------

    def get_entries(
        self,
        agent_name: str | None = None,
        metric_type: MetricType | None = None,
        since: str | None = None,
    ) -> list[MetricEntry]:
        """
        Get metric entries with optional filters.

        Args:
            agent_name: Filter by agent name
            metric_type: Filter by metric type
            since: Filter entries after this ISO timestamp

        Returns:
            List of matching MetricEntry objects
        """
        entries = []
        for data in self._data["entries"]:
            if agent_name and data["agent_name"] != agent_name:
                continue
            if metric_type and data["metric_type"] != metric_type.value:
                continue
            if since and data["timestamp"] < since:
                continue
            entries.append(MetricEntry.from_dict(data))
        return entries

    def get_agent_summary(self, agent_name: str) -> dict[str, Any]:
        """
        Get a summary of an agent's metrics.

        Returns:
            Dict with velocity, quality, and collaboration summaries
        """
        entries = self.get_entries(agent_name=agent_name)

        # Count by type
        phases_completed = sum(1 for e in entries if e.metric_type == MetricType.PHASE_COMPLETED)
        tasks_completed = sum(1 for e in entries if e.metric_type == MetricType.TASK_COMPLETED)

        # Latest quality metrics
        coverage_entries = [e for e in entries if e.metric_type == MetricType.TEST_COVERAGE]
        latest_coverage = coverage_entries[-1].value if coverage_entries else None

        lint_entries = [e for e in entries if e.metric_type == MetricType.LINT_ERRORS]
        latest_lint = lint_entries[-1].value if lint_entries else None

        # Collaboration counts
        coffee_breaks = sum(1 for e in entries if e.metric_type == MetricType.COFFEE_BREAK)
        help_given = sum(1 for e in entries if e.metric_type == MetricType.HELP_PROVIDED)
        help_received = sum(1 for e in entries if e.metric_type == MetricType.HELP_REQUESTED)
        knowledge_shares = sum(1 for e in entries if e.metric_type == MetricType.KNOWLEDGE_SHARED)

        return {
            "agent_name": agent_name,
            "velocity": {
                "phases_completed": phases_completed,
                "tasks_completed": tasks_completed,
            },
            "quality": {
                "latest_coverage": latest_coverage,
                "latest_lint_errors": latest_lint,
            },
            "collaboration": {
                "coffee_breaks": coffee_breaks,
                "help_given": help_given,
                "help_received": help_received,
                "knowledge_shares": knowledge_shares,
            },
            "total_entries": len(entries),
        }

    def get_team_summary(self) -> dict[str, Any]:
        """
        Get a summary of all agents' metrics.

        Returns:
            Dict with team-wide metrics
        """
        entries = self._data["entries"]

        # Get unique agents
        agents = set(e["agent_name"] for e in entries)

        # Team totals
        total_phases = sum(
            1 for e in entries if e["metric_type"] == MetricType.PHASE_COMPLETED.value
        )
        total_tasks = sum(1 for e in entries if e["metric_type"] == MetricType.TASK_COMPLETED.value)
        total_breaks = sum(1 for e in entries if e["metric_type"] == MetricType.COFFEE_BREAK.value)

        # Calculate average coverage from most recent per agent
        agent_coverage = {}
        for e in entries:
            if e["metric_type"] == MetricType.TEST_COVERAGE.value:
                agent_coverage[e["agent_name"]] = e["value"]

        avg_coverage = (
            sum(agent_coverage.values()) / len(agent_coverage) if agent_coverage else None
        )

        return {
            "total_agents": len(agents),
            "agents": list(agents),
            "velocity": {
                "total_phases_completed": total_phases,
                "total_tasks_completed": total_tasks,
            },
            "quality": {
                "average_coverage": avg_coverage,
            },
            "collaboration": {
                "total_coffee_breaks": total_breaks,
                "collaboration_ratio": total_breaks / max(len(agents), 1),
            },
        }

    def get_leaderboard(self, metric_type: MetricType) -> list[dict[str, Any]]:
        """
        Get leaderboard for a specific metric type.

        Returns:
            List of {agent_name, count/value} sorted by performance
        """
        entries = self._data["entries"]
        agent_scores: dict[str, float] = {}

        for e in entries:
            if e["metric_type"] == metric_type.value:
                agent = e["agent_name"]
                if metric_type in (
                    MetricType.TEST_COVERAGE,
                    MetricType.LINT_ERRORS,
                    MetricType.TYPE_ERRORS,
                ):
                    # For these, keep latest value
                    agent_scores[agent] = e["value"]
                else:
                    # For others, count occurrences
                    agent_scores[agent] = agent_scores.get(agent, 0) + 1

        # Sort by score (descending for most, ascending for errors)
        reverse = metric_type not in (MetricType.LINT_ERRORS, MetricType.TYPE_ERRORS)
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=reverse)

        return [{"agent_name": name, "score": score} for name, score in sorted_agents]


# -----------------------------------------------------------------------------
# Singleton and Convenience Functions
# -----------------------------------------------------------------------------

_metrics_instance: MetricsTracker | None = None


def get_metrics(metrics_file: Path | None = None) -> MetricsTracker:
    """Get the metrics tracker singleton."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsTracker(metrics_file)
    return _metrics_instance


def record_phase_completed(
    agent_name: str,
    phase_id: str,
    coverage: float | None = None,
    tests_added: int | None = None,
) -> None:
    """Record that an agent completed a phase."""
    get_metrics().record_phase_completed(agent_name, phase_id, coverage, tests_added)


def record_quality(
    agent_name: str,
    test_coverage: float | None = None,
    tests_passed: int | None = None,
    tests_failed: int | None = None,
    lint_errors: int | None = None,
    type_errors: int | None = None,
) -> None:
    """Record quality metrics from a session."""
    get_metrics().record_quality(
        agent_name, test_coverage, tests_passed, tests_failed, lint_errors, type_errors
    )


def record_coffee_break(
    agent_name: str,
    partners: list[str],
    topic: str | None = None,
    duration_minutes: float | None = None,
) -> None:
    """Record a coffee break session."""
    get_metrics().record_coffee_break(agent_name, partners, topic, duration_minutes)


def record_help_requested(agent_name: str, reason: str, approved: bool | None = None) -> None:
    """Record that an agent requested help."""
    get_metrics().record_help_requested(agent_name, reason, approved)


def record_help_provided(agent_name: str, helped_agent: str, task: str) -> None:
    """Record that an agent provided help to another."""
    get_metrics().record_help_provided(agent_name, helped_agent, task)


def record_knowledge_shared(agent_name: str, topic: str, recipients: list[str]) -> None:
    """Record knowledge sharing."""
    get_metrics().record_knowledge_shared(agent_name, topic, recipients)


def get_agent_summary(agent_name: str) -> dict[str, Any]:
    """Get a summary of an agent's metrics."""
    return get_metrics().get_agent_summary(agent_name)


def get_team_summary() -> dict[str, Any]:
    """Get a summary of all agents' metrics."""
    return get_metrics().get_team_summary()


def get_leaderboard(metric_type: MetricType) -> list[dict[str, Any]]:
    """Get leaderboard for a specific metric type."""
    return get_metrics().get_leaderboard(metric_type)
