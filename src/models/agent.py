"""Agent models for the orchestrator system."""

from dataclasses import dataclass, field
from typing import Any

from src.models.enums import AgentStatus


@dataclass
class AgentCapability:
    """
    Represents a specific capability or skill that an agent possesses.

    Capabilities define what an agent can do, including tools they can use
    and domains they have knowledge in.
    """

    name: str
    description: str
    tools: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    """
    Represents an individual agent within the orchestrator system.

    Agents are specialized workers with specific roles, capabilities, and
    responsibilities. They execute subtasks assigned to them.
    """

    id: str
    role: str
    capabilities: list[AgentCapability]
    status: AgentStatus = AgentStatus.IDLE
    current_task: str | None = None
    assigned_tasks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
