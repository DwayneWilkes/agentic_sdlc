"""Tests for the InteractionLogger."""

from datetime import datetime, timedelta

from src.coordination.interaction_logger import (
    InteractionLogger,
    InteractionQuery,
    LoggedInteraction,
)
from src.coordination.nats_bus import AgentMessage, MessageType


class TestInteractionLogger:
    """Test suite for InteractionLogger."""

    def test_log_interaction_stores_message(self):
        """Test that logging an interaction stores it correctly."""
        logger = InteractionLogger()

        message = AgentMessage(
            from_agent="agent-1",
            to_agent="agent-2",
            message_type=MessageType.TASK_ASSIGNMENT,
            content={"task_id": "task-123"},
            timestamp=datetime.now().isoformat(),
        )

        logger.log_interaction(message)

        # Verify message was logged
        interactions = logger.get_all_interactions()
        assert len(interactions) == 1
        assert interactions[0].from_agent == "agent-1"
        assert interactions[0].to_agent == "agent-2"
        assert interactions[0].message_type == MessageType.TASK_ASSIGNMENT

    def test_log_multiple_interactions(self):
        """Test logging multiple interactions."""
        logger = InteractionLogger()

        for i in range(5):
            message = AgentMessage(
                from_agent=f"agent-{i}",
                to_agent="agent-orchestrator",
                message_type=MessageType.STATUS_UPDATE,
                content={"status": "working"},
                timestamp=datetime.now().isoformat(),
            )
            logger.log_interaction(message)

        interactions = logger.get_all_interactions()
        assert len(interactions) == 5

    def test_query_by_agent(self):
        """Test querying interactions by agent ID."""
        logger = InteractionLogger()

        # Log interactions from different agents
        for i in range(3):
            message = AgentMessage(
                from_agent="agent-1",
                to_agent=f"agent-{i}",
                message_type=MessageType.QUESTION,
                content={"question": f"Question {i}"},
                timestamp=datetime.now().isoformat(),
            )
            logger.log_interaction(message)

        # Query for agent-1
        query = InteractionQuery(agent_id="agent-1")
        results = logger.query_interactions(query)

        assert len(results) == 3
        for interaction in results:
            assert interaction.from_agent == "agent-1"

    def test_query_by_message_type(self):
        """Test querying interactions by message type."""
        logger = InteractionLogger()

        # Log different message types
        types = [MessageType.STATUS_UPDATE, MessageType.TASK_COMPLETE, MessageType.STATUS_UPDATE]
        for msg_type in types:
            message = AgentMessage(
                from_agent="agent-1",
                to_agent="agent-2",
                message_type=msg_type,
                content={},
                timestamp=datetime.now().isoformat(),
            )
            logger.log_interaction(message)

        # Query for STATUS_UPDATE only
        query = InteractionQuery(message_type=MessageType.STATUS_UPDATE)
        results = logger.query_interactions(query)

        assert len(results) == 2
        for interaction in results:
            assert interaction.message_type == MessageType.STATUS_UPDATE

    def test_query_by_time_range(self):
        """Test querying interactions by time range."""
        logger = InteractionLogger()

        now = datetime.now()

        # Log interactions at different times
        times = [
            now - timedelta(hours=2),
            now - timedelta(hours=1),
            now,
        ]

        for time in times:
            message = AgentMessage(
                from_agent="agent-1",
                to_agent="agent-2",
                message_type=MessageType.STATUS_UPDATE,
                content={},
                timestamp=time.isoformat(),
            )
            logger.log_interaction(message)

        # Query for last hour
        query = InteractionQuery(
            start_time=now - timedelta(hours=1, minutes=30),
            end_time=now + timedelta(minutes=1),
        )
        results = logger.query_interactions(query)

        # Should get the last 2 messages
        assert len(results) == 2

    def test_query_multiple_filters(self):
        """Test querying with multiple filters combined."""
        logger = InteractionLogger()

        now = datetime.now()

        # Log various interactions
        interactions = [
            ("agent-1", "agent-2", MessageType.STATUS_UPDATE, now - timedelta(hours=1)),
            ("agent-1", "agent-3", MessageType.TASK_COMPLETE, now - timedelta(minutes=30)),
            ("agent-2", "agent-1", MessageType.STATUS_UPDATE, now - timedelta(minutes=10)),
            ("agent-1", "agent-2", MessageType.STATUS_UPDATE, now),
        ]

        for from_agent, to_agent, msg_type, time in interactions:
            message = AgentMessage(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=msg_type,
                content={},
                timestamp=time.isoformat(),
            )
            logger.log_interaction(message)

        # Query: agent-1, STATUS_UPDATE, last hour
        query = InteractionQuery(
            agent_id="agent-1",
            message_type=MessageType.STATUS_UPDATE,
            start_time=now - timedelta(hours=1, minutes=5),
        )
        results = logger.query_interactions(query)

        # Should match 3 interactions (rows 1, 3, 4 - agent-1 involved as sender or receiver)
        assert len(results) == 3

    def test_get_conversation_between_agents(self):
        """Test retrieving a conversation between two specific agents."""
        logger = InteractionLogger()

        # Log conversation between agent-1 and agent-2
        messages = [
            ("agent-1", "agent-2", "Hello"),
            ("agent-2", "agent-1", "Hi there"),
            ("agent-3", "agent-1", "Unrelated"),
            ("agent-1", "agent-2", "How are you?"),
            ("agent-2", "agent-1", "Good!"),
        ]

        for from_agent, to_agent, content in messages:
            message = AgentMessage(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=MessageType.QUESTION,
                content={"text": content},
                timestamp=datetime.now().isoformat(),
            )
            logger.log_interaction(message)

        # Get conversation between agent-1 and agent-2
        conversation = logger.get_conversation("agent-1", "agent-2")

        # Should get 4 messages (excluding agent-3)
        assert len(conversation) == 4

        # Verify all involve agent-1 and agent-2
        for interaction in conversation:
            agents = {interaction.from_agent, interaction.to_agent}
            assert agents == {"agent-1", "agent-2"}

    def test_get_agent_timeline(self):
        """Test getting chronological timeline for an agent."""
        logger = InteractionLogger()

        now = datetime.now()

        # Log interactions in mixed order
        interactions = [
            ("agent-1", "agent-2", now - timedelta(hours=2)),
            ("agent-3", "agent-1", now - timedelta(hours=1)),
            ("agent-1", "agent-4", now - timedelta(minutes=30)),
            ("agent-2", "agent-3", now - timedelta(minutes=10)),  # Unrelated
        ]

        for from_agent, to_agent, time in interactions:
            message = AgentMessage(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=MessageType.STATUS_UPDATE,
                content={},
                timestamp=time.isoformat(),
            )
            logger.log_interaction(message)

        # Get timeline for agent-1
        timeline = logger.get_agent_timeline("agent-1")

        # Should have 3 interactions involving agent-1
        assert len(timeline) == 3

        # Verify chronological order (oldest first)
        timestamps = [datetime.fromisoformat(i.timestamp) for i in timeline]
        assert timestamps == sorted(timestamps)

    def test_logged_interaction_format(self):
        """Test that LoggedInteraction captures all necessary data."""
        logger = InteractionLogger()

        message = AgentMessage(
            from_agent="agent-1",
            to_agent="agent-2",
            message_type=MessageType.TASK_ASSIGNMENT,
            content={"task_id": "task-123", "priority": "high"},
            timestamp=datetime.now().isoformat(),
            correlation_id="corr-456",
        )

        logger.log_interaction(message)

        interactions = logger.get_all_interactions()
        logged = interactions[0]

        assert isinstance(logged, LoggedInteraction)
        assert logged.from_agent == "agent-1"
        assert logged.to_agent == "agent-2"
        assert logged.message_type == MessageType.TASK_ASSIGNMENT
        assert logged.content == {"task_id": "task-123", "priority": "high"}
        assert logged.correlation_id == "corr-456"
        assert logged.timestamp is not None

    def test_clear_logs(self):
        """Test clearing interaction logs."""
        logger = InteractionLogger()

        # Log some interactions
        for i in range(3):
            message = AgentMessage(
                from_agent=f"agent-{i}",
                to_agent="agent-orchestrator",
                message_type=MessageType.STATUS_UPDATE,
                content={},
                timestamp=datetime.now().isoformat(),
            )
            logger.log_interaction(message)

        assert len(logger.get_all_interactions()) == 3

        # Clear logs
        logger.clear_logs()

        assert len(logger.get_all_interactions()) == 0

    def test_log_broadcast_message(self):
        """Test logging broadcast messages (to_agent=None)."""
        logger = InteractionLogger()

        message = AgentMessage(
            from_agent="orchestrator",
            to_agent=None,  # Broadcast
            message_type=MessageType.STATUS_UPDATE,
            content={"message": "System update"},
            timestamp=datetime.now().isoformat(),
        )

        logger.log_interaction(message)

        interactions = logger.get_all_interactions()
        assert len(interactions) == 1
        assert interactions[0].to_agent is None

    def test_query_broadcast_messages(self):
        """Test querying for broadcast messages."""
        logger = InteractionLogger()

        # Log mix of direct and broadcast messages
        messages = [
            ("agent-1", "agent-2", MessageType.QUESTION),
            ("orchestrator", None, MessageType.STATUS_UPDATE),  # Broadcast
            ("agent-2", None, MessageType.STATUS_UPDATE),  # Broadcast
            ("agent-3", "agent-1", MessageType.ANSWER),
        ]

        for from_agent, to_agent, msg_type in messages:
            message = AgentMessage(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=msg_type,
                content={},
                timestamp=datetime.now().isoformat(),
            )
            logger.log_interaction(message)

        # Query for broadcast messages
        query = InteractionQuery(broadcast_only=True)
        results = logger.query_interactions(query)

        assert len(results) == 2
        for interaction in results:
            assert interaction.to_agent is None
