"""
TokenEstimator - Phase 7.4

Estimates token costs for tasks before execution.

Features:
1. Task complexity assessment (simple, medium, complex, very_complex)
2. Token estimation based on task type and complexity
3. Context window overhead estimation
4. Batch task estimation

Usage:
    estimator = TokenEstimator()

    # Estimate single task
    tokens = estimator.estimate_task(task)

    # Estimate batch
    total_tokens = estimator.estimate_batch([task1, task2, task3])

    # Or use convenience function
    tokens = estimate_task_tokens(task)
"""

from enum import Enum

from src.models.task import Task, TaskType


class TaskComplexity(str, Enum):
    """Task complexity levels for token estimation."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


# Default token estimates by complexity
DEFAULT_BASE_TOKENS = {
    TaskComplexity.SIMPLE: 2000,  # Simple tasks: add comment, fix typo
    TaskComplexity.MEDIUM: 8000,  # Medium tasks: add function, update logic
    TaskComplexity.COMPLEX: 25000,  # Complex tasks: new feature, refactor
    TaskComplexity.VERY_COMPLEX: 60000,  # Very complex: architecture change, distributed system
}

# Token overhead for context windows
CONTEXT_OVERHEAD_PER_100_CHARS = 110  # Roughly 110 tokens per 100 chars of context


class TokenEstimator:
    """
    Estimates token costs for tasks.

    Uses heuristics based on task type, description length, subtask count,
    and context size.
    """

    def __init__(
        self,
        base_tokens: dict[TaskComplexity, int] | None = None,
    ):
        """
        Initialize token estimator.

        Args:
            base_tokens: Optional custom base token estimates by complexity
        """
        self.base_tokens = base_tokens or DEFAULT_BASE_TOKENS

    def assess_complexity(self, task: Task) -> TaskComplexity:
        """
        Assess task complexity based on various factors.

        Factors considered:
        - Description length
        - Number of subtasks
        - Task type

        Args:
            task: Task to assess

        Returns:
            TaskComplexity level
        """
        score = 0

        # Factor 1: Description length
        desc_len = len(task.description)
        if desc_len < 50:
            score += 0
        elif desc_len < 150:
            score += 1
        elif desc_len < 300:
            score += 2
        else:
            score += 3

        # Factor 2: Number of subtasks (more weight for subtasks)
        num_subtasks = len(task.subtasks) if task.subtasks else 0
        if num_subtasks == 0:
            score += 0
        elif num_subtasks < 3:
            score += 1
        elif num_subtasks < 8:
            score += 2
        else:
            score += 3

        # Factor 3: Task type (research/analysis often less complex than software)
        if task.task_type == TaskType.SOFTWARE:
            score += 1

        # Map score to complexity
        if score <= 1:
            return TaskComplexity.SIMPLE
        elif score <= 3:
            return TaskComplexity.MEDIUM
        elif score <= 5:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.VERY_COMPLEX

    def estimate_task(self, task: Task) -> int:
        """
        Estimate tokens needed for a task.

        Args:
            task: Task to estimate

        Returns:
            Estimated tokens
        """
        # Base estimate from complexity
        complexity = self.assess_complexity(task)
        base_estimate = self.base_tokens[complexity]

        # Add context overhead
        context_overhead = 0
        if task.context:
            context_chars = len(task.context)
            context_overhead = (context_chars // 100) * CONTEXT_OVERHEAD_PER_100_CHARS

        # Add subtask overhead (each subtask adds complexity)
        subtask_overhead = 0
        if task.subtasks:
            subtask_overhead = len(task.subtasks) * 500

        total = base_estimate + context_overhead + subtask_overhead

        return total

    def estimate_batch(self, tasks: list[Task]) -> int:
        """
        Estimate total tokens for a batch of tasks.

        Args:
            tasks: List of tasks to estimate

        Returns:
            Total estimated tokens
        """
        return sum(self.estimate_task(task) for task in tasks)


# =============================================================================
# Singleton and Convenience Functions
# =============================================================================

_token_estimator_instance: TokenEstimator | None = None


def get_token_estimator() -> TokenEstimator:
    """Get the singleton token estimator instance."""
    global _token_estimator_instance
    if _token_estimator_instance is None:
        _token_estimator_instance = TokenEstimator()
    return _token_estimator_instance


def estimate_task_tokens(task: Task) -> int:
    """
    Convenience function to estimate tokens for a task.

    Args:
        task: Task to estimate

    Returns:
        Estimated tokens
    """
    return get_token_estimator().estimate_task(task)


def estimate_batch_tokens(tasks: list[Task]) -> int:
    """
    Convenience function to estimate tokens for a batch of tasks.

    Args:
        tasks: List of tasks

    Returns:
        Total estimated tokens
    """
    return get_token_estimator().estimate_batch(tasks)
