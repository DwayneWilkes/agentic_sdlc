"""Tests for user communication interface - Phase 7.1.

Tests plan presentation, approval gates, and progress updates.
"""

import asyncio

import pytest

from src.coordination.execution_plan import ExecutionPlan, ExecutionStage
from src.models.enums import TaskStatus
from src.models.task import Subtask
from src.user_experience.user_communication import (
    DecisionType,
    PlanPresentation,
    ProgressUpdate,
    UserCommunicationInterface,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_subtasks() -> list[Subtask]:
    """Create sample subtasks for testing."""
    return [
        Subtask(
            id="task1",
            description="Set up authentication",
            status=TaskStatus.COMPLETED,
            dependencies=[],
        ),
        Subtask(
            id="task2",
            description="Create user registration",
            status=TaskStatus.IN_PROGRESS,
            dependencies=["task1"],
            assigned_agent="backend-dev",
        ),
        Subtask(
            id="task3",
            description="Add OAuth integration",
            status=TaskStatus.PENDING,
            dependencies=["task2"],
        ),
    ]


@pytest.fixture
def sample_execution_plan(sample_subtasks: list[Subtask]) -> ExecutionPlan:
    """Create sample execution plan."""
    return ExecutionPlan(
        stages=[
            ExecutionStage(stage_number=1, tasks=["task1"], estimated_duration=10),
            ExecutionStage(stage_number=2, tasks=["task2"], estimated_duration=15),
            ExecutionStage(stage_number=3, tasks=["task3"], estimated_duration=20),
        ],
        critical_path=["task1", "task2", "task3"],
        bottlenecks=["task2"],
        max_parallelism=1,
    )


@pytest.fixture
def communication_interface() -> UserCommunicationInterface:
    """Create user communication interface for testing."""
    return UserCommunicationInterface(approval_timeout=5.0)


# ============================================================================
# PlanPresentation Tests
# ============================================================================


def test_plan_presentation_basic(
    sample_execution_plan: ExecutionPlan,
    sample_subtasks: list[Subtask],
) -> None:
    """Test basic plan presentation formatting."""
    presentation = PlanPresentation.format_plan(
        execution_plan=sample_execution_plan,
        subtasks=sample_subtasks,
    )

    # Should contain key sections
    assert "Execution Plan" in presentation
    assert "Stage 1" in presentation
    assert "Stage 2" in presentation
    assert "Stage 3" in presentation

    # Should show task details
    assert "task1" in presentation
    assert "Set up authentication" in presentation
    assert "task2" in presentation
    assert "Create user registration" in presentation


def test_plan_presentation_shows_dependencies(
    sample_execution_plan: ExecutionPlan,
    sample_subtasks: list[Subtask],
) -> None:
    """Test that plan presentation shows dependencies."""
    presentation = PlanPresentation.format_plan(
        execution_plan=sample_execution_plan,
        subtasks=sample_subtasks,
    )

    # Should indicate dependencies
    assert "Dependencies" in presentation or "depends on" in presentation.lower()


def test_plan_presentation_shows_parallelism(
    sample_execution_plan: ExecutionPlan,
    sample_subtasks: list[Subtask],
) -> None:
    """Test that plan presentation shows parallelism information."""
    presentation = PlanPresentation.format_plan(
        execution_plan=sample_execution_plan,
        subtasks=sample_subtasks,
    )

    # Should show parallelism info
    assert "parallel" in presentation.lower() or "sequential" in presentation.lower()


def test_plan_presentation_shows_critical_path(
    sample_execution_plan: ExecutionPlan,
    sample_subtasks: list[Subtask],
) -> None:
    """Test that plan presentation highlights critical path."""
    presentation = PlanPresentation.format_plan(
        execution_plan=sample_execution_plan,
        subtasks=sample_subtasks,
    )

    # Should mention critical path
    assert "critical path" in presentation.lower()


def test_plan_presentation_empty_plan() -> None:
    """Test plan presentation with empty plan."""
    empty_plan = ExecutionPlan(
        stages=[],
        critical_path=[],
        bottlenecks=[],
        max_parallelism=0,
    )

    presentation = PlanPresentation.format_plan(
        execution_plan=empty_plan,
        subtasks=[],
    )

    # Should handle empty case gracefully
    assert "No tasks" in presentation or "Empty" in presentation


# ============================================================================
# ProgressUpdate Tests
# ============================================================================


def test_progress_update_basic(
    sample_execution_plan: ExecutionPlan,
    sample_subtasks: list[Subtask],
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test basic progress update generation."""
    update = communication_interface.send_progress_update(
        subtasks=sample_subtasks,
        execution_plan=sample_execution_plan,
    )

    # Should contain progress information
    assert "progress" in update.message.lower()
    assert "1" in update.message  # Completed count
    assert "3" in update.message  # Total count


def test_progress_update_structure(
    sample_execution_plan: ExecutionPlan,
    sample_subtasks: list[Subtask],
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test that progress update has proper structure."""
    update = communication_interface.send_progress_update(
        subtasks=sample_subtasks,
        execution_plan=sample_execution_plan,
    )

    # Check ProgressUpdate structure
    assert isinstance(update, ProgressUpdate)
    assert update.message
    assert update.overall_progress >= 0
    assert update.overall_progress <= 100
    assert update.timestamp


def test_progress_update_includes_blockers(
    sample_execution_plan: ExecutionPlan,
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test that progress update includes blocker information."""
    # Create tasks with a blocker
    tasks_with_blocker = [
        Subtask(
            id="task1",
            description="First task",
            status=TaskStatus.COMPLETED,
        ),
        Subtask(
            id="task2",
            description="Blocked task",
            status=TaskStatus.BLOCKED,
        ),
    ]

    update = communication_interface.send_progress_update(
        subtasks=tasks_with_blocker,
        execution_plan=sample_execution_plan,
    )

    # Should mention blockers
    assert "blocker" in update.message.lower() or "blocked" in update.message.lower()


# ============================================================================
# Approval Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_request_approval_approved(
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test approval request workflow - approval case."""
    # Submit approval request
    request_id = communication_interface.request_approval(
        decision_type=DecisionType.DESTRUCTIVE_OPERATION,
        details="Delete old deployment",
        requested_by="deploy-agent",
    )

    # Approve in background
    async def approve_after_delay():
        await asyncio.sleep(0.1)
        communication_interface.approve_request(
            request_id=request_id,
            approved_by="human-operator",
            reason="Safe to proceed",
        )

    # Run approval task
    asyncio.create_task(approve_after_delay())

    # Wait for approval
    decision = await communication_interface.wait_for_approval(request_id)

    assert decision.approved is True
    assert decision.approved_by == "human-operator"
    assert "Safe to proceed" in decision.reason


@pytest.mark.asyncio
async def test_request_approval_denied(
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test approval request workflow - denial case."""
    # Submit approval request
    request_id = communication_interface.request_approval(
        decision_type=DecisionType.DESTRUCTIVE_OPERATION,
        details="Delete production database",
        requested_by="db-agent",
    )

    # Deny in background
    async def deny_after_delay():
        await asyncio.sleep(0.1)
        communication_interface.deny_request(
            request_id=request_id,
            denied_by="human-operator",
            reason="Too risky",
        )

    # Run denial task
    asyncio.create_task(deny_after_delay())

    # Wait for decision
    decision = await communication_interface.wait_for_approval(request_id)

    assert decision.approved is False
    assert decision.approved_by == "human-operator"
    assert "Too risky" in decision.reason


@pytest.mark.asyncio
async def test_request_approval_timeout(
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test approval request timeout."""
    # Create interface with very short timeout
    fast_timeout_interface = UserCommunicationInterface(approval_timeout=0.2)

    # Submit request
    request_id = fast_timeout_interface.request_approval(
        decision_type=DecisionType.SIGNIFICANT_DECISION,
        details="Major architectural change",
        requested_by="architect-agent",
    )

    # Wait for timeout
    from src.security.approval_gate import ApprovalTimeoutError

    with pytest.raises(ApprovalTimeoutError):
        await fast_timeout_interface.wait_for_approval(request_id)


def test_get_pending_approvals(
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test retrieving pending approval requests."""
    # Submit multiple requests
    request_id1 = communication_interface.request_approval(
        decision_type=DecisionType.RESOURCE_ALLOCATION,
        details="Allocate 10 agents",
        requested_by="orchestrator",
    )
    request_id2 = communication_interface.request_approval(
        decision_type=DecisionType.SIGNIFICANT_DECISION,
        details="Switch to new algorithm",
        requested_by="optimizer",
    )

    # Get pending requests
    pending = communication_interface.get_pending_approvals()

    assert len(pending) == 2
    assert request_id1 in pending
    assert request_id2 in pending


# ============================================================================
# Integration Tests
# ============================================================================


def test_present_plan_integration(
    communication_interface: UserCommunicationInterface,
    sample_execution_plan: ExecutionPlan,
    sample_subtasks: list[Subtask],
) -> None:
    """Test plan presentation through interface."""
    presentation = communication_interface.present_plan(
        execution_plan=sample_execution_plan,
        subtasks=sample_subtasks,
    )

    # Should return formatted plan
    assert isinstance(presentation, str)
    assert len(presentation) > 0
    assert "Execution Plan" in presentation


def test_decision_types() -> None:
    """Test that all decision types are defined."""
    # Ensure all required decision types exist
    assert hasattr(DecisionType, "DESTRUCTIVE_OPERATION")
    assert hasattr(DecisionType, "SIGNIFICANT_DECISION")
    assert hasattr(DecisionType, "RESOURCE_ALLOCATION")


def test_communication_interface_initialization() -> None:
    """Test communication interface initialization."""
    interface = UserCommunicationInterface(approval_timeout=10.0)

    assert interface is not None
    assert interface.approval_gate is not None
    assert interface.progress_tracker is not None


def test_progress_update_empty_tasks(
    communication_interface: UserCommunicationInterface,
) -> None:
    """Test progress update with no tasks."""
    empty_plan = ExecutionPlan(
        stages=[],
        critical_path=[],
        bottlenecks=[],
        max_parallelism=0,
    )

    update = communication_interface.send_progress_update(
        subtasks=[],
        execution_plan=empty_plan,
    )

    assert update.overall_progress == 0.0
    assert "0" in update.message or "No" in update.message
