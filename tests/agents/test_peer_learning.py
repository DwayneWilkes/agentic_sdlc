"""
Tests for peer learning protocol - agent knowledge sharing.
"""

from src.agents.peer_learning import (
    KnowledgeTransferResult,
    PairDebugSession,
    PeerLearningProtocol,
    TeachingSession,
    WarStory,
)


class TestPeerLearningProtocol:
    """Tests for peer learning protocol."""

    def test_protocol_creation(self):
        """Test creating a peer learning protocol."""
        protocol = PeerLearningProtocol(agent_id="test-agent")
        assert protocol.agent_id == "test-agent"

    def test_find_expert(self):
        """Test finding an expert on a topic."""
        protocol = PeerLearningProtocol(agent_id="learner")

        # Record some expertise
        protocol.record_expertise("expert-1", "OAuth2", confidence=0.9)
        protocol.record_expertise("expert-2", "OAuth2", confidence=0.7)
        protocol.record_expertise("expert-3", "Docker", confidence=0.8)

        # Find expert on OAuth2
        expert = protocol.find_expert("OAuth2")
        assert expert == "expert-1"  # Highest confidence

        # Find expert on Docker
        expert = protocol.find_expert("Docker")
        assert expert == "expert-3"

        # No expert on unknown topic
        expert = protocol.find_expert("Quantum Computing")
        assert expert is None

    def test_request_teaching(self):
        """Test requesting a teaching session."""
        protocol = PeerLearningProtocol(agent_id="learner")

        session = protocol.request_teaching(
            topic="Test-Driven Development",
            current_knowledge_level=0.3,
            desired_outcome="Understand TDD workflow and pytest",
        )

        assert session.learner == "learner"
        assert session.topic == "Test-Driven Development"
        assert session.current_knowledge == 0.3
        assert session.desired_outcome == "Understand TDD workflow and pytest"
        assert session.teacher is None  # Not assigned yet

    def test_accept_teaching_request(self):
        """Test accepting a teaching request."""
        learner_protocol = PeerLearningProtocol(agent_id="learner")
        teacher_protocol = PeerLearningProtocol(agent_id="teacher")

        session = learner_protocol.request_teaching(
            topic="Git workflows",
            current_knowledge_level=0.4,
        )

        # Teacher accepts the request
        session = teacher_protocol.accept_teaching(session)
        assert session.teacher == "teacher"
        assert session.accepted_at is not None


class TestTeachingSession:
    """Tests for teaching sessions."""

    def test_teaching_session_creation(self):
        """Test creating a teaching session."""
        session = TeachingSession(
            session_id="teach-123",
            topic="Async programming",
            learner="student-agent",
            teacher="expert-agent",
            current_knowledge=0.4,
        )

        assert session.session_id == "teach-123"
        assert session.topic == "Async programming"
        assert session.learner == "student-agent"
        assert session.teacher == "expert-agent"
        assert session.current_knowledge == 0.4

    def test_complete_teaching_session(self):
        """Test completing a teaching session."""
        session = TeachingSession(
            session_id="teach-123",
            topic="Docker basics",
            learner="student",
            teacher="expert",
            current_knowledge=0.2,
        )

        result = KnowledgeTransferResult(
            knowledge_transferred=True,
            new_knowledge_level=0.7,
            key_learnings=[
                "Docker images are immutable",
                "Use docker-compose for multi-container apps",
            ],
            follow_up_needed=False,
        )

        session.complete(result)

        assert session.result == result
        assert session.completed_at is not None
        assert session.result.knowledge_transferred


class TestWarStory:
    """Tests for war story sharing."""

    def test_war_story_creation(self):
        """Test creating a war story."""
        story = WarStory(
            story_id="war-123",
            teller="veteran-agent",
            title="The Great Race Condition of 2024",
            context="Production outage during Black Friday",
            what_happened="Async tasks were accessing shared state without locks",
            lessons_learned=[
                "Always use locks for shared state",
                "Add timeout guards on all network calls",
                "Have a rollback plan",
            ],
        )

        assert story.story_id == "war-123"
        assert story.teller == "veteran-agent"
        assert len(story.lessons_learned) == 3
        assert "rollback" in story.lessons_learned[2]

    def test_war_story_listeners(self):
        """Test adding listeners to a war story."""
        story = WarStory(
            story_id="war-123",
            teller="veteran",
            title="Debugging nightmare",
            context="CI tests failing randomly",
            what_happened="Race condition in test setup",
            lessons_learned=["Avoid global state in tests"],
        )

        story.add_listener("agent-1")
        story.add_listener("agent-2")

        assert len(story.listeners) == 2
        assert "agent-1" in story.listeners
        assert "agent-2" in story.listeners


class TestPairDebugSession:
    """Tests for pair debugging."""

    def test_pair_debug_creation(self):
        """Test creating a pair debug session."""
        session = PairDebugSession(
            session_id="debug-123",
            topic="Test failing in CI",
            pair_members=["agent-1", "agent-2"],
            problem_description="Test passes locally but fails in CI",
            initial_hypothesis="Timing or environment issue",
        )

        assert session.session_id == "debug-123"
        assert len(session.pair_members) == 2
        assert session.problem_description is not None
        assert session.solution is None  # Not solved yet

    def test_pair_debug_solve(self):
        """Test solving a problem in pair debugging."""
        session = PairDebugSession(
            session_id="debug-123",
            topic="Memory leak",
            pair_members=["agent-1", "agent-2"],
            problem_description="Memory grows over time",
            initial_hypothesis="Circular references",
        )

        session.solve(
            solution="Added weak references to break cycles",
            who_found_it="agent-2",
            how_they_found_it="Used memory profiler to track references",
        )

        assert session.solution is not None
        assert session.solved_by == "agent-2"
        assert "profiler" in session.how_solved
        assert session.solved_at is not None


def test_knowledge_transfer_result():
    """Test knowledge transfer result."""
    result = KnowledgeTransferResult(
        knowledge_transferred=True,
        new_knowledge_level=0.8,
        key_learnings=["Learning 1", "Learning 2"],
        follow_up_needed=True,
        follow_up_topics=["Advanced topic A"],
    )

    assert result.knowledge_transferred
    assert result.new_knowledge_level == 0.8
    assert len(result.key_learnings) == 2
    assert result.follow_up_needed
    assert "Advanced topic A" in result.follow_up_topics
