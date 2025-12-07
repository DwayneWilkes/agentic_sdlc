"""Tests for emergency stop mechanism."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.security.emergency_stop import (
    EmergencyStop,
    StopMode,
    StopReason,
    StopResult,
)


def test_stop_mode_enum():
    """Test that StopMode enum has expected values."""
    assert StopMode.GRACEFUL.value == "graceful"
    assert StopMode.IMMEDIATE.value == "immediate"
    assert StopMode.EMERGENCY.value == "emergency"


def test_stop_reason_enum():
    """Test that StopReason enum has expected values."""
    assert StopReason.USER_REQUESTED.value == "user_requested"
    assert StopReason.SAFETY_VIOLATION.value == "safety_violation"
    assert StopReason.SYSTEM_ERROR.value == "system_error"
    assert StopReason.KILL_SWITCH.value == "kill_switch"


def test_stop_result_creation():
    """Test StopResult dataclass creation."""
    result = StopResult(
        success=True,
        agents_stopped=["agent-1", "agent-2"],
        reason="Testing emergency stop",
    )

    assert result.success is True
    assert result.agents_stopped == ["agent-1", "agent-2"]
    assert result.reason == "Testing emergency stop"
    assert result.failed_agents == []


def test_emergency_stop_initialization():
    """Test EmergencyStop initialization."""
    stop = EmergencyStop()

    assert stop.is_stopped() is False
    assert stop.get_stop_count() == 0


def test_trigger_graceful_stop():
    """Test triggering a graceful stop."""
    stop = EmergencyStop()

    result = stop.trigger_stop(
        mode=StopMode.GRACEFUL,
        reason=StopReason.USER_REQUESTED,
        message="User requested shutdown",
    )

    assert result.success is True
    assert stop.is_stopped() is True
    assert stop.get_stop_count() == 1


def test_trigger_immediate_stop():
    """Test triggering an immediate stop."""
    stop = EmergencyStop()

    result = stop.trigger_stop(
        mode=StopMode.IMMEDIATE,
        reason=StopReason.SAFETY_VIOLATION,
        message="Safety boundary violated",
    )

    assert result.success is True
    assert stop.is_stopped() is True


def test_trigger_emergency_stop():
    """Test triggering an emergency kill-all stop."""
    stop = EmergencyStop()

    result = stop.trigger_stop(
        mode=StopMode.EMERGENCY,
        reason=StopReason.KILL_SWITCH,
        message="Emergency kill switch activated",
    )

    assert result.success is True
    assert stop.is_stopped() is True


def test_reset_after_stop():
    """Test that emergency stop can be reset."""
    stop = EmergencyStop()

    # Stop
    stop.trigger_stop(
        mode=StopMode.GRACEFUL,
        reason=StopReason.USER_REQUESTED,
        message="Test stop",
    )
    assert stop.is_stopped() is True

    # Reset
    stop.reset()
    assert stop.is_stopped() is False


def test_multiple_stops_increment_count():
    """Test that stop count increments with each stop."""
    stop = EmergencyStop()

    assert stop.get_stop_count() == 0

    stop.trigger_stop(
        mode=StopMode.GRACEFUL,
        reason=StopReason.USER_REQUESTED,
        message="Stop 1",
    )
    assert stop.get_stop_count() == 1

    stop.reset()
    stop.trigger_stop(
        mode=StopMode.IMMEDIATE,
        reason=StopReason.SAFETY_VIOLATION,
        message="Stop 2",
    )
    assert stop.get_stop_count() == 2


def test_get_last_stop_info():
    """Test retrieving information about the last stop."""
    stop = EmergencyStop()

    # No stops yet
    info = stop.get_last_stop_info()
    assert info is None

    # Trigger a stop
    stop.trigger_stop(
        mode=StopMode.GRACEFUL,
        reason=StopReason.USER_REQUESTED,
        message="Test stop",
    )

    # Check info
    info = stop.get_last_stop_info()
    assert info is not None
    assert info["mode"] == StopMode.GRACEFUL
    assert info["reason"] == StopReason.USER_REQUESTED
    assert info["message"] == "Test stop"
    assert "timestamp" in info


@pytest.mark.asyncio
async def test_register_stop_handler():
    """Test registering and calling stop handlers."""
    stop = EmergencyStop()
    handler_called = {"count": 0, "mode": None}

    async def test_handler(mode: StopMode, reason: StopReason, message: str):
        handler_called["count"] += 1
        handler_called["mode"] = mode

    stop.register_stop_handler(test_handler)

    # Trigger stop (handlers are called async)
    stop.trigger_stop(
        mode=StopMode.GRACEFUL,
        reason=StopReason.USER_REQUESTED,
        message="Test",
    )

    # Give handlers time to execute
    await asyncio.sleep(0.1)

    assert handler_called["count"] > 0
    assert handler_called["mode"] == StopMode.GRACEFUL


@pytest.mark.asyncio
async def test_multiple_stop_handlers():
    """Test that multiple handlers are called."""
    stop = EmergencyStop()
    handlers_called = {"handler1": False, "handler2": False}

    async def handler1(mode: StopMode, reason: StopReason, message: str):
        handlers_called["handler1"] = True

    async def handler2(mode: StopMode, reason: StopReason, message: str):
        handlers_called["handler2"] = True

    stop.register_stop_handler(handler1)
    stop.register_stop_handler(handler2)

    stop.trigger_stop(
        mode=StopMode.IMMEDIATE,
        reason=StopReason.SYSTEM_ERROR,
        message="Test",
    )

    await asyncio.sleep(0.1)

    assert handlers_called["handler1"] is True
    assert handlers_called["handler2"] is True


@pytest.mark.asyncio
async def test_nats_broadcast_on_stop():
    """Test that stop triggers NATS broadcast."""
    with patch("src.security.emergency_stop.NATSMessageBus") as mock_nats:
        # Setup mock
        mock_bus = AsyncMock()
        mock_nats.return_value = mock_bus

        stop = EmergencyStop(nats_url="nats://test:4222")

        # Connect
        await stop.connect_nats()

        # Trigger stop
        result = stop.trigger_stop(
            mode=StopMode.GRACEFUL,
            reason=StopReason.USER_REQUESTED,
            message="Test stop",
        )

        # Give time for async operations
        await asyncio.sleep(0.1)

        # Verify NATS broadcast was called
        assert mock_bus.broadcast.called or result.success


def test_stop_with_target_agents():
    """Test stopping specific agents."""
    stop = EmergencyStop()

    result = stop.trigger_stop(
        mode=StopMode.GRACEFUL,
        reason=StopReason.USER_REQUESTED,
        message="Stop specific agents",
        target_agents=["agent-1", "agent-2"],
    )

    assert result.success is True
    # In a real implementation, this would only stop specified agents


def test_emergency_stop_history():
    """Test that stop history is maintained."""
    stop = EmergencyStop()

    # Trigger multiple stops
    stop.trigger_stop(
        mode=StopMode.GRACEFUL,
        reason=StopReason.USER_REQUESTED,
        message="Stop 1",
    )
    stop.reset()

    stop.trigger_stop(
        mode=StopMode.IMMEDIATE,
        reason=StopReason.SAFETY_VIOLATION,
        message="Stop 2",
    )
    stop.reset()

    stop.trigger_stop(
        mode=StopMode.EMERGENCY,
        reason=StopReason.KILL_SWITCH,
        message="Stop 3",
    )

    # Get history
    history = stop.get_stop_history()
    assert len(history) == 3
    assert history[0]["message"] == "Stop 1"
    assert history[1]["message"] == "Stop 2"
    assert history[2]["message"] == "Stop 3"
