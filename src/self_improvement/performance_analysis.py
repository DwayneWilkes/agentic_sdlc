"""
Performance Analysis Engine (Phase 8.1).

Analyzes orchestrator performance post-task to identify inefficiencies
in decomposition, agent selection, and coordination. Generates improvement
opportunities for Phase 8.2 strategy optimization.
"""

from dataclasses import dataclass, field
from typing import Any

from src.core.task_decomposer import DependencyGraph


@dataclass
class ImprovementOpportunity:
    """
    Represents an opportunity to improve orchestrator performance.

    Categorized by decomposition, selection, or coordination inefficiencies.
    """

    id: str
    category: str  # "decomposition", "selection", "coordination"
    description: str
    impact: str  # "low", "medium", "high"
    evidence: dict[str, Any]
    suggested_action: str


@dataclass
class DecompositionMetrics:
    """
    Metrics about task decomposition quality.

    Measures granularity, depth, dependencies, and parallel potential.
    """

    avg_subtask_count: int
    max_depth: int
    avg_dependencies_per_task: float
    parallel_potential: float  # 0.0-1.0
    granularity_score: float  # 0.0-1.0 (1.0 = optimal)


@dataclass
class SelectionMetrics:
    """
    Metrics about agent-task alignment and selection quality.

    Measures how well agents are matched to tasks and workload balance.
    """

    agent_task_alignment_score: float  # 0.0-1.0
    agent_utilization: dict[str, float]  # Agent -> utilization (0.0-1.0)
    reassignment_count: int
    role_mismatch_count: int


@dataclass
class CoordinationMetrics:
    """
    Metrics about coordination overhead and efficiency.

    Measures handoffs, blockers, idle time, and message volume.
    """

    total_handoffs: int
    avg_handoff_time: float  # Seconds
    blocker_count: int
    idle_time_percentage: float
    message_volume: int


@dataclass
class PerformanceReport:
    """
    Complete performance analysis report for an execution.

    Combines decomposition, selection, and coordination metrics with
    improvement opportunities and overall efficiency score.
    """

    execution_id: str
    timestamp: str
    decomposition: DecompositionMetrics
    selection: SelectionMetrics
    coordination: CoordinationMetrics
    opportunities: list[ImprovementOpportunity] = field(default_factory=list)
    overall_efficiency_score: float = 0.0  # 0.0-1.0


