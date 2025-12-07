"""Tests for agent metrics tracking."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from src.core.metrics import (
    MetricEntry,
    MetricType,
    MetricsTracker,
    get_metrics,
    record_phase_completed,
    record_quality,
    record_coffee_break,
    record_help_requested,
    record_help_provided,
    record_knowledge_shared,
    get_agent_summary,
    get_team_summary,
    get_leaderboard,
)
import src.core.metrics as metrics_module


class TestMetricEntry:
    """Tests for MetricEntry dataclass."""

    def test_create_entry(self):
        """Test creating a metric entry."""
        entry = MetricEntry(
            metric_type=MetricType.PHASE_COMPLETED,
            agent_name="Nova",
            value="2.1",
        )
        assert entry.metric_type == MetricType.PHASE_COMPLETED
        assert entry.agent_name == "Nova"
        assert entry.value == "2.1"
        assert entry.timestamp  # Auto-generated

    def test_entry_with_context(self):
        """Test creating entry with context."""
        entry = MetricEntry(
            metric_type=MetricType.TEST_COVERAGE,
            agent_name="Atlas",
            value=85.5,
            context={"module": "src/core"},
        )
        assert entry.context["module"] == "src/core"

    def test_to_dict(self):
        """Test serialization to dict."""
        entry = MetricEntry(
            metric_type=MetricType.LINT_ERRORS,
            agent_name="Nova",
            value=3,
            context={"files": ["a.py", "b.py"]},
        )
        data = entry.to_dict()
        assert data["metric_type"] == "lint_errors"
        assert data["agent_name"] == "Nova"
        assert data["value"] == 3
        assert data["context"]["files"] == ["a.py", "b.py"]

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "metric_type": "phase_completed",
            "agent_name": "Atlas",
            "value": "3.2",
            "timestamp": "2025-01-15T10:00:00",
            "context": {"coverage": 90.0},
        }
        entry = MetricEntry.from_dict(data)
        assert entry.metric_type == MetricType.PHASE_COMPLETED
        assert entry.agent_name == "Atlas"
        assert entry.value == "3.2"
        assert entry.timestamp == "2025-01-15T10:00:00"


class TestMetricsTracker:
    """Tests for MetricsTracker class."""

    @pytest.fixture
    def temp_metrics(self, tmp_path):
        """Create a tracker with temp file."""
        metrics_file = tmp_path / "metrics.json"
        return MetricsTracker(metrics_file)

    def test_init_creates_file(self, tmp_path):
        """Test that init creates metrics file parent dir."""
        metrics_file = tmp_path / "subdir" / "metrics.json"
        tracker = MetricsTracker(metrics_file)
        assert metrics_file.parent.exists()

    def test_record_and_retrieve(self, temp_metrics):
        """Test recording and retrieving entries."""
        entry = MetricEntry(
            metric_type=MetricType.TASK_COMPLETED,
            agent_name="Nova",
            value="Fix bug in parser",
        )
        temp_metrics.record(entry)

        entries = temp_metrics.get_entries(agent_name="Nova")
        assert len(entries) == 1
        assert entries[0].value == "Fix bug in parser"

    def test_persistence(self, tmp_path):
        """Test that entries persist across instances."""
        metrics_file = tmp_path / "metrics.json"

        # First instance records
        tracker1 = MetricsTracker(metrics_file)
        tracker1.record_phase_completed("Nova", "2.1")

        # Second instance reads
        tracker2 = MetricsTracker(metrics_file)
        entries = tracker2.get_entries(agent_name="Nova")
        assert len(entries) == 1

    # -------------------------------------------------------------------------
    # Velocity Metrics Tests
    # -------------------------------------------------------------------------

    def test_record_phase_completed(self, temp_metrics):
        """Test recording phase completion."""
        temp_metrics.record_phase_completed("Nova", "2.1", coverage=85.5, tests_added=10)

        entries = temp_metrics.get_entries(
            agent_name="Nova", metric_type=MetricType.PHASE_COMPLETED
        )
        assert len(entries) == 1
        assert entries[0].value == "2.1"
        assert entries[0].context["coverage"] == 85.5
        assert entries[0].context["tests_added"] == 10

    def test_record_task_started(self, temp_metrics):
        """Test recording task start."""
        temp_metrics.record_task_started("Atlas", "Implement error handler")

        entries = temp_metrics.get_entries(metric_type=MetricType.TASK_STARTED)
        assert len(entries) == 1
        assert entries[0].agent_name == "Atlas"

    def test_record_task_completed(self, temp_metrics):
        """Test recording task completion with duration."""
        temp_metrics.record_task_completed("Nova", "Fix parsing bug", duration_minutes=45.5)

        entries = temp_metrics.get_entries(metric_type=MetricType.TASK_COMPLETED)
        assert len(entries) == 1
        assert entries[0].context["duration_minutes"] == 45.5

    # -------------------------------------------------------------------------
    # Quality Metrics Tests
    # -------------------------------------------------------------------------

    def test_record_quality_coverage(self, temp_metrics):
        """Test recording test coverage."""
        temp_metrics.record_quality("Nova", test_coverage=87.3)

        entries = temp_metrics.get_entries(metric_type=MetricType.TEST_COVERAGE)
        assert len(entries) == 1
        assert entries[0].value == 87.3

    def test_record_quality_multiple(self, temp_metrics):
        """Test recording multiple quality metrics at once."""
        temp_metrics.record_quality(
            "Atlas",
            test_coverage=90.0,
            tests_passed=150,
            tests_failed=2,
            lint_errors=0,
            type_errors=3,
        )

        entries = temp_metrics.get_entries(agent_name="Atlas")
        assert len(entries) == 5  # One entry per metric type

    def test_record_quality_partial(self, temp_metrics):
        """Test recording only some quality metrics."""
        temp_metrics.record_quality("Nova", lint_errors=5)

        entries = temp_metrics.get_entries(agent_name="Nova")
        assert len(entries) == 1
        assert entries[0].metric_type == MetricType.LINT_ERRORS

    # -------------------------------------------------------------------------
    # Collaboration Metrics Tests
    # -------------------------------------------------------------------------

    def test_record_coffee_break(self, temp_metrics):
        """Test recording coffee break."""
        temp_metrics.record_coffee_break(
            "Nova",
            partners=["Atlas", "Phoenix"],
            topic="TDD patterns",
            duration_minutes=15.0,
        )

        entries = temp_metrics.get_entries(metric_type=MetricType.COFFEE_BREAK)
        assert len(entries) == 1
        assert entries[0].value == 3  # Total participants
        assert entries[0].context["partners"] == ["Atlas", "Phoenix"]
        assert entries[0].context["topic"] == "TDD patterns"

    def test_record_help_requested(self, temp_metrics):
        """Test recording help request."""
        temp_metrics.record_help_requested(
            "Phoenix", "Need help with async patterns", approved=True
        )

        entries = temp_metrics.get_entries(metric_type=MetricType.HELP_REQUESTED)
        assert len(entries) == 1
        assert entries[0].context["approved"] is True

    def test_record_help_provided(self, temp_metrics):
        """Test recording help provision."""
        temp_metrics.record_help_provided(
            "Nova", helped_agent="Phoenix", task="Async implementation"
        )

        entries = temp_metrics.get_entries(metric_type=MetricType.HELP_PROVIDED)
        assert len(entries) == 1
        assert entries[0].context["helped_agent"] == "Phoenix"

    def test_record_knowledge_shared(self, temp_metrics):
        """Test recording knowledge sharing."""
        temp_metrics.record_knowledge_shared(
            "Atlas", topic="Error handling patterns", recipients=["Nova", "Phoenix"]
        )

        entries = temp_metrics.get_entries(metric_type=MetricType.KNOWLEDGE_SHARED)
        assert len(entries) == 1
        assert entries[0].context["recipients"] == ["Nova", "Phoenix"]

    # -------------------------------------------------------------------------
    # Query Tests
    # -------------------------------------------------------------------------

    def test_get_entries_filter_by_agent(self, temp_metrics):
        """Test filtering entries by agent."""
        temp_metrics.record_phase_completed("Nova", "2.1")
        temp_metrics.record_phase_completed("Atlas", "2.2")
        temp_metrics.record_phase_completed("Nova", "2.3")

        nova_entries = temp_metrics.get_entries(agent_name="Nova")
        assert len(nova_entries) == 2

    def test_get_entries_filter_by_type(self, temp_metrics):
        """Test filtering entries by metric type."""
        temp_metrics.record_phase_completed("Nova", "2.1")
        temp_metrics.record_quality("Nova", lint_errors=0)

        phase_entries = temp_metrics.get_entries(metric_type=MetricType.PHASE_COMPLETED)
        assert len(phase_entries) == 1

    def test_get_entries_filter_by_timestamp(self, temp_metrics):
        """Test filtering entries by timestamp."""
        temp_metrics.record_phase_completed("Nova", "2.1")

        # Filter for entries after now (should be empty)
        future = datetime(2099, 1, 1).isoformat()
        entries = temp_metrics.get_entries(since=future)
        assert len(entries) == 0

    # -------------------------------------------------------------------------
    # Summary Tests
    # -------------------------------------------------------------------------

    def test_get_agent_summary(self, temp_metrics):
        """Test getting agent summary."""
        # Record various metrics
        temp_metrics.record_phase_completed("Nova", "2.1")
        temp_metrics.record_phase_completed("Nova", "2.2")
        temp_metrics.record_task_completed("Nova", "Task 1")
        temp_metrics.record_quality("Nova", test_coverage=85.0)
        temp_metrics.record_coffee_break("Nova", ["Atlas"])
        temp_metrics.record_help_provided("Nova", "Phoenix", "Help with tests")

        summary = temp_metrics.get_agent_summary("Nova")

        assert summary["agent_name"] == "Nova"
        assert summary["velocity"]["phases_completed"] == 2
        assert summary["velocity"]["tasks_completed"] == 1
        assert summary["quality"]["latest_coverage"] == 85.0
        assert summary["collaboration"]["coffee_breaks"] == 1
        assert summary["collaboration"]["help_given"] == 1

    def test_get_agent_summary_empty(self, temp_metrics):
        """Test getting summary for agent with no entries."""
        summary = temp_metrics.get_agent_summary("Unknown")

        assert summary["velocity"]["phases_completed"] == 0
        assert summary["quality"]["latest_coverage"] is None

    def test_get_team_summary(self, temp_metrics):
        """Test getting team summary."""
        temp_metrics.record_phase_completed("Nova", "2.1")
        temp_metrics.record_phase_completed("Atlas", "2.2")
        temp_metrics.record_quality("Nova", test_coverage=85.0)
        temp_metrics.record_quality("Atlas", test_coverage=90.0)
        temp_metrics.record_coffee_break("Nova", ["Atlas"])

        summary = temp_metrics.get_team_summary()

        assert summary["total_agents"] == 2
        assert "Nova" in summary["agents"]
        assert "Atlas" in summary["agents"]
        assert summary["velocity"]["total_phases_completed"] == 2
        assert summary["quality"]["average_coverage"] == 87.5

    def test_get_leaderboard_phases(self, temp_metrics):
        """Test leaderboard by phases completed."""
        temp_metrics.record_phase_completed("Nova", "2.1")
        temp_metrics.record_phase_completed("Nova", "2.2")
        temp_metrics.record_phase_completed("Atlas", "2.3")

        leaderboard = temp_metrics.get_leaderboard(MetricType.PHASE_COMPLETED)

        assert len(leaderboard) == 2
        assert leaderboard[0]["agent_name"] == "Nova"
        assert leaderboard[0]["score"] == 2

    def test_get_leaderboard_lint_errors(self, temp_metrics):
        """Test leaderboard by lint errors (lower is better)."""
        temp_metrics.record_quality("Nova", lint_errors=0)
        temp_metrics.record_quality("Atlas", lint_errors=5)

        leaderboard = temp_metrics.get_leaderboard(MetricType.LINT_ERRORS)

        # Lower errors should rank first
        assert leaderboard[0]["agent_name"] == "Nova"
        assert leaderboard[0]["score"] == 0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self, tmp_path):
        """Reset singleton and use temp file."""
        metrics_module._metrics_instance = None

        # Patch to use temp file
        original_init = MetricsTracker.__init__
        test_file = tmp_path / "metrics.json"

        def patched_init(self, metrics_file=None):
            original_init(self, test_file)

        metrics_module.MetricsTracker.__init__ = patched_init

        yield

        metrics_module.MetricsTracker.__init__ = original_init
        metrics_module._metrics_instance = None

    def test_get_metrics_singleton(self):
        """Test that get_metrics returns singleton."""
        tracker1 = get_metrics()
        tracker2 = get_metrics()
        assert tracker1 is tracker2

    def test_record_phase_completed_convenience(self):
        """Test convenience function for phase completion."""
        record_phase_completed("Nova", "2.1", coverage=85.0)

        summary = get_agent_summary("Nova")
        assert summary["velocity"]["phases_completed"] == 1

    def test_record_quality_convenience(self):
        """Test convenience function for quality metrics."""
        record_quality("Atlas", test_coverage=90.0, lint_errors=0)

        summary = get_agent_summary("Atlas")
        assert summary["quality"]["latest_coverage"] == 90.0

    def test_record_coffee_break_convenience(self):
        """Test convenience function for coffee breaks."""
        record_coffee_break("Nova", ["Atlas"], topic="Testing")

        summary = get_agent_summary("Nova")
        assert summary["collaboration"]["coffee_breaks"] == 1

    def test_record_help_requested_convenience(self):
        """Test convenience function for help requests."""
        record_help_requested("Phoenix", "Need async help", approved=True)

        summary = get_agent_summary("Phoenix")
        assert summary["collaboration"]["help_received"] == 1

    def test_record_help_provided_convenience(self):
        """Test convenience function for help provided."""
        record_help_provided("Nova", "Phoenix", "Async patterns")

        summary = get_agent_summary("Nova")
        assert summary["collaboration"]["help_given"] == 1

    def test_record_knowledge_shared_convenience(self):
        """Test convenience function for knowledge sharing."""
        record_knowledge_shared("Atlas", "TDD", ["Nova", "Phoenix"])

        summary = get_agent_summary("Atlas")
        assert summary["collaboration"]["knowledge_shares"] == 1

    def test_get_team_summary_convenience(self):
        """Test convenience function for team summary."""
        record_phase_completed("Nova", "2.1")
        record_phase_completed("Atlas", "2.2")

        summary = get_team_summary()
        assert summary["total_agents"] == 2

    def test_get_leaderboard_convenience(self):
        """Test convenience function for leaderboard."""
        record_phase_completed("Nova", "2.1")
        record_phase_completed("Nova", "2.2")
        record_phase_completed("Atlas", "2.3")

        leaderboard = get_leaderboard(MetricType.PHASE_COMPLETED)
        assert leaderboard[0]["agent_name"] == "Nova"


class TestMetricType:
    """Tests for MetricType enum."""

    def test_velocity_types(self):
        """Test velocity metric types exist."""
        assert MetricType.PHASE_COMPLETED == "phase_completed"
        assert MetricType.TASK_STARTED == "task_started"
        assert MetricType.TASK_COMPLETED == "task_completed"

    def test_quality_types(self):
        """Test quality metric types exist."""
        assert MetricType.TEST_COVERAGE == "test_coverage"
        assert MetricType.TESTS_PASSED == "tests_passed"
        assert MetricType.LINT_ERRORS == "lint_errors"
        assert MetricType.TYPE_ERRORS == "type_errors"

    def test_collaboration_types(self):
        """Test collaboration metric types exist."""
        assert MetricType.COFFEE_BREAK == "coffee_break"
        assert MetricType.HELP_REQUESTED == "help_requested"
        assert MetricType.HELP_PROVIDED == "help_provided"
        assert MetricType.KNOWLEDGE_SHARED == "knowledge_shared"
