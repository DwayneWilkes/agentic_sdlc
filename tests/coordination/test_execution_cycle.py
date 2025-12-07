"""
Tests for execution cycle management.

Tests cover:
- ExecutionCycle data model
- CycleCheckpoint mechanism
- CycleBudgetTracker
- ExecutionCycleManager lifecycle
"""

import time
from datetime import UTC, datetime, timedelta

import pytest

from src.coordination.execution_cycle import (
    CycleBudgetTracker,
    CycleCheckpoint,
    CycleStatus,
    CycleTerminationReason,
    ExecutionCycle,
    ExecutionCycleManager,
    ExecutionDecision,
)


class TestExecutionCycle:
    """Test ExecutionCycle data model."""

    def test_create_cycle(self):
        """Test basic cycle creation."""
        cycle = ExecutionCycle(
            cycle_id="cycle-1",
            agent_id="agent-1",
            task_id="task-1",
            start_time=datetime.now(UTC),
            duration_seconds=1800,  # 30 minutes
        )
        assert cycle.cycle_id == "cycle-1"
        assert cycle.agent_id == "agent-1"
        assert cycle.task_id == "task-1"
        assert cycle.status == CycleStatus.PENDING
        assert cycle.duration_seconds == 1800

    def test_cycle_elapsed_time(self):
        """Test elapsed time calculation."""
        start = datetime.now(UTC) - timedelta(seconds=100)
        cycle = ExecutionCycle(
            cycle_id="cycle-1",
            agent_id="agent-1",
            task_id="task-1",
            start_time=start,
            duration_seconds=1800,
        )
        elapsed = cycle.elapsed_seconds()
        assert 99 <= elapsed <= 101  # Allow small variance

    def test_cycle_remaining_time(self):
        """Test remaining time calculation."""
        start = datetime.now(UTC) - timedelta(seconds=100)
        cycle = ExecutionCycle(
            cycle_id="cycle-1",
            agent_id="agent-1",
            task_id="task-1",
            start_time=start,
            duration_seconds=1800,
        )
        remaining = cycle.remaining_seconds()
        assert 1699 <= remaining <= 1701  # Allow small variance

    def test_cycle_should_checkpoint(self):
        """Test checkpoint timing (at 50% and 100% of duration)."""
        start = datetime.now(UTC) - timedelta(seconds=900)  # 15 min elapsed
        cycle = ExecutionCycle(
            cycle_id="cycle-1",
            agent_id="agent-1",
            task_id="task-1",
            start_time=start,
            duration_seconds=1800,  # 30 min total
        )
        # At 50% mark, should checkpoint
        assert cycle.should_checkpoint()

    def test_cycle_is_expired(self):
        """Test cycle expiration detection."""
        start = datetime.now(UTC) - timedelta(seconds=1900)  # Expired
        cycle = ExecutionCycle(
            cycle_id="cycle-1",
            agent_id="agent-1",
            task_id="task-1",
            start_time=start,
            duration_seconds=1800,
        )
        assert cycle.is_expired()

    def test_cycle_serialization(self):
        """Test JSON serialization/deserialization."""
        cycle = ExecutionCycle(
            cycle_id="cycle-1",
            agent_id="agent-1",
            task_id="task-1",
            start_time=datetime.now(UTC),
            duration_seconds=1800,
        )
        json_str = cycle.to_json()
        restored = ExecutionCycle.from_json(json_str)
        assert restored.cycle_id == cycle.cycle_id
        assert restored.agent_id == cycle.agent_id
        assert restored.task_id == cycle.task_id
        assert restored.duration_seconds == cycle.duration_seconds


class TestCycleCheckpoint:
    """Test CycleCheckpoint mechanism."""

    def test_create_checkpoint(self):
        """Test checkpoint creation."""
        checkpoint = CycleCheckpoint(
            cycle_id="cycle-1",
            timestamp=datetime.now(UTC),
            state_snapshot={"key": "value"},
            progress_metrics={"tests_passed": 10, "tests_failed": 2},
        )
        assert checkpoint.cycle_id == "cycle-1"
        assert checkpoint.state_snapshot == {"key": "value"}
        assert checkpoint.progress_metrics["tests_passed"] == 10

    def test_checkpoint_serialization(self):
        """Test checkpoint save/restore."""
        checkpoint = CycleCheckpoint(
            cycle_id="cycle-1",
            timestamp=datetime.now(UTC),
            state_snapshot={"files_modified": ["file1.py", "file2.py"]},
            progress_metrics={"lines_changed": 50},
        )
        json_str = checkpoint.to_json()
        restored = CycleCheckpoint.from_json(json_str)
        assert restored.cycle_id == checkpoint.cycle_id
        assert restored.state_snapshot == checkpoint.state_snapshot
        assert restored.progress_metrics == checkpoint.progress_metrics

    def test_checkpoint_with_files_changed(self):
        """Test checkpoint tracks files changed."""
        checkpoint = CycleCheckpoint(
            cycle_id="cycle-1",
            timestamp=datetime.now(UTC),
            state_snapshot={},
            progress_metrics={},
            files_changed=["src/core/module.py", "tests/test_module.py"],
        )
        assert len(checkpoint.files_changed) == 2
        assert "src/core/module.py" in checkpoint.files_changed


