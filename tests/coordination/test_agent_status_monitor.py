"""
Tests for Agent Status Monitor - Phase 6.1

Tests cover:
1. Agent state tracking (idle, working, blocked, completed, failed)
2. Resource consumption monitoring (time, tokens, API calls)
3. Stuck agent detection (no progress for threshold time)
4. Status snapshots and history
5. Multi-agent monitoring
6. Edge cases (rapid state changes, concurrent updates)
"""

import time
from datetime import datetime

import pytest

from src.coordination.agent_status_monitor import (
    AgentResourceMetrics,
    AgentStatusMonitor,
    AgentStatusSnapshot,
    StuckAgentDetection,
)
from src.models.enums import AgentStatus

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def monitor():
    """Create a fresh AgentStatusMonitor for each test."""
    return AgentStatusMonitor(stuck_threshold_seconds=10.0)


@pytest.fixture
def monitor_short_threshold():
    """Create monitor with short stuck threshold for testing."""
    return AgentStatusMonitor(stuck_threshold_seconds=0.1)


# ============================================================================
# Test Agent State Tracking
# ============================================================================


def test_track_agent_state_transition(monitor):
    """Test tracking basic state transitions."""
    agent_id = "test-agent-1"

    # Initial state
    monitor.update_status(agent_id, AgentStatus.IDLE)
    snapshot = monitor.get_status(agent_id)

    assert snapshot is not None
    assert snapshot.agent_id == agent_id
    assert snapshot.status == AgentStatus.IDLE
    assert snapshot.current_task is None

    # Transition to working
    monitor.update_status(agent_id, AgentStatus.WORKING, current_task="Build feature X")
    snapshot = monitor.get_status(agent_id)

    assert snapshot.status == AgentStatus.WORKING
    assert snapshot.current_task == "Build feature X"

    # Transition to completed
    monitor.update_status(agent_id, AgentStatus.COMPLETED)
    snapshot = monitor.get_status(agent_id)

    assert snapshot.status == AgentStatus.COMPLETED


def test_track_multiple_agents(monitor):
    """Test monitoring multiple agents simultaneously."""
    agents = ["agent-1", "agent-2", "agent-3"]

    # Set different states
    monitor.update_status(agents[0], AgentStatus.IDLE)
    monitor.update_status(agents[1], AgentStatus.WORKING, current_task="Task A")
    monitor.update_status(agents[2], AgentStatus.BLOCKED)

    # Verify each agent tracked correctly
    snapshot_1 = monitor.get_status(agents[0])
    snapshot_2 = monitor.get_status(agents[1])
    snapshot_3 = monitor.get_status(agents[2])

    assert snapshot_1.status == AgentStatus.IDLE
    assert snapshot_2.status == AgentStatus.WORKING
    assert snapshot_2.current_task == "Task A"
    assert snapshot_3.status == AgentStatus.BLOCKED


def test_get_all_agents(monitor):
    """Test retrieving all monitored agents."""
    monitor.update_status("agent-1", AgentStatus.IDLE)
    monitor.update_status("agent-2", AgentStatus.WORKING)
    monitor.update_status("agent-3", AgentStatus.COMPLETED)

    all_snapshots = monitor.get_all_statuses()

    assert len(all_snapshots) == 3
    agent_ids = {s.agent_id for s in all_snapshots}
    assert agent_ids == {"agent-1", "agent-2", "agent-3"}


def test_filter_agents_by_status(monitor):
    """Test filtering agents by status."""
    monitor.update_status("agent-1", AgentStatus.IDLE)
    monitor.update_status("agent-2", AgentStatus.WORKING)
    monitor.update_status("agent-3", AgentStatus.WORKING)
    monitor.update_status("agent-4", AgentStatus.COMPLETED)

    working_agents = monitor.get_agents_by_status(AgentStatus.WORKING)

    assert len(working_agents) == 2
    working_ids = {s.agent_id for s in working_agents}
    assert working_ids == {"agent-2", "agent-3"}


