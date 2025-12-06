"""
NATS-based message bus for inter-agent communication.

This module provides a high-level interface for agent communication using NATS,
supporting pub/sub, request/reply, and queue groups for workload distribution.
"""

import asyncio
import json
from typing import Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import nats
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg


class MessageType(str, Enum):
    """Types of messages agents can exchange."""
    STATUS_UPDATE = "status_update"
    TASK_ASSIGNMENT = "task_assignment"
    TASK_ASSIGNED = "task_assigned"  # Work stream claimed
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    QUESTION = "question"
    ANSWER = "answer"
    BLOCKER = "blocker"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_RESPONSE = "resource_response"
    COORDINATION_REQUEST = "coordination_request"
    HEARTBEAT = "heartbeat"
    # Control commands from orchestrator to agents
    STOP_TASK = "stop_task"  # Stop current work (graceful or immediate)
    UPDATE_GOAL = "update_goal"  # Update agent's goal/task
    PAUSE_AGENT = "pause_agent"  # Pause agent activity
    RESUME_AGENT = "resume_agent"  # Resume agent activity
    PING = "ping"  # Check if agent is responsive
    PONG = "pong"  # Response to ping


@dataclass
class AgentMessage:
    """Standard message format for agent communication."""

    from_agent: str
    to_agent: Optional[str]  # None for broadcast
    message_type: MessageType
    content: dict[str, Any]
    timestamp: str
    correlation_id: Optional[str] = None  # For request/reply tracking

    def to_json(self) -> str:
        """Serialize message to JSON."""
        return json.dumps({
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        })

    @classmethod
    def from_json(cls, data: str) -> "AgentMessage":
        """Deserialize message from JSON."""
        obj = json.loads(data)
        return cls(
            from_agent=obj["from_agent"],
            to_agent=obj.get("to_agent"),
            message_type=MessageType(obj["message_type"]),
            content=obj["content"],
            timestamp=obj["timestamp"],
            correlation_id=obj.get("correlation_id"),
        )


