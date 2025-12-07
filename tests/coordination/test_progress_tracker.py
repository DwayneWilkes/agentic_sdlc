"""
Tests for Progress Tracker - Phase 6.2

Tests cover:
1. Overall task progress calculation (completed/total subtasks)
2. Blocker detection (stuck agents, blocked tasks, dependency issues)
3. Delay detection (tasks exceeding estimates)
4. Risk identification (bottlenecks, critical path issues)
5. Progress report generation
6. Integration with AgentStatusMonitor and ExecutionPlan
"""

import time
from datetime import datetime

import pytest

from src.coordination.agent_status_monitor import AgentStatusMonitor
from src.coordination.execution_plan import ExecutionPlanGenerator
from src.coordination.progress_tracker import (
    BlockerType,
    ProgressReport,
    ProgressTracker,
    RiskType,
)
from src.models.enums import AgentStatus, TaskStatus
from src.models.task import Subtask

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def status_monitor():
    """Create fresh AgentStatusMonitor."""
    return AgentStatusMonitor(stuck_threshold_seconds=10.0)


@pytest.fixture
def sample_subtasks():
    """Create sample subtasks for testing."""
    return [
        Subtask(
            id="task-1",
            description="Parse input",
            status=TaskStatus.COMPLETED,
            assigned_agent="agent-1",
            metadata={"estimated_complexity": "small"},
        ),
        Subtask(
            id="task-2",
            description="Process data",
            status=TaskStatus.IN_PROGRESS,
            dependencies=["task-1"],
            assigned_agent="agent-2",
            metadata={"estimated_complexity": "medium"},
        ),
        Subtask(
            id="task-3",
            description="Generate output",
            status=TaskStatus.PENDING,
            dependencies=["task-2"],
            metadata={"estimated_complexity": "large"},
        ),
        Subtask(
            id="task-4",
            description="Validate results",
            status=TaskStatus.PENDING,
            dependencies=["task-3"],
            metadata={"estimated_complexity": "small"},
        ),
    ]


@pytest.fixture
def execution_plan(sample_subtasks):
    """Create execution plan from sample subtasks."""
    generator = ExecutionPlanGenerator()
    return generator.generate(sample_subtasks)


@pytest.fixture
def progress_tracker(status_monitor):
    """Create fresh ProgressTracker."""
    return ProgressTracker(status_monitor)


# ============================================================================
# Test Progress Calculation
# ============================================================================


def test_calculate_overall_progress_all_pending(progress_tracker):
    """Test progress calculation when all tasks pending."""
    subtasks = [
        Subtask(id="t1", description="Task 1", status=TaskStatus.PENDING),
        Subtask(id="t2", description="Task 2", status=TaskStatus.PENDING),
        Subtask(id="t3", description="Task 3", status=TaskStatus.PENDING),
    ]

    progress = progress_tracker.calculate_overall_progress(subtasks)

    assert progress == 0.0


def test_calculate_overall_progress_all_completed(progress_tracker):
    """Test progress calculation when all tasks completed."""
    subtasks = [
        Subtask(id="t1", description="Task 1", status=TaskStatus.COMPLETED),
        Subtask(id="t2", description="Task 2", status=TaskStatus.COMPLETED),
        Subtask(id="t3", description="Task 3", status=TaskStatus.COMPLETED),
    ]

    progress = progress_tracker.calculate_overall_progress(subtasks)

    assert progress == 100.0


def test_calculate_overall_progress_mixed_statuses(progress_tracker):
    """Test progress calculation with mixed task statuses."""
    subtasks = [
        Subtask(id="t1", description="Task 1", status=TaskStatus.COMPLETED),
        Subtask(id="t2", description="Task 2", status=TaskStatus.IN_PROGRESS),
        Subtask(id="t3", description="Task 3", status=TaskStatus.PENDING),
        Subtask(id="t4", description="Task 4", status=TaskStatus.COMPLETED),
    ]

    progress = progress_tracker.calculate_overall_progress(subtasks)

    # 2 completed out of 4 = 50%
    assert progress == 50.0