def test_unknown_agent_returns_none(monitor):
    """Test that querying unknown agent returns None."""
    snapshot = monitor.get_status("unknown-agent")
    assert snapshot is None


# ============================================================================
# Test Resource Consumption Monitoring
# ============================================================================


def test_track_resource_time(monitor):
    """Test tracking time consumption."""
    agent_id = "agent-1"

    # Start working
    monitor.update_status(agent_id, AgentStatus.WORKING)
    time.sleep(0.05)  # 50ms

    snapshot = monitor.get_status(agent_id)
    assert snapshot.resources.time_seconds >= 0.04  # Allow some variance


def test_track_resource_tokens(monitor):
    """Test tracking token consumption."""
    agent_id = "agent-1"

    monitor.update_status(agent_id, AgentStatus.WORKING)
    monitor.record_resource_usage(agent_id, tokens=1500)
    monitor.record_resource_usage(agent_id, tokens=2500)

    snapshot = monitor.get_status(agent_id)
    assert snapshot.resources.tokens == 4000


def test_track_resource_api_calls(monitor):
    """Test tracking API call consumption."""
    agent_id = "agent-1"

    monitor.update_status(agent_id, AgentStatus.WORKING)
    monitor.record_resource_usage(agent_id, api_calls=3)
    monitor.record_resource_usage(agent_id, api_calls=2)

    snapshot = monitor.get_status(agent_id)
    assert snapshot.resources.api_calls == 5


def test_track_multiple_resources_at_once(monitor):
    """Test tracking multiple resource types simultaneously."""
    agent_id = "agent-1"

    monitor.update_status(agent_id, AgentStatus.WORKING)
    monitor.record_resource_usage(agent_id, tokens=1000, api_calls=2)

    snapshot = monitor.get_status(agent_id)
    assert snapshot.resources.tokens == 1000
    assert snapshot.resources.api_calls == 2


def test_resource_tracking_across_state_transitions(monitor):
    """Test that resources accumulate across state transitions."""
    agent_id = "agent-1"

    # IDLE -> WORKING
    monitor.update_status(agent_id, AgentStatus.IDLE)
    monitor.record_resource_usage(agent_id, tokens=500)

    # WORKING -> BLOCKED
    monitor.update_status(agent_id, AgentStatus.WORKING)
    monitor.record_resource_usage(agent_id, tokens=1000)

    # BLOCKED -> WORKING
    monitor.update_status(agent_id, AgentStatus.BLOCKED)
    monitor.record_resource_usage(agent_id, tokens=300)

    # Verify accumulation
    snapshot = monitor.get_status(agent_id)
    assert snapshot.resources.tokens == 1800


# ============================================================================
# Test Stuck Agent Detection
# ============================================================================


def test_detect_stuck_agent(monitor_short_threshold):
    """Test detecting an agent that hasn't made progress."""
    agent_id = "agent-1"

    # Start working
    monitor_short_threshold.update_status(agent_id, AgentStatus.WORKING, current_task="Task A")

    # Wait for stuck threshold
    time.sleep(0.15)

    # Check for stuck agents
    stuck_agents = monitor_short_threshold.detect_stuck_agents()

    assert len(stuck_agents) == 1
    assert stuck_agents[0].agent_id == agent_id
    assert stuck_agents[0].seconds_stuck >= 0.1


def test_progress_update_prevents_stuck_detection(monitor_short_threshold):
    """Test that reporting progress prevents stuck detection."""
    agent_id = "agent-1"

    # Start working
    monitor_short_threshold.update_status(agent_id, AgentStatus.WORKING, current_task="Task A")

    # Wait a bit
    time.sleep(0.08)

    # Report progress before threshold
    monitor_short_threshold.record_progress(agent_id, "Made progress on subtask 1")

    # Wait again
    time.sleep(0.08)

    # Should not be stuck because we reported progress
    stuck_agents = monitor_short_threshold.detect_stuck_agents()
    assert len(stuck_agents) == 0


