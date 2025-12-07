"""Tests for the Agent Dashboard."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.orchestrator.dashboard import (
    AgentDashboard,
    AgentInfo,
)


class TestAgentInfo:
    """Tests for AgentInfo dataclass."""

    def test_create_agent_info(self):
        """Test creating an AgentInfo object."""
        info = AgentInfo(
            agent_id="test-agent-123",
            personal_name="Nova",
            work_stream_id="2.1",
            status="running",
        )
        assert info.agent_id == "test-agent-123"
        assert info.personal_name == "Nova"
        assert info.work_stream_id == "2.1"
        assert info.status == "running"

    def test_duration_seconds(self):
        """Test duration display for short times."""
        info = AgentInfo(
            agent_id="test",
            started_at=datetime.now() - timedelta(seconds=30),
        )
        assert info.duration == "30s"

    def test_duration_minutes(self):
        """Test duration display for minutes."""
        info = AgentInfo(
            agent_id="test",
            started_at=datetime.now() - timedelta(minutes=5),
        )
        assert info.duration == "5m"

    def test_duration_hours(self):
        """Test duration display for hours."""
        info = AgentInfo(
            agent_id="test",
            started_at=datetime.now() - timedelta(hours=2, minutes=30),
        )
        assert info.duration == "2h 30m"

    def test_duration_no_start(self):
        """Test duration when not started."""
        info = AgentInfo(agent_id="test")
        assert info.duration == "-"

    def test_status_emoji_running(self):
        """Test emoji for running status."""
        info = AgentInfo(agent_id="test", status="running")
        assert info.status_emoji == "🔄"

    def test_status_emoji_started(self):
        """Test emoji for started status."""
        info = AgentInfo(agent_id="test", status="started")
        assert info.status_emoji == "🔄"

    def test_status_emoji_completed(self):
        """Test emoji for completed status."""
        info = AgentInfo(agent_id="test", status="completed")
        assert info.status_emoji == "✅"

    def test_status_emoji_failed(self):
        """Test emoji for failed status."""
        info = AgentInfo(agent_id="test", status="failed")
        assert info.status_emoji == "❌"

    def test_status_emoji_stopped(self):
        """Test emoji for stopped status."""
        info = AgentInfo(agent_id="test", status="stopped")
        assert info.status_emoji == "⏹️"

    def test_status_emoji_on_break(self):
        """Test emoji for on_break status."""
        info = AgentInfo(agent_id="test", status="on_break")
        assert info.status_emoji == "☕"

    def test_status_emoji_available(self):
        """Test emoji for available status."""
        info = AgentInfo(agent_id="test", status="available")
        assert info.status_emoji == "🟢"

    def test_status_emoji_unknown(self):
        """Test emoji for unknown status."""
        info = AgentInfo(agent_id="test", status="unknown")
        assert info.status_emoji == "❓"

    def test_status_emoji_invalid(self):
        """Test emoji for invalid status defaults to unknown."""
        info = AgentInfo(agent_id="test", status="invalid_status_xyz")
        assert info.status_emoji == "❓"


class TestAgentInfoBreakDuration:
    """Tests for break-related properties on AgentInfo."""

    def test_break_time_remaining_property(self):
        """Test calculating break time remaining."""
        info = AgentInfo(
            agent_id="test",
            status="on_break",
        )
        # Set break_end in details
        end_time = datetime.now() + timedelta(seconds=30)
        info.details = {"scheduled_end": end_time.isoformat()}

        remaining = info.break_time_remaining
        # Should be approximately 30 seconds (allow 2 second margin)
        assert remaining is not None
        assert 28 <= remaining <= 32

    def test_break_time_remaining_expired(self):
        """Test break time remaining when expired."""
        info = AgentInfo(
            agent_id="test",
            status="on_break",
        )
        # Set break_end in the past
        end_time = datetime.now() - timedelta(seconds=10)
        info.details = {"scheduled_end": end_time.isoformat()}

        remaining = info.break_time_remaining
        # Should be negative
        assert remaining is not None
        assert remaining < 0

    def test_break_time_remaining_not_on_break(self):
        """Test break time remaining when not on break."""
        info = AgentInfo(agent_id="test", status="running")
        assert info.break_time_remaining is None

    def test_break_time_remaining_no_end_time(self):
        """Test break time remaining with no scheduled_end."""
        info = AgentInfo(agent_id="test", status="on_break", details={})
        assert info.break_time_remaining is None


class TestAgentDashboard:
    """Tests for AgentDashboard class."""

    def test_init(self):
        """Test dashboard initialization."""
        with patch("src.orchestrator.dashboard.AgentRunner"):
            dashboard = AgentDashboard()
            assert dashboard.agents == {}
            assert dashboard._running is False

    def test_sync_from_runner(self):
        """Test syncing agent info from the runner."""
        mock_runner = MagicMock()
        mock_process = MagicMock()
        mock_process.personal_name = "Nova"
        mock_process.work_stream_id = "2.1"
        mock_process.started_at = datetime.now()
        mock_process.state = MagicMock()
        mock_process.state.value = "running"
        mock_runner.agents = {"agent-123": mock_process}

        dashboard = AgentDashboard(runner=mock_runner)
        dashboard._sync_from_runner()

        assert "agent-123" in dashboard.agents
        assert dashboard.agents["agent-123"].personal_name == "Nova"
        assert dashboard.agents["agent-123"].work_stream_id == "2.1"
        assert dashboard.agents["agent-123"].status == "running"

    def test_clear_completed(self):
        """Test clearing completed agents."""
        mock_runner = MagicMock()
        mock_runner.agents = {}

        dashboard = AgentDashboard(runner=mock_runner)
        dashboard.agents = {
            "agent-1": AgentInfo(agent_id="agent-1", status="completed"),
            "agent-2": AgentInfo(agent_id="agent-2", status="running"),
            "agent-3": AgentInfo(agent_id="agent-3", status="failed"),
            "agent-4": AgentInfo(agent_id="agent-4", status="stopped"),
        }

        dashboard.clear_completed()

        # Only running should remain
        assert len(dashboard.agents) == 1
        assert "agent-2" in dashboard.agents

    def test_clear_completed_includes_on_break(self):
        """Test that on_break agents are NOT cleared."""
        mock_runner = MagicMock()
        mock_runner.agents = {}

        dashboard = AgentDashboard(runner=mock_runner)
        dashboard.agents = {
            "agent-1": AgentInfo(agent_id="agent-1", status="completed"),
            "agent-2": AgentInfo(agent_id="agent-2", status="on_break"),
        }

        dashboard.clear_completed()

        # on_break should remain
        assert len(dashboard.agents) == 1
        assert "agent-2" in dashboard.agents


class TestDashboardWithBreaks:
    """Tests for dashboard integration with coffee break system."""

    def test_agents_on_break_shown_separately(self):
        """Test that agents on break are tracked correctly."""
        mock_runner = MagicMock()
        mock_runner.agents = {}

        dashboard = AgentDashboard(runner=mock_runner)

        # Add agents with different statuses
        dashboard.agents = {
            "coder-1": AgentInfo(
                agent_id="coder-1",
                personal_name="Nova",
                status="on_break",
                details={"scheduled_end": (datetime.now() + timedelta(seconds=30)).isoformat()},
            ),
            "coder-2": AgentInfo(
                agent_id="coder-2",
                personal_name="Atlas",
                status="running",
            ),
        }

        # Get agents on break
        on_break = [a for a in dashboard.agents.values() if a.status == "on_break"]
        running = [a for a in dashboard.agents.values() if a.status == "running"]

        assert len(on_break) == 1
        assert on_break[0].personal_name == "Nova"
        assert len(running) == 1
        assert running[0].personal_name == "Atlas"


class TestDashboardStats:
    """Tests for dashboard statistics."""

    def test_count_by_status(self):
        """Test counting agents by status."""
        mock_runner = MagicMock()
        mock_runner.agents = {}

        dashboard = AgentDashboard(runner=mock_runner)
        dashboard.agents = {
            "a1": AgentInfo(agent_id="a1", status="running"),
            "a2": AgentInfo(agent_id="a2", status="running"),
            "a3": AgentInfo(agent_id="a3", status="completed"),
            "a4": AgentInfo(agent_id="a4", status="failed"),
            "a5": AgentInfo(agent_id="a5", status="on_break"),
            "a6": AgentInfo(agent_id="a6", status="on_break"),
        }

        running = sum(1 for a in dashboard.agents.values() if a.status in ("started", "running"))
        completed = sum(1 for a in dashboard.agents.values() if a.status == "completed")
        failed = sum(1 for a in dashboard.agents.values() if a.status == "failed")
        on_break = sum(1 for a in dashboard.agents.values() if a.status == "on_break")

        assert running == 2
        assert completed == 1
        assert failed == 1
        assert on_break == 2
