"""Emergency stop mechanism for agent control.

This module provides emergency stop capabilities that allow:
- Graceful shutdown (save state, complete current operation)
- Immediate stop (cancel current operation)
- Emergency kill-all (stop everything immediately)
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.coordination.nats_bus import MessageType, NATSMessageBus


class StopMode(Enum):
    """Mode for stopping agents."""

    GRACEFUL = "graceful"  # Save state, complete current operation
    IMMEDIATE = "immediate"  # Cancel current operation
    EMERGENCY = "emergency"  # Kill everything immediately


class StopReason(Enum):
    """Reason for stopping agents."""

    USER_REQUESTED = "user_requested"
    SAFETY_VIOLATION = "safety_violation"
    SYSTEM_ERROR = "system_error"
    KILL_SWITCH = "kill_switch"


@dataclass
class StopResult:
    """Result of emergency stop operation."""

    success: bool
    """Whether the stop was successful."""

    agents_stopped: list[str] = field(default_factory=list)
    """List of agents that were stopped."""

    failed_agents: list[str] = field(default_factory=list)
    """List of agents that failed to stop."""

    reason: str = ""
    """Explanation for the stop."""


class EmergencyStop:
    """Emergency stop mechanism for agent control.

    Provides three modes of stopping:
    1. GRACEFUL - Agents save state and complete current operation
    2. IMMEDIATE - Agents cancel current operation but save state
    3. EMERGENCY - Everything stops immediately (kill switch)
    """

    def __init__(self, nats_url: str = "nats://localhost:4222") -> None:
        """Initialize emergency stop mechanism.

        Args:
            nats_url: URL for NATS server
        """
        self.nats_url = nats_url
        self._stopped = False
        self._stop_count = 0
        self._stop_history: list[dict] = []
        self._last_stop_info: dict | None = None
        self._stop_handlers: list[Callable] = []
        self._nats_bus: NATSMessageBus | None = None

    def is_stopped(self) -> bool:
        """Check if emergency stop is active.

        Returns:
            True if stopped, False otherwise
        """
        return self._stopped

    def get_stop_count(self) -> int:
        """Get the total number of stops triggered.

        Returns:
            Number of times stop has been triggered
        """
        return self._stop_count

    def trigger_stop(
        self,
        mode: StopMode,
        reason: StopReason,
        message: str,
        target_agents: list[str] | None = None,
    ) -> StopResult:
        """Trigger emergency stop.

        Args:
            mode: Mode of stopping (graceful, immediate, emergency)
            reason: Reason for the stop
            message: Human-readable explanation
            target_agents: Optional list of specific agents to stop

        Returns:
            StopResult with outcome
        """
        self._stopped = True
        self._stop_count += 1

        # Record stop info
        stop_info = {
            "mode": mode,
            "reason": reason,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "target_agents": target_agents or [],
        }
        self._last_stop_info = stop_info
        self._stop_history.append(stop_info)

        # Call registered handlers asynchronously
        if self._stop_handlers:
            asyncio.create_task(self._call_handlers(mode, reason, message))

        # If we have NATS connection, broadcast stop
        if self._nats_bus:
            asyncio.create_task(
                self._broadcast_stop(mode, reason, message, target_agents)
            )

        # For now, consider it successful
        # In a real implementation, this would track which agents actually stopped
        result = StopResult(
            success=True,
            agents_stopped=target_agents or [],
            reason=message,
        )

        return result

    def reset(self) -> None:
        """Reset the emergency stop state.

        This allows the system to resume operation after a stop.
        """
        self._stopped = False

    def get_last_stop_info(self) -> dict | None:
        """Get information about the last stop.

        Returns:
            Dictionary with stop information, or None if no stops
        """
        return self._last_stop_info.copy() if self._last_stop_info else None

    def get_stop_history(self) -> list[dict]:
        """Get complete history of all stops.

        Returns:
            List of stop information dictionaries
        """
        return self._stop_history.copy()

    def register_stop_handler(
        self,
        handler: Callable[[StopMode, StopReason, str], None],
    ) -> None:
        """Register a handler to be called when stop is triggered.

        Args:
            handler: Async callable that takes (mode, reason, message)
        """
        self._stop_handlers.append(handler)

    async def connect_nats(self) -> None:
        """Connect to NATS for broadcasting stop messages."""
        self._nats_bus = NATSMessageBus(self.nats_url)
        await self._nats_bus.connect()

    async def disconnect_nats(self) -> None:
        """Disconnect from NATS."""
        if self._nats_bus:
            await self._nats_bus.disconnect()
            self._nats_bus = None

    async def _call_handlers(
        self,
        mode: StopMode,
        reason: StopReason,
        message: str,
    ) -> None:
        """Call all registered stop handlers.

        Args:
            mode: Stop mode
            reason: Stop reason
            message: Stop message
        """
        for handler in self._stop_handlers:
            try:
                await handler(mode, reason, message)
            except Exception:
                # Don't let handler failures prevent stop
                pass

    async def _broadcast_stop(
        self,
        mode: StopMode,
        reason: StopReason,
        message: str,
        target_agents: list[str] | None,
    ) -> None:
        """Broadcast stop message via NATS.

        Args:
            mode: Stop mode
            reason: Stop reason
            message: Stop message
            target_agents: Optional list of specific agents to stop
        """
        if not self._nats_bus:
            return

        try:
            # Broadcast to all agents or specific targets
            content = {
                "mode": mode.value,
                "reason": reason.value,
                "message": message,
            }

            if target_agents:
                # Send to specific agents
                for agent_id in target_agents:
                    await self._nats_bus.send_to_agent(
                        from_agent="emergency_stop",
                        to_agent=agent_id,
                        message_type=MessageType.STOP_TASK,
                        content=content,
                    )
            else:
                # Broadcast to all
                await self._nats_bus.broadcast(
                    message_type=MessageType.STOP_TASK,
                    content=content,
                    from_agent="emergency_stop",
                )
        except Exception:
            # Don't let NATS failures prevent stop
            pass
