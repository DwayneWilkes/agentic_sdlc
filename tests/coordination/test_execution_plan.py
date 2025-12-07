"""Tests for execution plan generation."""

import pytest

from src.coordination.execution_plan import (
    ExecutionPlan,
    ExecutionPlanGenerator,
    ExecutionStage,
)
from src.models.task import Subtask


class TestExecutionStage:
    """Tests for ExecutionStage data model."""

    def test_create_execution_stage(self):
        """Test creating an execution stage."""
        stage = ExecutionStage(
            stage_number=1,
            tasks=["task1", "task2"],
            estimated_duration=5
        )

        assert stage.stage_number == 1
        assert stage.tasks == ["task1", "task2"]
        assert stage.estimated_duration == 5

    def test_execution_stage_defaults(self):
        """Test execution stage with minimal arguments."""
        stage = ExecutionStage(
            stage_number=0,
            tasks=[],
            estimated_duration=0
        )

        assert stage.stage_number == 0
        assert stage.tasks == []
        assert stage.estimated_duration == 0


class TestExecutionPlan:
    """Tests for ExecutionPlan data model."""

    def test_create_execution_plan(self):
        """Test creating an execution plan."""
        stage1 = ExecutionStage(1, ["task1"], 2)
        stage2 = ExecutionStage(2, ["task2", "task3"], 3)

        plan = ExecutionPlan(
            stages=[stage1, stage2],
            critical_path=["task1", "task2"],
            bottlenecks=["task2"],
            total_estimated_time=5,
            max_parallelism=2
        )

        assert len(plan.stages) == 2
        assert plan.critical_path == ["task1", "task2"]
        assert plan.bottlenecks == ["task2"]
        assert plan.total_estimated_time == 5
        assert plan.max_parallelism == 2

    def test_execution_plan_empty(self):
        """Test execution plan with no tasks."""
        plan = ExecutionPlan(
            stages=[],
            critical_path=[],
            bottlenecks=[],
            total_estimated_time=0,
            max_parallelism=0
        )

        assert plan.stages == []
        assert plan.critical_path == []
        assert plan.total_estimated_time == 0