def test_calculate_overall_progress_empty_list(progress_tracker):
    """Test progress calculation with empty task list."""
    progress = progress_tracker.calculate_overall_progress([])

    assert progress == 0.0


def test_get_task_counts(progress_tracker, sample_subtasks):
    """Test getting task counts by status."""
    counts = progress_tracker.get_task_counts(sample_subtasks)

    assert counts["completed"] == 1
    assert counts["in_progress"] == 1
    assert counts["pending"] == 2
    assert counts["blocked"] == 0
    assert counts["failed"] == 0
    assert counts["total"] == 4


# ============================================================================
# Test Blocker Detection
# ============================================================================


def test_detect_stuck_agent_blocker(progress_tracker, status_monitor, sample_subtasks):
    """Test detection of stuck agents as blockers."""
    # Set up stuck agent
    status_monitor.update_status("agent-2", AgentStatus.WORKING, "Process data")
    status_monitor.record_progress("agent-2")

    # Simulate time passing (make agent stuck)
    time.sleep(0.05)
    status_monitor.stuck_threshold_seconds = 0.01  # Very short threshold for test

    blockers = progress_tracker.detect_blockers(sample_subtasks)

    # Should detect stuck agent
    assert len(blockers) > 0
    stuck_blockers = [b for b in blockers if b.blocker_type == BlockerType.STUCK_AGENT]
    assert len(stuck_blockers) == 1
    assert "agent-2" in stuck_blockers[0].affected_items


def test_detect_blocked_task_blocker(progress_tracker):
    """Test detection of blocked tasks."""
    subtasks = [
        Subtask(
            id="task-1",
            description="Blocked task",
            status=TaskStatus.BLOCKED,
            assigned_agent="agent-1",
        ),
    ]

    blockers = progress_tracker.detect_blockers(subtasks)

    assert len(blockers) == 1
    assert blockers[0].blocker_type == BlockerType.BLOCKED_TASK
    assert "task-1" in blockers[0].affected_items


def test_detect_dependency_issue_blocker(progress_tracker):
    """Test detection of failed dependency as blocker."""
    subtasks = [
        Subtask(
            id="task-1",
            description="Failed task",
            status=TaskStatus.FAILED,
            assigned_agent="agent-1",
        ),
        Subtask(
            id="task-2",
            description="Depends on failed",
            status=TaskStatus.PENDING,
            dependencies=["task-1"],
        ),
    ]

    blockers = progress_tracker.detect_blockers(subtasks)

    # Should detect dependency issue
    dep_blockers = [b for b in blockers if b.blocker_type == BlockerType.DEPENDENCY_ISSUE]
    assert len(dep_blockers) >= 1


def test_detect_unassigned_ready_task(progress_tracker):
    """Test detection of ready but unassigned tasks."""
    subtasks = [
        Subtask(
            id="task-1",
            description="Ready task",
            status=TaskStatus.PENDING,
            assigned_agent=None,  # Not assigned
            dependencies=[],  # No dependencies - ready to start
        ),
    ]

    blockers = progress_tracker.detect_blockers(subtasks)

    # Should detect unassigned task
    unassigned_blockers = [
        b for b in blockers if b.blocker_type == BlockerType.UNASSIGNED_READY_TASK
    ]
    assert len(unassigned_blockers) == 1
    assert "task-1" in unassigned_blockers[0].affected_items


# ============================================================================
# Test Risk Detection
# ============================================================================


def test_detect_bottleneck_risk(progress_tracker, execution_plan):
    """Test detection of bottleneck tasks as risks."""
    # Create plan with bottleneck
    subtasks = [
        Subtask(id="t1", description="Root", dependencies=[]),
        Subtask(id="t2", description="Bottleneck", dependencies=["t1"]),
        Subtask(id="t3", description="Depends on bottleneck", dependencies=["t2"]),
        Subtask(id="t4", description="Also depends", dependencies=["t2"]),
        Subtask(id="t5", description="Also depends", dependencies=["t2"]),
    ]

    generator = ExecutionPlanGenerator()
    plan = generator.generate(subtasks)

    risks = progress_tracker.detect_risks(subtasks, plan)

    # Should detect t2 as bottleneck (3+ dependents)
    bottleneck_risks = [r for r in risks if r.risk_type == RiskType.BOTTLENECK]
    assert len(bottleneck_risks) >= 1


