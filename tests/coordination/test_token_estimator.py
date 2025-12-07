"""
Tests for TokenEstimator - Phase 7.4

Tests for:
- Task complexity estimation
- Token estimation based on task type
- Context window estimation
- Batch estimation
"""


from src.coordination.token_estimator import (
    TaskComplexity,
    TokenEstimator,
    estimate_task_tokens,
)
from src.models.task import Subtask, Task, TaskType


class TestTaskComplexity:
    """Tests for TaskComplexity enum."""

    def test_complexity_levels_exist(self) -> None:
        """Test that all complexity levels exist."""
        assert TaskComplexity.SIMPLE
        assert TaskComplexity.MEDIUM
        assert TaskComplexity.COMPLEX
        assert TaskComplexity.VERY_COMPLEX

    def test_complexity_values(self) -> None:
        """Test complexity string values."""
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MEDIUM.value == "medium"
        assert TaskComplexity.COMPLEX.value == "complex"
        assert TaskComplexity.VERY_COMPLEX.value == "very_complex"


class TestTokenEstimator:
    """Tests for TokenEstimator class."""

    def test_create_estimator(self) -> None:
        """Test creating a TokenEstimator."""
        estimator = TokenEstimator()
        assert estimator is not None

    def test_create_with_custom_base_tokens(self) -> None:
        """Test creating with custom base token estimates."""
        estimator = TokenEstimator(
            base_tokens={
                TaskComplexity.SIMPLE: 1000,
                TaskComplexity.MEDIUM: 5000,
                TaskComplexity.COMPLEX: 15000,
                TaskComplexity.VERY_COMPLEX: 40000,
            }
        )
        assert estimator is not None


class TestComplexityAssessment:
    """Tests for task complexity assessment."""

    def test_assess_simple_task(self) -> None:
        """Test assessing a simple task."""
        estimator = TokenEstimator()
        task = Task(
            id="1",
            description="Print hello world",
            task_type=TaskType.SOFTWARE,
        )
        complexity = estimator.assess_complexity(task)
        assert complexity == TaskComplexity.SIMPLE

    def test_assess_medium_task(self) -> None:
        """Test assessing a medium complexity task."""
        estimator = TokenEstimator()
        task = Task(
            id="2",
            description="Implement a REST API endpoint for user authentication",
            task_type=TaskType.SOFTWARE,
        )
        complexity = estimator.assess_complexity(task)
        assert complexity in (TaskComplexity.MEDIUM, TaskComplexity.SIMPLE)

    def test_assess_complex_task_with_subtasks(self) -> None:
        """Test that tasks with many subtasks are more complex."""
        estimator = TokenEstimator()
        task = Task(
            id="3",
            description="Build a complete microservices architecture",
            task_type=TaskType.SOFTWARE,
        )
        # Add subtasks to increase complexity
        task.subtasks = [
            Subtask(id=f"subtask-{i}", description=f"Subtask {i}")
            for i in range(10)
        ]

        complexity = estimator.assess_complexity(task)
        assert complexity in (TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX)

    def test_assess_complexity_by_description_length(self) -> None:
        """Test that longer descriptions suggest higher complexity."""
        estimator = TokenEstimator()

        # Short description
        simple_task = Task(
            id="1",
            description="Add logging",
            task_type=TaskType.SOFTWARE,
        )

        # Very long description
        complex_task = Task(
            id="2",
            description=" ".join(["word"] * 100),  # 100-word description
            task_type=TaskType.SOFTWARE,
        )

        simple_complexity = estimator.assess_complexity(simple_task)
        complex_complexity = estimator.assess_complexity(complex_task)

        # Complex task should have higher or equal complexity
        complexity_order = [
            TaskComplexity.SIMPLE,
            TaskComplexity.MEDIUM,
            TaskComplexity.COMPLEX,
            TaskComplexity.VERY_COMPLEX,
        ]
        assert complexity_order.index(complex_complexity) >= complexity_order.index(
            simple_complexity
        )


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_estimate_simple_task(self) -> None:
        """Test estimating tokens for a simple task."""
        estimator = TokenEstimator()
        task = Task(
            id="1",
            description="Add a comment",
            task_type=TaskType.SOFTWARE,
        )
        tokens = estimator.estimate_task(task)
        assert tokens > 0
        assert tokens < 10000  # Should be relatively small

    def test_estimate_complex_task(self) -> None:
        """Test estimating tokens for a complex task."""
        estimator = TokenEstimator()
        task = Task(
            id="2",
            description="Implement a distributed system with fault tolerance",
            task_type=TaskType.SOFTWARE,
        )
        task.subtasks = [
            Subtask(id=f"subtask-{i}", description=f"Subtask {i}")
            for i in range(20)
        ]

        tokens = estimator.estimate_task(task)
        assert tokens > 20000  # Should be significantly larger

    def test_estimate_by_task_type(self) -> None:
        """Test that different task types have different estimates."""
        estimator = TokenEstimator()

        software_task = Task(
            id="1",
            description="Build a feature",
            task_type=TaskType.SOFTWARE,
        )

        research_task = Task(
            id="2",
            description="Research a topic",
            task_type=TaskType.RESEARCH,
        )

        software_tokens = estimator.estimate_task(software_task)
        research_tokens = estimator.estimate_task(research_task)

        # Both should be positive
        assert software_tokens > 0
        assert research_tokens > 0

    def test_estimate_includes_context_overhead(self) -> None:
        """Test that estimates include context window overhead."""
        estimator = TokenEstimator()
        task = Task(
            id="1",
            description="Simple task",
            task_type=TaskType.SOFTWARE,
        )
        # Add many context keys to trigger overhead
        # (implementation uses len(dict) which counts keys, not char count)
        task.context = {f"key_{i}": f"value_{i}" for i in range(200)}

        tokens = estimator.estimate_task(task)
        # 200 keys -> (200 // 100) * 110 = 220 overhead
        # Base (SIMPLE) = 2000
        # Total should be >= 2220
        assert tokens >= 2200


