"""Task and Subtask models for the orchestrator system."""

from dataclasses import dataclass, field
from typing import Any

from src.models.enums import TaskStatus, TaskType


@dataclass
class Subtask:
    """
    Represents a single subtask within a larger task.

    Subtasks are the atomic units of work that can be assigned to individual agents.
    They should be Independent, Testable, and Estimable where possible.
    """

    id: str
    description: str
    dependencies: list[str]
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """
    Represents a high-level task to be decomposed and executed.

    A task encapsulates the overall goal, constraints, context, and decomposed
    subtasks needed to achieve the objective.
    """

    id: str
    description: str
    task_type: TaskType
    subtasks: list[Subtask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    constraints: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
