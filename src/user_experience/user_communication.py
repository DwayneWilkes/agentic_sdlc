"""User Communication Interface - Phase 7.1.

Provides plan presentation, approval gates, and progress updates for user interaction.

Features:
1. Present execution plans before starting work
2. Request approval for significant decisions
3. Generate user-friendly progress updates

Usage:
    from src.user_experience import UserCommunicationInterface, DecisionType

    interface = UserCommunicationInterface()

    # Present plan to user
    plan_text = interface.present_plan(execution_plan, subtasks)
    print(plan_text)

    # Request approval
    request_id = interface.request_approval(
        DecisionType.DESTRUCTIVE_OPERATION,
        "Delete old logs",
        "cleanup-agent"
    )
    decision = await interface.wait_for_approval(request_id)

    # Send progress update
    update = interface.send_progress_update(subtasks, execution_plan)
    print(update.message)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.coordination.execution_plan import ExecutionPlan
from src.coordination.progress_tracker import ProgressTracker, get_progress_tracker
from src.models.task import Subtask
from src.security.access_control import Action, ActionType, Resource, ResourceType
from src.security.approval_gate import ApprovalDecision, ApprovalGate

# ============================================================================
# Enums
# ============================================================================


class DecisionType(str, Enum):
    """Types of decisions that may require approval."""

    DESTRUCTIVE_OPERATION = "destructive_operation"  # Delete, remove, destroy
    SIGNIFICANT_DECISION = "significant_decision"  # Major changes
    RESOURCE_ALLOCATION = "resource_allocation"  # Allocate many resources


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ProgressUpdate:
    """A progress update message for the user."""

    message: str
    """Formatted progress message."""

    overall_progress: float
    """Overall progress percentage (0-100)."""

    timestamp: datetime
    """When the update was generated."""


# ============================================================================
# Plan Presentation
# ============================================================================


class PlanPresentation:
    """Formats execution plans for user review."""

    @staticmethod
    def format_plan(
        execution_plan: ExecutionPlan,
        subtasks: list[Subtask],
    ) -> str:
        """
        Format an execution plan for user presentation.

        Args:
            execution_plan: The execution plan to present
            subtasks: List of subtasks in the plan

        Returns:
            Formatted plan text for user review
        """
        if not execution_plan.stages and not subtasks:
            return "=" * 60 + "\nExecution Plan\n" + "=" * 60 + "\n\nNo tasks to execute.\n"

        lines = []
        lines.append("=" * 60)
        lines.append("Execution Plan")
        lines.append("=" * 60)
        lines.append("")

        # Create task lookup
        task_map = {task.id: task for task in subtasks}

        # Show stages
        lines.append("Stages:")
        for stage in execution_plan.stages:
            lines.append(f"\nStage {stage.stage_number}:")
            lines.append(f"  Parallel Tasks: {len(stage.tasks)}")
            lines.append("  Tasks:")
            for task_id in stage.tasks:
                task = task_map.get(task_id)
                if task:
                    status_icon = {
                        "COMPLETED": "✅",
                        "IN_PROGRESS": "🔄",
                        "PENDING": "⚪",
                        "BLOCKED": "🔴",
                        "FAILED": "❌",
                    }.get(task.status.value.upper(), "⚪")

                    lines.append(f"    {status_icon} {task_id}: {task.description}")

                    # Show dependencies
                    if task.dependencies:
                        dep_list = ", ".join(task.dependencies)
                        lines.append(f"       Dependencies: {dep_list}")

                    # Show assigned agent
                    if task.assigned_agent:
                        lines.append(f"       Assigned to: {task.assigned_agent}")

        lines.append("")

        # Show critical path
        if execution_plan.critical_path:
            lines.append("Critical Path:")
            critical_path_str = " → ".join(execution_plan.critical_path)
            lines.append(f"  {critical_path_str}")
            lines.append("")

        # Show bottlenecks
        if execution_plan.bottlenecks:
            lines.append("Bottlenecks:")
            for bottleneck in execution_plan.bottlenecks:
                lines.append(f"  ⚠️  {bottleneck}")
            lines.append("")

        # Show parallelism info
        lines.append("Execution Info:")
        lines.append(f"  Max Parallelism: {execution_plan.max_parallelism}")
        if execution_plan.max_parallelism == 1:
            lines.append("  ⚠️  Tasks will run sequentially")
        else:
            lines.append(f"  ✅ Up to {execution_plan.max_parallelism} tasks can run in parallel")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# ============================================================================
# User Communication Interface
# ============================================================================


class UserCommunicationInterface:
    """
    Main interface for user communication.

    Coordinates plan presentation, approval gates, and progress updates.
    """

    def __init__(
        self,
        approval_timeout: float = 300.0,
        approval_gate: ApprovalGate | None = None,
        progress_tracker: ProgressTracker | None = None,
    ):
        """
        Initialize user communication interface.

        Args:
            approval_timeout: Timeout in seconds for approval requests
            approval_gate: Optional ApprovalGate instance (creates new if None)
            progress_tracker: Optional ProgressTracker instance (uses singleton if None)
        """
        self.approval_gate = approval_gate or ApprovalGate(
            timeout_seconds=approval_timeout
        )
        self.progress_tracker = progress_tracker or get_progress_tracker()

    def present_plan(
        self,
        execution_plan: ExecutionPlan,
        subtasks: list[Subtask],
    ) -> str:
        """
        Present an execution plan to the user.

        Args:
            execution_plan: The execution plan to present
            subtasks: List of subtasks in the plan

        Returns:
            Formatted plan text for user review
        """
        return PlanPresentation.format_plan(execution_plan, subtasks)

    def request_approval(
        self,
        decision_type: DecisionType,
        details: str,
        requested_by: str,
    ) -> str:
        """
        Request approval for a significant decision.

        Args:
            decision_type: Type of decision requiring approval
            details: Detailed description of what needs approval
            requested_by: Agent or component requesting approval

        Returns:
            Request ID for tracking the approval
        """
        # Map decision type to ActionType
        action_type_map = {
            DecisionType.DESTRUCTIVE_OPERATION: ActionType.DELETE,
            DecisionType.SIGNIFICANT_DECISION: ActionType.MODIFY,
            DecisionType.RESOURCE_ALLOCATION: ActionType.CREATE,
        }

        action_type = action_type_map.get(decision_type, ActionType.MODIFY)

        # Create Action with appropriate resource
        action = Action(
            action_type=action_type,
            resource=Resource(
                resource_type=ResourceType.AGENT,
                path=f"decision/{decision_type.value}",
            ),
            agent_id=requested_by,
        )

        return self.approval_gate.submit_request(
            action=action,
            requested_by=requested_by,
            reason=details,
        )

    async def wait_for_approval(self, request_id: str) -> ApprovalDecision:
        """
        Wait for approval decision on a request.

        Args:
            request_id: Request ID from request_approval()

        Returns:
            ApprovalDecision with the result

        Raises:
            ApprovalTimeoutError: If no decision made within timeout
        """
        return await self.approval_gate.wait_for_approval(request_id)

    def approve_request(
        self,
        request_id: str,
        approved_by: str,
        reason: str,
    ) -> None:
        """
        Approve a pending request.

        Args:
            request_id: Request to approve
            approved_by: Who is approving
            reason: Explanation for approval
        """
        self.approval_gate.approve_request(request_id, approved_by, reason)

    def deny_request(
        self,
        request_id: str,
        denied_by: str,
        reason: str,
    ) -> None:
        """
        Deny a pending request.

        Args:
            request_id: Request to deny
            denied_by: Who is denying
            reason: Explanation for denial
        """
        self.approval_gate.deny_request(request_id, denied_by, reason)

    def get_pending_approvals(self) -> list[str]:
        """
        Get all pending approval request IDs.

        Returns:
            List of request IDs awaiting approval
        """
        return self.approval_gate.get_pending_requests()

    def send_progress_update(
        self,
        subtasks: list[Subtask],
        execution_plan: ExecutionPlan,
    ) -> ProgressUpdate:
        """
        Generate a user-friendly progress update.

        Args:
            subtasks: Current list of subtasks
            execution_plan: Execution plan being followed

        Returns:
            ProgressUpdate with formatted message
        """
        # Generate comprehensive progress report
        report = self.progress_tracker.generate_progress_report(
            subtasks, execution_plan
        )

        # Format as user-friendly message
        message = self.progress_tracker.format_progress_report(report)

        return ProgressUpdate(
            message=message,
            overall_progress=report.overall_progress,
            timestamp=report.timestamp,
        )


# ============================================================================
# Singleton and Convenience Functions
# ============================================================================

_interface_instance: UserCommunicationInterface | None = None


def get_user_communication_interface() -> UserCommunicationInterface:
    """Get the singleton user communication interface instance."""
    global _interface_instance
    if _interface_instance is None:
        _interface_instance = UserCommunicationInterface()
    return _interface_instance
