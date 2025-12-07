"""
Interaction Logger for tracking all agent communications.

This module provides comprehensive logging of all agent-to-agent interactions
via the NATS message bus, enabling full transparency and debugging capabilities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.coordination.nats_bus import AgentMessage, MessageType


@dataclass
class LoggedInteraction:
    """
    A logged interaction between agents.

    Captures all relevant data from an AgentMessage for queryable history.
    """

    from_agent: str
    to_agent: str | None  # None for broadcast messages
    message_type: MessageType
    content: dict[str, Any]
    timestamp: str
    correlation_id: str | None = None

    @classmethod
    def from_agent_message(cls, message: AgentMessage) -> "LoggedInteraction":
        """
        Create a LoggedInteraction from an AgentMessage.

        Args:
            message: The AgentMessage to log

        Returns:
            LoggedInteraction instance
        """
        return cls(
            from_agent=message.from_agent,
            to_agent=message.to_agent,
            message_type=message.message_type,
            content=message.content,
            timestamp=message.timestamp,
            correlation_id=message.correlation_id,
        )


@dataclass
class InteractionQuery:
    """
    Query parameters for filtering interaction logs.

    All parameters are optional and will be combined with AND logic.
    """

    agent_id: str | None = None  # Match either from_agent or to_agent
    message_type: MessageType | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    broadcast_only: bool = False  # Only return broadcast messages (to_agent=None)


class InteractionLogger:
    """
    Logs and queries agent interactions for transparency and debugging.

    This logger captures all agent-to-agent communications passing through
    the NATS message bus, storing them in a queryable format.

    Features:
    - Full message history with timestamps
    - Query by agent, message type, time range
    - Conversation reconstruction between agents
    - Agent timeline views
    - Broadcast message tracking
    """

    def __init__(self) -> None:
        """Initialize the interaction logger."""
        self._interactions: list[LoggedInteraction] = []

    def log_interaction(self, message: AgentMessage) -> None:
        """
        Log an agent interaction.

        Args:
            message: The AgentMessage to log
        """
        interaction = LoggedInteraction.from_agent_message(message)
        self._interactions.append(interaction)

    def get_all_interactions(self) -> list[LoggedInteraction]:
        """
        Get all logged interactions.

        Returns:
            List of all LoggedInteraction objects
        """
        return self._interactions.copy()

    def query_interactions(self, query: InteractionQuery) -> list[LoggedInteraction]:
        """
        Query interactions with filters.

        Args:
            query: InteractionQuery with filter parameters

        Returns:
            List of LoggedInteraction objects matching the query
        """
        results = self._interactions

        # Filter by agent ID (either from or to)
        if query.agent_id is not None:
            results = [
                i for i in results
                if i.from_agent == query.agent_id or i.to_agent == query.agent_id
            ]

        # Filter by message type
        if query.message_type is not None:
            results = [
                i for i in results
                if i.message_type == query.message_type
            ]

        # Filter by time range
        if query.start_time is not None:
            results = [
                i for i in results
                if datetime.fromisoformat(i.timestamp) >= query.start_time
            ]

        if query.end_time is not None:
            results = [
                i for i in results
                if datetime.fromisoformat(i.timestamp) <= query.end_time
            ]

        # Filter for broadcast messages only
        if query.broadcast_only:
            results = [
                i for i in results
                if i.to_agent is None
            ]

        return results

    def get_conversation(self, agent1: str, agent2: str) -> list[LoggedInteraction]:
        """
        Get all interactions between two specific agents.

        Args:
            agent1: First agent ID
            agent2: Second agent ID

        Returns:
            List of interactions between the two agents, in chronological order
        """
        # Get interactions where both agents are involved
        conversation = [
            i for i in self._interactions
            if (i.from_agent == agent1 and i.to_agent == agent2)
            or (i.from_agent == agent2 and i.to_agent == agent1)
        ]

        # Sort by timestamp
        conversation.sort(key=lambda i: datetime.fromisoformat(i.timestamp))

        return conversation

    def get_agent_timeline(self, agent_id: str) -> list[LoggedInteraction]:
        """
        Get chronological timeline of all interactions involving an agent.

        Args:
            agent_id: The agent ID

        Returns:
            List of interactions involving the agent, sorted by timestamp (oldest first)
        """
        # Get all interactions involving this agent
        timeline = [
            i for i in self._interactions
            if i.from_agent == agent_id or i.to_agent == agent_id
        ]

        # Sort by timestamp (oldest first)
        timeline.sort(key=lambda i: datetime.fromisoformat(i.timestamp))

        return timeline

    def clear_logs(self) -> None:
        """Clear all logged interactions."""
        self._interactions.clear()
