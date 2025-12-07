"""Tests for Feedback Handler - Phase 7.2

Test-driven development for:
1. Mid-execution feedback handling
2. Clarification request mechanism
3. Iterative refinement based on feedback
"""

from datetime import datetime

from src.user_interaction.feedback_handler import (
    ClarificationManager,
    FeedbackHandler,
    FeedbackType,
    IterativeRefinementEngine,
)

# ============================================================================
# FeedbackHandler Tests
# ============================================================================


class TestFeedbackHandler:
    """Test feedback handling during execution."""

    def test_create_feedback_handler(self):
        """Should create a feedback handler."""
        handler = FeedbackHandler(execution_id="exec-1")
        assert handler.execution_id == "exec-1"
        assert len(handler.get_all_feedback()) == 0

    def test_store_feedback_event(self):
        """Should store feedback events during execution."""
        handler = FeedbackHandler(execution_id="exec-1")

        event = handler.add_feedback(
            feedback_type=FeedbackType.CORRECTION,
            content="Please use Python 3.12 instead of 3.11",
            source="user",
        )

        assert event.feedback_type == FeedbackType.CORRECTION
        assert event.content == "Please use Python 3.12 instead of 3.11"
        assert event.source == "user"
        assert isinstance(event.timestamp, datetime)
        assert event.applied is False

        all_feedback = handler.get_all_feedback()
        assert len(all_feedback) == 1
        assert all_feedback[0] == event

    def test_mark_feedback_applied(self):
        """Should mark feedback as applied after processing."""
        handler = FeedbackHandler(execution_id="exec-1")

        event = handler.add_feedback(
            feedback_type=FeedbackType.CORRECTION, content="Fix this", source="user"
        )
        assert event.applied is False

        handler.mark_feedback_applied(event.event_id)

        updated = handler.get_feedback_by_id(event.event_id)
        assert updated.applied is True

    def test_get_pending_feedback(self):
        """Should get only feedback that hasn't been applied yet."""
        handler = FeedbackHandler(execution_id="exec-1")

        event1 = handler.add_feedback(
            feedback_type=FeedbackType.GUIDANCE, content="Use TDD", source="user"
        )
        event2 = handler.add_feedback(
            feedback_type=FeedbackType.CORRECTION, content="Fix bug", source="user"
        )

        handler.mark_feedback_applied(event1.event_id)

        pending = handler.get_pending_feedback()
        assert len(pending) == 1
        assert pending[0].event_id == event2.event_id

    def test_feedback_by_type(self):
        """Should filter feedback by type."""
        handler = FeedbackHandler(execution_id="exec-1")

        handler.add_feedback(
            feedback_type=FeedbackType.CORRECTION, content="Fix this", source="user"
        )
        handler.add_feedback(
            feedback_type=FeedbackType.GUIDANCE, content="Try this", source="user"
        )
        handler.add_feedback(
            feedback_type=FeedbackType.CORRECTION, content="Fix that", source="user"
        )

        corrections = handler.get_feedback_by_type(FeedbackType.CORRECTION)
        assert len(corrections) == 2

        guidance = handler.get_feedback_by_type(FeedbackType.GUIDANCE)
        assert len(guidance) == 1

    def test_pause_for_feedback(self):
        """Should support pausing execution to wait for feedback."""
        handler = FeedbackHandler(execution_id="exec-1")

        handler.pause_for_feedback(reason="Need user decision on approach")
        assert handler.is_paused() is True
        assert handler.pause_reason == "Need user decision on approach"

    def test_resume_with_feedback(self):
        """Should resume execution after receiving feedback."""
        handler = FeedbackHandler(execution_id="exec-1")

        handler.pause_for_feedback(reason="Need clarification")
        assert handler.is_paused() is True

        handler.add_feedback(
            feedback_type=FeedbackType.GUIDANCE,
            content="Use approach A",
            source="user",
        )

        handler.resume_execution()
        assert handler.is_paused() is False
        assert handler.pause_reason is None


# ============================================================================
# ClarificationManager Tests
# ============================================================================


class TestClarificationManager:
    """Test clarification request mechanism."""

    def test_create_clarification_manager(self):
        """Should create a clarification manager."""
        manager = ClarificationManager(execution_id="exec-1")
        assert manager.execution_id == "exec-1"
        assert len(manager.get_all_requests()) == 0

    def test_request_clarification(self):
        """Should create and track clarification requests."""
        manager = ClarificationManager(execution_id="exec-1")

        request = manager.request_clarification(
            question="Which Python version should I use?",
            context={"current_version": "3.11", "available": ["3.11", "3.12"]},
        )

        assert request.question == "Which Python version should I use?"
        assert request.context["current_version"] == "3.11"
        assert request.response is None
        assert isinstance(request.requested_at, datetime)

        all_requests = manager.get_all_requests()
        assert len(all_requests) == 1
        assert all_requests[0] == request

    def test_respond_to_clarification(self):
        """Should record user response to clarification request."""
        manager = ClarificationManager(execution_id="exec-1")

        request = manager.request_clarification(
            question="Which approach?", context={"options": ["A", "B"]}
        )

        response = manager.respond_to_clarification(
            request_id=request.request_id, response_text="Use approach A"
        )

        assert response.request_id == request.request_id
        assert response.response_text == "Use approach A"
        assert isinstance(response.responded_at, datetime)

        # Request should now have response
        updated_request = manager.get_request_by_id(request.request_id)
        assert updated_request.response == response

    def test_get_pending_clarifications(self):
        """Should get clarifications that haven't been answered yet."""
        manager = ClarificationManager(execution_id="exec-1")

        request1 = manager.request_clarification(
            question="Question 1?", context={}
        )
        request2 = manager.request_clarification(
            question="Question 2?", context={}
        )

        manager.respond_to_clarification(
            request_id=request1.request_id, response_text="Answer 1"
        )

        pending = manager.get_pending_clarifications()
        assert len(pending) == 1
        assert pending[0].request_id == request2.request_id

    def test_bulk_request_clarifications(self):
        """Should support requesting multiple clarifications at once."""
        manager = ClarificationManager(execution_id="exec-1")

        questions = [
            "Which Python version?",
            "Which framework?",
            "Which database?",
        ]

        requests = manager.request_multiple_clarifications(
            questions=questions, context={"task": "setup"}
        )

        assert len(requests) == 3
        assert all(req.context["task"] == "setup" for req in requests)

        all_requests = manager.get_all_requests()
        assert len(all_requests) == 3