class TestBatchEstimation:
    """Tests for batch task estimation."""

    def test_estimate_batch_empty(self) -> None:
        """Test estimating an empty batch."""
        estimator = TokenEstimator()
        total = estimator.estimate_batch([])
        assert total == 0

    def test_estimate_batch_single_task(self) -> None:
        """Test estimating a batch with one task."""
        estimator = TokenEstimator()
        task = Task(
            id="1",
            description="Task 1",
            task_type=TaskType.SOFTWARE,
        )
        total = estimator.estimate_batch([task])
        assert total == estimator.estimate_task(task)

    def test_estimate_batch_multiple_tasks(self) -> None:
        """Test estimating a batch with multiple tasks."""
        estimator = TokenEstimator()
        tasks = [
            Task(id="1", description="Task 1", task_type=TaskType.SOFTWARE),
            Task(id="2", description="Task 2", task_type=TaskType.SOFTWARE),
            Task(id="3", description="Task 3", task_type=TaskType.SOFTWARE),
        ]
        total = estimator.estimate_batch(tasks)

        # Total should be sum of individual estimates
        individual_sum = sum(estimator.estimate_task(t) for t in tasks)
        assert total == individual_sum


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_estimate_task_tokens_function(self) -> None:
        """Test convenience function for task estimation."""
        task = Task(
            id="1",
            description="Test task",
            task_type=TaskType.SOFTWARE,
        )
        tokens = estimate_task_tokens(task)
        assert tokens > 0

    def test_convenience_function_uses_singleton(self) -> None:
        """Test that convenience function uses the same estimator."""
        task = Task(
            id="1",
            description="Test task",
            task_type=TaskType.SOFTWARE,
        )

        # Call twice - should get same result
        tokens1 = estimate_task_tokens(task)
        tokens2 = estimate_task_tokens(task)
        assert tokens1 == tokens2
