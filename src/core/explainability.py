"""
Transparency and Explainability Framework.

Provides comprehensive tracking and explanation of orchestrator decisions:
- Task decomposition rationale
- Team design and composition explanations
- Agent selection reasoning
- Agent interaction logging
- Failure diagnostics and debugging information

Phase 7.3 Requirements:
1. Add decomposition rationale explanations ✓
2. Explain team design and agent selection decisions ✓
3. Log all agent interactions (accessible) ✓
4. Implement debugging/diagnostic information on failure ✓
"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ExplanationEntry:
    """Base class for all explanation entries."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class DecompositionExplanation(ExplanationEntry):
    """Explains why and how a task was decomposed."""

    task_id: str = ""
    original_task: str = ""
    num_subtasks: int = 0
    strategy: str = ""
    reasons: list[str] = field(default_factory=list)
    complexity_factors: dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamDesignExplanation(ExplanationEntry):
    """Explains team composition and role assignments."""

    team_id: str = ""
    team_size: int = 0
    roles: list[str] = field(default_factory=list)
    role_justifications: dict[str, str] = field(default_factory=dict)
    composition_strategy: str = "balanced"


@dataclass
class AgentSelectionExplanation(ExplanationEntry):
    """Explains why a specific agent was selected for a task."""

    agent_name: str = ""
    task_id: str = ""
    selection_reasons: list[str] = field(default_factory=list)
    affinity_score: float = 0.0
    alternatives: list[str] = field(default_factory=list)


@dataclass
class InteractionLog(ExplanationEntry):
    """Records an interaction between agents."""

    from_agent: str = ""
    to_agent: str = ""
    interaction_type: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureDiagnostics(ExplanationEntry):
    """Provides debugging information for task failures."""

    task_id: str = ""
    failure_type: str = ""
    error_message: str = ""
    agent_name: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    stack_trace: str | None = None
    recovery_suggestions: list[str] = field(default_factory=list)


class ExplainabilityTracker:
    """
    Central tracker for all explainability and transparency data.

    This class fulfills Phase 7.3 requirements:
    - Tracks decomposition rationale
    - Tracks team design decisions
    - Tracks agent selection reasoning
    - Logs all agent interactions
    - Captures failure diagnostics for debugging

    Usage:
        tracker = ExplainabilityTracker()
        tracker.record_decomposition("task-1", "Build API", 3, ["Complex task"])
        tracker.record_interaction("Alice", "Bob", "handoff", "Task complete")
        report = tracker.generate_report()
    """

    def __init__(self) -> None:
        """Initialize the explainability tracker."""
        self._decompositions: list[DecompositionExplanation] = []
        self._team_designs: list[TeamDesignExplanation] = []
        self._agent_selections: list[AgentSelectionExplanation] = []
        self._interactions: list[InteractionLog] = []
        self._failures: list[FailureDiagnostics] = []

    def record_decomposition(
        self,
        task_id: str,
        original_task: str,
        num_subtasks: int,
        reasons: list[str],
        strategy: str = "default",
        complexity_factors: dict[str, Any] | None = None,
    ) -> None:
        """Record task decomposition rationale."""
        self._decompositions.append(
            DecompositionExplanation(
                task_id=task_id,
                original_task=original_task,
                num_subtasks=num_subtasks,
                strategy=strategy,
                reasons=reasons,
                complexity_factors=complexity_factors or {},
            )
        )

    def record_team_design(
        self,
        team_id: str,
        team_size: int,
        roles: list[str],
        role_justifications: dict[str, str] | None = None,
        strategy: str = "balanced",
    ) -> None:
        """Record team design decisions."""
        self._team_designs.append(
            TeamDesignExplanation(
                team_id=team_id,
                team_size=team_size,
                roles=roles,
                role_justifications=role_justifications or {},
                composition_strategy=strategy,
            )
        )

    def record_agent_selection(
        self,
        agent_name: str,
        task_id: str,
        selection_reasons: list[str],
        affinity_score: float = 0.0,
        alternatives: list[str] | None = None,
    ) -> None:
        """Record agent selection reasoning."""
        self._agent_selections.append(
            AgentSelectionExplanation(
                agent_name=agent_name,
                task_id=task_id,
                selection_reasons=selection_reasons,
                affinity_score=affinity_score,
                alternatives=alternatives or [],
            )
        )

    def record_interaction(
        self,
        from_agent: str,
        to_agent: str,
        interaction_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log agent interaction."""
        self._interactions.append(
            InteractionLog(
                from_agent=from_agent,
                to_agent=to_agent,
                interaction_type=interaction_type,
                message=message,
                metadata=metadata or {},
            )
        )

    def record_failure(
        self,
        task_id: str,
        failure_type: str,
        error_message: str,
        agent_name: str,
        context: dict[str, Any] | None = None,
        stack_trace: str | None = None,
        recovery_suggestions: list[str] | None = None,
    ) -> None:
        """Record failure diagnostics."""
        self._failures.append(
            FailureDiagnostics(
                task_id=task_id,
                failure_type=failure_type,
                error_message=error_message,
                agent_name=agent_name,
                context=context or {},
                stack_trace=stack_trace,
                recovery_suggestions=recovery_suggestions or [],
            )
        )

    def get_decompositions(self) -> list[DecompositionExplanation]:
        """Get all decomposition explanations."""
        return list(self._decompositions)

    def get_team_designs(self) -> list[TeamDesignExplanation]:
        """Get all team design explanations."""
        return list(self._team_designs)

    def get_agent_selections(self) -> list[AgentSelectionExplanation]:
        """Get all agent selection explanations."""
        return list(self._agent_selections)

    def get_interactions(self) -> list[InteractionLog]:
        """Get all interaction logs."""
        return list(self._interactions)

    def get_failures(self) -> list[FailureDiagnostics]:
        """Get all failure diagnostics."""
        return list(self._failures)

    def get_interactions_by_agent(self, agent_name: str) -> list[InteractionLog]:
        """Get interactions involving a specific agent."""
        return [
            log
            for log in self._interactions
            if log.from_agent == agent_name or log.to_agent == agent_name
        ]

    def get_failures_by_task(self, task_id: str) -> list[FailureDiagnostics]:
        """Get failures for a specific task."""
        return [f for f in self._failures if f.task_id == task_id]

    def export_all(self) -> dict[str, Any]:
        """Export all tracked data as JSON-serializable dict."""
        return {
            "decompositions": [d.to_dict() for d in self._decompositions],
            "team_designs": [t.to_dict() for t in self._team_designs],
            "agent_selections": [a.to_dict() for a in self._agent_selections],
            "interactions": [i.to_dict() for i in self._interactions],
            "failures": [f.to_dict() for f in self._failures],
        }

    def generate_report(self) -> str:
        """Generate human-readable summary report."""
        lines = [
            "=== Explainability Report ===",
            f"Decompositions: {len(self._decompositions)}",
            f"Team Designs: {len(self._team_designs)}",
            f"Agent Selections: {len(self._agent_selections)}",
            f"Interactions: {len(self._interactions)}",
            f"Failures: {len(self._failures)}",
        ]
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all tracked data."""
        self._decompositions.clear()
        self._team_designs.clear()
        self._agent_selections.clear()
        self._interactions.clear()
        self._failures.clear()