class TestCycleBudgetTracker:
    """Test CycleBudgetTracker."""

    def test_create_budget_tracker(self):
        """Test budget tracker initialization."""
        tracker = CycleBudgetTracker(
            max_tokens=100000,
            max_time_seconds=1800,
            max_api_calls=50,
        )
        assert tracker.max_tokens == 100000
        assert tracker.tokens_used == 0
        assert tracker.time_used_seconds == 0
        assert tracker.api_calls_made == 0

    def test_track_token_usage(self):
        """Test token usage tracking."""
        tracker = CycleBudgetTracker(max_tokens=1000)
        tracker.add_tokens(300)
        assert tracker.tokens_used == 300
        assert tracker.get_token_percentage() == 30.0

    def test_track_time_usage(self):
        """Test time usage tracking."""
        tracker = CycleBudgetTracker(max_time_seconds=1800)
        tracker.add_time(600)
        assert tracker.time_used_seconds == 600
        assert tracker.get_time_percentage() == pytest.approx(33.33, rel=0.01)

    def test_track_api_calls(self):
        """Test API call tracking."""
        tracker = CycleBudgetTracker(max_api_calls=50)
        tracker.add_api_call()
        tracker.add_api_call()
        assert tracker.api_calls_made == 2

    def test_budget_exceeded_tokens(self):
        """Test budget exceeded detection for tokens."""
        tracker = CycleBudgetTracker(max_tokens=1000)
        tracker.add_tokens(1100)
        assert tracker.is_budget_exceeded()

    def test_budget_exceeded_time(self):
        """Test budget exceeded detection for time."""
        tracker = CycleBudgetTracker(max_time_seconds=100)
        tracker.add_time(150)
        assert tracker.is_budget_exceeded()

    def test_budget_exceeded_api_calls(self):
        """Test budget exceeded detection for API calls."""
        tracker = CycleBudgetTracker(max_api_calls=10)
        for _ in range(11):
            tracker.add_api_call()
        assert tracker.is_budget_exceeded()

    def test_approaching_limit(self):
        """Test approaching limit detection (>80%)."""
        tracker = CycleBudgetTracker(max_tokens=1000)
        tracker.add_tokens(850)
        assert tracker.is_approaching_limit()

    def test_budget_summary(self):
        """Test budget summary generation."""
        tracker = CycleBudgetTracker(
            max_tokens=1000,
            max_time_seconds=1800,
            max_api_calls=50,
        )
        tracker.add_tokens(500)
        tracker.add_time(900)
        tracker.add_api_call()

        summary = tracker.get_budget_summary()
        assert summary["tokens"]["used"] == 500
        assert summary["tokens"]["percentage"] == 50.0
        assert summary["time"]["used"] == 900
        assert summary["api_calls"]["used"] == 1


