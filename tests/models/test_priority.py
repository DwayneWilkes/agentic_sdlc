"""Tests for priority and work queue models."""

import pytest

from src.models.priority import Priority, TaskPriority, WorkQueueTask


class TestPriority:
    """Test the Priority enum."""

    def test_priority_levels(self):
        """Test that all priority levels are defined."""
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"

    def test_priority_comparison(self):
        """Test that priorities can be compared for sorting."""
        # Create list of priorities in random order
        priorities = [Priority.LOW, Priority.CRITICAL, Priority.MEDIUM, Priority.HIGH]

        # Sort by priority order (CRITICAL > HIGH > MEDIUM > LOW)
        # We'll define a priority_order property for this
        sorted_priorities = sorted(priorities, key=lambda p: p.priority_order, reverse=True)

        assert sorted_priorities == [
            Priority.CRITICAL,
            Priority.HIGH,
            Priority.MEDIUM,
            Priority.LOW,
        ]


class TestTaskPriority:
    """Test the TaskPriority model."""

    def test_create_task_priority(self):
        """Test creating a task priority with default status."""
        tp = TaskPriority(
            task_id="task-1",
            priority=Priority.CRITICAL,
        )

        assert tp.task_id == "task-1"
        assert tp.priority == Priority.CRITICAL
        assert tp.assigned_agent is None
        assert tp.claimed_at is None

    def test_claim_task(self):
        """Test claiming a task."""
        tp = TaskPriority(
            task_id="task-1",
            priority=Priority.HIGH,
        )

        # Claim the task
        tp.claim("agent-123")

        assert tp.assigned_agent == "agent-123"
        assert tp.claimed_at is not None

    def test_release_task(self):
        """Test releasing a claimed task."""
        tp = TaskPriority(
            task_id="task-1",
            priority=Priority.HIGH,
        )

        # Claim then release
        tp.claim("agent-123")
        tp.release()

        assert tp.assigned_agent is None
        assert tp.claimed_at is None

    def test_cannot_claim_already_claimed_task(self):
        """Test that claiming an already claimed task raises an error."""
        tp = TaskPriority(
            task_id="task-1",
            priority=Priority.HIGH,
        )

        tp.claim("agent-123")

        with pytest.raises(ValueError, match="already claimed"):
            tp.claim("agent-456")

    def test_is_claimed(self):
        """Test checking if a task is claimed."""
        tp = TaskPriority(
            task_id="task-1",
            priority=Priority.HIGH,
        )

        assert not tp.is_claimed()

        tp.claim("agent-123")
        assert tp.is_claimed()

        tp.release()
        assert not tp.is_claimed()


class TestWorkQueueTask:
    """Test the WorkQueueTask model."""

    def test_create_work_queue_task(self):
        """Test creating a work queue task with all fields."""
        wqt = WorkQueueTask(
            id="CRITICAL-1",
            priority=Priority.CRITICAL,
            title="Fix authentication crash",
            description="Fix crash when logging in with OAuth",
            estimated_tokens=40000,
            acceptance_criteria=["All auth tests pass", "No security regressions"],
        )

        assert wqt.id == "CRITICAL-1"
        assert wqt.priority == Priority.CRITICAL
        assert wqt.title == "Fix authentication crash"
        assert wqt.estimated_tokens == 40000
        assert len(wqt.acceptance_criteria) == 2
        assert wqt.assigned_agent is None
        assert wqt.status == "pending"

    def test_create_work_queue_task_with_defaults(self):
        """Test creating a work queue task with minimal fields."""
        wqt = WorkQueueTask(
            id="LOW-1",
            priority=Priority.LOW,
            title="Update README",
        )

        assert wqt.id == "LOW-1"
        assert wqt.description == ""
        assert wqt.estimated_tokens is None
        assert wqt.acceptance_criteria == []

    def test_work_queue_task_claim(self):
        """Test claiming a work queue task."""
        wqt = WorkQueueTask(
            id="HIGH-1",
            priority=Priority.HIGH,
            title="Implement feature X",
        )

        wqt.claim("backend-maintainer")

        assert wqt.assigned_agent == "backend-maintainer"
        assert wqt.status == "claimed"

    def test_work_queue_task_release(self):
        """Test releasing a work queue task."""
        wqt = WorkQueueTask(
            id="HIGH-1",
            priority=Priority.HIGH,
            title="Implement feature X",
        )

        wqt.claim("backend-maintainer")
        wqt.release()

        assert wqt.assigned_agent is None
        assert wqt.status == "pending"

    def test_work_queue_task_complete(self):
        """Test completing a work queue task."""
        wqt = WorkQueueTask(
            id="HIGH-1",
            priority=Priority.HIGH,
            title="Implement feature X",
        )

        wqt.claim("backend-maintainer")
        wqt.complete()

        assert wqt.status == "completed"
        # Assigned agent should remain set for tracking
        assert wqt.assigned_agent == "backend-maintainer"

    def test_work_queue_task_fail(self):
        """Test marking a work queue task as failed."""
        wqt = WorkQueueTask(
            id="HIGH-1",
            priority=Priority.HIGH,
            title="Implement feature X",
        )

        wqt.claim("backend-maintainer")
        wqt.fail("Agent crashed during execution")

        assert wqt.status == "failed"
        assert wqt.assigned_agent == "backend-maintainer"

    def test_to_dict(self):
        """Test converting work queue task to dictionary."""
        wqt = WorkQueueTask(
            id="CRITICAL-1",
            priority=Priority.CRITICAL,
            title="Fix authentication crash",
            estimated_tokens=40000,
            acceptance_criteria=["All auth tests pass"],
        )

        result = wqt.to_dict()

        assert result["id"] == "CRITICAL-1"
        assert result["priority"] == "critical"
        assert result["title"] == "Fix authentication crash"
        assert result["assignedAgent"] is None
        assert result["status"] == "pending"
        assert result["estimatedTokens"] == 40000
        assert result["acceptanceCriteria"] == ["All auth tests pass"]

    def test_from_subtask(self):
        """Test creating a WorkQueueTask from a Subtask."""
        from src.models.task import Subtask

        subtask = Subtask(
            id="subtask-1",
            description="Implement login endpoint",
            metadata={
                "priority": "high",
                "estimated_tokens": 15000,
                "acceptance_criteria": ["Endpoint returns 200", "Auth token is valid"],
            },
        )

        wqt = WorkQueueTask.from_subtask(subtask)

        assert wqt.id == "subtask-1"
        assert wqt.priority == Priority.HIGH
        assert wqt.title == "Implement login endpoint"
        assert wqt.estimated_tokens == 15000
        assert len(wqt.acceptance_criteria) == 2

    def test_from_subtask_with_defaults(self):
        """Test creating a WorkQueueTask from a Subtask with minimal metadata."""
        from src.models.task import Subtask

        subtask = Subtask(
            id="subtask-2",
            description="Write tests",
        )

        wqt = WorkQueueTask.from_subtask(subtask)

        assert wqt.id == "subtask-2"
        assert wqt.priority == Priority.MEDIUM  # Default priority
        assert wqt.title == "Write tests"
        assert wqt.estimated_tokens is None
        assert wqt.acceptance_criteria == []