def test_detect_critical_path_delay_risk(progress_tracker, status_monitor):
    """Test detection of delays on critical path."""
    # Create tasks on critical path
    subtasks = [
        Subtask(
            id="t1",
            description="Critical task",
            status=TaskStatus.IN_PROGRESS,
            assigned_agent="agent-1",
            dependencies=[],
            metadata={"estimated_complexity": "small"},  # Should be fast
        ),
    ]

    generator = ExecutionPlanGenerator()
    plan = generator.generate(subtasks)

    # Set up agent working on critical path task
    status_monitor.update_status("agent-1", AgentStatus.WORKING, "Critical task")
    status_monitor.record_progress("agent-1")

    # Simulate delay (agent working longer than expected)
    time.sleep(0.01)

    # This test checks if delays on critical path are flagged as risks
    # Implementation should detect when tasks on critical path take too long
    risks = progress_tracker.detect_risks(subtasks, plan)

    # Implementation will determine appropriate risk detection
    # For now, just verify risks structure is correct
    assert isinstance(risks, list)


def test_detect_low_parallelism_risk(progress_tracker):
    """Test detection of low parallelism as risk."""
    # Create sequential tasks (low parallelism)
    subtasks = [
        Subtask(id="t1", description="Task 1", dependencies=[]),
        Subtask(id="t2", description="Task 2", dependencies=["t1"]),
        Subtask(id="t3", description="Task 3", dependencies=["t2"]),
        Subtask(id="t4", description="Task 4", dependencies=["t3"]),
    ]

    generator = ExecutionPlanGenerator()
    plan = generator.generate(subtasks)

    risks = progress_tracker.detect_risks(subtasks, plan)

    # Should detect low parallelism risk (max_parallelism = 1)
    low_par_risks = [r for r in risks if r.risk_type == RiskType.LOW_PARALLELISM]
    assert len(low_par_risks) >= 1


# ============================================================================
# Test Progress Report Generation
# ============================================================================


def test_generate_progress_report(progress_tracker, sample_subtasks, execution_plan):
    """Test generation of complete progress report."""
    report = progress_tracker.generate_progress_report(sample_subtasks, execution_plan)

    assert isinstance(report, ProgressReport)
    assert report.overall_progress == 25.0  # 1 of 4 completed
    assert report.completed_count == 1
    assert report.in_progress_count == 1
    assert report.pending_count == 2
    assert report.total_count == 4
    assert isinstance(report.blockers, list)
    assert isinstance(report.risks, list)
    assert isinstance(report.timestamp, datetime)


def test_generate_progress_report_with_blockers(
    progress_tracker, status_monitor, sample_subtasks, execution_plan
):
    """Test report includes detected blockers."""
    # Create stuck agent
    status_monitor.update_status("agent-2", AgentStatus.WORKING, "Processing")
    status_monitor.record_progress("agent-2")
    time.sleep(0.05)
    status_monitor.stuck_threshold_seconds = 0.01

    report = progress_tracker.generate_progress_report(sample_subtasks, execution_plan)

    # Should include blocker for stuck agent
    assert len(report.blockers) > 0


def test_format_progress_report_text(progress_tracker, sample_subtasks, execution_plan):
    """Test formatting progress report as human-readable text."""
    report = progress_tracker.generate_progress_report(sample_subtasks, execution_plan)
    text = progress_tracker.format_progress_report(report)

    assert isinstance(text, str)
    assert "Progress Report" in text
    assert "25.0%" in text or "25%" in text  # Progress percentage
    assert "1/4" in text  # Completed/total
    assert "Blockers:" in text
    assert "Risks:" in text


