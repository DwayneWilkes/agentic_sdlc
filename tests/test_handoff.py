"""Tests for agent handoff protocol."""

import json
from datetime import UTC, datetime

import pytest

from src.coordination.handoff import (
    Assumption,
    AssumptionTracker,
    Blocker,
    HandoffDocument,
    HandoffGenerator,
    HandoffTestStatus,
    HandoffValidator,
    ProgressCapture,
)


class TestHandoffDocument:
    """Test HandoffDocument data model."""

    def test_create_basic_handoff(self):
        """Test creating a basic handoff document."""
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="Implemented OAuth2 authentication",
            assumptions=[],
            completed_items=["Login form", "Token service"],
            remaining_items=["Error boundary", "Session timeout"],
            blockers=[],
            test_status=HandoffTestStatus(
                unit_tests="passing",
                integration_tests="2 skipped",
                coverage="78%"
            ),
            files_changed=["src/auth/LoginForm.tsx", "src/auth/AuthService.ts"],
        )

        assert handoff.from_agent == "agent-1"
        assert handoff.to_agent == "agent-2"
        assert handoff.task_id == "TASK-42"
        assert len(handoff.completed_items) == 2
        assert len(handoff.remaining_items) == 2

    def test_handoff_to_yaml(self):
        """Test serializing handoff to YAML."""
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="Test summary",
            assumptions=[
                Assumption(
                    assumption="Backend endpoints deployed",
                    confidence=0.9,
                    impact_if_false="Need to deploy endpoints first"
                )
            ],
            completed_items=["Item 1"],
            remaining_items=["Item 2"],
            blockers=[],
            test_status=HandoffTestStatus(
                unit_tests="passing",
                integration_tests="passing",
                coverage="85%"
            ),
            files_changed=["file1.py"],
        )

        yaml_str = handoff.to_yaml()
        assert "from_agent: agent-1" in yaml_str
        assert "to_agent: agent-2" in yaml_str
        assert "task_id: TASK-42" in yaml_str
        assert "Backend endpoints deployed" in yaml_str

    def test_handoff_from_yaml(self):
        """Test deserializing handoff from YAML."""
        yaml_str = """
from_agent: agent-1
to_agent: agent-2
task_id: TASK-42
timestamp: '2025-12-06T10:00:00'
context_summary: Test summary
assumptions:
  - assumption: Backend ready
    confidence: 0.9
    impact_if_false: Need backend
completed_items:
  - Item 1
remaining_items:
  - Item 2
blockers: []
test_status:
  unit_tests: passing
  integration_tests: passing
  coverage: 85%
files_changed:
  - file1.py
"""
        handoff = HandoffDocument.from_yaml(yaml_str)

        assert handoff.from_agent == "agent-1"
        assert handoff.to_agent == "agent-2"
        assert handoff.task_id == "TASK-42"
        assert len(handoff.assumptions) == 1
        assert handoff.assumptions[0].assumption == "Backend ready"
        assert handoff.assumptions[0].confidence == 0.9

    def test_handoff_to_json(self):
        """Test serializing handoff to JSON."""
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="Test",
            assumptions=[],
            completed_items=["Done"],
            remaining_items=["Todo"],
            blockers=[],
            test_status=HandoffTestStatus("passing", "passing", "80%"),
            files_changed=["file.py"],
        )

        json_str = handoff.to_json()
        data = json.loads(json_str)

        assert data["from_agent"] == "agent-1"
        assert data["task_id"] == "TASK-42"
        assert "Done" in data["completed_items"]

    def test_handoff_from_json(self):
        """Test deserializing handoff from JSON."""
        json_str = """
{
  "from_agent": "agent-1",
  "to_agent": "agent-2",
  "task_id": "TASK-42",
  "timestamp": "2025-12-06T10:00:00",
  "context_summary": "Test",
  "assumptions": [],
  "completed_items": ["Done"],
  "remaining_items": ["Todo"],
  "blockers": [],
  "test_status": {
    "unit_tests": "passing",
    "integration_tests": "passing",
    "coverage": "80%"
  },
  "files_changed": ["file.py"]
}
"""
        handoff = HandoffDocument.from_json(json_str)

        assert handoff.from_agent == "agent-1"
        assert handoff.task_id == "TASK-42"
        assert len(handoff.completed_items) == 1


