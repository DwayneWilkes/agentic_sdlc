"""
Progress Tracker - Phase 6.2

Provides progress tracking and reporting for task execution:

Features:
1. Overall task progress calculation (completed/total)
2. Blocker detection (stuck agents, blocked tasks, dependency issues)
3. Delay detection (tasks exceeding estimates)
4. Risk identification (bottlenecks, critical path issues, low parallelism)
5. Progress report generation with formatted output

Usage:
    from src.coordination.progress_tracker import ProgressTracker
    from src.coordination.agent_status_monitor import get_agent_status_monitor

    monitor = get_agent_status_monitor()
    tracker = ProgressTracker(monitor)

    # Calculate progress
    progress = tracker.calculate_overall_progress(subtasks)

    # Detect blockers
    blockers = tracker.detect_blockers(subtasks)

    # Generate full report
    report = tracker.generate_progress_report(subtasks, execution_plan)
    print(tracker.format_progress_report(report))
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.coordination.agent_status_monitor import AgentStatusMonitor
from src.coordination.execution_plan import ExecutionPlan
from src.models.enums import TaskStatus
from src.models.task import Subtask

# ============================================================================
# Enums
# ============================================================================


class BlockerType(str, Enum):
    """Types of blockers that can prevent progress."""

    STUCK_AGENT = "stuck_agent"
    BLOCKED_TASK = "blocked_task"
    DEPENDENCY_ISSUE = "dependency_issue"
    UNASSIGNED_READY_TASK = "unassigned_ready_task"


class RiskType(str, Enum):
    """Types of risks that could impact completion."""

    BOTTLENECK = "bottleneck"
    CRITICAL_PATH_DELAY = "critical_path_delay"
    LOW_PARALLELISM = "low_parallelism"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class BlockerReport:
    """Report of a blocking issue."""

    blocker_type: BlockerType
    affected_items: list[str]  # Task IDs or agent IDs
    description: str
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class RiskReport:
    """Report of a potential risk."""

    risk_type: RiskType
    affected_items: list[str]
    description: str
    impact: str = "medium"  # low, medium, high


@dataclass
class ProgressReport:
    """Comprehensive progress report for task execution."""

    # Progress metrics
    overall_progress: float  # Percentage (0-100)
    completed_count: int
    in_progress_count: int
    pending_count: int
    blocked_count: int
    failed_count: int
    total_count: int

    # Issues
    blockers: list[BlockerReport] = field(default_factory=list)
    risks: list[RiskReport] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# Progress Tracker
# ============================================================================


class ProgressTracker:
    """
    Tracks and reports on task execution progress.

    Monitors task completion, detects blockers and risks, and generates
    comprehensive progress reports.
    """

    def __init__(self, status_monitor: AgentStatusMonitor):
        """
        Initialize progress tracker.

        Args:
            status_monitor: AgentStatusMonitor instance for agent state tracking
        """
        self.status_monitor = status_monitor

    def calculate_overall_progress(self, subtasks: list[Subtask]) -> float:
        """
        Calculate overall progress as percentage of completed tasks.

        Args:
            subtasks: List of subtasks to analyze

        Returns:
            Progress percentage (0-100), rounded to 2 decimal places
        """
        if not subtasks:
            return 0.0

        completed = sum(1 for task in subtasks if task.status == TaskStatus.COMPLETED)
        total = len(subtasks)

        progress = (completed / total) * 100
        return round(progress, 2)

    def get_task_counts(self, subtasks: list[Subtask]) -> dict[str, int]:
        """
        Get count of tasks by status.

        Args:
            subtasks: List of subtasks to analyze

        Returns:
            Dictionary with counts by status
        """
        counts = {
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "blocked": 0,
            "failed": 0,
            "total": len(subtasks),
        }

        for task in subtasks:
            if task.status == TaskStatus.COMPLETED:
                counts["completed"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                counts["in_progress"] += 1
            elif task.status == TaskStatus.PENDING:
                counts["pending"] += 1
            elif task.status == TaskStatus.BLOCKED:
                counts["blocked"] += 1
            elif task.status == TaskStatus.FAILED:
                counts["failed"] += 1

        return counts

    def detect_blockers(self, subtasks: list[Subtask]) -> list[BlockerReport]:
        """
        Detect blockers preventing task progress.

        Detects:
        - Stuck agents (no progress within threshold)
        - Blocked tasks (explicitly in BLOCKED state)
        - Dependency issues (failed dependencies)
        - Unassigned ready tasks (ready to start but no agent assigned)

        Args:
            subtasks: List of subtasks to analyze

        Returns:
            List of detected blockers
        """
        blockers: list[BlockerReport] = []

        # Detect stuck agents
        stuck_agents = self.status_monitor.detect_stuck_agents()
        for stuck in stuck_agents:
            blockers.append(
                BlockerReport(
                    blocker_type=BlockerType.STUCK_AGENT,
                    affected_items=[stuck.agent_id],
                    description=f"Agent {stuck.agent_id} stuck on '{stuck.current_task}' "
                    f"for {stuck.seconds_stuck:.1f}s",
                    severity="high",
                )
            )

        # Detect blocked tasks
        for task in subtasks:
            if task.status == TaskStatus.BLOCKED:
                blockers.append(
                    BlockerReport(
                        blocker_type=BlockerType.BLOCKED_TASK,
                        affected_items=[task.id],
                        description=f"Task {task.id} is blocked: {task.description}",
                        severity="high",
                    )
                )

        # Detect dependency issues (failed dependencies blocking other tasks)
        task_map = {t.id: t for t in subtasks}
        failed_task_ids = {t.id for t in subtasks if t.status == TaskStatus.FAILED}

        for task in subtasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                failed_deps = [dep for dep in task.dependencies if dep in failed_task_ids]
                if failed_deps:
                    blockers.append(
                        BlockerReport(
                            blocker_type=BlockerType.DEPENDENCY_ISSUE,
                            affected_items=[task.id] + failed_deps,
                            description=f"Task {task.id} blocked by failed "
                            f"dependencies: {', '.join(failed_deps)}",
                            severity="critical",
                        )
                    )

        # Detect unassigned ready tasks
        for task in subtasks:
            if task.status == TaskStatus.PENDING and task.assigned_agent is None:
                # Check if task is ready (all dependencies met)
                if not task.dependencies:
                    blockers.append(
                        BlockerReport(
                            blocker_type=BlockerType.UNASSIGNED_READY_TASK,
                            affected_items=[task.id],
                            description=f"Task {task.id} is ready but unassigned",
                            severity="medium",
                        )
                    )
                else:
                    # Check if all dependencies are complete
                    deps_complete = all(
                        task_map.get(dep_id, Subtask(id=dep_id, description="")).status
                        == TaskStatus.COMPLETED
                        for dep_id in task.dependencies
                    )
                    if deps_complete:
                        blockers.append(
                            BlockerReport(
                                blocker_type=BlockerType.UNASSIGNED_READY_TASK,
                                affected_items=[task.id],
                                description=f"Task {task.id} is ready but unassigned",
                                severity="medium",
                            )
                        )

        return blockers

    def detect_risks(
        self, subtasks: list[Subtask], execution_plan: ExecutionPlan
    ) -> list[RiskReport]:
        """
        Detect risks that could impact task completion.

        Detects:
        - Bottlenecks (tasks with many dependents)
        - Critical path delays
        - Low parallelism (sequential execution)

        Args:
            subtasks: List of subtasks to analyze
            execution_plan: Execution plan with dependency analysis

        Returns:
            List of detected risks
        """
        risks: list[RiskReport] = []

        if not subtasks or not execution_plan.stages:
            return risks

        # Detect bottlenecks from execution plan
        for bottleneck_id in execution_plan.bottlenecks:
            risks.append(
                RiskReport(
                    risk_type=RiskType.BOTTLENECK,
                    affected_items=[bottleneck_id],
                    description=f"Task {bottleneck_id} is a bottleneck "
                    f"(many tasks depend on it)",
                    impact="high",
                )
            )

        # Detect low parallelism risk
        if execution_plan.max_parallelism == 1 and len(subtasks) > 1:
            risks.append(
                RiskReport(
                    risk_type=RiskType.LOW_PARALLELISM,
                    affected_items=[],
                    description="Tasks are entirely sequential (no parallelism)",
                    impact="medium",
                )
            )

        return risks

    def generate_progress_report(
        self, subtasks: list[Subtask], execution_plan: ExecutionPlan
    ) -> ProgressReport:
        """
        Generate comprehensive progress report.

        Args:
            subtasks: List of subtasks to analyze
            execution_plan: Execution plan for the tasks

        Returns:
            Complete progress report with metrics, blockers, and risks
        """
        # Calculate progress
        overall_progress = self.calculate_overall_progress(subtasks)
        counts = self.get_task_counts(subtasks)

        # Detect issues
        blockers = self.detect_blockers(subtasks)
        risks = self.detect_risks(subtasks, execution_plan)

        return ProgressReport(
            overall_progress=overall_progress,
            completed_count=counts["completed"],
            in_progress_count=counts["in_progress"],
            pending_count=counts["pending"],
            blocked_count=counts["blocked"],
            failed_count=counts["failed"],
            total_count=counts["total"],
            blockers=blockers,
            risks=risks,
            timestamp=datetime.now(),
        )

    def format_progress_report(self, report: ProgressReport) -> str:
        """
        Format progress report as human-readable text.

        Args:
            report: ProgressReport to format

        Returns:
            Formatted text representation
        """
        lines = []
        lines.append("=" * 60)
        lines.append("Progress Report")
        lines.append("=" * 60)
        lines.append(f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Overall progress
        lines.append(f"Overall Progress: {report.overall_progress}%")
        lines.append(
            f"Tasks: {report.completed_count}/{report.total_count} completed "
            f"({report.in_progress_count} in progress, {report.pending_count} pending)"
        )

        if report.failed_count > 0:
            lines.append(f"⚠️  Failed tasks: {report.failed_count}")
        if report.blocked_count > 0:
            lines.append(f"🔴 Blocked tasks: {report.blocked_count}")

        lines.append("")

        # Blockers
        lines.append("Blockers:")
        if report.blockers:
            for blocker in report.blockers:
                severity_icon = {
                    "low": "ℹ️",
                    "medium": "⚠️",
                    "high": "🔴",
                    "critical": "🚨",
                }.get(blocker.severity, "⚠️")
                lines.append(
                    f"  {severity_icon} [{blocker.blocker_type.value}] {blocker.description}"
                )
        else:
            lines.append("  ✅ No blockers detected")

        lines.append("")

        # Risks
        lines.append("Risks:")
        if report.risks:
            for risk in report.risks:
                impact_icon = {
                    "low": "ℹ️",
                    "medium": "⚠️",
                    "high": "🔴",
                }.get(risk.impact, "⚠️")
                lines.append(f"  {impact_icon} [{risk.risk_type.value}] {risk.description}")
        else:
            lines.append("  ✅ No risks detected")

        lines.append("=" * 60)

        return "\n".join(lines)


# ============================================================================
# Singleton and Convenience Functions
# ============================================================================

_tracker_instance: ProgressTracker | None = None


def get_progress_tracker(
    status_monitor: AgentStatusMonitor | None = None,
) -> ProgressTracker:
    """Get the singleton progress tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        if status_monitor is None:
            from src.coordination.agent_status_monitor import get_agent_status_monitor

            status_monitor = get_agent_status_monitor()
        _tracker_instance = ProgressTracker(status_monitor)
    return _tracker_instance
