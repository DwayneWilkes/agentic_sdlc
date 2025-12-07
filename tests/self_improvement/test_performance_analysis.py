"""
Tests for Performance Analysis Engine (Phase 8.1).

Tests analyze orchestrator performance post-task to identify inefficiencies
in decomposition, agent selection, and coordination.
"""

import pytest

from src.core.task_decomposer import DependencyGraph, SubtaskNode
from src.self_improvement.performance_analysis import (
    CoordinationMetrics,
    DecompositionMetrics,
    ImprovementOpportunity,
    PerformanceAnalysisEngine,
    PerformanceReport,
    SelectionMetrics,
)


class TestImprovementOpportunity:
    """Test ImprovementOpportunity dataclass."""

    def test_create_opportunity(self):
        """Test creating an improvement opportunity."""
        opp = ImprovementOpportunity(
            id="opp-1",
            category="decomposition",
            description="Task decomposition too granular",
            impact="medium",
            evidence={"avg_subtasks": 25, "threshold": 10},
            suggested_action="Merge related subtasks",
        )

        assert opp.id == "opp-1"
        assert opp.category == "decomposition"
        assert opp.impact == "medium"
        assert opp.evidence["avg_subtasks"] == 25


class TestDecompositionMetrics:
    """Test DecompositionMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating decomposition metrics."""
        metrics = DecompositionMetrics(
            avg_subtask_count=8,
            max_depth=3,
            avg_dependencies_per_task=2.5,
            parallel_potential=0.65,
            granularity_score=0.9,
        )

        assert metrics.avg_subtask_count == 8
        assert metrics.max_depth == 3
        assert metrics.parallel_potential == 0.65
        assert metrics.granularity_score == 0.9


class TestSelectionMetrics:
    """Test SelectionMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating selection metrics."""
        metrics = SelectionMetrics(
            agent_task_alignment_score=0.85,
            agent_utilization={"agent-1": 0.9, "agent-2": 0.7},
            reassignment_count=2,
            role_mismatch_count=1,
        )

        assert metrics.agent_task_alignment_score == 0.85
        assert metrics.agent_utilization["agent-1"] == 0.9
        assert metrics.reassignment_count == 2


class TestCoordinationMetrics:
    """Test CoordinationMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating coordination metrics."""
        metrics = CoordinationMetrics(
            total_handoffs=15,
            avg_handoff_time=45.5,
            blocker_count=3,
            idle_time_percentage=12.5,
            message_volume=150,
        )

        assert metrics.total_handoffs == 15
        assert metrics.avg_handoff_time == 45.5
        assert metrics.blocker_count == 3
        assert metrics.idle_time_percentage == 12.5


class TestPerformanceReport:
    """Test PerformanceReport dataclass."""

    def test_create_report(self):
        """Test creating a performance report."""
        decomp = DecompositionMetrics(
            avg_subtask_count=8,
            max_depth=3,
            avg_dependencies_per_task=2.0,
            parallel_potential=0.7,
            granularity_score=0.9,
        )
        selection = SelectionMetrics(
            agent_task_alignment_score=0.85,
            agent_utilization={"agent-1": 0.8},
            reassignment_count=1,
            role_mismatch_count=0,
        )
        coordination = CoordinationMetrics(
            total_handoffs=10,
            avg_handoff_time=30.0,
            blocker_count=2,
            idle_time_percentage=10.0,
            message_volume=100,
        )
        opportunities = [
            ImprovementOpportunity(
                id="opp-1",
                category="coordination",
                description="Reduce handoffs",
                impact="high",
                evidence={},
                suggested_action="Batch tasks",
            )
        ]

        report = PerformanceReport(
            execution_id="exec-123",
            timestamp="2025-12-07T10:00:00",
            decomposition=decomp,
            selection=selection,
            coordination=coordination,
            opportunities=opportunities,
            overall_efficiency_score=0.82,
        )

        assert report.execution_id == "exec-123"
        assert report.overall_efficiency_score == 0.82
        assert len(report.opportunities) == 1