class NATSMessageBus:
    """
    NATS-based message bus for orchestrator agent communication.

    Features:
    - Pub/sub for broadcast messages
    - Request/reply for direct agent communication
    - Queue groups for load balancing
    - Subject hierarchy for topic organization

    Subject Structure:
    - orchestrator.broadcast.{message_type} - Broadcast to all agents
    - orchestrator.agent.{agent_id}.{message_type} - Direct to specific agent
    - orchestrator.team.{team_id}.{message_type} - Team-specific
    - orchestrator.queue.{queue_name} - Work queue for load balancing
    """

    def __init__(self, nats_url: str = "nats://localhost:4222"):
        """
        Initialize NATS message bus.

        Args:
            nats_url: NATS server URL
        """
        self.nats_url = nats_url
        self.nc: Optional[NATSClient] = None
        self.subscriptions: dict[str, int] = {}

    async def connect(self) -> None:
        """Connect to NATS server."""
        if self.nc:
            return

        self.nc = await nats.connect(self.nats_url)
        print(f"Connected to NATS at {self.nats_url}")

    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            self.nc = None
            print("Disconnected from NATS")

    async def publish(
        self,
        subject: str,
        message: AgentMessage
    ) -> None:
        """
        Publish a message to a subject.

        Args:
            subject: NATS subject to publish to
            message: Message to publish
        """
        if not self.nc:
            raise RuntimeError("Not connected to NATS")

        await self.nc.publish(subject, message.to_json().encode())

    async def broadcast(
        self,
        from_agent: str,
        message_type: MessageType,
        content: dict[str, Any]
    ) -> None:
        """
        Broadcast a message to all agents.

        Args:
            from_agent: ID of sending agent
            message_type: Type of message
            content: Message payload
        """
        subject = f"orchestrator.broadcast.{message_type.value}"
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=None,
            message_type=message_type,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
        )
        await self.publish(subject, message)

    async def send_to_agent(
        self,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        content: dict[str, Any]
    ) -> None:
        """
        Send a direct message to a specific agent.

        Args:
            from_agent: ID of sending agent
            to_agent: ID of receiving agent
            message_type: Type of message
            content: Message payload
        """
        subject = f"orchestrator.agent.{to_agent}.{message_type.value}"
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
        )
        await self.publish(subject, message)

    async def request(
        self,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        content: dict[str, Any],
        timeout: float = 5.0
    ) -> AgentMessage:
        """
        Send a request and wait for reply (request/reply pattern).

        Args:
            from_agent: ID of requesting agent
            to_agent: ID of agent to request from
            message_type: Type of request
            content: Request payload
            timeout: Timeout in seconds

        Returns:
            Reply message

        Raises:
            TimeoutError: If no reply received within timeout
        """
        if not self.nc:
            raise RuntimeError("Not connected to NATS")

        subject = f"orchestrator.agent.{to_agent}.{message_type.value}"
        correlation_id = f"{from_agent}-{datetime.utcnow().timestamp()}"

        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id,
        )

        try:
            response = await self.nc.request(
                subject,
                message.to_json().encode(),
                timeout=timeout
            )
            return AgentMessage.from_json(response.data.decode())
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"No reply from {to_agent} within {timeout}s"
            )

    async def subscribe(
        self,
        subject: str,
        callback: Callable[[AgentMessage], None],
        queue: Optional[str] = None
    ) -> int:
        """
        Subscribe to a subject.

        Args:
            subject: NATS subject pattern to subscribe to
            callback: Function to call when message received
            queue: Optional queue group name for load balancing

        Returns:
            Subscription ID
        """
        if not self.nc:
            raise RuntimeError("Not connected to NATS")

        async def message_handler(msg: Msg) -> None:
            """Internal handler that deserializes and calls callback."""
            try:
                agent_msg = AgentMessage.from_json(msg.data.decode())

                # If this is a request, callback should return response
                if msg.reply:
                    response = await callback(agent_msg)
                    if response:
                        await self.nc.publish(msg.reply, response.to_json().encode())
                else:
                    await callback(agent_msg)
            except Exception as e:
                print(f"Error handling message: {e}")

        sub = await self.nc.subscribe(subject, queue=queue, cb=message_handler)
        self.subscriptions[subject] = sub._id

        return sub._id

    async def subscribe_to_agent_messages(
        self,
        agent_id: str,
        callback: Callable[[AgentMessage], Optional[AgentMessage]]
    ) -> list[int]:
        """
        Subscribe to all messages for a specific agent.

        Args:
            agent_id: ID of agent to receive messages for
            callback: Function to handle messages (can return reply for requests)

        Returns:
            List of subscription IDs
        """
        # Subscribe to direct messages
        subject = f"orchestrator.agent.{agent_id}.>"
        sub_ids = []

        sub_id = await self.subscribe(subject, callback)
        sub_ids.append(sub_id)

        # Subscribe to broadcasts
        broadcast_subject = "orchestrator.broadcast.>"
        sub_id = await self.subscribe(broadcast_subject, callback)
        sub_ids.append(sub_id)

        return sub_ids

    async def create_work_queue(
        self,
        queue_name: str,
        callback: Callable[[AgentMessage], None],
        num_workers: int = 1
    ) -> list[int]:
        """
        Create a work queue with multiple workers for load balancing.

        Args:
            queue_name: Name of the work queue
            callback: Function to process work items
            num_workers: Number of workers in queue group

        Returns:
            List of subscription IDs
        """
        subject = f"orchestrator.queue.{queue_name}"
        sub_ids = []

        for i in range(num_workers):
            sub_id = await self.subscribe(
                subject,
                callback,
                queue=f"{queue_name}_workers"
            )
            sub_ids.append(sub_id)

        return sub_ids

    async def publish_to_queue(
        self,
        queue_name: str,
        from_agent: str,
        message_type: MessageType,
        content: dict[str, Any]
    ) -> None:
        """
        Publish work to a queue.

        Args:
            queue_name: Name of work queue
            from_agent: ID of agent publishing work
            message_type: Type of work
            content: Work payload
        """
        subject = f"orchestrator.queue.{queue_name}"
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=None,
            message_type=message_type,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
        )
        await self.publish(subject, message)

    async def get_stats(self) -> dict[str, Any]:
        """
        Get NATS connection statistics.

        Returns:
            Dictionary of connection stats
        """
        if not self.nc:
            return {"connected": False}

        return {
            "connected": self.nc.is_connected,
            "server_info": self.nc.connected_server_info,
            "stats": self.nc.stats,
            "subscriptions": len(self.subscriptions),
        }


# Singleton instance for convenience
_bus_instance: Optional[NATSMessageBus] = None


async def get_message_bus(nats_url: str = "nats://localhost:4222") -> NATSMessageBus:
    """
    Get or create the global message bus instance.

    Args:
        nats_url: NATS server URL

    Returns:
        Message bus instance
    """
    global _bus_instance

    if _bus_instance is None:
        _bus_instance = NATSMessageBus(nats_url)
        await _bus_instance.connect()

    return _bus_instance


async def cleanup_message_bus() -> None:
    """Cleanup global message bus instance."""
    global _bus_instance

    if _bus_instance:
        await _bus_instance.disconnect()
        _bus_instance = None