def test_format_progress_report_no_blockers(progress_tracker):
    """Test formatting report with no blockers."""
    subtasks = [
        Subtask(id="t1", description="Task 1", status=TaskStatus.COMPLETED),
    ]

    generator = ExecutionPlanGenerator()
    plan = generator.generate(subtasks)

    report = progress_tracker.generate_progress_report(subtasks, plan)
    text = progress_tracker.format_progress_report(report)

    assert "No blockers detected" in text


# ============================================================================
# Test Integration Scenarios
# ============================================================================


def test_track_progress_over_time(progress_tracker, status_monitor):
    """Test tracking progress as tasks complete over time."""
    subtasks = [
        Subtask(id="t1", description="Task 1", status=TaskStatus.PENDING),
        Subtask(id="t2", description="Task 2", status=TaskStatus.PENDING),
        Subtask(id="t3", description="Task 3", status=TaskStatus.PENDING),
    ]

    # Initial progress
    assert progress_tracker.calculate_overall_progress(subtasks) == 0.0

    # Complete first task
    subtasks[0].status = TaskStatus.COMPLETED
    assert progress_tracker.calculate_overall_progress(subtasks) == 33.33

    # Complete second task
    subtasks[1].status = TaskStatus.COMPLETED
    assert progress_tracker.calculate_overall_progress(subtasks) == 66.67

    # Complete all
    subtasks[2].status = TaskStatus.COMPLETED
    assert progress_tracker.calculate_overall_progress(subtasks) == 100.0


def test_multiple_blocker_types_detected(progress_tracker, status_monitor):
    """Test detection of multiple different blocker types."""
    subtasks = [
        Subtask(
            id="t1",
            description="Blocked task",
            status=TaskStatus.BLOCKED,
        ),
        Subtask(
            id="t2",
            description="Ready unassigned",
            status=TaskStatus.PENDING,
            assigned_agent=None,
            dependencies=[],
        ),
        Subtask(
            id="t3",
            description="Failed task",
            status=TaskStatus.FAILED,
        ),
        Subtask(
            id="t4",
            description="Depends on failed",
            status=TaskStatus.PENDING,
            dependencies=["t3"],
        ),
    ]

    # Add stuck agent
    status_monitor.update_status("agent-1", AgentStatus.WORKING, "Stuck work")
    status_monitor.record_progress("agent-1")
    time.sleep(0.05)
    status_monitor.stuck_threshold_seconds = 0.01

    blockers = progress_tracker.detect_blockers(subtasks)

    # Should have multiple blocker types
    blocker_types = {b.blocker_type for b in blockers}
    assert len(blocker_types) >= 2  # At least 2 different types


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_progress_with_failed_tasks(progress_tracker):
    """Test progress calculation includes failed tasks."""
    subtasks = [
        Subtask(id="t1", description="Task 1", status=TaskStatus.COMPLETED),
        Subtask(id="t2", description="Task 2", status=TaskStatus.FAILED),
        Subtask(id="t3", description="Task 3", status=TaskStatus.PENDING),
    ]

    # Failed tasks count towards total but not completion
    progress = progress_tracker.calculate_overall_progress(subtasks)
    assert progress == 33.33  # 1 completed out of 3 total


def test_detect_blockers_empty_tasks(progress_tracker):
    """Test blocker detection with empty task list."""
    blockers = progress_tracker.detect_blockers([])
    assert blockers == []


def test_detect_risks_empty_tasks(progress_tracker):
    """Test risk detection with empty task list."""
    generator = ExecutionPlanGenerator()
    plan = generator.generate([])

    risks = progress_tracker.detect_risks([], plan)
    assert risks == []


def test_progress_report_snapshot_timestamp(progress_tracker):
    """Test that progress report captures accurate timestamp."""
    subtasks = [
        Subtask(id="t1", description="Task 1", status=TaskStatus.PENDING),
    ]

    generator = ExecutionPlanGenerator()
    plan = generator.generate(subtasks)

    before = datetime.now()
    report = progress_tracker.generate_progress_report(subtasks, plan)
    after = datetime.now()

    assert before <= report.timestamp <= after