class TestAssumptionTracker:
    """Test assumption tracking functionality."""

    def test_create_tracker(self):
        """Test creating an assumption tracker."""
        tracker = AssumptionTracker()
        assert len(tracker.assumptions) == 0

    def test_add_assumption(self):
        """Test adding assumptions."""
        tracker = AssumptionTracker()
        tracker.add_assumption(
            "API endpoints exist",
            confidence=0.8,
            impact_if_false="Need to create endpoints"
        )

        assert len(tracker.assumptions) == 1
        assert tracker.assumptions[0].assumption == "API endpoints exist"
        assert tracker.assumptions[0].confidence == 0.8

    def test_get_all_assumptions(self):
        """Test retrieving all assumptions."""
        tracker = AssumptionTracker()
        tracker.add_assumption("Assumption 1", 0.9, "Impact 1")
        tracker.add_assumption("Assumption 2", 0.7, "Impact 2")

        assumptions = tracker.get_all_assumptions()
        assert len(assumptions) == 2
        assert assumptions[0].assumption == "Assumption 1"
        assert assumptions[1].assumption == "Assumption 2"

    def test_get_low_confidence_assumptions(self):
        """Test filtering low confidence assumptions."""
        tracker = AssumptionTracker()
        tracker.add_assumption("High confidence", 0.9, "Impact A")
        tracker.add_assumption("Low confidence", 0.4, "Impact B")
        tracker.add_assumption("Medium confidence", 0.6, "Impact C")

        low_conf = tracker.get_low_confidence_assumptions(threshold=0.7)
        assert len(low_conf) == 2
        assert low_conf[0].assumption == "Low confidence"
        assert low_conf[1].assumption == "Medium confidence"


class TestProgressCapture:
    """Test progress capture functionality."""

    def test_create_progress_capture(self):
        """Test creating progress capture."""
        progress = ProgressCapture(
            completed_items=["Item 1", "Item 2"],
            remaining_items=["Item 3", "Item 4"],
            in_progress_items=["Item 5"],
        )

        assert len(progress.completed_items) == 2
        assert len(progress.remaining_items) == 2
        assert len(progress.in_progress_items) == 1

    def test_calculate_completion_percentage(self):
        """Test calculating completion percentage."""
        progress = ProgressCapture(
            completed_items=["Done 1", "Done 2"],
            remaining_items=["Todo 1", "Todo 2", "Todo 3"],
            in_progress_items=["InProgress"],
        )

        # 2 completed out of (2 + 3 + 1) = 6 total
        percentage = progress.calculate_completion_percentage()
        assert percentage == pytest.approx(33.33, rel=0.01)

    def test_completion_percentage_all_done(self):
        """Test completion percentage when everything is done."""
        progress = ProgressCapture(
            completed_items=["Done 1", "Done 2"],
            remaining_items=[],
            in_progress_items=[],
        )

        percentage = progress.calculate_completion_percentage()
        assert percentage == 100.0

    def test_completion_percentage_nothing_done(self):
        """Test completion percentage when nothing is done."""
        progress = ProgressCapture(
            completed_items=[],
            remaining_items=["Todo 1", "Todo 2"],
            in_progress_items=[],
        )

        percentage = progress.calculate_completion_percentage()
        assert percentage == 0.0


class TestHandoffGenerator:
    """Test handoff document generation."""

    def test_create_generator(self):
        """Test creating a handoff generator."""
        generator = HandoffGenerator()
        assert generator is not None

    def test_generate_basic_handoff(self):
        """Test generating a basic handoff document."""
        generator = HandoffGenerator()

        handoff = generator.generate(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            context_summary="Implemented feature X",
            completed_items=["Item 1"],
            remaining_items=["Item 2"],
            files_changed=["file.py"],
        )

        assert handoff.from_agent == "agent-1"
        assert handoff.to_agent == "agent-2"
        assert handoff.task_id == "TASK-42"
        assert handoff.context_summary == "Implemented feature X"
        assert len(handoff.completed_items) == 1
        assert len(handoff.remaining_items) == 1

    def test_generate_with_assumptions(self):
        """Test generating handoff with assumptions."""
        generator = HandoffGenerator()
        tracker = AssumptionTracker()
        tracker.add_assumption("Assumption 1", 0.8, "Impact 1")

        handoff = generator.generate(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            context_summary="Test",
            completed_items=["Done"],
            remaining_items=["Todo"],
            files_changed=["file.py"],
            assumption_tracker=tracker,
        )

        assert len(handoff.assumptions) == 1
        assert handoff.assumptions[0].assumption == "Assumption 1"

    def test_generate_with_blockers(self):
        """Test generating handoff with blockers."""
        generator = HandoffGenerator()
        blocker = Blocker(
            issue="CORS configuration needed",
            severity="medium",
            workaround="Using dev proxy"
        )

        handoff = generator.generate(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            context_summary="Test",
            completed_items=["Done"],
            remaining_items=["Todo"],
            files_changed=["file.py"],
            blockers=[blocker],
        )

        assert len(handoff.blockers) == 1
        assert handoff.blockers[0].issue == "CORS configuration needed"
        assert handoff.blockers[0].severity == "medium"

    def test_generate_with_test_status(self):
        """Test generating handoff with test status."""
        generator = HandoffGenerator()
        test_status = HandoffTestStatus(
            unit_tests="passing",
            integration_tests="3 skipped",
            coverage="82%"
        )

        handoff = generator.generate(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            context_summary="Test",
            completed_items=["Done"],
            remaining_items=["Todo"],
            files_changed=["file.py"],
            test_status=test_status,
        )

        assert handoff.test_status.unit_tests == "passing"
        assert handoff.test_status.integration_tests == "3 skipped"
        assert handoff.test_status.coverage == "82%"


