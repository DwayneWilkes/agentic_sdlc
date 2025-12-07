"""Priority and work queue task models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Priority(str, Enum):
    """
    Task priority levels.

    Priorities determine the order in which tasks are assigned and executed.
    CRITICAL tasks block other work and need immediate attention.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def priority_order(self) -> int:
        """
        Get numeric priority for sorting.

        Returns higher numbers for higher priorities to enable reverse sorting.
        CRITICAL = 4, HIGH = 3, MEDIUM = 2, LOW = 1
        """
        order_map = {
            Priority.CRITICAL: 4,
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1,
        }
        return order_map[self]


@dataclass
class TaskPriority:
    """
    Represents a task with priority and claim tracking.

    Used for managing task queue with priority ordering and claim/release mechanism.
    """

    task_id: str
    priority: Priority
    assigned_agent: str | None = None
    claimed_at: datetime | None = None

    def claim(self, agent_id: str) -> None:
        """
        Claim this task for an agent.

        Args:
            agent_id: ID of the agent claiming the task

        Raises:
            ValueError: If task is already claimed
        """
        if self.is_claimed():
            raise ValueError(
                f"Task {self.task_id} is already claimed by {self.assigned_agent}"
            )

        self.assigned_agent = agent_id
        self.claimed_at = datetime.now()

    def release(self) -> None:
        """Release this task (make it available for assignment again)."""
        self.assigned_agent = None
        self.claimed_at = None

    def is_claimed(self) -> bool:
        """
        Check if this task is currently claimed.

        Returns:
            True if task is claimed, False otherwise
        """
        return self.assigned_agent is not None


@dataclass
class WorkQueueTask:
    """
    Represents a task in the work queue with full metadata.

    Includes priority, assignment status, token estimates, and acceptance criteria.
    This is the complete task representation used by the task assignment system.
    """

    id: str
    priority: Priority
    title: str
    description: str = ""
    assigned_agent: str | None = None
    status: str = "pending"  # pending, claimed, completed, failed
    estimated_tokens: int | None = None
    acceptance_criteria: list[str] = field(default_factory=list)
    requirements: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def claim(self, agent_id: str) -> None:
        """
        Claim this task for an agent.

        Args:
            agent_id: ID of the agent claiming the task

        Raises:
            ValueError: If task is already claimed
        """
        if self.status == "claimed":
            raise ValueError(
                f"Task {self.id} is already claimed by {self.assigned_agent}"
            )

        self.assigned_agent = agent_id
        self.status = "claimed"

    def release(self) -> None:
        """Release this task (make it available for assignment again)."""
        self.assigned_agent = None
        self.status = "pending"

    def complete(self) -> None:
        """Mark this task as completed."""
        self.status = "completed"

    def fail(self, reason: str | None = None) -> None:
        """
        Mark this task as failed.

        Args:
            reason: Optional reason for failure
        """
        self.status = "failed"
        if reason:
            self.metadata["failure_reason"] = reason

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with camelCase keys matching JSON schema
        """
        return {
            "id": self.id,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "assignedAgent": self.assigned_agent,
            "status": self.status,
            "estimatedTokens": self.estimated_tokens,
            "acceptanceCriteria": self.acceptance_criteria,
        }

    @classmethod
    def from_subtask(cls, subtask: Any) -> "WorkQueueTask":
        """
        Create a WorkQueueTask from a Subtask.

        Args:
            subtask: Subtask instance to convert

        Returns:
            WorkQueueTask with data from subtask
        """
        # Get priority from metadata, default to MEDIUM
        priority_str = subtask.metadata.get("priority", "medium")
        try:
            priority = Priority(priority_str.lower())
        except ValueError:
            priority = Priority.MEDIUM

        # Get other metadata
        estimated_tokens = subtask.metadata.get("estimated_tokens")
        acceptance_criteria = subtask.metadata.get("acceptance_criteria", [])

        # Get requirements
        requirements = subtask.requirements or {}

        return cls(
            id=subtask.id,
            priority=priority,
            title=subtask.description,
            description=subtask.description,
            estimated_tokens=estimated_tokens,
            acceptance_criteria=acceptance_criteria,
            requirements=requirements,
            assigned_agent=subtask.assigned_agent,
        )
