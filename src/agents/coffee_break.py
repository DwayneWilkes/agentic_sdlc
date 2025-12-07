"""
Coffee Break System - Agent peer learning dialogue.

Implements scheduled and on-demand coffee breaks where agents:
- Share knowledge through teaching sessions
- Tell "war stories" about interesting/difficult cases
- Pair debug problems together
- Conduct post-task retrospectives

Supports learning validation to measure knowledge transfer effectiveness.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class SessionType(str, Enum):
    """Types of coffee break sessions."""

    SCHEDULED = "scheduled"  # Regular scheduled knowledge share
    TEACHING = "teaching"  # Peer teaching (expert explains to learner)
    WAR_STORY = "war_story"  # Narrative-based learning from experience
    PAIR_DEBUG = "pair_debug"  # Two agents debug together
    RETROSPECTIVE = "retrospective"  # Post-task reflection
    NEED_BASED = "need_based"  # Triggered by agent needing help


class SessionTrigger(str, Enum):
    """What triggered the coffee break."""

    SCHEDULED = "scheduled"  # Time or task count based
    MANUAL = "manual"  # Explicitly requested
    POST_TASK = "post_task"  # After completing a task
    NEED_BASED = "need_based"  # Agent needs help/knowledge


@dataclass
class CoffeeBreakSession:
    """
    A single coffee break session between agents.

    Attributes:
        session_id: Unique session identifier
        initiator: Agent who initiated the session
        participants: List of participating agent IDs
        session_type: Type of session (teaching, war story, etc.)
        topic: Main topic of discussion
        trigger: What triggered this session
        context: Additional context specific to session type
        created_at: When session was created
        completed_at: When session completed (None if ongoing)
        outcome: Results of the session (knowledge transferred, etc.)
    """

    session_id: str
    initiator: str
    participants: list[str]
    session_type: SessionType
    topic: str
    trigger: SessionTrigger
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    outcome: dict[str, Any] | None = None

    def complete(self, outcome: dict[str, Any]) -> None:
        """
        Mark session as complete with outcome.

        Args:
            outcome: Dictionary containing session results
                - knowledge_transferred: bool
                - receiving_agent: str (if applicable)
                - confidence_before: float (0-1)
                - confidence_after: float (0-1)
                - summary: str
        """
        self.outcome = outcome
        self.completed_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "initiator": self.initiator,
            "participants": self.participants,
            "session_type": self.session_type.value,
            "topic": self.topic,
            "trigger": self.trigger.value,
            "context": self.context,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoffeeBreakSession":
        """Reconstruct session from dictionary."""
        return cls(
            session_id=data["session_id"],
            initiator=data["initiator"],
            participants=data["participants"],
            session_type=SessionType(data["session_type"]),
            topic=data["topic"],
            trigger=SessionTrigger(data["trigger"]),
            context=data.get("context", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
            outcome=data.get("outcome"),
        )


class CoffeeBreakScheduler:
    """
    Schedules coffee breaks for an agent.

    Supports multiple trigger mechanisms:
    - Task count based (every N tasks)
    - Time based (every N minutes)
    - Manual triggers (explicit requests)
    - Post-task triggers (after completing tasks)
    """

    def __init__(
        self,
        agent_id: str,
        task_interval: int | None = None,
        time_interval_minutes: int | None = None,
    ):
        """
        Initialize coffee break scheduler.

        Args:
            agent_id: ID of the agent this scheduler belongs to
            task_interval: Trigger coffee break every N tasks (None to disable)
            time_interval_minutes: Trigger every N minutes (None to disable)
        """
        self.agent_id = agent_id
        self.task_interval = task_interval
        self.time_interval_minutes = time_interval_minutes
        self.task_count = 0
        self.last_break_time: datetime | None = None

    def increment_task_count(self) -> None:
        """Increment the task counter."""
        self.task_count += 1

    def should_trigger(self) -> bool:
        """
        Check if a coffee break should be triggered.

        Returns:
            True if break should trigger, False otherwise
        """
        # Check task interval
        if self.task_interval is not None:
            if self.task_count >= self.task_interval:
                return True

        # Check time interval
        if self.time_interval_minutes is not None and self.last_break_time is not None:
            elapsed = datetime.now() - self.last_break_time
            if elapsed >= timedelta(minutes=self.time_interval_minutes):
                return True

        return False

    def reset(self) -> None:
        """Reset counters after a coffee break."""
        self.task_count = 0
        self.last_break_time = datetime.now()

    def create_scheduled_break(
        self,
        topic: str | None = None,
        participants: list[str] | None = None,
    ) -> CoffeeBreakSession:
        """
        Create a scheduled coffee break session.

        Args:
            topic: Optional topic for the break
            participants: Optional list of participants

        Returns:
            CoffeeBreakSession instance
        """
        session_id = f"coffee-{uuid.uuid4().hex[:8]}"
        topic = topic or "General knowledge sharing"
        participants = participants or [self.agent_id]

        session = CoffeeBreakSession(
            session_id=session_id,
            initiator=self.agent_id,
            participants=participants,
            session_type=SessionType.SCHEDULED,
            topic=topic,
            trigger=SessionTrigger.SCHEDULED,
        )

        self.reset()
        return session

    def trigger_manual(
        self,
        topic: str,
        reason: str,
        participants: list[str] | None = None,
    ) -> CoffeeBreakSession:
        """
        Manually trigger a coffee break.

        Args:
            topic: Topic for discussion
            reason: Reason for the manual trigger
            participants: Optional list of participants

        Returns:
            CoffeeBreakSession instance
        """
        session_id = f"coffee-{uuid.uuid4().hex[:8]}"
        participants = participants or [self.agent_id]

        session = CoffeeBreakSession(
            session_id=session_id,
            initiator=self.agent_id,
            participants=participants,
            session_type=SessionType.NEED_BASED,
            topic=topic,
            trigger=SessionTrigger.MANUAL,
            context={"reason": reason},
        )

        return session

    def create_retrospective(
        self,
        task_id: str,
        participants: list[str],
        challenges: list[str] | None = None,
        duration_hours: float | None = None,
    ) -> CoffeeBreakSession:
        """
        Create a post-task retrospective session.

        Args:
            task_id: ID of the completed task
            participants: Agents who worked on the task
            challenges: List of challenges encountered
            duration_hours: How long the task took

        Returns:
            CoffeeBreakSession instance
        """
        session_id = f"retro-{uuid.uuid4().hex[:8]}"

        context: dict[str, Any] = {
            "task_id": task_id,
        }
        if challenges:
            context["challenges"] = challenges
        if duration_hours is not None:
            context["duration_hours"] = duration_hours

        session = CoffeeBreakSession(
            session_id=session_id,
            initiator=self.agent_id,
            participants=participants,
            session_type=SessionType.RETROSPECTIVE,
            topic=f"Retrospective: {task_id}",
            trigger=SessionTrigger.POST_TASK,
            context=context,
        )

        return session