class TestHandoffValidator:
    """Test handoff document validation."""

    def test_create_validator(self):
        """Test creating a validator."""
        validator = HandoffValidator()
        assert validator is not None

    def test_validate_valid_handoff(self):
        """Test validating a valid handoff document."""
        validator = HandoffValidator()
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="Valid handoff",
            assumptions=[],
            completed_items=["Done"],
            remaining_items=["Todo"],
            blockers=[],
            test_status=HandoffTestStatus("passing", "passing", "80%"),
            files_changed=["file.py"],
        )

        is_valid, errors = validator.validate(handoff)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_agents(self):
        """Test validation fails when agents are missing."""
        validator = HandoffValidator()
        handoff = HandoffDocument(
            from_agent="",
            to_agent="",
            task_id="TASK-42",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="Test",
            assumptions=[],
            completed_items=[],
            remaining_items=[],
            blockers=[],
            test_status=HandoffTestStatus("passing", "passing", "80%"),
            files_changed=[],
        )

        is_valid, errors = validator.validate(handoff)
        assert is_valid is False
        assert "from_agent" in str(errors)
        assert "to_agent" in str(errors)

    def test_validate_missing_task_id(self):
        """Test validation fails when task_id is missing."""
        validator = HandoffValidator()
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="Test",
            assumptions=[],
            completed_items=[],
            remaining_items=[],
            blockers=[],
            test_status=HandoffTestStatus("passing", "passing", "80%"),
            files_changed=[],
        )

        is_valid, errors = validator.validate(handoff)
        assert is_valid is False
        assert "task_id" in str(errors)

    def test_validate_missing_context(self):
        """Test validation fails when context_summary is missing."""
        validator = HandoffValidator()
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="",
            assumptions=[],
            completed_items=[],
            remaining_items=[],
            blockers=[],
            test_status=HandoffTestStatus("passing", "passing", "80%"),
            files_changed=[],
        )

        is_valid, errors = validator.validate(handoff)
        assert is_valid is False
        assert "context_summary" in str(errors)

    def test_validate_no_work_items(self):
        """Test validation warns when no completed or remaining items."""
        validator = HandoffValidator()
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            timestamp=datetime.now(UTC).isoformat(),
            context_summary="Test",
            assumptions=[],
            completed_items=[],
            remaining_items=[],
            blockers=[],
            test_status=HandoffTestStatus("passing", "passing", "80%"),
            files_changed=[],
        )

        is_valid, errors = validator.validate(handoff)
        assert is_valid is False
        assert "work items" in str(errors).lower()

    def test_validate_timestamp_format(self):
        """Test validation checks timestamp format."""
        validator = HandoffValidator()
        handoff = HandoffDocument(
            from_agent="agent-1",
            to_agent="agent-2",
            task_id="TASK-42",
            timestamp="invalid-timestamp",
            context_summary="Test",
            assumptions=[],
            completed_items=["Done"],
            remaining_items=[],
            blockers=[],
            test_status=HandoffTestStatus("passing", "passing", "80%"),
            files_changed=[],
        )

        is_valid, errors = validator.validate(handoff)
        assert is_valid is False
        assert "timestamp" in str(errors).lower()