class TestExecutionPlanGenerator:
    """Tests for ExecutionPlanGenerator."""

    def test_generate_simple_sequential_plan(self):
        """Test generating plan for simple sequential tasks."""
        tasks = [
            Subtask(id="task1", description="First task", dependencies=[]),
            Subtask(id="task2", description="Second task", dependencies=["task1"]),
            Subtask(id="task3", description="Third task", dependencies=["task2"]),
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)

        # Should have 3 stages (sequential)
        assert len(plan.stages) == 3
        assert plan.stages[0].tasks == ["task1"]
        assert plan.stages[1].tasks == ["task2"]
        assert plan.stages[2].tasks == ["task3"]

        # Critical path should be all tasks
        assert plan.critical_path == ["task1", "task2", "task3"]

        # Max parallelism should be 1
        assert plan.max_parallelism == 1

    def test_generate_parallel_plan(self):
        """Test generating plan for parallel tasks."""
        tasks = [
            Subtask(id="task1", description="Setup", dependencies=[]),
            Subtask(id="task2", description="Parallel A", dependencies=["task1"]),
            Subtask(id="task3", description="Parallel B", dependencies=["task1"]),
            Subtask(id="task4", description="Merge", dependencies=["task2", "task3"]),
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)

        # Should have 3 stages: [task1], [task2, task3], [task4]
        assert len(plan.stages) == 3
        assert plan.stages[0].tasks == ["task1"]
        assert set(plan.stages[1].tasks) == {"task2", "task3"}
        assert plan.stages[2].tasks == ["task4"]

        # Max parallelism should be 2
        assert plan.max_parallelism == 2

    def test_generate_complex_dag(self):
        """Test generating plan for complex DAG."""
        tasks = [
            Subtask(id="A", description="Task A", dependencies=[]),
            Subtask(id="B", description="Task B", dependencies=[]),
            Subtask(id="C", description="Task C", dependencies=["A"]),
            Subtask(id="D", description="Task D", dependencies=["A", "B"]),
            Subtask(id="E", description="Task E", dependencies=["C", "D"]),
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)

        # Should have stages with proper dependencies
        assert len(plan.stages) >= 3

        # First stage should have A and B (no dependencies)
        assert set(plan.stages[0].tasks) == {"A", "B"}

        # Max parallelism should be at least 2
        assert plan.max_parallelism >= 2

    def test_identify_bottlenecks(self):
        """Test bottleneck identification."""
        # Create a bottleneck: many tasks depend on one task
        tasks = [
            Subtask(id="bottleneck", description="Bottleneck", dependencies=[]),
            Subtask(id="task1", description="Task 1", dependencies=["bottleneck"]),
            Subtask(id="task2", description="Task 2", dependencies=["bottleneck"]),
            Subtask(id="task3", description="Task 3", dependencies=["bottleneck"]),
            Subtask(id="task4", description="Task 4", dependencies=["bottleneck"]),
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)

        # "bottleneck" should be identified as a bottleneck
        assert "bottleneck" in plan.bottlenecks

    def test_critical_path_calculation(self):
        """Test critical path calculation."""
        # Create a graph where one path is clearly longer
        tasks = [
            Subtask(id="A", description="Start", dependencies=[]),
            # Short path: A -> B
            Subtask(id="B", description="Short", dependencies=["A"]),
            # Long path: A -> C -> D -> E
            Subtask(id="C", description="Long 1", dependencies=["A"]),
            Subtask(id="D", description="Long 2", dependencies=["C"]),
            Subtask(id="E", description="Long 3", dependencies=["D"]),
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)

        # Critical path should include the longer path
        assert "A" in plan.critical_path
        assert "C" in plan.critical_path or "D" in plan.critical_path

    def test_estimate_completion_time(self):
        """Test completion time estimation."""
        tasks = [
            Subtask(id="task1", description="Task 1", dependencies=[],
                   metadata={"estimated_complexity": "large"}),
            Subtask(id="task2", description="Task 2", dependencies=["task1"],
                   metadata={"estimated_complexity": "small"}),
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)

        # Total time should be sum of sequential tasks
        # large (3) + small (1) = 4
        assert plan.total_estimated_time > 0

    def test_format_plan_text(self):
        """Test textual plan formatting."""
        tasks = [
            Subtask(id="task1", description="First", dependencies=[]),
            Subtask(id="task2", description="Second", dependencies=["task1"]),
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)
        formatted = generator.format_plan_text(plan)

        # Should contain key information
        assert "Stage" in formatted or "stage" in formatted
        assert "task1" in formatted
        assert "task2" in formatted
        assert "Critical Path" in formatted or "critical path" in formatted

    def test_empty_task_list(self):
        """Test generating plan with no tasks."""
        generator = ExecutionPlanGenerator()
        plan = generator.generate([])

        assert plan.stages == []
        assert plan.critical_path == []
        assert plan.total_estimated_time == 0
        assert plan.max_parallelism == 0

    def test_single_task(self):
        """Test generating plan with single task."""
        tasks = [
            Subtask(id="only", description="Only task", dependencies=[])
        ]

        generator = ExecutionPlanGenerator()
        plan = generator.generate(tasks)

        assert len(plan.stages) == 1
        assert plan.stages[0].tasks == ["only"]
        assert plan.critical_path == ["only"]
        assert plan.max_parallelism == 1

    def test_circular_dependency_handling(self):
        """Test that circular dependencies are handled."""
        # Create circular dependency
        tasks = [
            Subtask(id="A", description="Task A", dependencies=["B"]),
            Subtask(id="B", description="Task B", dependencies=["A"]),
        ]

        generator = ExecutionPlanGenerator()

        # Should raise an error or handle gracefully
        with pytest.raises(ValueError, match="(?i)circular|cycle"):
            generator.generate(tasks)

    def test_missing_dependency_handling(self):
        """Test that missing dependencies are handled."""
        tasks = [
            Subtask(id="A", description="Task A", dependencies=["MISSING"]),
        ]

        generator = ExecutionPlanGenerator()

        # Should raise an error
        with pytest.raises(ValueError, match="missing|not found"):
            generator.generate(tasks)
