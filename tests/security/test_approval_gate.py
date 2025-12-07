"""Tests for destructive operation approval gates."""

import asyncio

import pytest

from src.security.access_control import Action, ActionType, Resource, ResourceType
from src.security.approval_gate import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalTimeoutError,
)


def test_approval_status_enum():
    """Test that ApprovalStatus enum has expected values."""
    assert ApprovalStatus.PENDING.value == "pending"
    assert ApprovalStatus.APPROVED.value == "approved"
    assert ApprovalStatus.DENIED.value == "denied"
    assert ApprovalStatus.TIMEOUT.value == "timeout"


def test_approval_request_creation():
    """Test ApprovalRequest dataclass creation."""
    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    request = ApprovalRequest(
        request_id="test-request-id",
        action=action,
        reason="Testing deletion",
        requested_by="test-agent",
    )

    assert request.request_id == "test-request-id"
    assert request.action == action
    assert request.reason == "Testing deletion"
    assert request.requested_by == "test-agent"
    assert request.status == ApprovalStatus.PENDING
    assert request.approved_by is None
    assert request.decision_reason is None


def test_approval_decision_creation():
    """Test ApprovalDecision dataclass creation."""
    decision = ApprovalDecision(
        approved=True,
        reason="Action is safe to proceed",
        approved_by="human-reviewer",
    )

    assert decision.approved is True
    assert decision.reason == "Action is safe to proceed"
    assert decision.approved_by == "human-reviewer"


@pytest.mark.asyncio
async def test_approval_gate_approve():
    """Test approving a destructive action."""
    gate = ApprovalGate(timeout_seconds=5)

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    # Start request in background
    async def approve_after_delay():
        await asyncio.sleep(0.1)
        gate.approve_request(request_id, "human", "Looks safe")

    request_id = gate.submit_request(action, "test-agent", "Need to delete temp file")
    task = asyncio.create_task(approve_after_delay())

    # Wait for approval
    decision = await gate.wait_for_approval(request_id)

    await task

    assert decision.approved is True
    assert decision.approved_by == "human"
    assert decision.reason == "Looks safe"


@pytest.mark.asyncio
async def test_approval_gate_deny():
    """Test denying a destructive action."""
    gate = ApprovalGate(timeout_seconds=5)

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/etc/important.txt"),
        agent_id="test-agent",
    )

    # Start request in background
    async def deny_after_delay():
        await asyncio.sleep(0.1)
        gate.deny_request(request_id, "human", "Too risky")

    request_id = gate.submit_request(action, "test-agent", "Need to delete system file")
    task = asyncio.create_task(deny_after_delay())

    # Wait for decision
    decision = await gate.wait_for_approval(request_id)

    await task

    assert decision.approved is False
    assert decision.approved_by == "human"
    assert decision.reason == "Too risky"


@pytest.mark.asyncio
async def test_approval_gate_timeout():
    """Test that approval requests timeout after configured duration."""
    gate = ApprovalGate(timeout_seconds=0.2)

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    request_id = gate.submit_request(action, "test-agent", "Need approval")

    # Wait for timeout
    with pytest.raises(ApprovalTimeoutError) as exc_info:
        await gate.wait_for_approval(request_id)

    assert "timed out" in str(exc_info.value).lower()
    assert request_id in str(exc_info.value)


def test_get_pending_requests():
    """Test retrieving all pending approval requests."""
    gate = ApprovalGate()

    action1 = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/file1.txt"),
        agent_id="agent-1",
    )
    action2 = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/file2.txt"),
        agent_id="agent-2",
    )

    req1 = gate.submit_request(action1, "agent-1", "Delete file 1")
    req2 = gate.submit_request(action2, "agent-2", "Delete file 2")

    pending = gate.get_pending_requests()
    assert len(pending) == 2
    assert req1 in pending
    assert req2 in pending


@pytest.mark.asyncio
async def test_get_pending_requests_after_approval():
    """Test that approved requests are no longer pending."""
    gate = ApprovalGate()

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    request_id = gate.submit_request(action, "test-agent", "Need approval")

    # Before approval
    pending = gate.get_pending_requests()
    assert len(pending) == 1

    # Approve
    gate.approve_request(request_id, "human", "OK")

    # After approval - should no longer be pending
    pending = gate.get_pending_requests()
    assert len(pending) == 0


def test_get_request_status():
    """Test retrieving the status of a request."""
    gate = ApprovalGate()

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    request_id = gate.submit_request(action, "test-agent", "Need approval")

    # Should be pending
    request = gate.get_request_status(request_id)
    assert request is not None
    assert request.status == ApprovalStatus.PENDING

    # Approve it
    gate.approve_request(request_id, "human", "OK")

    # Should be approved
    request = gate.get_request_status(request_id)
    assert request is not None
    assert request.status == ApprovalStatus.APPROVED
    assert request.approved_by == "human"


def test_get_request_status_unknown():
    """Test retrieving status of unknown request returns None."""
    gate = ApprovalGate()

    request = gate.get_request_status("unknown-id")
    assert request is None


def test_cancel_request():
    """Test canceling a pending request."""
    gate = ApprovalGate()

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    request_id = gate.submit_request(action, "test-agent", "Need approval")

    # Should be pending
    assert len(gate.get_pending_requests()) == 1

    # Cancel it
    gate.cancel_request(request_id)

    # Should no longer be pending
    assert len(gate.get_pending_requests()) == 0

    # Should be marked as denied
    request = gate.get_request_status(request_id)
    assert request is not None
    assert request.status == ApprovalStatus.DENIED
    assert "cancelled" in request.decision_reason.lower()


@pytest.mark.asyncio
async def test_auto_deny_on_timeout():
    """Test that requests are auto-denied when timeout expires."""
    gate = ApprovalGate(timeout_seconds=0.2, auto_deny_on_timeout=True)

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    request_id = gate.submit_request(action, "test-agent", "Need approval")

    # Wait for timeout
    with pytest.raises(ApprovalTimeoutError):
        await gate.wait_for_approval(request_id)

    # Should be marked as timeout
    request = gate.get_request_status(request_id)
    assert request is not None
    assert request.status == ApprovalStatus.TIMEOUT


def test_request_history():
    """Test that completed requests are tracked in history."""
    gate = ApprovalGate()

    action1 = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/file1.txt"),
        agent_id="agent-1",
    )
    action2 = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/file2.txt"),
        agent_id="agent-2",
    )

    req1 = gate.submit_request(action1, "agent-1", "Delete file 1")
    req2 = gate.submit_request(action2, "agent-2", "Delete file 2")

    gate.approve_request(req1, "human", "OK")
    gate.deny_request(req2, "human", "Not OK")

    history = gate.get_request_history()
    assert len(history) >= 2  # May include other requests if not isolated

    # Find our requests in history
    req1_history = next((r for r in history if r.request_id == req1), None)
    req2_history = next((r for r in history if r.request_id == req2), None)

    assert req1_history is not None
    assert req1_history.status == ApprovalStatus.APPROVED

    assert req2_history is not None
    assert req2_history.status == ApprovalStatus.DENIED
