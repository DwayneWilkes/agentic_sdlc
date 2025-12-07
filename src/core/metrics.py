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


# -----------------------------------------------------------------------------
# Metrics Dashboard - Phase 7.5
# -----------------------------------------------------------------------------


class MetricsDashboard:
    """
    Metrics Dashboard for reporting and trend analysis.

    Provides formatted reports, trend analysis, completion rates,
    and efficiency metrics.

    Usage:
        dashboard = MetricsDashboard(tracker)
        print(dashboard.format_agent_report("Nova"))
        print(dashboard.format_team_report())
        trend = dashboard.get_trend_data(MetricType.PHASE_COMPLETED, "Nova")
    """

    def __init__(self, tracker: MetricsTracker):
        """
        Initialize dashboard.

        Args:
            tracker: The MetricsTracker instance to use
        """
        self.tracker = tracker

    # -------------------------------------------------------------------------
    # Report Formatting
    # -------------------------------------------------------------------------

    def format_agent_report(self, agent_name: str) -> str:
        """
        Format a detailed report for an individual agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Formatted text report
        """
        summary = self.tracker.get_agent_summary(agent_name)

        if summary["total_entries"] == 0:
            return f"Agent: {agent_name}\nNo data available."

        report_lines = [
            f"=== Agent Report: {agent_name} ===",
            "",
            "Velocity:",
            f"  Phases Completed: {summary['velocity']['phases_completed']}",
            f"  Tasks Completed: {summary['velocity']['tasks_completed']}",
            "",
            "Quality:",
            f"  Latest Coverage: {summary['quality']['latest_coverage']}%"
            if summary["quality"]["latest_coverage"] is not None
            else "  Latest Coverage: N/A",
            f"  Latest Lint Errors: {summary['quality']['latest_lint_errors']}"
            if summary["quality"]["latest_lint_errors"] is not None
            else "  Latest Lint Errors: N/A",
            "",
            "Collaboration:",
            f"  Coffee Breaks: {summary['collaboration']['coffee_breaks']}",
            f"  Help Given: {summary['collaboration']['help_given']}",
            f"  Help Received: {summary['collaboration']['help_received']}",
            f"  Knowledge Shares: {summary['collaboration']['knowledge_shares']}",
            "",
            f"Total Entries: {summary['total_entries']}",
        ]

        return "\n".join(report_lines)

    def format_team_report(self) -> str:
        """
        Format a team-wide summary report.

        Returns:
            Formatted text report
        """
        summary = self.tracker.get_team_summary()

        report_lines = [
            "=== Team Overview ===",
            "",
            f"Total Agents: {summary['total_agents']}",
            f"Agents: {', '.join(summary['agents'])}",
            "",
            "Velocity:",
            f"  Total Phases Completed: {summary['velocity']['total_phases_completed']}",
            f"  Total Tasks Completed: {summary['velocity']['total_tasks_completed']}",
            "",
            "Quality:",
            f"  Average Coverage: {summary['quality']['average_coverage']:.1f}%"
            if summary["quality"]["average_coverage"] is not None
            else "  Average Coverage: N/A",
            "",
            "Collaboration:",
            f"  Total Coffee Breaks: {summary['collaboration']['total_coffee_breaks']}",
            f"  Collaboration Ratio: {summary['collaboration']['collaboration_ratio']:.2f}",
        ]

        return "\n".join(report_lines)

    # -------------------------------------------------------------------------
    # Trend Analysis
    # -------------------------------------------------------------------------

    def get_trend_data(
        self, metric_type: MetricType, agent_name: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get time series data for a metric.

        Args:
            metric_type: The type of metric to get
            agent_name: Optional agent name filter

        Returns:
            List of {timestamp, value} dicts ordered by time
        """
        entries = self.tracker.get_entries(agent_name=agent_name, metric_type=metric_type)

        trend_data = [{"timestamp": e.timestamp, "value": e.value} for e in entries]

        # Sort by timestamp
        return sorted(trend_data, key=lambda x: x["timestamp"])

    def calculate_velocity_trend(self, agent_name: str) -> dict[str, Any]:
        """
        Calculate velocity trend over time.

        Args:
            agent_name: Name of the agent

        Returns:
            Dict with velocity trend metrics
        """
        phase_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.PHASE_COMPLETED
        )

        if not phase_entries:
            return {"phases_per_day": 0, "trend": "no data"}

        # Calculate phases per day
        if len(phase_entries) == 1:
            return {"phases_per_day": 1, "trend": "single data point"}

        # Get time span
        timestamps = [datetime.fromisoformat(e.timestamp) for e in phase_entries]
        time_span = (max(timestamps) - min(timestamps)).total_seconds() / 86400  # days

        if time_span == 0:
            phases_per_day: float = float(len(phase_entries))  # All in one day
        else:
            phases_per_day = len(phase_entries) / time_span

        return {"phases_per_day": round(phases_per_day, 2), "trend": "calculated"}

    def calculate_quality_trend(self, agent_name: str) -> dict[str, Any]:
        """
        Calculate quality trend over time.

        Args:
            agent_name: Name of the agent

        Returns:
            Dict with quality trend metrics
        """
        coverage_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.TEST_COVERAGE
        )

        if not coverage_entries:
            return {"avg_coverage": None, "coverage_trend": "no data"}

        # Calculate average coverage
        values = [float(e.value) for e in coverage_entries]
        avg_coverage = sum(values) / len(values)

        return {
            "avg_coverage": round(avg_coverage, 2),
            "coverage_trend": "calculated",
            "data_points": len(coverage_entries),
        }

    def calculate_collaboration_trend(self, agent_name: str) -> dict[str, Any]:
        """
        Calculate collaboration trend.

        Args:
            agent_name: Name of the agent

        Returns:
            Dict with collaboration metrics
        """
        coffee_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.COFFEE_BREAK
        )
        help_given_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.HELP_PROVIDED
        )
        help_received_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.HELP_REQUESTED
        )

        return {
            "coffee_breaks": len(coffee_entries),
            "help_given": len(help_given_entries),
            "help_received": len(help_received_entries),
            "collaboration_count": len(coffee_entries)
            + len(help_given_entries)
            + len(help_received_entries),
        }

    # -------------------------------------------------------------------------
    # Completion Rates
    # -------------------------------------------------------------------------

    def get_completion_rates(self) -> dict[str, float]:
        """
        Get overall completion rates.

        Returns:
            Dict with phase and task completion rates
        """
        return {
            "phase_completion_rate": self.get_phase_completion_rate(),
            "task_completion_rate": self.get_task_completion_rate(),
        }

    def get_phase_completion_rate(self) -> float:
        """
        Calculate phase completion rate.

        Returns:
            Percentage of phases completed (0-100)
        """
        # Get all phase completions
        all_entries = self.tracker._data["entries"]
        completed = sum(1 for e in all_entries if e["metric_type"] == "phase_completed")

        # Get total phases from roadmap (if available)
        try:
            from src.orchestrator.work_stream import parse_roadmap

            all_streams = parse_roadmap()
            total_phases = len(all_streams)

            if total_phases > 0:
                return round((completed / total_phases) * 100, 2)
        except (ImportError, FileNotFoundError):
            pass

        # Fallback: just return completed count as percentage
        # (assumes completed is out of 100, or return count if < 100)
        return min(completed, 100)

    def get_task_completion_rate(self) -> float:
        """
        Calculate task completion rate.

        Returns:
            Percentage of tasks completed vs started (0-100)
        """
        all_entries = self.tracker._data["entries"]
        started = sum(1 for e in all_entries if e["metric_type"] == "task_started")
        completed = sum(1 for e in all_entries if e["metric_type"] == "task_completed")

        if started == 0:
            return 100.0 if completed > 0 else 0.0

        return round((completed / started) * 100, 2)

    def get_success_rate(self, agent_name: str) -> float:
        """
        Calculate test success rate for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Percentage of tests passed (0-100)
        """
        passed_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.TESTS_PASSED
        )
        failed_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.TESTS_FAILED
        )

        if not passed_entries and not failed_entries:
            return 100.0  # No test data = assume success

        # Get latest values (cast to int for arithmetic)
        total_passed = int(passed_entries[-1].value) if passed_entries else 0
        total_failed = int(failed_entries[-1].value) if failed_entries else 0

        total_tests = total_passed + total_failed
        if total_tests == 0:
            return 100.0

        return round((total_passed / total_tests) * 100, 2)

    # -------------------------------------------------------------------------
    # Efficiency Metrics
    # -------------------------------------------------------------------------

    def get_efficiency_metrics(self, agent_name: str) -> dict[str, Any]:
        """
        Get efficiency metrics for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Dict with efficiency metrics
        """
        return {
            "avg_time_per_phase": self.get_avg_time_per_phase(agent_name),
            "avg_time_per_task": self.get_avg_time_per_task(agent_name),
            "time_efficiency": "calculated",
        }

    def get_avg_time_per_phase(self, agent_name: str) -> float | None:
        """
        Calculate average time per phase.

        Args:
            agent_name: Name of the agent

        Returns:
            Average minutes per phase, or None if no timing data
        """
        # Currently we don't track phase duration directly
        # This could be added in the future
        return None

    def get_avg_time_per_task(self, agent_name: str) -> float | None:
        """
        Calculate average time per task.

        Args:
            agent_name: Name of the agent

        Returns:
            Average minutes per task, or None if no timing data
        """
        task_entries = self.tracker.get_entries(
            agent_name=agent_name, metric_type=MetricType.TASK_COMPLETED
        )

        # Filter to entries with duration
        durations: list[float] = [
            float(e.context["duration_minutes"])
            for e in task_entries
            if "duration_minutes" in e.context
        ]

        if not durations:
            return None

        return round(sum(durations) / len(durations), 2)
