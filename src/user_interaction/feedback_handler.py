"""Feedback Handler - Phase 7.2

Implements mid-execution feedback handling, clarification requests,
and iterative refinement based on user feedback.

Features:
1. Store and manage feedback events during execution
2. Pause/resume execution for feedback
3. Request clarifications from user
4. Support iterative refinement with multiple rounds
5. Track feedback history and convergence

Usage:
    from src.user_interaction.feedback_handler import (
        FeedbackHandler, ClarificationManager, IterativeRefinementEngine
    )

    # Handle feedback during execution
    handler = FeedbackHandler(execution_id="exec-123")
    handler.pause_for_feedback(reason="Need user decision")
    feedback = handler.add_feedback(
        feedback_type=FeedbackType.GUIDANCE,
        content="Use approach A",
        source="user"
    )
    handler.resume_execution()

    # Request clarifications
    manager = ClarificationManager(execution_id="exec-123")
    request = manager.request_clarification(
        question="Which Python version?",
        context={"available": ["3.11", "3.12"]}
    )
    response = manager.respond_to_clarification(
        request_id=request.request_id,
        response_text="Use 3.12"
    )

    # Iterative refinement
    engine = IterativeRefinementEngine(execution_id="exec-123")
    round1 = engine.start_refinement_round(
        description="Initial implementation",
        output="Code version 1"
    )
    engine.add_feedback_to_round(1, "Add error handling")
    engine.complete_refinement_round(1)

    if engine.has_converged():
        final_output = engine.get_latest_output()
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================


class FeedbackType(str, Enum):
    """Types of feedback that can be provided during execution."""

    CORRECTION = "correction"  # Fix something wrong
    GUIDANCE = "guidance"  # Suggest an approach
    APPROVAL = "approval"  # Approve a decision
    REJECTION = "rejection"  # Reject a decision
    CLARIFICATION = "clarification"  # Answer a question


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class FeedbackEvent:
    """Represents a single feedback event during execution.

    Attributes:
        event_id: Unique identifier for this feedback
        feedback_type: Type of feedback (correction, guidance, etc.)
        content: The actual feedback content
        source: Who provided the feedback (user, agent, system)
        timestamp: When the feedback was provided
        applied: Whether this feedback has been applied to execution
        context: Additional context data
    """

    event_id: str
    feedback_type: FeedbackType
    content: str
    source: str
    timestamp: datetime
    applied: bool = False
    context: dict[str, str] = field(default_factory=dict)


@dataclass
class ClarificationRequest:
    """Represents a request for clarification from the user.

    Attributes:
        request_id: Unique identifier for this request
        question: The clarification question
        context: Additional context for the question
        requested_at: When the clarification was requested
        response: The user's response (None if not yet answered)
    """

    request_id: str
    question: str
    context: dict[str, str]
    requested_at: datetime
    response: "ClarificationResponse | None" = None


@dataclass
class ClarificationResponse:
    """Represents a user's response to a clarification request.

    Attributes:
        request_id: ID of the request being answered
        response_text: The user's answer
        responded_at: When the response was provided
    """

    request_id: str
    response_text: str
    responded_at: datetime


@dataclass
class RefinementRound:
    """Represents one round of iterative refinement.

    Attributes:
        round_number: Sequential round number (1, 2, 3, ...)
        description: Description of what was done in this round
        output: The output/result from this round
        feedback: Feedback received for this round (None if not yet received)
        started_at: When this round started
        completed_at: When this round was completed (None if in progress)
    """

    round_number: int
    description: str
    output: str
    started_at: datetime
    feedback: str | None = None
    completed_at: datetime | None = None


# ============================================================================
# FeedbackHandler
# ============================================================================


class FeedbackHandler:
    """Handles feedback events during execution.

    Supports:
    - Storing feedback events
    - Pausing/resuming execution for feedback
    - Tracking applied vs pending feedback
    - Filtering feedback by type
    """

    def __init__(self, execution_id: str):
        """Initialize feedback handler.

        Args:
            execution_id: ID of the execution being tracked
        """
        self.execution_id = execution_id
        self._feedback_events: list[FeedbackEvent] = []
        self._paused = False
        self.pause_reason: str | None = None

    def add_feedback(
        self,
        feedback_type: FeedbackType,
        content: str,
        source: str,
        context: dict[str, str] | None = None,
    ) -> FeedbackEvent:
        """Add a new feedback event.

        Args:
            feedback_type: Type of feedback
            content: Feedback content
            source: Source of feedback (user, agent, system)
            context: Optional additional context

        Returns:
            The created FeedbackEvent
        """
        event = FeedbackEvent(
            event_id=str(uuid.uuid4()),
            feedback_type=feedback_type,
            content=content,
            source=source,
            timestamp=datetime.now(),
            applied=False,
            context=context or {},
        )
        self._feedback_events.append(event)
        return event

    def get_all_feedback(self) -> list[FeedbackEvent]:
        """Get all feedback events.

        Returns:
            List of all feedback events
        """
        return self._feedback_events.copy()

    def get_feedback_by_id(self, event_id: str) -> FeedbackEvent:
        """Get a specific feedback event by ID.

        Args:
            event_id: ID of the event to retrieve

        Returns:
            The feedback event

        Raises:
            ValueError: If event_id not found
        """
        for event in self._feedback_events:
            if event.event_id == event_id:
                return event
        raise ValueError(f"Feedback event {event_id} not found")

    def mark_feedback_applied(self, event_id: str) -> None:
        """Mark a feedback event as applied.

        Args:
            event_id: ID of the event to mark as applied

        Raises:
            ValueError: If event_id not found
        """
        event = self.get_feedback_by_id(event_id)
        event.applied = True

    def get_pending_feedback(self) -> list[FeedbackEvent]:
        """Get feedback that hasn't been applied yet.

        Returns:
            List of pending feedback events
        """
        return [e for e in self._feedback_events if not e.applied]

    def get_feedback_by_type(self, feedback_type: FeedbackType) -> list[FeedbackEvent]:
        """Get all feedback of a specific type.

        Args:
            feedback_type: Type to filter by

        Returns:
            List of feedback events matching the type
        """
        return [e for e in self._feedback_events if e.feedback_type == feedback_type]

    def pause_for_feedback(self, reason: str) -> None:
        """Pause execution to wait for user feedback.

        Args:
            reason: Reason for pausing
        """
        self._paused = True
        self.pause_reason = reason

    def resume_execution(self) -> None:
        """Resume execution after receiving feedback."""
        self._paused = False
        self.pause_reason = None

    def is_paused(self) -> bool:
        """Check if execution is currently paused for feedback.

        Returns:
            True if paused, False otherwise
        """
        return self._paused


# ============================================================================
# ClarificationManager
# ============================================================================


class ClarificationManager:
    """Manages clarification requests and responses.

    Supports:
    - Requesting clarifications from user
    - Tracking clarification requests
    - Recording user responses
    - Finding pending clarifications
    """

    def __init__(self, execution_id: str):
        """Initialize clarification manager.

        Args:
            execution_id: ID of the execution being tracked
        """
        self.execution_id = execution_id
        self._requests: list[ClarificationRequest] = []

    def request_clarification(
        self, question: str, context: dict[str, str]
    ) -> ClarificationRequest:
        """Request a clarification from the user.

        Args:
            question: The question to ask
            context: Additional context for the question

        Returns:
            The created ClarificationRequest
        """
        request = ClarificationRequest(
            request_id=str(uuid.uuid4()),
            question=question,
            context=context,
            requested_at=datetime.now(),
        )
        self._requests.append(request)
        return request

    def request_multiple_clarifications(
        self, questions: list[str], context: dict[str, str]
    ) -> list[ClarificationRequest]:
        """Request multiple clarifications at once.

        Args:
            questions: List of questions to ask
            context: Shared context for all questions

        Returns:
            List of created ClarificationRequests
        """
        return [
            self.request_clarification(question=q, context=context) for q in questions
        ]

    def get_all_requests(self) -> list[ClarificationRequest]:
        """Get all clarification requests.

        Returns:
            List of all requests
        """
        return self._requests.copy()

    def get_request_by_id(self, request_id: str) -> ClarificationRequest:
        """Get a specific clarification request by ID.

        Args:
            request_id: ID of the request to retrieve

        Returns:
            The clarification request

        Raises:
            ValueError: If request_id not found
        """
        for request in self._requests:
            if request.request_id == request_id:
                return request
        raise ValueError(f"Clarification request {request_id} not found")

    def respond_to_clarification(
        self, request_id: str, response_text: str
    ) -> ClarificationResponse:
        """Record a user's response to a clarification request.

        Args:
            request_id: ID of the request being answered
            response_text: The user's answer

        Returns:
            The created ClarificationResponse

        Raises:
            ValueError: If request_id not found
        """
        request = self.get_request_by_id(request_id)

        response = ClarificationResponse(
            request_id=request_id,
            response_text=response_text,
            responded_at=datetime.now(),
        )

        request.response = response
        return response

    def get_pending_clarifications(self) -> list[ClarificationRequest]:
        """Get clarification requests that haven't been answered yet.

        Returns:
            List of pending requests
        """
        return [r for r in self._requests if r.response is None]


# ============================================================================
# IterativeRefinementEngine
# ============================================================================


class IterativeRefinementEngine:
    """Manages iterative refinement based on user feedback.

    Supports:
    - Multiple rounds of refinement
    - Tracking refinement history
    - Detecting convergence
    - Feedback summary across rounds
    """

    def __init__(self, execution_id: str):
        """Initialize refinement engine.

        Args:
            execution_id: ID of the execution being tracked
        """
        self.execution_id = execution_id
        self.current_round = 0
        self._rounds: list[RefinementRound] = []

    def start_refinement_round(self, description: str, output: str) -> RefinementRound:
        """Start a new round of refinement.

        Args:
            description: Description of this round
            output: Output/result from this round

        Returns:
            The created RefinementRound
        """
        self.current_round += 1

        round_obj = RefinementRound(
            round_number=self.current_round,
            description=description,
            output=output,
            started_at=datetime.now(),
        )

        self._rounds.append(round_obj)
        return round_obj

    def add_feedback_to_round(self, round_number: int, feedback: str) -> None:
        """Add feedback to a specific round.

        Args:
            round_number: Round to add feedback to
            feedback: The feedback content

        Raises:
            ValueError: If round_number not found
        """
        round_obj = self.get_round_by_number(round_number)
        round_obj.feedback = feedback

    def complete_refinement_round(self, round_number: int) -> None:
        """Mark a refinement round as complete.

        Args:
            round_number: Round to mark as complete

        Raises:
            ValueError: If round_number not found
        """
        round_obj = self.get_round_by_number(round_number)
        round_obj.completed_at = datetime.now()

    def get_round_by_number(self, round_number: int) -> RefinementRound:
        """Get a specific refinement round.

        Args:
            round_number: Round number to retrieve

        Returns:
            The refinement round

        Raises:
            ValueError: If round_number not found
        """
        for round_obj in self._rounds:
            if round_obj.round_number == round_number:
                return round_obj
        raise ValueError(f"Refinement round {round_number} not found")

    def get_refinement_history(self) -> list[RefinementRound]:
        """Get all refinement rounds in order.

        Returns:
            List of all rounds
        """
        return self._rounds.copy()

    def has_converged(self) -> bool:
        """Check if refinement has converged (positive feedback in latest round).

        Convergence is detected when the latest round has feedback containing
        positive indicators like "good", "perfect", "looks good", etc.

        Returns:
            True if converged, False otherwise
        """
        if not self._rounds:
            return False

        latest_round = self._rounds[-1]
        if not latest_round.feedback:
            return False

        # Simple heuristic: positive words indicate convergence
        feedback_lower = latest_round.feedback.lower()
        positive_indicators = [
            "good",
            "perfect",
            "excellent",
            "great",
            "looks good",
            "lgtm",
            "approved",
        ]

        return any(indicator in feedback_lower for indicator in positive_indicators)

    def get_latest_output(self) -> str:
        """Get the output from the most recent round.

        Returns:
            Latest round's output

        Raises:
            ValueError: If no rounds exist
        """
        if not self._rounds:
            raise ValueError("No refinement rounds exist")

        return self._rounds[-1].output

    def get_feedback_summary(self) -> list[str]:
        """Get a summary of all feedback across rounds.

        Returns:
            List of feedback strings, one per round
        """
        return [
            f"Round {r.round_number}: {r.feedback}" for r in self._rounds if r.feedback
        ]