def test_stuck_detection_ignores_idle_agents(monitor_short_threshold):
    """Test that idle agents are not flagged as stuck."""
    agent_id = "agent-1"

    # Set to idle
    monitor_short_threshold.update_status(agent_id, AgentStatus.IDLE)

    # Wait past threshold
    time.sleep(0.15)

    # Should not detect as stuck
    stuck_agents = monitor_short_threshold.detect_stuck_agents()
    assert len(stuck_agents) == 0


def test_stuck_detection_ignores_completed_agents(monitor_short_threshold):
    """Test that completed agents are not flagged as stuck."""
    agent_id = "agent-1"

    # Start working then complete
    monitor_short_threshold.update_status(agent_id, AgentStatus.WORKING)
    time.sleep(0.05)
    monitor_short_threshold.update_status(agent_id, AgentStatus.COMPLETED)

    # Wait past threshold
    time.sleep(0.15)

    # Should not detect as stuck
    stuck_agents = monitor_short_threshold.detect_stuck_agents()
    assert len(stuck_agents) == 0


def test_multiple_stuck_agents(monitor_short_threshold):
    """Test detecting multiple stuck agents."""
    monitor_short_threshold.update_status("agent-1", AgentStatus.WORKING, current_task="Task A")
    monitor_short_threshold.update_status("agent-2", AgentStatus.WORKING, current_task="Task B")
    monitor_short_threshold.update_status("agent-3", AgentStatus.IDLE)

    # Wait past threshold
    time.sleep(0.15)

    stuck_agents = monitor_short_threshold.detect_stuck_agents()

    assert len(stuck_agents) == 2
    stuck_ids = {s.agent_id for s in stuck_agents}
    assert stuck_ids == {"agent-1", "agent-2"}


# ============================================================================
# Test Status Snapshots and History
# ============================================================================


def test_snapshot_contains_all_fields(monitor):
    """Test that status snapshots contain all required fields."""
    agent_id = "agent-1"

    monitor.update_status(agent_id, AgentStatus.WORKING, current_task="Build X")
    monitor.record_resource_usage(agent_id, tokens=1000, api_calls=5)

    snapshot = monitor.get_status(agent_id)

    assert snapshot.agent_id == agent_id
    assert snapshot.status == AgentStatus.WORKING
    assert snapshot.current_task == "Build X"
    assert isinstance(snapshot.last_update, datetime)
    assert isinstance(snapshot.resources, AgentResourceMetrics)
    assert snapshot.resources.tokens == 1000
    assert snapshot.resources.api_calls == 5


def test_get_status_history(monitor):
    """Test retrieving agent status history."""
    agent_id = "agent-1"

    # Series of state transitions
    monitor.update_status(agent_id, AgentStatus.IDLE)
    time.sleep(0.01)
    monitor.update_status(agent_id, AgentStatus.WORKING, current_task="Task A")
    time.sleep(0.01)
    monitor.update_status(agent_id, AgentStatus.BLOCKED)
    time.sleep(0.01)
    monitor.update_status(agent_id, AgentStatus.WORKING, current_task="Task A")
    time.sleep(0.01)
    monitor.update_status(agent_id, AgentStatus.COMPLETED)

    # Get history
    history = monitor.get_status_history(agent_id)

    assert len(history) == 5
    assert history[0].status == AgentStatus.IDLE
    assert history[1].status == AgentStatus.WORKING
    assert history[2].status == AgentStatus.BLOCKED
    assert history[3].status == AgentStatus.WORKING
    assert history[4].status == AgentStatus.COMPLETED


def test_status_history_limit(monitor):
    """Test that history is limited to prevent unbounded growth."""
    agent_id = "agent-1"

    # Create many state transitions (more than default limit)
    for i in range(150):
        status = AgentStatus.WORKING if i % 2 == 0 else AgentStatus.IDLE
        monitor.update_status(agent_id, status)

    history = monitor.get_status_history(agent_id)

    # Should be capped at 100 (or configured limit)
    assert len(history) <= 100


