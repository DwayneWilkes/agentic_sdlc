"""
Agent handoff protocol implementation.

This module provides structured handoff documents that enable agents to pass
work to each other with full context preservation, ensuring no information
is lost during transitions.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

import yaml


@dataclass
class Assumption:
    """
    Represents an assumption made during task execution.

    Assumptions are explicit statements about what the agent believed to be
    true while working on the task. These help the receiving agent understand
    the context and verify correctness.
    """

    assumption: str
    confidence: float  # 0.0 to 1.0
    impact_if_false: str


@dataclass
class Blocker:
    """
    Represents a blocker or issue encountered during task execution.

    Blockers document obstacles that prevented full task completion or
    required workarounds.
    """

    issue: str
    severity: str  # "low", "medium", "high", "critical"
    workaround: str | None = None


@dataclass
class HandoffTestStatus:
    """
    Represents the current state of testing for the task.

    Tracks unit test status, integration test status, and code coverage
    to give the receiving agent clear quality metrics.
    """

    unit_tests: str  # "passing", "failing", "not run", etc.
    integration_tests: str  # "passing", "failing", "skipped", etc.
    coverage: str  # e.g., "78%", "85%"


@dataclass
class HandoffDocument:
    """
    Standard handoff document for agent-to-agent work transitions.

    This document captures all necessary context for an agent to hand off
    work to another agent, including completed work, remaining work,
    assumptions made, blockers encountered, and test status.

    Format supports both YAML and JSON serialization for flexibility.
    """

    from_agent: str
    to_agent: str
    task_id: str
    timestamp: str  # ISO 8601 format
    context_summary: str
    assumptions: list[Assumption]
    completed_items: list[str]
    remaining_items: list[str]
    blockers: list[Blocker]
    test_status: HandoffTestStatus
    files_changed: list[str]
    metadata: dict = field(default_factory=dict)

    def to_yaml(self) -> str:
        """Serialize handoff document to YAML format."""
        data = asdict(self)
        result: str = yaml.dump(data, sort_keys=False, default_flow_style=False)
        return result

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "HandoffDocument":
        """Deserialize handoff document from YAML format."""
        data = yaml.safe_load(yaml_str)
        return cls._from_dict(data)

    def to_json(self) -> str:
        """Serialize handoff document to JSON format."""
        data = asdict(self)
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "HandoffDocument":
        """Deserialize handoff document from JSON format."""
        data = json.loads(json_str)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "HandoffDocument":
        """Helper to construct HandoffDocument from dictionary."""
        # Convert nested dicts to dataclass instances
        assumptions = [
            Assumption(**a) if isinstance(a, dict) else a
            for a in data.get("assumptions", [])
        ]
        blockers = [
            Blocker(**b) if isinstance(b, dict) else b
            for b in data.get("blockers", [])
        ]
        test_status_data = data.get("test_status", {})
        if isinstance(test_status_data, dict):
            test_status = HandoffTestStatus(**test_status_data)
        else:
            test_status = test_status_data

        return cls(
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            task_id=data["task_id"],
            timestamp=data["timestamp"],
            context_summary=data["context_summary"],
            assumptions=assumptions,
            completed_items=data.get("completed_items", []),
            remaining_items=data.get("remaining_items", []),
            blockers=blockers,
            test_status=test_status,
            files_changed=data.get("files_changed", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProgressCapture:
    """
    Captures the current progress state of a task.

    Tracks what has been completed, what is in progress, and what remains
    to be done.
    """

    completed_items: list[str] = field(default_factory=list)
    remaining_items: list[str] = field(default_factory=list)
    in_progress_items: list[str] = field(default_factory=list)

    def calculate_completion_percentage(self) -> float:
        """
        Calculate the percentage of work completed.

        Returns:
            Completion percentage as a float (0.0 to 100.0)
        """
        total_items = (
            len(self.completed_items)
            + len(self.remaining_items)
            + len(self.in_progress_items)
        )

        if total_items == 0:
            return 100.0  # Nothing to do = 100% complete

        return (len(self.completed_items) / total_items) * 100.0


class AssumptionTracker:
    """
    Tracks assumptions made during task execution.

    Helps agents explicitly document what they believe to be true
    while working on a task.
    """

    def __init__(self) -> None:
        """Initialize an empty assumption tracker."""
        self.assumptions: list[Assumption] = []

    def add_assumption(
        self,
        assumption: str,
        confidence: float,
        impact_if_false: str,
    ) -> None:
        """
        Add a new assumption.

        Args:
            assumption: Description of what is assumed to be true
            confidence: Confidence level (0.0 to 1.0)
            impact_if_false: What happens if this assumption is wrong
        """
        self.assumptions.append(
            Assumption(
                assumption=assumption,
                confidence=confidence,
                impact_if_false=impact_if_false,
            )
        )

    def get_all_assumptions(self) -> list[Assumption]:
        """Get all tracked assumptions."""
        return self.assumptions.copy()

    def get_low_confidence_assumptions(
        self,
        threshold: float = 0.7
    ) -> list[Assumption]:
        """
        Get assumptions below a confidence threshold.

        Args:
            threshold: Confidence threshold (default 0.7)

        Returns:
            List of assumptions with confidence < threshold
        """
        return [a for a in self.assumptions if a.confidence < threshold]


class HandoffGenerator:
    """
    Generates handoff documents from agent state.

    Creates structured handoff documents that capture all necessary
    context for agent-to-agent transitions.
    """

    def generate(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        context_summary: str,
        completed_items: list[str],
        remaining_items: list[str],
        files_changed: list[str],
        assumption_tracker: AssumptionTracker | None = None,
        blockers: list[Blocker] | None = None,
        test_status: HandoffTestStatus | None = None,
        metadata: dict | None = None,
    ) -> HandoffDocument:
        """
        Generate a handoff document.

        Args:
            from_agent: ID of agent handing off work
            to_agent: ID of agent receiving work
            task_id: ID of task being handed off
            context_summary: Summary of work done and context
            completed_items: List of completed work items
            remaining_items: List of remaining work items
            files_changed: List of files modified during work
            assumption_tracker: Optional tracker with assumptions made
            blockers: Optional list of blockers encountered
            test_status: Optional current test status
            metadata: Optional additional metadata

        Returns:
            HandoffDocument ready to be serialized and transmitted
        """
        assumptions = []
        if assumption_tracker:
            assumptions = assumption_tracker.get_all_assumptions()

        if blockers is None:
            blockers = []

        if test_status is None:
            test_status = HandoffTestStatus(
                unit_tests="not run",
                integration_tests="not run",
                coverage="0%"
            )

        if metadata is None:
            metadata = {}

        return HandoffDocument(
            from_agent=from_agent,
            to_agent=to_agent,
            task_id=task_id,
            timestamp=datetime.now(UTC).isoformat(),
            context_summary=context_summary,
            assumptions=assumptions,
            completed_items=completed_items,
            remaining_items=remaining_items,
            blockers=blockers,
            test_status=test_status,
            files_changed=files_changed,
            metadata=metadata,
        )


class HandoffValidator:
    """
    Validates handoff documents for completeness and correctness.

    Ensures that handoff documents contain all required information
    before an agent accepts work.
    """

    def validate(self, handoff: HandoffDocument) -> tuple[bool, list[str]]:
        """
        Validate a handoff document.

        Args:
            handoff: HandoffDocument to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []

        # Required fields validation
        if not handoff.from_agent:
            errors.append("Missing from_agent")
        if not handoff.to_agent:
            errors.append("Missing to_agent")
        if not handoff.task_id:
            errors.append("Missing task_id")
        if not handoff.context_summary:
            errors.append("Missing context_summary")

        # Timestamp validation
        try:
            datetime.fromisoformat(handoff.timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            errors.append("Invalid timestamp format (must be ISO 8601)")

        # Work items validation
        if not handoff.completed_items and not handoff.remaining_items:
            errors.append("No work items specified (completed or remaining)")

        # Confidence validation for assumptions
        for i, assumption in enumerate(handoff.assumptions):
            if not (0.0 <= assumption.confidence <= 1.0):
                errors.append(
                    f"Assumption {i}: confidence must be between 0.0 and 1.0"
                )

        # Severity validation for blockers
        valid_severities = {"low", "medium", "high", "critical"}
        for i, blocker in enumerate(handoff.blockers):
            if blocker.severity not in valid_severities:
                errors.append(
                    f"Blocker {i}: severity must be one of {valid_severities}"
                )

        return len(errors) == 0, errors
