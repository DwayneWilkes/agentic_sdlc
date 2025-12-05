"""Core enumerations for the orchestrator system."""

from enum import Enum


class TaskStatus(str, Enum):
    """Status of a task or subtask."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Status of an agent."""

    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    """Type/category of a task."""

    SOFTWARE = "software"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    HYBRID = "hybrid"
