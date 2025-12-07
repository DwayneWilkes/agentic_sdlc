"""Tests for conflict detection and resolution."""

import pytest

from src.coordination.conflict_detector import (
    Conflict,
    ConflictDetector,
    ConflictType,
    ResolutionStrategy,
)


class TestConflictDetection:
    """Tests for detecting conflicts between agent outputs."""

    def test_detect_output_conflict_same_subtask_different_outputs(self):
        """Test detecting when two agents produce different outputs for same subtask."""
        detector = ConflictDetector()

        agent_outputs = {
            "agent-1": {"subtask_id": "task-1", "output": "Solution A"},
            "agent-2": {"subtask_id": "task-1", "output": "Solution B"},
        }

        conflicts = detector.detect_output_conflicts(agent_outputs)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.OUTPUT_MISMATCH
        assert conflicts[0].subtask_id == "task-1"
        assert "agent-1" in conflicts[0].involved_agents
        assert "agent-2" in conflicts[0].involved_agents

    def test_no_conflict_when_outputs_match(self):
        """Test no conflict when agents agree on output."""
        detector = ConflictDetector()

        agent_outputs = {
            "agent-1": {"subtask_id": "task-1", "output": "Solution A"},
            "agent-2": {"subtask_id": "task-1", "output": "Solution A"},
        }

        conflicts = detector.detect_output_conflicts(agent_outputs)

        assert len(conflicts) == 0

    def test_detect_interpretation_conflict(self):
        """Test detecting when agents interpret task requirements differently."""
        detector = ConflictDetector()

        interpretations = {
            "agent-1": {
                "subtask_id": "task-1",
                "requirements": ["req-A", "req-B"],
            },
            "agent-2": {
                "subtask_id": "task-1",
                "requirements": ["req-A", "req-C"],
            },
        }

        conflicts = detector.detect_interpretation_conflicts(interpretations)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.INTERPRETATION_MISMATCH
        assert conflicts[0].subtask_id == "task-1"

    def test_detect_dependency_conflict(self):
        """Test detecting when agents disagree on task dependencies."""
        detector = ConflictDetector()

        dependency_views = {
            "agent-1": {
                "subtask_id": "task-2",
                "dependencies": ["task-1"],
            },
            "agent-2": {
                "subtask_id": "task-2",
                "dependencies": ["task-1", "task-0"],
            },
        }

        conflicts = detector.detect_dependency_conflicts(dependency_views)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.DEPENDENCY_MISMATCH

    def test_detect_multiple_conflicts(self):
        """Test detecting multiple conflicts across different subtasks."""
        detector = ConflictDetector()

        agent_outputs = {
            "agent-1": {"subtask_id": "task-1", "output": "Solution A"},
            "agent-2": {"subtask_id": "task-1", "output": "Solution B"},
            "agent-3": {"subtask_id": "task-2", "output": "Solution X"},
            "agent-4": {"subtask_id": "task-2", "output": "Solution Y"},
        }

        conflicts = detector.detect_output_conflicts(agent_outputs)

        assert len(conflicts) == 2
        subtask_ids = {c.subtask_id for c in conflicts}
        assert subtask_ids == {"task-1", "task-2"}


