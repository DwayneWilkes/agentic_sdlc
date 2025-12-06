"""
NATS Coordinator - Real-time agent communication via NATS.

Provides:
- Broadcasting commands to all agents
- Direct messaging to specific agents
- Receiving status updates from agents
- Stop/pause/resume commands
"""

import asyncio
import json
from typing import Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

try:
    import nats
    from nats.aio.client import Client as NATSClient
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    NATSClient = None


class CommandType(str, Enum):
    """Types of commands that can be sent to agents."""
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    STATUS = "status"
    REDIRECT = "redirect"
    FEEDBACK = "feedback"


@dataclass
class AgentCommand:
    """A command to send to an agent."""
    command_type: CommandType
    target_agent: Optional[str] = None  # None = broadcast to all
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentMessage:
    """A message received from an agent."""
    agent_id: str
    message_type: str
    content: Any
    timestamp: str


class NATSCoordinator:
    """
    Coordinates agent communication via NATS.

    Subject hierarchy:
    - orchestrator.broadcast.{type} - Broadcast to all agents
    - orchestrator.agent.{agent_id}.{type} - Direct to specific agent
    - orchestrator.status.{agent_id} - Status updates from agents
    """

    BROADCAST_SUBJECT = "orchestrator.broadcast"
    AGENT_SUBJECT = "orchestrator.agent"
    STATUS_SUBJECT = "orchestrator.status"

    def __init__(
        self,
        nats_url: str = "nats://localhost:4222",
        on_message: Optional[Callable[[AgentMessage], None]] = None,
    ):
        """
        Initialize the NATS coordinator.

        Args:
            nats_url: NATS server URL
            on_message: Callback for received messages
        """
        if not NATS_AVAILABLE:
            raise ImportError("nats-py not installed. Run: pip install nats-py")

        self.nats_url = nats_url
        self.on_message = on_message
        self.nc: Optional[NATSClient] = None
        self._subscriptions = []
        self._connected = False

    async def connect(self) -> None:
        """Connect to NATS server."""
        self.nc = await nats.connect(self.nats_url)
        self._connected = True

        # Subscribe to status updates from agents
        sub = await self.nc.subscribe(
            f"{self.STATUS_SUBJECT}.*",
            cb=self._handle_status,
        )
        self._subscriptions.append(sub)

    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        for sub in self._subscriptions:
            await sub.unsubscribe()
        self._subscriptions.clear()

        if self.nc:
            await self.nc.drain()
            self._connected = False

    async def _handle_status(self, msg) -> None:
        """Handle status messages from agents."""
        try:
            data = json.loads(msg.data.decode())
            agent_id = msg.subject.split(".")[-1]

            message = AgentMessage(
                agent_id=agent_id,
                message_type=data.get("type", "unknown"),
                content=data.get("content"),
                timestamp=data.get("timestamp", datetime.now().isoformat()),
            )

            if self.on_message:
                self.on_message(message)

        except Exception as e:
            print(f"Error handling status message: {e}")

    async def broadcast(self, command: AgentCommand) -> None:
        """
        Broadcast a command to all agents.

        Args:
            command: Command to broadcast
        """
        if not self._connected:
            raise RuntimeError("Not connected to NATS")

        subject = f"{self.BROADCAST_SUBJECT}.{command.command_type.value}"
        data = json.dumps({
            "type": command.command_type.value,
            "payload": command.payload,
            "timestamp": command.timestamp,
        }).encode()

        await self.nc.publish(subject, data)

    async def send_to_agent(
        self,
        agent_id: str,
        command: AgentCommand,
    ) -> None:
        """
        Send a command to a specific agent.

        Args:
            agent_id: Target agent ID
            command: Command to send
        """
        if not self._connected:
            raise RuntimeError("Not connected to NATS")

        subject = f"{self.AGENT_SUBJECT}.{agent_id}.{command.command_type.value}"
        data = json.dumps({
            "type": command.command_type.value,
            "payload": command.payload,
            "timestamp": command.timestamp,
        }).encode()

        await self.nc.publish(subject, data)

    async def stop_all_agents(self) -> None:
        """Broadcast stop command to all agents."""
        await self.broadcast(AgentCommand(command_type=CommandType.STOP))

    async def stop_agent(self, agent_id: str) -> None:
        """Send stop command to a specific agent."""
        await self.send_to_agent(
            agent_id,
            AgentCommand(command_type=CommandType.STOP),
        )

    async def pause_agent(self, agent_id: str) -> None:
        """Send pause command to a specific agent."""
        await self.send_to_agent(
            agent_id,
            AgentCommand(command_type=CommandType.PAUSE),
        )

    async def resume_agent(self, agent_id: str) -> None:
        """Send resume command to a specific agent."""
        await self.send_to_agent(
            agent_id,
            AgentCommand(command_type=CommandType.RESUME),
        )

    async def request_status(self, agent_id: Optional[str] = None) -> None:
        """Request status from agent(s)."""
        command = AgentCommand(command_type=CommandType.STATUS)
        if agent_id:
            await self.send_to_agent(agent_id, command)
        else:
            await self.broadcast(command)

    async def send_feedback(
        self,
        agent_id: str,
        feedback: str,
        action: Optional[str] = None,
    ) -> None:
        """
        Send feedback/correction to an agent.

        Args:
            agent_id: Target agent
            feedback: Feedback message
            action: Optional action to take (e.g., "retry", "abort", "continue")
        """
        await self.send_to_agent(
            agent_id,
            AgentCommand(
                command_type=CommandType.FEEDBACK,
                payload={
                    "feedback": feedback,
                    "action": action,
                },
            ),
        )

    async def redirect_agent(
        self,
        agent_id: str,
        new_work_stream: str,
        reason: str,
    ) -> None:
        """
        Redirect an agent to a different work stream.

        Args:
            agent_id: Target agent
            new_work_stream: New work stream ID
            reason: Reason for redirect
        """
        await self.send_to_agent(
            agent_id,
            AgentCommand(
                command_type=CommandType.REDIRECT,
                payload={
                    "new_work_stream": new_work_stream,
                    "reason": reason,
                },
            ),
        )


# Synchronous wrapper for non-async contexts
class SyncNATSCoordinator:
    """Synchronous wrapper for NATSCoordinator."""

    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.async_coordinator = NATSCoordinator(nats_url)
        self._loop = None

    def _get_loop(self):
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def connect(self) -> None:
        self._get_loop().run_until_complete(self.async_coordinator.connect())

    def disconnect(self) -> None:
        self._get_loop().run_until_complete(self.async_coordinator.disconnect())

    def stop_all_agents(self) -> None:
        self._get_loop().run_until_complete(self.async_coordinator.stop_all_agents())

    def stop_agent(self, agent_id: str) -> None:
        self._get_loop().run_until_complete(self.async_coordinator.stop_agent(agent_id))

    def send_feedback(self, agent_id: str, feedback: str, action: str = None) -> None:
        self._get_loop().run_until_complete(
            self.async_coordinator.send_feedback(agent_id, feedback, action)
        )
