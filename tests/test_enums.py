"""Tests for core enumerations."""

from src.models.enums import AgentStatus, TaskStatus, TaskType


class TestTaskStatus:
    """Test TaskStatus enumeration."""

    def test_task_status_values(self):
        """Test that all expected task status values exist."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_count(self):
        """Test that we have the expected number of statuses."""
        assert len(TaskStatus) == 6

    def test_task_status_membership(self):
        """Test enum membership checks."""
        assert "pending" in [s.value for s in TaskStatus]
        assert "in_progress" in [s.value for s in TaskStatus]
        assert "invalid_status" not in [s.value for s in TaskStatus]


class TestAgentStatus:
    """Test AgentStatus enumeration."""

    def test_agent_status_values(self):
        """Test that all expected agent status values exist."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.WORKING.value == "working"
        assert AgentStatus.BLOCKED.value == "blocked"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"

    def test_agent_status_count(self):
        """Test that we have the expected number of statuses."""
        assert len(AgentStatus) == 5

    def test_agent_status_membership(self):
        """Test enum membership checks."""
        assert "idle" in [s.value for s in AgentStatus]
        assert "working" in [s.value for s in AgentStatus]
        assert "invalid_status" not in [s.value for s in AgentStatus]


class TestTaskType:
    """Test TaskType enumeration."""

    def test_task_type_values(self):
        """Test that all expected task type values exist."""
        assert TaskType.SOFTWARE.value == "software"
        assert TaskType.RESEARCH.value == "research"
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.CREATIVE.value == "creative"
        assert TaskType.HYBRID.value == "hybrid"

    def test_task_type_count(self):
        """Test that we have the expected number of task types."""
        assert len(TaskType) == 5

    def test_task_type_membership(self):
        """Test enum membership checks."""
        assert "software" in [t.value for t in TaskType]
        assert "research" in [t.value for t in TaskType]
        assert "invalid_type" not in [t.value for t in TaskType]
