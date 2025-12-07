"""
Tests for Attention Schema (Phase 10.3) - Written FIRST (TDD)

This test suite defines the contract for attention tracking before implementation.
"""

import time
from datetime import datetime, timedelta

import pytest

from src.core.attention_schema import (
    AttentionSchema,
    AttentionState,
    BudgetStatus,
    DriftSeverity,
    PriorityLevel,
    SignalType,
)


class TestBasicAttentionTracking:
    """Tests for basic attention state tracking."""

    def test_set_primary_focus(self):
        """Test setting initial primary focus."""
        schema = AttentionSchema()
        schema.set_focus("Fix authentication bug", budget_minutes=30.0)

        state = schema.get_attention_state()
        assert state.primary_focus == "Fix authentication bug"
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_track_focus_duration(self):
        """Test measuring time spent on current focus."""
        schema = AttentionSchema()
        schema.set_focus("Build feature X", budget_minutes=20.0)

        # Simulate some time passing
        time.sleep(0.1)

        state = schema.get_attention_state()
        assert state.focus_duration > timedelta(0)
        assert state.focus_duration < timedelta(seconds=1)  # Should be ~0.1s

    def test_multiple_focus_levels(self):
        """Test primary, secondary, and background focus tracking."""
        schema = AttentionSchema()
        schema.set_focus("Fix bug", budget_minutes=30.0)
        schema.add_secondary_focus("Understand OAuth flow")
        schema.add_background_thread("Test coverage")
        schema.add_background_thread("Documentation")

        state = schema.get_attention_state()
        assert state.primary_focus == "Fix bug"
        assert "Understand OAuth flow" in state.secondary_focus
        assert "Test coverage" in state.background_threads
        assert "Documentation" in state.background_threads


class TestDriftDetection:
    """Tests for attention drift detection."""

    def test_detect_attention_drift(self):
        """Test detecting when focus changes unexpectedly."""
        schema = AttentionSchema()
        schema.set_focus("Fix bug in module A", budget_minutes=20.0)

        # Explicitly drift to a different task
        drift_event = schema.track_drift("Refactor entire module A")

        assert drift_event is not None
        assert drift_event.from_focus == "Fix bug in module A"
        assert drift_event.to_focus == "Refactor entire module A"
        assert drift_event.drift_time is not None

    def test_drift_severity_low(self):
        """Test low-severity drift (minor tangent)."""
        schema = AttentionSchema()
        schema.set_focus("Fix bug", budget_minutes=20.0)

        # Small, related drift
        drift = schema.track_drift("Add logging around bug fix")

        assert drift.severity == DriftSeverity.LOW

    def test_drift_severity_high(self):
        """Test high-severity drift (major scope creep)."""
        schema = AttentionSchema()
        schema.set_focus("Fix typo in comments", budget_minutes=5.0)

        # Major drift - completely different task
        drift = schema.track_drift("Rewrite authentication system")

        assert drift.severity == DriftSeverity.HIGH

    def test_drift_history_tracking(self):
        """Test recording all drift events."""
        schema = AttentionSchema()
        schema.set_focus("Task A", budget_minutes=30.0)

        schema.track_drift("Task B")
        schema.track_drift("Task C")
        schema.track_drift("Task A")  # Back to original

        history = schema.get_drift_history()
        assert len(history) == 3
        assert history[0].from_focus == "Task A"
        assert history[1].from_focus == "Task B"
        assert history[2].from_focus == "Task C"


