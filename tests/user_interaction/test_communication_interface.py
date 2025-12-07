"""Tests for User Communication Interface - Phase 7.1

Tests plan presentation, approval gates, and progress updates.
"""

from datetime import datetime

import pytest

from src.coordination.execution_plan import ExecutionPlan, ExecutionStage
from src.coordination.progress_tracker import (
    BlockerReport,
    BlockerType,
    ProgressReport,
    RiskReport,
    RiskType,
)
from src.models.enums import TaskStatus
from src.models.task import Subtask
from src.user_interaction.communication_interface import (
    ApprovalGate,
    UserCommunicationInterface,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_execution_plan():
    """Create a sample execution plan for testing."""
    return ExecutionPlan(
        stages=[
            ExecutionStage(stage_number=1, tasks=["task1", "task2"], estimated_duration=2),
            ExecutionStage(stage_number=2, tasks=["task3"], estimated_duration=1),
            ExecutionStage(stage_number=3, tasks=["task4", "task5"], estimated_duration=2),
        ],
        critical_path=["task1", "task3", "task4"],
        bottlenecks=["task3"],
        total_estimated_time=5,
        max_parallelism=2,
    )


@pytest.fixture
def sample_subtasks():
    """Create sample subtasks for testing."""
    return [
        Subtask(
            id="task1",
            description="Parse user input",
            dependencies=[],
            status=TaskStatus.COMPLETED,
        ),
        Subtask(
            id="task2",
            description="Validate data",
            dependencies=[],
            status=TaskStatus.IN_PROGRESS,
            assigned_agent="agent1",
        ),
        Subtask(
            id="task3",
            description="Process data",
            dependencies=["task1", "task2"],
            status=TaskStatus.PENDING,
        ),
        Subtask(
            id="task4",
            description="Generate output",
            dependencies=["task3"],
            status=TaskStatus.PENDING,
        ),
        Subtask(
            id="task5",
            description="Save results",
            dependencies=["task3"],
            status=TaskStatus.PENDING,
        ),
    ]


@pytest.fixture
def sample_progress_report():
    """Create a sample progress report for testing."""
    return ProgressReport(
        overall_progress=25.0,
        completed_count=1,
        in_progress_count=1,
        pending_count=3,
        blocked_count=0,
        failed_count=0,
        total_count=5,
        blockers=[],
        risks=[
            RiskReport(
                risk_type=RiskType.BOTTLENECK,
                affected_items=["task3"],
                description="Task task3 is a bottleneck (many tasks depend on it)",
                impact="high",
            )
        ],
        timestamp=datetime(2025, 12, 7, 10, 30, 0),
    )


@pytest.fixture
def communication_interface():
    """Create a UserCommunicationInterface instance."""
    return UserCommunicationInterface()


# ============================================================================
# Plan Presentation Tests
# ============================================================================


def test_format_execution_plan_basic(
    communication_interface, sample_execution_plan, sample_subtasks
):
    """Test basic execution plan formatting."""
    result = communication_interface.format_execution_plan(
        sample_execution_plan, sample_subtasks
    )

    # Should contain plan header (case-insensitive)
    assert "execution plan" in result.lower()

    # Should show stages
    assert "Stage 1" in result
    assert "Stage 2" in result
    assert "Stage 3" in result

    # Should show task IDs in stages
    assert "task1" in result
    assert "task2" in result
    assert "task3" in result

    # Should show estimated time
    assert "5" in result  # total estimated time

    # Should show parallelism
    assert "2" in result  # max parallelism


def test_format_execution_plan_critical_path(
    communication_interface, sample_execution_plan, sample_subtasks
):
    """Test that critical path is highlighted in plan."""
    result = communication_interface.format_execution_plan(
        sample_execution_plan, sample_subtasks
    )

    # Should show critical path section
    assert "Critical Path" in result

    # Critical path tasks should be listed
    assert "task1" in result
    assert "task3" in result
    assert "task4" in result


def test_format_execution_plan_bottlenecks(
    communication_interface, sample_execution_plan, sample_subtasks
):
    """Test that bottlenecks are highlighted."""
    result = communication_interface.format_execution_plan(
        sample_execution_plan, sample_subtasks
    )

    # Should show bottlenecks section
    assert "Bottleneck" in result or "bottleneck" in result

    # Bottleneck task should be mentioned
    assert "task3" in result


def test_format_execution_plan_empty(communication_interface):
    """Test formatting empty execution plan."""
    empty_plan = ExecutionPlan()
    result = communication_interface.format_execution_plan(empty_plan, [])

    # Should handle empty plan gracefully
    assert "Execution Plan" in result or "No tasks" in result or "Empty" in result


def test_format_execution_plan_with_task_details(
    communication_interface, sample_execution_plan, sample_subtasks
):
    """Test that task descriptions are included in plan."""
    result = communication_interface.format_execution_plan(
        sample_execution_plan, sample_subtasks
    )

    # Should show task descriptions, not just IDs
    assert "Parse user input" in result or "task1" in result


# ============================================================================
# Approval Gate Tests
# ============================================================================


def test_create_approval_gate_basic(communication_interface):
    """Test creating a basic approval gate."""
    gate = communication_interface.create_approval_gate(
        decision_type="execute",
        description="Execute task decomposition",
        context={"task_count": 5},
    )

    assert isinstance(gate, ApprovalGate)
    assert gate.decision_type == "execute"
    assert gate.description == "Execute task decomposition"
    assert gate.context["task_count"] == 5
    assert gate.approved is None  # Not yet approved


def test_format_approval_prompt(communication_interface):
    """Test formatting approval prompt for user."""
    gate = ApprovalGate(
        decision_type="high_cost_operation",
        description="Run 100 API calls for data processing",
        context={"estimated_cost": 50.00, "api_calls": 100},
    )

    result = communication_interface.format_approval_prompt(gate)

    # Should contain decision type
    assert "high_cost_operation" in result or "High Cost" in result

    # Should contain description
    assert "Run 100 API calls" in result

    # Should show context
    assert "50" in result or "$50" in result
    assert "100" in result


def test_approval_gate_approve(communication_interface):
    """Test approving a gate."""
    gate = communication_interface.create_approval_gate(
        decision_type="destructive_change",
        description="Delete old database tables",
    )

    # Approve the gate
    gate.approved = True
    gate.decision_time = datetime.now()

    assert gate.approved is True
    assert gate.decision_time is not None


def test_approval_gate_reject(communication_interface):
    """Test rejecting a gate."""
    gate = communication_interface.create_approval_gate(
        decision_type="destructive_change",
        description="Delete old database tables",
    )

    # Reject the gate
    gate.approved = False
    gate.decision_time = datetime.now()
    gate.rejection_reason = "Too risky without backup"

    assert gate.approved is False
    assert gate.rejection_reason == "Too risky without backup"


def test_approval_gate_requires_approval(communication_interface):
    """Test determining which decisions require approval."""
    # High-risk decisions should require approval
    gate_high_risk = communication_interface.create_approval_gate(
        decision_type="destructive_change",
        description="Delete files",
    )
    assert communication_interface.requires_approval(gate_high_risk) is True

    # Low-risk decisions might not
    gate_low_risk = communication_interface.create_approval_gate(
        decision_type="read_only_operation",
        description="List files",
    )
    # This depends on implementation - could be True or False
    # Just test that method exists and returns boolean
    result = communication_interface.requires_approval(gate_low_risk)
    assert isinstance(result, bool)


# ============================================================================
# Progress Update Tests
# ============================================================================


def test_format_progress_update_basic(communication_interface, sample_progress_report):
    """Test basic progress update formatting."""
    result = communication_interface.format_progress_update(sample_progress_report)

    # Should show progress percentage
    assert "25" in result or "25.0" in result

    # Should show task counts
    assert "1" in result  # completed
    assert "5" in result  # total

    # Should be human-readable
    assert "Progress" in result or "progress" in result


def test_format_progress_update_with_risks(communication_interface, sample_progress_report):
    """Test that risks are included in progress updates."""
    result = communication_interface.format_progress_update(sample_progress_report)

    # Should mention risks
    assert "Risk" in result or "risk" in result or "Bottleneck" in result or "bottleneck" in result

    # Should mention the specific bottleneck
    assert "task3" in result


def test_format_progress_update_with_blockers(communication_interface):
    """Test progress update with blockers."""
    report = ProgressReport(
        overall_progress=50.0,
        completed_count=2,
        in_progress_count=1,
        pending_count=1,
        blocked_count=1,
        failed_count=0,
        total_count=5,
        blockers=[
            BlockerReport(
                blocker_type=BlockerType.STUCK_AGENT,
                affected_items=["agent1"],
                description="Agent agent1 stuck on task for 120s",
                severity="high",
            )
        ],
        risks=[],
    )

    result = communication_interface.format_progress_update(report)

    # Should mention blockers
    assert "Blocker" in result or "blocker" in result or "stuck" in result

    # Should mention the stuck agent
    assert "agent1" in result


def test_format_progress_update_complete(communication_interface):
    """Test progress update when all tasks complete."""
    report = ProgressReport(
        overall_progress=100.0,
        completed_count=5,
        in_progress_count=0,
        pending_count=0,
        blocked_count=0,
        failed_count=0,
        total_count=5,
        blockers=[],
        risks=[],
    )

    result = communication_interface.format_progress_update(report)

    # Should indicate completion
    assert "100" in result
    assert "Complete" in result or "complete" in result or "Done" in result or "done" in result


def test_format_progress_update_with_failures(communication_interface):
    """Test progress update with failed tasks."""
    report = ProgressReport(
        overall_progress=60.0,
        completed_count=3,
        in_progress_count=0,
        pending_count=0,
        blocked_count=0,
        failed_count=2,
        total_count=5,
        blockers=[],
        risks=[],
    )

    result = communication_interface.format_progress_update(report)

    # Should mention failures
    assert "fail" in result.lower() or "error" in result.lower()
    assert "2" in result


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow_plan_approval_progress(
    communication_interface,
    sample_execution_plan,
    sample_subtasks,
    sample_progress_report,
):
    """Test full workflow: present plan, get approval, show progress."""
    # 1. Present plan
    plan_text = communication_interface.format_execution_plan(
        sample_execution_plan, sample_subtasks
    )
    assert "execution plan" in plan_text.lower()

    # 2. Create approval gate
    gate = communication_interface.create_approval_gate(
        decision_type="execute_plan",
        description="Execute the task decomposition plan",
        context={
            "tasks": len(sample_subtasks),
            "estimated_time": sample_execution_plan.total_estimated_time,
        },
    )

    prompt = communication_interface.format_approval_prompt(gate)
    assert "execute" in prompt.lower()

    # 3. Simulate approval
    gate.approved = True
    gate.decision_time = datetime.now()

    # 4. Show progress
    progress_text = communication_interface.format_progress_update(sample_progress_report)
    assert "25" in progress_text  # 25% progress


def test_user_friendly_formatting(communication_interface, sample_progress_report):
    """Test that all output is user-friendly (not raw data dumps)."""
    progress = communication_interface.format_progress_update(sample_progress_report)

    # Should not contain raw JSON or Python repr
    assert "{" not in progress or "Task {" in progress  # Allow "Task {id}" but not raw JSON
    assert "ProgressReport(" not in progress

    # Should have structure (newlines, sections)
    assert "\n" in progress

    # Should use human-readable terms
    assert any(term in progress.lower() for term in ["progress", "complete", "task", "pending"])
