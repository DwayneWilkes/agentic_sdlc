"""Approval gate for destructive operations.

This module provides a human-in-the-loop approval mechanism for
high-risk operations that require manual review before execution.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.security.access_control import Action


class ApprovalStatus(Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


class ApprovalTimeoutError(Exception):
    """Exception raised when approval request times out."""

    pass


@dataclass
class ApprovalRequest:
    """Request for approval of a destructive action."""

    request_id: str
    """Unique identifier for this request."""

    action: Action
    """Action requiring approval."""

    reason: str
    """Explanation for why this action is needed."""

    requested_by: str
    """Agent or user requesting the action."""

    requested_at: datetime = field(default_factory=datetime.now)
    """Timestamp when request was submitted."""

    status: ApprovalStatus = ApprovalStatus.PENDING
    """Current status of the request."""

    approved_by: str | None = None
    """Who approved/denied the request."""

    decision_reason: str | None = None
    """Explanation for the approval/denial."""

    decided_at: datetime | None = None
    """Timestamp when decision was made."""


@dataclass
class ApprovalDecision:
    """Decision on an approval request."""

    approved: bool
    """Whether the action was approved."""

    reason: str
    """Explanation for the decision."""

    approved_by: str
    """Who made the decision."""


class ApprovalGate:
    """Gate for approving destructive operations.

    The approval gate provides a mechanism for human review of
    high-risk actions before they are executed. Requests can be:
    - Approved (action proceeds)
    - Denied (action is blocked)
    - Timeout (no decision made in time, auto-deny)
    """

    def __init__(
        self,
        timeout_seconds: float = 300.0,
        auto_deny_on_timeout: bool = True,
    ) -> None:
        """Initialize approval gate.

        Args:
            timeout_seconds: How long to wait for approval before timeout
            auto_deny_on_timeout: Whether to auto-deny on timeout
        """
        self.timeout_seconds = timeout_seconds
        self.auto_deny_on_timeout = auto_deny_on_timeout
        self._pending_requests: dict[str, ApprovalRequest] = {}
        self._decision_events: dict[str, asyncio.Event] = {}
        self._request_history: list[ApprovalRequest] = []

    def submit_request(
        self,
        action: Action,
        requested_by: str,
        reason: str,
    ) -> str:
        """Submit a request for approval.

        Args:
            action: Action requiring approval
            requested_by: Agent or user requesting the action
            reason: Explanation for why this action is needed

        Returns:
            Request ID for tracking
        """
        request_id = str(uuid.uuid4())

        request = ApprovalRequest(
            request_id=request_id,
            action=action,
            reason=reason,
            requested_by=requested_by,
        )

        self._pending_requests[request_id] = request
        self._decision_events[request_id] = asyncio.Event()

        return request_id

    async def wait_for_approval(
        self,
        request_id: str,
        timeout_override: float | None = None,
    ) -> ApprovalDecision:
        """Wait for approval decision on a request.

        Args:
            request_id: Request to wait for
            timeout_override: Optional timeout override for this request

        Returns:
            ApprovalDecision with the result

        Raises:
            ApprovalTimeout: If no decision made within timeout
        """
        if request_id not in self._decision_events:
            raise ValueError(f"Unknown request ID: {request_id}")

        timeout = timeout_override if timeout_override is not None else self.timeout_seconds

        try:
            # Wait for decision event with timeout
            await asyncio.wait_for(
                self._decision_events[request_id].wait(),
                timeout=timeout,
            )
        except TimeoutError:
            # Handle timeout
            request = self._pending_requests.get(request_id)
            if request:
                request.status = ApprovalStatus.TIMEOUT
                request.decided_at = datetime.now()
                request.decision_reason = "Request timed out waiting for approval"
                self._move_to_history(request_id)

            raise ApprovalTimeoutError(
                f"Approval request {request_id} timed out after {timeout} seconds"
            )

        # Get the decision
        request = self._request_history[-1] if self._request_history else None
        if not request or request.request_id != request_id:
            # Find in history
            request = next(
                (r for r in self._request_history if r.request_id == request_id),
                None,
            )

        if not request:
            raise ValueError(f"Request {request_id} not found")

        return ApprovalDecision(
            approved=(request.status == ApprovalStatus.APPROVED),
            reason=request.decision_reason or "No reason provided",
            approved_by=request.approved_by or "unknown",
        )

    def approve_request(
        self,
        request_id: str,
        approved_by: str,
        reason: str,
    ) -> None:
        """Approve a pending request.

        Args:
            request_id: Request to approve
            approved_by: Who is approving
            reason: Explanation for approval
        """
        if request_id not in self._pending_requests:
            return

        request = self._pending_requests[request_id]
        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.decision_reason = reason
        request.decided_at = datetime.now()

        # Move to history and signal decision
        self._move_to_history(request_id)
        self._decision_events[request_id].set()

    def deny_request(
        self,
        request_id: str,
        denied_by: str,
        reason: str,
    ) -> None:
        """Deny a pending request.

        Args:
            request_id: Request to deny
            denied_by: Who is denying
            reason: Explanation for denial
        """
        if request_id not in self._pending_requests:
            return

        request = self._pending_requests[request_id]
        request.status = ApprovalStatus.DENIED
        request.approved_by = denied_by
        request.decision_reason = reason
        request.decided_at = datetime.now()

        # Move to history and signal decision
        self._move_to_history(request_id)
        self._decision_events[request_id].set()

    def cancel_request(self, request_id: str) -> None:
        """Cancel a pending request.

        Args:
            request_id: Request to cancel
        """
        if request_id not in self._pending_requests:
            return

        request = self._pending_requests[request_id]
        request.status = ApprovalStatus.DENIED
        request.approved_by = "system"
        request.decision_reason = "Request cancelled"
        request.decided_at = datetime.now()

        # Move to history
        self._move_to_history(request_id)

    def get_pending_requests(self) -> list[str]:
        """Get all pending request IDs.

        Returns:
            List of pending request IDs
        """
        return list(self._pending_requests.keys())

    def get_request_status(self, request_id: str) -> ApprovalRequest | None:
        """Get the status of a request.

        Args:
            request_id: Request to check

        Returns:
            ApprovalRequest if found, None otherwise
        """
        # Check pending first
        if request_id in self._pending_requests:
            return self._pending_requests[request_id]

        # Check history
        return next(
            (r for r in self._request_history if r.request_id == request_id),
            None,
        )

    def get_request_history(self) -> list[ApprovalRequest]:
        """Get history of all requests.

        Returns:
            List of all requests (completed and pending)
        """
        return self._request_history.copy()

    def _move_to_history(self, request_id: str) -> None:
        """Move a request from pending to history.

        Args:
            request_id: Request to move
        """
        if request_id in self._pending_requests:
            request = self._pending_requests.pop(request_id)
            self._request_history.append(request)