class TestAttentionBudget:
    """Tests for attention budget tracking."""

    def test_create_attention_budget(self):
        """Test allocating time budget for a task."""
        schema = AttentionSchema()
        schema.set_focus("Build feature", budget_minutes=45.0)

        budget = schema.check_budget()
        assert budget.allocated_minutes == 45.0
        assert budget.consumed_minutes >= 0.0
        assert budget.budget_status in [BudgetStatus.UNDER, BudgetStatus.ON_TRACK]

    def test_budget_consumption(self):
        """Test tracking time spent against budget."""
        schema = AttentionSchema()
        schema.set_focus("Task X", budget_minutes=1.0)

        time.sleep(0.1)

        budget = schema.check_budget()
        assert budget.consumed_minutes > 0.0
        assert budget.consumed_minutes < 1.0  # Haven't exceeded yet

    def test_budget_exceeded_signal(self):
        """Test alert when budget is exceeded."""
        schema = AttentionSchema()
        # Set a very small budget
        schema.set_focus("Quick task", budget_minutes=0.001)  # 0.06 seconds

        time.sleep(0.1)  # Exceed the budget

        signals = schema.get_priority_signals()
        budget_signals = [s for s in signals if s.signal_type == SignalType.BUDGET_EXCEEDED]
        assert len(budget_signals) > 0
        assert budget_signals[0].priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]

    def test_budget_on_track(self):
        """Test normal budget consumption (no alerts)."""
        schema = AttentionSchema()
        schema.set_focus("Task Y", budget_minutes=10.0)

        time.sleep(0.05)

        budget = schema.check_budget()
        assert budget.budget_status in [BudgetStatus.UNDER, BudgetStatus.ON_TRACK]


class TestAttentionRedirection:
    """Tests for deliberate attention redirection."""

    def test_deliberate_redirect(self):
        """Test manually changing focus."""
        schema = AttentionSchema()
        schema.set_focus("Original task", budget_minutes=20.0)

        schema.redirect_attention("New urgent task", reason="Critical bug found")

        state = schema.get_attention_state()
        assert state.primary_focus == "New urgent task"

    def test_redirect_with_reason(self):
        """Test documenting why attention was redirected."""
        schema = AttentionSchema()
        schema.set_focus("Task A", budget_minutes=15.0)

        schema.redirect_attention("Task B", reason="Dependency blocker")

        # Redirection should be in history with reason
        history = schema.get_attention_history()
        assert len(history) > 0
        # The last entry should have the redirect reason in metadata
        last_entry = history[-1]
        assert "redirect_reason" in last_entry.metadata
        assert last_entry.metadata["redirect_reason"] == "Dependency blocker"

    def test_return_to_primary_task(self):
        """Test coming back from a tangent to original task."""
        schema = AttentionSchema()
        original_task = "Build authentication"
        schema.set_focus(original_task, budget_minutes=30.0)

        # Drift to tangent
        schema.track_drift("Research OAuth libraries")

        # Return to original
        schema.redirect_attention(original_task, reason="Tangent complete")

        state = schema.get_attention_state()
        assert state.primary_focus == original_task


class TestThreadPersistence:
    """Tests for persisting pending threads."""

    def test_persist_pending_thread(self):
        """Test saving a thread for later."""
        schema = AttentionSchema()
        schema.set_focus("Current task", budget_minutes=20.0)

        schema.persist_thread("Remember to update docs")
        schema.persist_thread("Add test coverage")

        threads = schema.get_pending_threads()
        assert "Remember to update docs" in threads
        assert "Add test coverage" in threads

    def test_retrieve_pending_threads(self):
        """Test getting all saved threads."""
        schema = AttentionSchema()
        schema.persist_thread("Thread 1")
        schema.persist_thread("Thread 2")
        schema.persist_thread("Thread 3")

        threads = schema.get_pending_threads()
        assert len(threads) == 3

    def test_thread_priority_ordering(self):
        """Test ordering threads by importance."""
        schema = AttentionSchema()
        schema.persist_thread("Low priority task", priority=PriorityLevel.LOW)
        schema.persist_thread("Critical task", priority=PriorityLevel.CRITICAL)
        schema.persist_thread("Medium task", priority=PriorityLevel.MEDIUM)

        threads = schema.get_pending_threads(ordered=True)
        # Should be ordered by priority (CRITICAL first)
        assert "Critical" in threads[0]