# ============================================================================
# IterativeRefinementEngine Tests
# ============================================================================


class TestIterativeRefinementEngine:
    """Test iterative refinement based on feedback."""

    def test_create_refinement_engine(self):
        """Should create refinement engine."""
        engine = IterativeRefinementEngine(execution_id="exec-1")
        assert engine.execution_id == "exec-1"
        assert engine.current_round == 0
        assert len(engine.get_refinement_history()) == 0

    def test_start_refinement_round(self):
        """Should start a new refinement round."""
        engine = IterativeRefinementEngine(execution_id="exec-1")

        round1 = engine.start_refinement_round(
            description="Initial implementation", output="Version 1 code"
        )

        assert round1.round_number == 1
        assert round1.description == "Initial implementation"
        assert round1.output == "Version 1 code"
        assert round1.feedback is None
        assert isinstance(round1.started_at, datetime)

        assert engine.current_round == 1

    def test_add_feedback_to_round(self):
        """Should add feedback to current refinement round."""
        engine = IterativeRefinementEngine(execution_id="exec-1")

        engine.start_refinement_round(
            description="Initial", output="V1"
        )

        engine.add_feedback_to_round(
            round_number=1, feedback="Please add error handling"
        )

        updated_round = engine.get_round_by_number(1)
        assert updated_round.feedback == "Please add error handling"

    def test_complete_refinement_round(self):
        """Should mark refinement round as complete."""
        engine = IterativeRefinementEngine(execution_id="exec-1")

        engine.start_refinement_round(description="Initial", output="V1")
        engine.add_feedback_to_round(round_number=1, feedback="Add tests")

        engine.complete_refinement_round(round_number=1)

        updated_round = engine.get_round_by_number(1)
        assert updated_round.completed_at is not None

    def test_multiple_refinement_rounds(self):
        """Should support multiple rounds of refinement."""
        engine = IterativeRefinementEngine(execution_id="exec-1")

        # Round 1
        engine.start_refinement_round(description="Initial", output="V1")
        engine.add_feedback_to_round(1, "Add error handling")
        engine.complete_refinement_round(1)

        # Round 2
        engine.start_refinement_round(
            description="Added error handling", output="V2"
        )
        engine.add_feedback_to_round(2, "Add logging")
        engine.complete_refinement_round(2)

        # Round 3
        engine.start_refinement_round(
            description="Added logging", output="V3"
        )
        engine.add_feedback_to_round(3, "Looks good!")
        engine.complete_refinement_round(3)

        history = engine.get_refinement_history()
        assert len(history) == 3
        assert history[0].round_number == 1
        assert history[1].round_number == 2
        assert history[2].round_number == 3

        assert engine.current_round == 3

    def test_detect_convergence(self):
        """Should detect when refinement has converged (no more changes needed)."""
        engine = IterativeRefinementEngine(execution_id="exec-1")

        # Round 1
        engine.start_refinement_round(description="Initial", output="V1")
        engine.add_feedback_to_round(1, "Add tests")
        engine.complete_refinement_round(1)

        assert engine.has_converged() is False

        # Round 2 - positive feedback indicates convergence
        engine.start_refinement_round(description="With tests", output="V2")
        engine.add_feedback_to_round(2, "Looks perfect!")
        engine.complete_refinement_round(2)

        assert engine.has_converged() is True

    def test_get_latest_output(self):
        """Should get the output from the most recent round."""
        engine = IterativeRefinementEngine(execution_id="exec-1")

        engine.start_refinement_round(description="V1", output="Code V1")
        engine.complete_refinement_round(1)

        engine.start_refinement_round(description="V2", output="Code V2")
        engine.complete_refinement_round(2)

        latest = engine.get_latest_output()
        assert latest == "Code V2"

    def test_get_feedback_summary(self):
        """Should summarize all feedback across rounds."""
        engine = IterativeRefinementEngine(execution_id="exec-1")

        engine.start_refinement_round(description="V1", output="Code V1")
        engine.add_feedback_to_round(1, "Add error handling")
        engine.complete_refinement_round(1)

        engine.start_refinement_round(description="V2", output="Code V2")
        engine.add_feedback_to_round(2, "Add logging")
        engine.complete_refinement_round(2)

        engine.start_refinement_round(description="V3", output="Code V3")
        engine.add_feedback_to_round(3, "Perfect!")
        engine.complete_refinement_round(3)

        summary = engine.get_feedback_summary()
        assert len(summary) == 3
        assert summary[0] == "Round 1: Add error handling"
        assert summary[1] == "Round 2: Add logging"
        assert summary[2] == "Round 3: Perfect!"
