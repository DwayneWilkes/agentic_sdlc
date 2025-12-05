"""Team model for the orchestrator system."""

from dataclasses import dataclass, field
from typing import Any

from src.models.agent import Agent


@dataclass
class Team:
    """
    Represents a team of agents working together on a task.

    Teams are composed to have complementary skills and balanced workload
    distribution for optimal task execution.
    """

    id: str
    name: str
    agents: list[Agent]
    metadata: dict[str, Any] = field(default_factory=dict)