class TestExecutionCycleManager:
    """Test ExecutionCycleManager."""

    def test_create_manager(self):
        """Test manager initialization."""
        manager = ExecutionCycleManager(
            default_duration_seconds=1800,
            checkpoint_interval_seconds=900,
        )
        assert manager.default_duration_seconds == 1800
        assert manager.checkpoint_interval_seconds == 900

    def test_start_cycle(self):
        """Test starting a new cycle."""
        manager = ExecutionCycleManager()
        cycle = manager.start_cycle(
            agent_id="agent-1",
            task_id="task-1",
            duration_seconds=1800,
        )
        assert cycle.status == CycleStatus.RUNNING
        assert cycle.agent_id == "agent-1"
        assert cycle.task_id == "task-1"

    def test_save_checkpoint(self):
        """Test checkpoint saving."""
        manager = ExecutionCycleManager()
        cycle = manager.start_cycle(agent_id="agent-1", task_id="task-1")

        checkpoint = manager.save_checkpoint(
            cycle_id=cycle.cycle_id,
            state_snapshot={"current_file": "test.py"},
            progress_metrics={"lines": 100},
        )
        assert checkpoint.cycle_id == cycle.cycle_id
        assert checkpoint.state_snapshot["current_file"] == "test.py"

    def test_load_checkpoint(self):
        """Test checkpoint loading."""
        manager = ExecutionCycleManager()
        cycle = manager.start_cycle(agent_id="agent-1", task_id="task-1")

        # Save a checkpoint
        saved = manager.save_checkpoint(
            cycle_id=cycle.cycle_id,
            state_snapshot={"var": "value"},
            progress_metrics={"progress": 0.5},
        )

        # Load it back
        loaded = manager.load_latest_checkpoint(cycle.cycle_id)
        assert loaded is not None
        assert loaded.state_snapshot == saved.state_snapshot

    def test_complete_cycle(self):
        """Test completing a cycle."""
        manager = ExecutionCycleManager()
        cycle = manager.start_cycle(agent_id="agent-1", task_id="task-1")

        manager.complete_cycle(
            cycle_id=cycle.cycle_id,
            termination_reason=CycleTerminationReason.TASK_COMPLETED,
        )

        updated = manager.get_cycle(cycle.cycle_id)
        assert updated is not None
        assert updated.status == CycleStatus.COMPLETED
        assert updated.termination_reason == CycleTerminationReason.TASK_COMPLETED

    def test_cycle_timeout(self):
        """Test cycle timeout handling."""
        manager = ExecutionCycleManager()
        # Create cycle with very short duration
        cycle = manager.start_cycle(
            agent_id="agent-1",
            task_id="task-1",
            duration_seconds=1,
        )
        time.sleep(1.1)

        # Check if expired
        decision = manager.check_cycle_status(cycle.cycle_id)
        assert decision == ExecutionDecision.TERMINATE_TIMEOUT

    def test_graceful_termination(self):
        """Test graceful cycle termination saves state."""
        manager = ExecutionCycleManager()
        cycle = manager.start_cycle(agent_id="agent-1", task_id="task-1")

        # Terminate gracefully
        checkpoint = manager.graceful_terminate(
            cycle_id=cycle.cycle_id,
            state_snapshot={"final_state": "saved"},
            progress_metrics={"completion": 0.75},
        )

        assert checkpoint is not None
        assert checkpoint.state_snapshot["final_state"] == "saved"

        # Cycle should be completed
        updated = manager.get_cycle(cycle.cycle_id)
        assert updated is not None
        assert updated.status == CycleStatus.COMPLETED

    def test_preemption(self):
        """Test cycle preemption for higher priority work."""
        manager = ExecutionCycleManager()
        cycle = manager.start_cycle(agent_id="agent-1", task_id="task-1")

        # Preempt for higher priority task
        checkpoint = manager.preempt_cycle(
            cycle_id=cycle.cycle_id,
            reason="Higher priority task available",
            state_snapshot={"interrupted_at": "line 42"},
        )

        assert checkpoint is not None
        updated = manager.get_cycle(cycle.cycle_id)
        assert updated is not None
        assert updated.status == CycleStatus.PREEMPTED
        assert updated.termination_reason == CycleTerminationReason.PREEMPTED

    def test_resume_from_checkpoint(self):
        """Test resuming a cycle from a checkpoint."""
        manager = ExecutionCycleManager()
        cycle1 = manager.start_cycle(agent_id="agent-1", task_id="task-1")

        # Save checkpoint and preempt
        manager.save_checkpoint(
            cycle_id=cycle1.cycle_id,
            state_snapshot={"progress": "halfway"},
            progress_metrics={"done": 50},
        )
        manager.preempt_cycle(
            cycle_id=cycle1.cycle_id,
            reason="Testing resume",
            state_snapshot={"progress": "halfway"},
        )

        # Resume from checkpoint
        checkpoint = manager.load_latest_checkpoint(cycle1.cycle_id)
        assert checkpoint is not None

        cycle2 = manager.start_cycle(
            agent_id="agent-1",
            task_id="task-1",
            resume_from_checkpoint=checkpoint,
        )
        assert cycle2.status == CycleStatus.RUNNING

    def test_budget_tracking_integration(self):
        """Test budget tracking integration with cycle."""
        manager = ExecutionCycleManager()
        cycle = manager.start_cycle(
            agent_id="agent-1",
            task_id="task-1",
            max_tokens=1000,
        )

        # Track usage
        manager.track_token_usage(cycle.cycle_id, 500)
        assert cycle.budget_tracker.tokens_used == 500

        # Check if approaching limit
        manager.track_token_usage(cycle.cycle_id, 400)
        decision = manager.check_cycle_status(cycle.cycle_id)
        assert decision == ExecutionDecision.CONTINUE_WITH_WARNING

    def test_cycle_history(self):
        """Test cycle history tracking."""
        manager = ExecutionCycleManager()
        cycle1 = manager.start_cycle(agent_id="agent-1", task_id="task-1")
        manager.complete_cycle(
            cycle_id=cycle1.cycle_id,
            termination_reason=CycleTerminationReason.TASK_COMPLETED,
        )

        cycle2 = manager.start_cycle(agent_id="agent-1", task_id="task-2")

        history = manager.get_agent_cycle_history("agent-1")
        assert len(history) == 2
        assert history[0].cycle_id == cycle1.cycle_id
        assert history[1].cycle_id == cycle2.cycle_id