class PerformanceAnalysisEngine:
    """
    Analyzes orchestrator performance to identify improvement opportunities.

    Usage:
        engine = PerformanceAnalysisEngine()
        report = engine.analyze_execution("exec-123")
        print(engine.format_report(report))
    """

    # Constants for analysis thresholds
    OPTIMAL_SUBTASK_COUNT = 10  # Sweet spot for task count
    MAX_ACCEPTABLE_DEPTH = 3
    OPTIMAL_DEPENDENCIES_PER_TASK = 2.0
    MIN_PARALLEL_POTENTIAL = 0.5
    ALIGNMENT_THRESHOLD = 0.75
    UTILIZATION_BALANCE_THRESHOLD = 0.3  # Max variance in utilization
    MAX_ACCEPTABLE_HANDOFFS = 10
    MAX_ACCEPTABLE_IDLE_PERCENTAGE = 15.0

    def _analyze_decomposition(self, graph: DependencyGraph) -> DecompositionMetrics:
        """
        Analyze task decomposition quality.

        Args:
            graph: Dependency graph of subtasks

        Returns:
            DecompositionMetrics with quality indicators
        """
        # Access internal nodes dict (DependencyGraph doesn't expose get_all_nodes)
        nodes = list(graph._nodes.values())
        node_count = len(nodes)

        if node_count == 0:
            return DecompositionMetrics(
                avg_subtask_count=0,
                max_depth=0,
                avg_dependencies_per_task=0.0,
                parallel_potential=0.0,
                granularity_score=0.0,
            )

        # Calculate max depth
        max_depth = max(node.depth for node in nodes)

        # Calculate average dependencies per task
        total_deps = sum(len(node.dependencies) for node in nodes)
        avg_deps = total_deps / node_count if node_count > 0 else 0.0

        # Calculate parallel potential (tasks with no dependencies / total tasks)
        tasks_with_no_deps = sum(1 for node in nodes if not node.dependencies)
        parallel_potential = tasks_with_no_deps / node_count if node_count > 0 else 0.0

        # Calculate granularity score (how close to optimal task count)
        # Score = 1.0 at optimal count, decreases as we move away
        distance_from_optimal = abs(node_count - self.OPTIMAL_SUBTASK_COUNT)
        granularity_score = max(0.0, 1.0 - (distance_from_optimal / self.OPTIMAL_SUBTASK_COUNT))

        return DecompositionMetrics(
            avg_subtask_count=node_count,
            max_depth=max_depth,
            avg_dependencies_per_task=avg_deps,
            parallel_potential=parallel_potential,
            granularity_score=granularity_score,
        )

    def _analyze_selection(
        self,
        assignments: dict[str, str],
        agent_capabilities: dict[str, dict[str, Any]],
        task_types: dict[str, str],
    ) -> SelectionMetrics:
        """
        Analyze agent-task alignment and selection quality.

        Args:
            assignments: Task ID -> Agent name mapping
            agent_capabilities: Agent name -> capabilities dict
            task_types: Task ID -> task type mapping

        Returns:
            SelectionMetrics with alignment and utilization data
        """
        if not assignments:
            return SelectionMetrics(
                agent_task_alignment_score=0.0,
                agent_utilization={},
                reassignment_count=0,
                role_mismatch_count=0,
            )

        # Calculate agent utilization (tasks per agent / total tasks)
        agent_task_counts: dict[str, int] = {}
        for task_id, agent_name in assignments.items():
            agent_task_counts[agent_name] = agent_task_counts.get(agent_name, 0) + 1

        total_tasks = len(assignments)
        agent_utilization = {
            agent: count / total_tasks
            for agent, count in agent_task_counts.items()
        }

        # Calculate role mismatch count
        role_mismatch_count = 0
        for task_id, agent_name in assignments.items():
            task_type = task_types.get(task_id, "unknown")
            agent_role = agent_capabilities.get(agent_name, {}).get("role", "unknown")

            # Simple role matching (coder -> coding, reviewer -> review, etc.)
            if task_type == "coding" and agent_role != "coder":
                role_mismatch_count += 1
            elif task_type == "review" and agent_role != "reviewer":
                role_mismatch_count += 1

        # Calculate alignment score (1.0 - mismatch_rate)
        mismatch_rate = role_mismatch_count / total_tasks if total_tasks > 0 else 0.0
        alignment_score = 1.0 - mismatch_rate

        # Reassignment count would come from execution history
        # For now, set to 0 (can be enhanced later)
        reassignment_count = 0

        return SelectionMetrics(
            agent_task_alignment_score=alignment_score,
            agent_utilization=agent_utilization,
            reassignment_count=reassignment_count,
            role_mismatch_count=role_mismatch_count,
        )

    def _analyze_coordination(
        self,
        handoffs: list[dict[str, Any]],
        blockers: list[dict[str, Any]],
        total_time: float,
        idle_time: float,
        message_count: int,
    ) -> CoordinationMetrics:
        """
        Analyze coordination overhead and efficiency.

        Args:
            handoffs: List of handoff events with duration
            blockers: List of blocker events
            total_time: Total execution time (seconds)
            idle_time: Total idle time (seconds)
            message_count: Total inter-agent messages

        Returns:
            CoordinationMetrics with overhead indicators
        """
        total_handoffs = len(handoffs)

        # Calculate average handoff time
        if total_handoffs > 0:
            total_handoff_time = sum(h.get("duration", 0) for h in handoffs)
            avg_handoff_time = total_handoff_time / total_handoffs
        else:
            avg_handoff_time = 0.0

        blocker_count = len(blockers)

        # Calculate idle time percentage
        idle_percentage = (idle_time / total_time * 100.0) if total_time > 0 else 0.0

        return CoordinationMetrics(
            total_handoffs=total_handoffs,
            avg_handoff_time=avg_handoff_time,
            blocker_count=blocker_count,
            idle_time_percentage=idle_percentage,
            message_volume=message_count,
        )

    def _identify_opportunities(
        self,
        decomposition: DecompositionMetrics,
        selection: SelectionMetrics,
        coordination: CoordinationMetrics,
    ) -> list[ImprovementOpportunity]:
        """
        Identify improvement opportunities based on metrics.

        Args:
            decomposition: Decomposition metrics
            selection: Selection metrics
            coordination: Coordination metrics

        Returns:
            List of improvement opportunities prioritized by impact
        """
        opportunities: list[ImprovementOpportunity] = []
        opp_counter = 0

        # Check decomposition issues
        if decomposition.granularity_score < 0.7:
            opp_counter += 1
            impact = "high" if decomposition.granularity_score < 0.5 else "medium"
            desc = (
                f"Task decomposition granularity is suboptimal "
                f"({decomposition.avg_subtask_count} tasks vs optimal {self.OPTIMAL_SUBTASK_COUNT})"
            )
            action = (
                "Merge related subtasks"
                if decomposition.avg_subtask_count > self.OPTIMAL_SUBTASK_COUNT
                else "Break down large tasks further"
            )
            opportunities.append(
                ImprovementOpportunity(
                    id=f"opp-{opp_counter}",
                    category="decomposition",
                    description=desc,
                    impact=impact,
                    evidence={
                        "avg_subtask_count": decomposition.avg_subtask_count,
                        "granularity_score": decomposition.granularity_score,
                    },
                    suggested_action=action,
                )
            )

        if decomposition.parallel_potential < self.MIN_PARALLEL_POTENTIAL:
            opp_counter += 1
            opportunities.append(
                ImprovementOpportunity(
                    id=f"opp-{opp_counter}",
                    category="decomposition",
                    description=f"Low parallel potential ({decomposition.parallel_potential:.1%})",
                    impact="medium",
                    evidence={"parallel_potential": decomposition.parallel_potential},
                    suggested_action="Reduce unnecessary dependencies to enable parallel execution",
                )
            )

        # Check selection issues
        if selection.agent_task_alignment_score < self.ALIGNMENT_THRESHOLD:
            opp_counter += 1
            opportunities.append(
                ImprovementOpportunity(
                    id=f"opp-{opp_counter}",
                    category="selection",
                    description=(
                        f"Poor agent-task alignment "
                        f"({selection.agent_task_alignment_score:.1%})"
                    ),
                    impact="high",
                    evidence={
                        "alignment_score": selection.agent_task_alignment_score,
                        "role_mismatch_count": selection.role_mismatch_count,
                    },
                    suggested_action="Improve agent selection to match task types with agent roles",
                )
            )

        # Check for unbalanced utilization
        if selection.agent_utilization:
            utilization_values = list(selection.agent_utilization.values())
            utilization_variance = max(utilization_values) - min(utilization_values)
            if utilization_variance > self.UTILIZATION_BALANCE_THRESHOLD:
                opp_counter += 1
                opportunities.append(
                    ImprovementOpportunity(
                        id=f"opp-{opp_counter}",
                        category="selection",
                        description=(
                            f"Unbalanced agent utilization "
                            f"(variance: {utilization_variance:.1%})"
                        ),
                        impact="medium",
                        evidence={"agent_utilization": selection.agent_utilization},
                        suggested_action="Redistribute tasks more evenly across agents",
                    )
                )

        # Check coordination issues
        if coordination.total_handoffs > self.MAX_ACCEPTABLE_HANDOFFS:
            opp_counter += 1
            opportunities.append(
                ImprovementOpportunity(
                    id=f"opp-{opp_counter}",
                    category="coordination",
                    description=f"Excessive handoffs ({coordination.total_handoffs})",
                    impact="high",
                    evidence={"total_handoffs": coordination.total_handoffs},
                    suggested_action="Batch related tasks to same agent to reduce handoffs",
                )
            )

        if coordination.blocker_count > 0:
            opp_counter += 1
            impact = "high" if coordination.blocker_count >= 5 else "medium"
            opportunities.append(
                ImprovementOpportunity(
                    id=f"opp-{opp_counter}",
                    category="coordination",
                    description=f"Multiple blockers encountered ({coordination.blocker_count})",
                    impact=impact,
                    evidence={"blocker_count": coordination.blocker_count},
                    suggested_action="Review dependency graph to eliminate blockers",
                )
            )

        if coordination.idle_time_percentage > self.MAX_ACCEPTABLE_IDLE_PERCENTAGE:
            opp_counter += 1
            opportunities.append(
                ImprovementOpportunity(
                    id=f"opp-{opp_counter}",
                    category="coordination",
                    description=f"High idle time ({coordination.idle_time_percentage:.1f}%)",
                    impact="medium",
                    evidence={"idle_time_percentage": coordination.idle_time_percentage},
                    suggested_action="Improve task scheduling to reduce idle time",
                )
            )

        return opportunities

    def format_report(self, report: PerformanceReport) -> str:
        """
        Format performance report as human-readable text.

        Args:
            report: Performance report to format

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("PERFORMANCE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Execution ID: {report.execution_id}")
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append(f"Overall Efficiency Score: {report.overall_efficiency_score:.1%}")
        lines.append("")

        # Decomposition section
        lines.append("DECOMPOSITION METRICS")
        lines.append("-" * 80)
        d = report.decomposition
        lines.append(f"  Subtask Count: {d.avg_subtask_count}")
        lines.append(f"  Max Depth: {d.max_depth}")
        lines.append(f"  Avg Dependencies/Task: {d.avg_dependencies_per_task:.2f}")
        lines.append(f"  Parallel Potential: {d.parallel_potential:.1%}")
        lines.append(f"  Granularity Score: {d.granularity_score:.1%}")
        lines.append("")

        # Selection section
        lines.append("AGENT SELECTION METRICS")
        lines.append("-" * 80)
        s = report.selection
        lines.append(f"  Alignment Score: {s.agent_task_alignment_score:.1%}")
        lines.append(f"  Role Mismatches: {s.role_mismatch_count}")
        lines.append(f"  Reassignments: {s.reassignment_count}")
        lines.append("  Agent Utilization:")
        for agent, util in s.agent_utilization.items():
            lines.append(f"    {agent}: {util:.1%}")
        lines.append("")

        # Coordination section
        lines.append("COORDINATION METRICS")
        lines.append("-" * 80)
        c = report.coordination
        lines.append(f"  Total Handoffs: {c.total_handoffs}")
        lines.append(f"  Avg Handoff Time: {c.avg_handoff_time:.1f}s")
        lines.append(f"  Blockers: {c.blocker_count}")
        lines.append(f"  Idle Time: {c.idle_time_percentage:.1f}%")
        lines.append(f"  Message Volume: {c.message_volume}")
        lines.append("")

        # Improvement opportunities
        if report.opportunities:
            lines.append("IMPROVEMENT OPPORTUNITIES")
            lines.append("-" * 80)
            for opp in report.opportunities:
                lines.append(f"  [{opp.impact.upper()}] {opp.description}")
                lines.append(f"    Action: {opp.suggested_action}")
                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)
