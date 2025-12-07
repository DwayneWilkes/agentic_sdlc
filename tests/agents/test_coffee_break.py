"""
Tests for coffee break system - agent peer learning dialogue.
"""

from src.agents.coffee_break import (
    CoffeeBreakScheduler,
    CoffeeBreakSession,
    SessionTrigger,
    SessionType,
)


class TestCoffeeBreakScheduler:
    """Tests for coffee break scheduler."""

    def test_scheduler_creation(self):
        """Test creating a coffee break scheduler."""
        scheduler = CoffeeBreakScheduler(
            agent_id="test-agent",
            task_interval=5,  # Every 5 tasks
            time_interval_minutes=30,  # Or every 30 minutes
        )
        assert scheduler.agent_id == "test-agent"
        assert scheduler.task_interval == 5
        assert scheduler.time_interval_minutes == 30
        assert scheduler.task_count == 0

    def test_should_trigger_on_task_count(self):
        """Test triggering coffee break after N tasks."""
        scheduler = CoffeeBreakScheduler(
            agent_id="test-agent",
            task_interval=3,
        )

        # Not triggered yet
        assert not scheduler.should_trigger()

        # Increment task count
        scheduler.increment_task_count()
        scheduler.increment_task_count()
        assert not scheduler.should_trigger()

        # Third task should trigger
        scheduler.increment_task_count()
        assert scheduler.should_trigger()

        # Reset after trigger
        scheduler.reset()
        assert scheduler.task_count == 0
        assert not scheduler.should_trigger()

    def test_manual_trigger(self):
        """Test manually triggering a coffee break."""
        scheduler = CoffeeBreakScheduler(agent_id="test-agent")

        session = scheduler.trigger_manual(
            topic="OAuth2 implementation",
            reason="Stuck on token refresh"
        )

        assert session.trigger == SessionTrigger.MANUAL
        assert session.topic == "OAuth2 implementation"
        assert session.context["reason"] == "Stuck on token refresh"
        assert session.session_type == SessionType.NEED_BASED

    def test_scheduled_coffee_break(self):
        """Test scheduled coffee break creation."""
        scheduler = CoffeeBreakScheduler(
            agent_id="test-agent",
            task_interval=1,
        )

        scheduler.increment_task_count()
        assert scheduler.should_trigger()

        session = scheduler.create_scheduled_break()
        assert session.trigger == SessionTrigger.SCHEDULED
        assert session.session_type == SessionType.SCHEDULED
        assert session.initiator == "test-agent"


class TestCoffeeBreakSession:
    """Tests for coffee break sessions."""

    def test_session_creation(self):
        """Test creating a coffee break session."""
        session = CoffeeBreakSession(
            session_id="session-123",
            initiator="agent-1",
            participants=["agent-1", "agent-2"],
            session_type=SessionType.PAIR_DEBUG,
            topic="Async debugging",
            trigger=SessionTrigger.MANUAL,
        )

        assert session.session_id == "session-123"
        assert session.initiator == "agent-1"
        assert session.participants == ["agent-1", "agent-2"]
        assert session.session_type == SessionType.PAIR_DEBUG
        assert session.topic == "Async debugging"
        assert session.trigger == SessionTrigger.MANUAL
        assert session.outcome is None

    def test_session_completion(self):
        """Test completing a session with outcome."""
        session = CoffeeBreakSession(
            session_id="session-123",
            initiator="agent-1",
            participants=["agent-1", "agent-2"],
            session_type=SessionType.TEACHING,
            topic="Test-driven development",
            trigger=SessionTrigger.NEED_BASED,
        )

        outcome = {
            "knowledge_transferred": True,
            "receiving_agent": "agent-2",
            "confidence_before": 0.3,
            "confidence_after": 0.8,
            "summary": "Learned TDD workflow and pytest best practices",
        }

        session.complete(outcome)

        assert session.outcome == outcome
        assert session.completed_at is not None

    def test_retrospective_session(self):
        """Test creating a retrospective session."""
        session = CoffeeBreakSession(
            session_id="retro-1",
            initiator="agent-1",
            participants=["agent-1", "agent-2", "agent-3"],
            session_type=SessionType.RETROSPECTIVE,
            topic="Phase 2.1 completion",
            trigger=SessionTrigger.POST_TASK,
            context={
                "task_id": "phase-2.1",
                "duration_hours": 4.5,
                "challenges": ["Complex dependencies", "Unclear requirements"],
            },
        )

        assert session.session_type == SessionType.RETROSPECTIVE
        assert len(session.participants) == 3
        assert "task_id" in session.context


class TestSessionTypes:
    """Test different session type behaviors."""

    def test_teaching_session(self):
        """Test peer teaching session."""
        session = CoffeeBreakSession(
            session_id="teach-1",
            initiator="expert-agent",
            participants=["expert-agent", "learner-agent"],
            session_type=SessionType.TEACHING,
            topic="Git rebase workflow",
            trigger=SessionTrigger.NEED_BASED,
            context={
                "teacher": "expert-agent",
                "learner": "learner-agent",
            },
        )

        assert session.session_type == SessionType.TEACHING
        assert session.context["teacher"] == "expert-agent"
        assert session.context["learner"] == "learner-agent"

    def test_war_story_session(self):
        """Test war story sharing session."""
        session = CoffeeBreakSession(
            session_id="story-1",
            initiator="veteran-agent",
            participants=["veteran-agent", "agent-2", "agent-3"],
            session_type=SessionType.WAR_STORY,
            topic="Debugging production outage",
            trigger=SessionTrigger.SCHEDULED,
            context={
                "story": "The time I tracked down a race condition in async code...",
                "lessons": [
                    "Always check event loop state",
                    "Use asyncio debug mode in development",
                    "Add timeout guards on all awaits",
                ],
            },
        )

        assert session.session_type == SessionType.WAR_STORY
        assert "lessons" in session.context
        assert len(session.context["lessons"]) == 3

    def test_pair_debug_session(self):
        """Test pair debugging session."""
        session = CoffeeBreakSession(
            session_id="debug-1",
            initiator="agent-1",
            participants=["agent-1", "agent-2"],
            session_type=SessionType.PAIR_DEBUG,
            topic="Failing test in test_orchestrator.py",
            trigger=SessionTrigger.MANUAL,
            context={
                "problem": "Test passes locally but fails in CI",
                "hypothesis": "Timing or environment issue",
            },
        )

        assert session.session_type == SessionType.PAIR_DEBUG
        assert len(session.participants) == 2
        assert "problem" in session.context


def test_session_serialization():
    """Test serializing and deserializing sessions."""
    session = CoffeeBreakSession(
        session_id="session-123",
        initiator="agent-1",
        participants=["agent-1", "agent-2"],
        session_type=SessionType.TEACHING,
        topic="Test patterns",
        trigger=SessionTrigger.SCHEDULED,
    )

    # Convert to dict
    data = session.to_dict()
    assert data["session_id"] == "session-123"
    assert data["session_type"] == "teaching"
    assert data["trigger"] == "scheduled"

    # Reconstruct from dict
    reconstructed = CoffeeBreakSession.from_dict(data)
    assert reconstructed.session_id == session.session_id
    assert reconstructed.session_type == session.session_type
    assert reconstructed.trigger == session.trigger
