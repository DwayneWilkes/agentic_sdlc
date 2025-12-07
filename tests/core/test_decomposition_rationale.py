"""Tests for decomposition rationale tracking."""

import pytest

from src.core.task_decomposer import TaskDecomposer, DecompositionRationale
from src.core.task_parser import ParsedTask, TaskParser
from src.models.enums import TaskType


class TestDecompositionRationale:
    """Test suite for decomposition rationale tracking."""

    def test_decomposition_includes_rationale(self):
        """Test that decomposition result includes rationale."""
        decomposer = TaskDecomposer()
        parser = TaskParser()

        task = parser.parse("Build a REST API for user authentication")
        result = decomposer.decompose(task)

        # Result should have a rationale
        assert hasattr(result, "rationale")
        assert result.rationale is not None
        assert isinstance(result.rationale, DecompositionRationale)

    def test_rationale_explains_strategy(self):
        """Test that rationale explains the decomposition strategy used."""
        decomposer = TaskDecomposer()
        parser = TaskParser()

        task = parser.parse("Build a REST API for user authentication")
        result = decomposer.decompose(task)

        # Rationale should explain strategy
        assert result.rationale.strategy is not None
        assert isinstance(result.rationale.strategy, str)
        assert len(result.rationale.strategy) > 0

    def test_rationale_explains_subtask_creation(self):
        """Test that rationale explains why each subtask was created."""
        decomposer = TaskDecomposer()
        parser = TaskParser()

        task = parser.parse("Build a REST API for user authentication")
        result = decomposer.decompose(task)

        # Should have explanations for each subtask
        assert result.rationale.subtask_explanations is not None
        assert len(result.rationale.subtask_explanations) == len(result.subtasks)

        # Each explanation should be meaningful
        for subtask_id, explanation in result.rationale.subtask_explanations.items():
            assert isinstance(explanation, str)
            assert len(explanation) > 0

    def test_rationale_explains_dependencies(self):
        """Test that rationale explains dependency relationships."""
        decomposer = TaskDecomposer()
        parser = TaskParser()

        task = parser.parse("Build a REST API with tests")
        result = decomposer.decompose(task)

        # Should explain dependencies
        assert result.rationale.dependency_explanations is not None

        # Check that dependencies are explained
        for subtask in result.subtasks:
            if subtask.dependencies:
                for dep_id in subtask.dependencies:
                    dep_key = f"{subtask.id}->{dep_id}"
                    assert dep_key in result.rationale.dependency_explanations
                    explanation = result.rationale.dependency_explanations[dep_key]
                    assert isinstance(explanation, str)
                    assert len(explanation) > 0

    def test_rationale_format_as_text(self):
        """Test that rationale can be formatted as human-readable text."""
        decomposer = TaskDecomposer()
        parser = TaskParser()

        task = parser.parse("Build a REST API for user authentication")
        result = decomposer.decompose(task)

        # Should be able to format as text
        text = result.rationale.format_as_text()
        assert isinstance(text, str)
        assert len(text) > 0

        # Should contain key sections
        assert "Strategy" in text or "strategy" in text.lower()
        assert "Subtask" in text or "subtask" in text.lower()

    def test_software_task_rationale(self):
        """Test rationale for software tasks."""
        decomposer = TaskDecomposer()
        parser = TaskParser()

        task = parser.parse("Implement user authentication with JWT tokens")
        result = decomposer.decompose(task)

        # Strategy should mention software decomposition
        assert result.rationale.strategy is not None
        assert "software" in result.rationale.strategy.lower()

    def test_research_task_rationale(self):
        """Test rationale for research tasks."""
        decomposer = TaskDecomposer()

        task = ParsedTask(
            goal="Research best practices for API security",
            raw_description="Research best practices for API security",
            task_type=TaskType.RESEARCH,
            constraints=[],
            context=[],
            success_criteria=[],
            ambiguities=[],
        )
        result = decomposer.decompose(task)

        # Strategy should mention research decomposition
        assert result.rationale.strategy is not None
        assert "research" in result.rationale.strategy.lower()

    def test_empty_task_rationale(self):
        """Test rationale for empty tasks."""
        decomposer = TaskDecomposer()

        task = ParsedTask(
            goal="",
            raw_description="",
            task_type=TaskType.SOFTWARE,
            constraints=[],
            context=[],
            success_criteria=[],
            ambiguities=[],
        )
        result = decomposer.decompose(task)

        # Should still have a rationale (explaining why no subtasks)
        assert result.rationale is not None
        assert result.rationale.strategy is not None