class TestPerformanceAnalysisEngine:
    """Test PerformanceAnalysisEngine class."""

    def test_analyze_decomposition_optimal(self):
        """Test analyzing optimal task decomposition."""
        engine = PerformanceAnalysisEngine()

        # Create a well-balanced dependency graph
        graph = DependencyGraph()
        for i in range(8):
            node = SubtaskNode(
                id=f"task-{i}",
                description=f"Task {i}",
                parent_id=None,
                depth=1,
                dependencies=[],
                estimated_complexity="medium",
            )
            graph.add_node(node)

        # Add some dependencies to create structure
        graph.add_dependency("task-2", "task-0")
        graph.add_dependency("task-3", "task-1")
        graph.add_dependency("task-6", "task-4")

        # Update node dependencies to match graph edges
        graph._nodes["task-2"].dependencies = ["task-0"]
        graph._nodes["task-3"].dependencies = ["task-1"]
        graph._nodes["task-6"].dependencies = ["task-4"]

        metrics = engine._analyze_decomposition(graph)

        assert metrics.avg_subtask_count == 8
        assert metrics.max_depth == 1
        assert metrics.avg_dependencies_per_task == pytest.approx(0.375, abs=0.1)
        assert 0.0 <= metrics.parallel_potential <= 1.0
        assert 0.0 <= metrics.granularity_score <= 1.0

    def test_analyze_decomposition_too_granular(self):
        """Test detecting overly granular decomposition."""
        engine = PerformanceAnalysisEngine()

        # Create many small tasks (too granular)
        graph = DependencyGraph()
        for i in range(30):
            node = SubtaskNode(
                id=f"task-{i}",
                description=f"Small task {i}",
                parent_id=None,
                depth=1,
                dependencies=[],
                estimated_complexity="small",
            )
            graph.add_node(node)

        metrics = engine._analyze_decomposition(graph)

        assert metrics.avg_subtask_count == 30
        # Granularity score should be low (far from optimal)
        assert metrics.granularity_score < 0.7

    def test_analyze_decomposition_deep_nesting(self):
        """Test detecting overly deep task nesting."""
        engine = PerformanceAnalysisEngine()

        # Create deeply nested tasks
        graph = DependencyGraph()
        for i in range(5):
            node = SubtaskNode(
                id=f"task-{i}",
                description=f"Nested task {i}",
                parent_id=f"task-{i-1}" if i > 0 else None,
                depth=i + 1,
                dependencies=[f"task-{i-1}"] if i > 0 else [],
            )
            graph.add_node(node)
            if i > 0:
                graph.add_dependency(f"task-{i}", f"task-{i-1}")

        metrics = engine._analyze_decomposition(graph)

        assert metrics.max_depth == 5
        # Should have limited parallel potential due to sequential dependencies
        assert metrics.parallel_potential < 0.3

    def test_analyze_selection_well_aligned(self):
        """Test analyzing well-aligned agent selection."""
        engine = PerformanceAnalysisEngine()

        assignments = {
            "task-1": "coder-agent",
            "task-2": "coder-agent",
            "task-3": "reviewer-agent",
        }

        agent_capabilities = {
            "coder-agent": {"role": "coder", "skills": ["python", "testing"]},
            "reviewer-agent": {"role": "reviewer", "skills": ["review"]},
        }

        task_types = {
            "task-1": "coding",
            "task-2": "coding",
            "task-3": "review",
        }

        metrics = engine._analyze_selection(assignments, agent_capabilities, task_types)

        assert metrics.agent_task_alignment_score >= 0.8
        assert metrics.role_mismatch_count == 0

    def test_analyze_selection_misaligned(self):
        """Test detecting misaligned agent-task assignments."""
        engine = PerformanceAnalysisEngine()

        assignments = {
            "task-1": "reviewer-agent",  # Mismatch: reviewer doing coding
            "task-2": "coder-agent",
            "task-3": "coder-agent",  # Mismatch: coder doing review
        }

        agent_capabilities = {
            "coder-agent": {"role": "coder", "skills": ["python"]},
            "reviewer-agent": {"role": "reviewer", "skills": ["review"]},
        }

        task_types = {
            "task-1": "coding",
            "task-2": "coding",
            "task-3": "review",
        }

        metrics = engine._analyze_selection(assignments, agent_capabilities, task_types)

        assert metrics.agent_task_alignment_score < 0.7
        assert metrics.role_mismatch_count == 2

    def test_analyze_selection_unbalanced_utilization(self):
        """Test detecting unbalanced agent utilization."""
        engine = PerformanceAnalysisEngine()

        # One agent overloaded, one underutilized
        assignments = {
            "task-1": "agent-1",
            "task-2": "agent-1",
            "task-3": "agent-1",
            "task-4": "agent-1",
            "task-5": "agent-2",  # Only 1 task
        }

        agent_capabilities = {
            "agent-1": {"role": "coder", "skills": ["python"]},
            "agent-2": {"role": "coder", "skills": ["python"]},
        }

        task_types = {f"task-{i}": "coding" for i in range(1, 6)}

        metrics = engine._analyze_selection(assignments, agent_capabilities, task_types)

        assert metrics.agent_utilization["agent-1"] == pytest.approx(0.8, abs=0.1)
        assert metrics.agent_utilization["agent-2"] == pytest.approx(0.2, abs=0.1)

    def test_analyze_coordination_efficient(self):
        """Test analyzing efficient coordination."""
        engine = PerformanceAnalysisEngine()

        handoffs = [
            {"from": "agent-1", "to": "agent-2", "duration": 30},
            {"from": "agent-2", "to": "agent-3", "duration": 25},
        ]

        blockers = []

        total_time = 1000
        idle_time = 50
        message_count = 20

        metrics = engine._analyze_coordination(
            handoffs, blockers, total_time, idle_time, message_count
        )

        assert metrics.total_handoffs == 2
        assert metrics.avg_handoff_time == pytest.approx(27.5, abs=1.0)
        assert metrics.blocker_count == 0
        assert metrics.idle_time_percentage == pytest.approx(5.0, abs=0.1)

    def test_analyze_coordination_excessive_handoffs(self):
        """Test detecting excessive handoffs."""
        engine = PerformanceAnalysisEngine()

        # Many handoffs indicate coordination overhead
        handoffs = [{"from": f"agent-{i}", "to": f"agent-{i+1}", "duration": 45}
                    for i in range(20)]

        metrics = engine._analyze_coordination(handoffs, [], 1000, 100, 200)

        assert metrics.total_handoffs == 20
        assert metrics.avg_handoff_time == 45

    def test_identify_opportunities_from_metrics(self):
        """Test identifying improvement opportunities from metrics."""
        engine = PerformanceAnalysisEngine()

        # Create metrics indicating inefficiencies
        decomp = DecompositionMetrics(
            avg_subtask_count=30,  # Too granular
            max_depth=2,
            avg_dependencies_per_task=1.0,
            parallel_potential=0.3,  # Low parallelism
            granularity_score=0.4,
        )

        selection = SelectionMetrics(
            agent_task_alignment_score=0.6,  # Poor alignment
            agent_utilization={"agent-1": 0.95, "agent-2": 0.3},  # Unbalanced
            reassignment_count=5,  # Many reassignments
            role_mismatch_count=3,
        )

        coordination = CoordinationMetrics(
            total_handoffs=25,  # Excessive
            avg_handoff_time=60,
            blocker_count=5,  # Many blockers
            idle_time_percentage=20,  # High idle time
            message_volume=500,
        )

        opportunities = engine._identify_opportunities(decomp, selection, coordination)

        # Should identify multiple opportunities
        assert len(opportunities) > 0

        # Should include decomposition issue
        decomp_opps = [o for o in opportunities if o.category == "decomposition"]
        assert len(decomp_opps) > 0

        # Should include selection issue
        selection_opps = [o for o in opportunities if o.category == "selection"]
        assert len(selection_opps) > 0

        # Should include coordination issue
        coord_opps = [o for o in opportunities if o.category == "coordination"]
        assert len(coord_opps) > 0

    def test_format_report_readable(self):
        """Test formatting performance report as human-readable text."""
        engine = PerformanceAnalysisEngine()

        report = PerformanceReport(
            execution_id="exec-123",
            timestamp="2025-12-07T10:00:00",
            decomposition=DecompositionMetrics(
                avg_subtask_count=8,
                max_depth=3,
                avg_dependencies_per_task=2.0,
                parallel_potential=0.7,
                granularity_score=0.9,
            ),
            selection=SelectionMetrics(
                agent_task_alignment_score=0.85,
                agent_utilization={"agent-1": 0.8},
                reassignment_count=1,
                role_mismatch_count=0,
            ),
            coordination=CoordinationMetrics(
                total_handoffs=10,
                avg_handoff_time=30.0,
                blocker_count=2,
                idle_time_percentage=10.0,
                message_volume=100,
            ),
            opportunities=[
                ImprovementOpportunity(
                    id="opp-1",
                    category="coordination",
                    description="Reduce idle time",
                    impact="medium",
                    evidence={},
                    suggested_action="Improve task scheduling",
                )
            ],
            overall_efficiency_score=0.82,
        )

        formatted = engine.format_report(report)

        # Should contain key sections
        assert "PERFORMANCE ANALYSIS REPORT" in formatted
        assert "exec-123" in formatted
        assert "DECOMPOSITION" in formatted
        assert "SELECTION" in formatted
        assert "COORDINATION" in formatted
        assert "IMPROVEMENT OPPORTUNITIES" in formatted
        assert "82.0%" in formatted  # Efficiency score shown as percentage