def test_empty_history_for_unknown_agent(monitor):
    """Test that unknown agent has empty history."""
    history = monitor.get_status_history("unknown-agent")
    assert history == []


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_rapid_state_changes(monitor):
    """Test handling rapid state transitions."""
    agent_id = "agent-1"

    # Rapid transitions
    for _ in range(20):
        monitor.update_status(agent_id, AgentStatus.WORKING)
        monitor.update_status(agent_id, AgentStatus.IDLE)

    # Should track final state correctly
    snapshot = monitor.get_status(agent_id)
    assert snapshot.status == AgentStatus.IDLE


def test_concurrent_resource_updates(monitor):
    """Test that concurrent resource updates are handled correctly."""
    agent_id = "agent-1"

    monitor.update_status(agent_id, AgentStatus.WORKING)

    # Simulate concurrent updates
    import threading

    def record_tokens():
        for _ in range(10):
            monitor.record_resource_usage(agent_id, tokens=100)

    def record_api_calls():
        for _ in range(10):
            monitor.record_resource_usage(agent_id, api_calls=1)

    thread1 = threading.Thread(target=record_tokens)
    thread2 = threading.Thread(target=record_api_calls)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    snapshot = monitor.get_status(agent_id)
    assert snapshot.resources.tokens == 1000
    assert snapshot.resources.api_calls == 10


def test_reset_agent_tracking(monitor):
    """Test resetting/removing an agent from tracking."""
    agent_id = "agent-1"

    monitor.update_status(agent_id, AgentStatus.WORKING)
    monitor.record_resource_usage(agent_id, tokens=1000)

    # Remove from tracking
    monitor.remove_agent(agent_id)

    # Should return None now
    snapshot = monitor.get_status(agent_id)
    assert snapshot is None


def test_update_with_empty_task(monitor):
    """Test updating status without a task."""
    agent_id = "agent-1"

    monitor.update_status(agent_id, AgentStatus.WORKING)
    snapshot = monitor.get_status(agent_id)

    assert snapshot.status == AgentStatus.WORKING
    assert snapshot.current_task is None


# ============================================================================
# Test Data Classes
# ============================================================================


def test_agent_resource_metrics_creation():
    """Test creating AgentResourceMetrics."""
    metrics = AgentResourceMetrics(
        time_seconds=120.5, tokens=5000, api_calls=15, memory_mb=256.0
    )

    assert metrics.time_seconds == 120.5
    assert metrics.tokens == 5000
    assert metrics.api_calls == 15
    assert metrics.memory_mb == 256.0


def test_agent_status_snapshot_creation():
    """Test creating AgentStatusSnapshot."""
    now = datetime.now()
    metrics = AgentResourceMetrics(time_seconds=60.0, tokens=2000, api_calls=10)

    snapshot = AgentStatusSnapshot(
        agent_id="agent-1",
        status=AgentStatus.WORKING,
        current_task="Build feature",
        last_update=now,
        resources=metrics,
    )

    assert snapshot.agent_id == "agent-1"
    assert snapshot.status == AgentStatus.WORKING
    assert snapshot.current_task == "Build feature"
    assert snapshot.last_update == now
    assert snapshot.resources == metrics


def test_stuck_agent_detection_creation():
    """Test creating StuckAgentDetection."""
    now = datetime.now()

    detection = StuckAgentDetection(
        agent_id="agent-1",
        status=AgentStatus.WORKING,
        current_task="Stuck task",
        last_progress=now,
        seconds_stuck=125.5,
    )

    assert detection.agent_id == "agent-1"
    assert detection.status == AgentStatus.WORKING
    assert detection.current_task == "Stuck task"
    assert detection.last_progress == now
    assert detection.seconds_stuck == 125.5