class TestConflictResolution:
    """Tests for conflict resolution strategies."""

    def test_voting_resolution_majority_wins(self):
        """Test voting strategy where majority opinion wins."""
        detector = ConflictDetector()

        conflict = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2", "agent-3"],
            details={
                "agent-1": "Solution A",
                "agent-2": "Solution A",
                "agent-3": "Solution B",
            },
        )

        resolution = detector.resolve_conflict(
            conflict,
            strategy=ResolutionStrategy.VOTING
        )

        assert resolution.winning_output == "Solution A"
        assert resolution.strategy_used == ResolutionStrategy.VOTING
        assert resolution.confidence > 0.5  # Majority = higher confidence

    def test_voting_resolution_tie_returns_lower_confidence(self):
        """Test voting with tie returns lower confidence."""
        detector = ConflictDetector()

        conflict = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2"],
            details={
                "agent-1": "Solution A",
                "agent-2": "Solution B",
            },
        )

        resolution = detector.resolve_conflict(
            conflict,
            strategy=ResolutionStrategy.VOTING
        )

        assert resolution.confidence < 0.5  # Tie = low confidence
        assert resolution.requires_escalation is True

    def test_priority_based_resolution(self):
        """Test priority-based resolution where higher priority agent wins."""
        detector = ConflictDetector()

        conflict = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2"],
            details={
                "agent-1": "Solution A",
                "agent-2": "Solution B",
            },
        )

        agent_priorities = {
            "agent-1": 10,
            "agent-2": 5,
        }

        resolution = detector.resolve_conflict(
            conflict,
            strategy=ResolutionStrategy.PRIORITY_BASED,
            agent_priorities=agent_priorities
        )

        assert resolution.winning_output == "Solution A"
        assert resolution.winning_agent == "agent-1"
        assert resolution.strategy_used == ResolutionStrategy.PRIORITY_BASED

    def test_re_evaluation_marks_for_review(self):
        """Test re-evaluation strategy marks conflict for external review."""
        detector = ConflictDetector()

        conflict = Conflict(
            conflict_type=ConflictType.INTERPRETATION_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2"],
            details={
                "agent-1": {"requirements": ["req-A"]},
                "agent-2": {"requirements": ["req-B"]},
            },
        )

        resolution = detector.resolve_conflict(
            conflict,
            strategy=ResolutionStrategy.RE_EVALUATION
        )

        assert resolution.requires_re_evaluation is True
        assert resolution.strategy_used == ResolutionStrategy.RE_EVALUATION

    def test_invalid_strategy_raises_error(self):
        """Test that invalid resolution strategy raises error."""
        detector = ConflictDetector()

        conflict = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1"],
            details={},
        )

        with pytest.raises(ValueError, match="Unknown resolution strategy"):
            detector.resolve_conflict(conflict, strategy="invalid_strategy")

    def test_resolution_includes_metadata(self):
        """Test resolution includes useful metadata."""
        detector = ConflictDetector()

        conflict = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2", "agent-3"],
            details={
                "agent-1": "Solution A",
                "agent-2": "Solution A",
                "agent-3": "Solution B",
            },
        )

        resolution = detector.resolve_conflict(
            conflict,
            strategy=ResolutionStrategy.VOTING
        )

        assert resolution.conflict_id == conflict.conflict_id
        assert resolution.timestamp is not None
        assert "vote_counts" in resolution.metadata


class TestConflictDataStructures:
    """Tests for conflict-related data structures."""

    def test_conflict_has_unique_id(self):
        """Test that each conflict gets a unique ID."""
        conflict1 = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2"],
            details={},
        )

        conflict2 = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2"],
            details={},
        )

        assert conflict1.conflict_id != conflict2.conflict_id

    def test_conflict_tracks_severity(self):
        """Test that conflicts can be assigned severity levels."""
        conflict = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2"],
            details={},
            severity="high",
        )

        assert conflict.severity == "high"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_single_agent_no_conflict(self):
        """Test that single agent output creates no conflict."""
        detector = ConflictDetector()

        agent_outputs = {
            "agent-1": {"subtask_id": "task-1", "output": "Solution A"},
        }

        conflicts = detector.detect_output_conflicts(agent_outputs)

        assert len(conflicts) == 0

    def test_empty_outputs_no_conflict(self):
        """Test that empty outputs list creates no conflicts."""
        detector = ConflictDetector()

        conflicts = detector.detect_output_conflicts({})

        assert len(conflicts) == 0

    def test_resolution_without_priorities_uses_default(self):
        """Test priority-based resolution works with default priorities."""
        detector = ConflictDetector()

        conflict = Conflict(
            conflict_type=ConflictType.OUTPUT_MISMATCH,
            subtask_id="task-1",
            involved_agents=["agent-1", "agent-2"],
            details={
                "agent-1": "Solution A",
                "agent-2": "Solution B",
            },
        )

        # Should not raise error, use default priorities
        resolution = detector.resolve_conflict(
            conflict,
            strategy=ResolutionStrategy.PRIORITY_BASED
        )

        assert resolution is not None
        assert resolution.winning_output in ["Solution A", "Solution B"]