class TestPrioritySignals:
    """Tests for attention priority signals."""

    def test_time_limit_signal(self):
        """Test alert when approaching time limit."""
        schema = AttentionSchema()
        schema.set_focus("Task with deadline", budget_minutes=1.0)

        time.sleep(0.06)  # Use 60% of budget (1 min = 60s, 60% = 36s but we sleep 0.06s)

        signals = schema.get_priority_signals()
        # Should have signals (even if budget not exceeded, might warn)
        assert isinstance(signals, list)

    def test_drift_detection_signal(self):
        """Test alert when drift is detected."""
        schema = AttentionSchema()
        schema.set_focus("Original task", budget_minutes=20.0)

        # Create a high-severity drift
        schema.track_drift("Completely different task")

        signals = schema.get_priority_signals()
        drift_signals = [s for s in signals if s.signal_type == SignalType.DRIFT_DETECTED]
        assert len(drift_signals) > 0

    def test_signal_priority_ordering(self):
        """Test critical signals appear first."""
        schema = AttentionSchema()
        schema.set_focus("Task", budget_minutes=0.001)  # Will exceed immediately

        time.sleep(0.1)

        # Create multiple signals
        schema.track_drift("Different task")  # Drift signal

        signals = schema.get_priority_signals()
        # Signals should be ordered by priority
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                assert signals[i].priority.value >= signals[i + 1].priority.value


class TestIntegration:
    """Integration tests for complete attention workflow."""

    def test_full_attention_workflow(self):
        """Test end-to-end attention tracking scenario."""
        schema = AttentionSchema()

        # 1. Start with a task
        schema.set_focus("Fix bug #123", budget_minutes=30.0)

        # 2. Add secondary focus
        schema.add_secondary_focus("Understand authentication flow")

        # 3. Add background threads
        schema.persist_thread("Update tests after fix")

        # 4. Drift to a tangent
        drift = schema.track_drift("Refactor auth module")
        assert drift.severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH]

        # 5. Redirect back
        schema.redirect_attention("Fix bug #123", reason="Refactor can wait")

        # 6. Check state
        state = schema.get_attention_state()
        assert state.primary_focus == "Fix bug #123"

        # 7. Check signals
        signals = schema.get_priority_signals()
        assert isinstance(signals, list)

    def test_attention_state_snapshot(self):
        """Test getting current attention state snapshot."""
        schema = AttentionSchema()
        schema.set_focus("Task A", budget_minutes=25.0)
        schema.add_secondary_focus("Task B")
        schema.persist_thread("Task C")

        state = schema.get_attention_state()
        assert isinstance(state, AttentionState)
        assert state.primary_focus == "Task A"
        assert len(state.secondary_focus) > 0
        assert len(state.background_threads) > 0
        assert state.focus_duration >= timedelta(0)

    def test_attention_persistence(self):
        """Test save/load attention state."""
        schema = AttentionSchema()
        schema.set_focus("Persistent task", budget_minutes=40.0)
        schema.add_secondary_focus("Secondary work")
        schema.persist_thread("Remember this")

        # Save state
        saved_state = schema.save_state()
        assert saved_state is not None

        # Create new schema and restore
        new_schema = AttentionSchema()
        new_schema.restore_state(saved_state)

        restored_state = new_schema.get_attention_state()
        assert restored_state.primary_focus == "Persistent task"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_no_focus_set(self):
        """Test behavior when no focus has been set."""
        schema = AttentionSchema()

        state = schema.get_attention_state()
        assert state.primary_focus is None or state.primary_focus == ""

    def test_zero_budget(self):
        """Test handling of zero budget."""
        schema = AttentionSchema()
        schema.set_focus("Instant task", budget_minutes=0.0)

        budget = schema.check_budget()
        assert budget.budget_status == BudgetStatus.OVER

    def test_negative_budget(self):
        """Test that negative budgets are rejected."""
        schema = AttentionSchema()

        with pytest.raises(ValueError):
            schema.set_focus("Task", budget_minutes=-10.0)

    def test_empty_task_name(self):
        """Test handling empty task names."""
        schema = AttentionSchema()

        with pytest.raises(ValueError):
            schema.set_focus("", budget_minutes=10.0)

    def test_thread_safety(self):
        """Test concurrent attention updates."""
        import threading

        schema = AttentionSchema()
        schema.set_focus("Concurrent task", budget_minutes=30.0)

        errors = []

        def update_focus():
            try:
                for i in range(10):
                    schema.add_secondary_focus(f"Secondary {i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_focus) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"
        state = schema.get_attention_state()
        assert len(state.secondary_focus) > 0
