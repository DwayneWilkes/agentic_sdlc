"""User Communication Interface - Phase 7.1

Provides user-facing communication for:
1. Plan presentation before execution
2. Approval gates for significant decisions
3. User-friendly progress updates

Usage:
    from src.user_interaction.communication_interface import (
        UserCommunicationInterface, ApprovalGate
    )

    interface = UserCommunicationInterface()

    # Present execution plan
    plan_text = interface.format_execution_plan(execution_plan, subtasks)
    print(plan_text)

    # Create approval gate
    gate = interface.create_approval_gate(
        decision_type="high_cost_operation",
        description="Run 100 API calls",
        context={"cost": 50.00}
    )
    print(interface.format_approval_prompt(gate))

    # Show progress
    progress_text = interface.format_progress_update(progress_report)
    print(progress_text)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.coordination.execution_plan import ExecutionPlan
from src.coordination.progress_tracker import ProgressReport
from src.models.task import Subtask

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ApprovalGate:
    """Represents a decision point requiring user approval.

    Attributes:
        decision_type: Type of decision (e.g., "execute_plan", "high_cost_operation")
        description: Human-readable description of what's being approved
        context: Additional context data for the decision
        approved: None (pending), True (approved), False (rejected)
        decision_time: When the decision was made
        rejection_reason: If rejected, why
    """

    decision_type: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    approved: bool | None = None
    decision_time: datetime | None = None
    rejection_reason: str | None = None


# ============================================================================
# User Communication Interface
# ============================================================================


class UserCommunicationInterface:
    """
    Handles user-facing communication for the orchestrator.

    Provides:
    - Execution plan presentation
    - Approval gate creation and formatting
    - Progress update formatting

    All output is designed to be human-readable and user-friendly.
    """

    # Decision types that require approval
    HIGH_RISK_DECISIONS = {
        "destructive_change",
        "high_cost_operation",
        "external_api_call",
        "data_deletion",
        "system_modification",
    }

    def __init__(self) -> None:
        """Initialize the communication interface."""
        pass

    # ========================================================================
    # Plan Presentation
    # ========================================================================

    def format_execution_plan(
        self, execution_plan: ExecutionPlan, subtasks: list[Subtask]
    ) -> str:
        """
        Format an execution plan for user presentation.

        Shows:
        - Overall structure (stages and parallelism)
        - Task details in each stage
        - Critical path
        - Bottlenecks
        - Time estimates

        Args:
            execution_plan: The ExecutionPlan to format
            subtasks: List of subtasks for details

        Returns:
            Human-readable formatted plan
        """
        if not execution_plan.stages:
            return "Execution Plan\n\nNo tasks to execute."

        # Build task lookup map
        task_map = {t.id: t for t in subtasks}

        lines = []
        lines.append("=" * 70)
        lines.append("EXECUTION PLAN")
        lines.append("=" * 70)
        lines.append("")

        # Overview
        lines.append(f"Total Stages: {len(execution_plan.stages)}")
        lines.append(f"Max Parallelism: {execution_plan.max_parallelism} tasks")
        lines.append(f"Estimated Time: {execution_plan.total_estimated_time} units")
        lines.append("")

        # Stages
        lines.append("Execution Stages:")
        lines.append("-" * 70)
        for stage in execution_plan.stages:
            lines.append(f"\nStage {stage.stage_number}:")
            lines.append(f"  Parallelism: {len(stage.tasks)} task(s)")
            lines.append(f"  Duration: {stage.estimated_duration} units")
            lines.append("  Tasks:")
            for task_id in stage.tasks:
                task = task_map.get(task_id)
                if task:
                    lines.append(f"    • {task_id}: {task.description}")
                    if task.dependencies:
                        lines.append(f"      Depends on: {', '.join(task.dependencies)}")
                else:
                    lines.append(f"    • {task_id}")

        lines.append("")

        # Critical path
        if execution_plan.critical_path:
            lines.append("Critical Path:")
            lines.append("-" * 70)
            lines.append("  Tasks on the critical path determine completion time:")
            for task_id in execution_plan.critical_path:
                task = task_map.get(task_id)
                desc = f": {task.description}" if task else ""
                lines.append(f"  → {task_id}{desc}")
            lines.append("")

        # Bottlenecks
        if execution_plan.bottlenecks:
            lines.append("Bottlenecks:")
            lines.append("-" * 70)
            lines.append("  These tasks have many dependents and could delay completion:")
            for task_id in execution_plan.bottlenecks:
                task = task_map.get(task_id)
                desc = f": {task.description}" if task else ""
                lines.append(f"  ⚠️  {task_id}{desc}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    # ========================================================================
    # Approval Gates
    # ========================================================================

    def create_approval_gate(
        self,
        decision_type: str,
        description: str,
        context: dict[str, Any] | None = None,
    ) -> ApprovalGate:
        """
        Create an approval gate for a decision.

        Args:
            decision_type: Type of decision being made
            description: Human-readable description
            context: Additional context data

        Returns:
            ApprovalGate instance
        """
        return ApprovalGate(
            decision_type=decision_type,
            description=description,
            context=context or {},
        )

    def format_approval_prompt(self, gate: ApprovalGate) -> str:
        """
        Format an approval gate as a prompt for the user.

        Args:
            gate: The ApprovalGate to format

        Returns:
            Formatted approval prompt
        """
        lines = []
        lines.append("=" * 70)
        lines.append("APPROVAL REQUIRED")
        lines.append("=" * 70)
        lines.append("")

        # Decision type
        decision_label = gate.decision_type.replace("_", " ").title()
        lines.append(f"Decision Type: {decision_label}")
        lines.append("")

        # Description
        lines.append("Description:")
        lines.append(f"  {gate.description}")
        lines.append("")

        # Context
        if gate.context:
            lines.append("Context:")
            for key, value in gate.context.items():
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {value}")
            lines.append("")

        lines.append("Please approve or reject this action.")
        lines.append("=" * 70)

        return "\n".join(lines)

    def requires_approval(self, gate: ApprovalGate) -> bool:
        """
        Determine if a decision requires user approval.

        High-risk decisions always require approval.
        Other decisions may be auto-approved based on policy.

        Args:
            gate: The ApprovalGate to check

        Returns:
            True if approval is required
        """
        return gate.decision_type in self.HIGH_RISK_DECISIONS

    # ========================================================================
    # Progress Updates
    # ========================================================================

    def format_progress_update(self, progress_report: ProgressReport) -> str:
        """
        Format a progress report for user display.

        Shows:
        - Overall progress percentage
        - Task counts by status
        - Blockers (if any)
        - Risks (if any)

        Args:
            progress_report: The ProgressReport to format

        Returns:
            Human-readable progress update
        """
        lines = []
        lines.append("=" * 70)
        lines.append("PROGRESS UPDATE")
        lines.append("=" * 70)
        lines.append(f"Generated: {progress_report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Progress bar
        progress_pct = progress_report.overall_progress
        bar_width = 50
        filled = int(bar_width * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"Progress: [{bar}] {progress_pct}%")
        lines.append("")

        # Task counts
        lines.append("Task Status:")
        lines.append(
            f"  ✅ Completed:   {progress_report.completed_count}/{progress_report.total_count}"
        )
        if progress_report.in_progress_count > 0:
            lines.append(f"  🔄 In Progress: {progress_report.in_progress_count}")
        if progress_report.pending_count > 0:
            lines.append(f"  ⏳ Pending:     {progress_report.pending_count}")
        if progress_report.blocked_count > 0:
            lines.append(f"  🔴 Blocked:     {progress_report.blocked_count}")
        if progress_report.failed_count > 0:
            lines.append(f"  ❌ Failed:      {progress_report.failed_count}")
        lines.append("")

        # Completion status
        if progress_pct == 100.0:
            lines.append("✨ All tasks complete!")
            lines.append("")

        # Blockers
        if progress_report.blockers:
            lines.append("Current Blockers:")
            lines.append("-" * 70)
            for blocker in progress_report.blockers:
                severity_icon = {
                    "low": "ℹ️ ",
                    "medium": "⚠️ ",
                    "high": "🔴",
                    "critical": "🚨",
                }.get(blocker.severity, "⚠️ ")
                lines.append(f"  {severity_icon} {blocker.description}")
            lines.append("")

        # Risks
        if progress_report.risks:
            lines.append("Identified Risks:")
            lines.append("-" * 70)
            for risk in progress_report.risks:
                impact_icon = {
                    "low": "ℹ️ ",
                    "medium": "⚠️ ",
                    "high": "🔴",
                }.get(risk.impact, "⚠️ ")
                lines.append(f"  {impact_icon} {risk.description}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


# ============================================================================
# Singleton and Convenience Functions
# ============================================================================

_interface_instance: UserCommunicationInterface | None = None


def get_user_communication_interface() -> UserCommunicationInterface:
    """Get the singleton UserCommunicationInterface instance."""
    global _interface_instance
    if _interface_instance is None:
        _interface_instance = UserCommunicationInterface()
    return _interface_instance
