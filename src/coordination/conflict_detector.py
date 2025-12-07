"""
Conflict detection and resolution for agent outputs.

This module provides functionality to detect conflicts between agent outputs
and resolve them using various strategies (voting, priority-based, re-evaluation).
"""

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ConflictType(str, Enum):
    """Types of conflicts that can occur between agents."""
    OUTPUT_MISMATCH = "output_mismatch"
    INTERPRETATION_MISMATCH = "interpretation_mismatch"
    DEPENDENCY_MISMATCH = "dependency_mismatch"
    STATE_MISMATCH = "state_mismatch"
    RESOURCE_CONFLICT = "resource_conflict"


class ResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts."""
    VOTING = "voting"
    PRIORITY_BASED = "priority_based"
    RE_EVALUATION = "re_evaluation"
    MERGE = "merge"
    ESCALATE = "escalate"


@dataclass
class Conflict:
    """
    Represents a conflict between agent outputs.

    Attributes:
        conflict_type: Type of conflict
        subtask_id: ID of subtask where conflict occurred
        involved_agents: List of agent IDs involved in conflict
        details: Conflict-specific details (outputs, interpretations, etc.)
        severity: Severity level (low, medium, high, critical)
        conflict_id: Unique identifier for this conflict
        timestamp: When conflict was detected
    """
    conflict_type: ConflictType
    subtask_id: str
    involved_agents: list[str]
    details: dict[str, Any]
    severity: str = "medium"
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ConflictResolution:
    """
    Represents the resolution of a conflict.

    Attributes:
        conflict_id: ID of conflict being resolved
        strategy_used: Strategy used to resolve conflict
        winning_output: The chosen output/solution
        winning_agent: Agent whose output was selected (if applicable)
        confidence: Confidence in resolution (0.0 to 1.0)
        requires_escalation: Whether human intervention needed
        requires_re_evaluation: Whether re-evaluation by different agent needed
        metadata: Additional resolution details
        timestamp: When resolution was made
    """
    conflict_id: str
    strategy_used: ResolutionStrategy
    winning_output: Any = None
    winning_agent: str | None = None
    confidence: float = 0.5
    requires_escalation: bool = False
    requires_re_evaluation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ConflictDetector:
    """
    Detects and resolves conflicts between agent outputs.

    The detector can identify various types of conflicts (output mismatches,
    interpretation differences, dependency disagreements) and apply different
    resolution strategies.
    """

    def __init__(self) -> None:
        """Initialize the conflict detector."""
        self.detected_conflicts: list[Conflict] = []
        self.resolutions: list[ConflictResolution] = []

    def detect_output_conflicts(
        self,
        agent_outputs: dict[str, dict[str, Any]]
    ) -> list[Conflict]:
        """
        Detect conflicts in agent outputs for the same subtask.

        Args:
            agent_outputs: Dict mapping agent_id to output dict
                          (must include 'subtask_id' and 'output' keys)

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Group outputs by subtask
        subtask_outputs: dict[str, dict[str, Any]] = {}
        for agent_id, output_data in agent_outputs.items():
            subtask_id = output_data.get("subtask_id")
            if not subtask_id:
                continue

            if subtask_id not in subtask_outputs:
                subtask_outputs[subtask_id] = {}

            subtask_outputs[subtask_id][agent_id] = output_data.get("output")

        # Check for conflicts within each subtask
        for subtask_id, outputs in subtask_outputs.items():
            if len(outputs) <= 1:
                # No conflict with single agent
                continue

            # Check if all outputs are the same
            unique_outputs = set(
                str(output) for output in outputs.values()
            )

            if len(unique_outputs) > 1:
                # Conflict detected
                conflict = Conflict(
                    conflict_type=ConflictType.OUTPUT_MISMATCH,
                    subtask_id=subtask_id,
                    involved_agents=list(outputs.keys()),
                    details=outputs,
                )
                conflicts.append(conflict)
                self.detected_conflicts.append(conflict)

        return conflicts

    def detect_interpretation_conflicts(
        self,
        interpretations: dict[str, dict[str, Any]]
    ) -> list[Conflict]:
        """
        Detect conflicts in task interpretation between agents.

        Args:
            interpretations: Dict mapping agent_id to interpretation dict
                           (must include 'subtask_id' and 'requirements' keys)

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Group interpretations by subtask
        subtask_interps: dict[str, dict[str, Any]] = {}
        for agent_id, interp_data in interpretations.items():
            subtask_id = interp_data.get("subtask_id")
            if not subtask_id:
                continue

            if subtask_id not in subtask_interps:
                subtask_interps[subtask_id] = {}

            subtask_interps[subtask_id][agent_id] = interp_data.get("requirements", [])

        # Check for conflicts within each subtask
        for subtask_id, interps in subtask_interps.items():
            if len(interps) <= 1:
                continue

            # Compare requirement sets
            requirement_sets = [set(reqs) for reqs in interps.values()]

            # Check if all sets are equal
            if not all(req_set == requirement_sets[0] for req_set in requirement_sets):
                conflict = Conflict(
                    conflict_type=ConflictType.INTERPRETATION_MISMATCH,
                    subtask_id=subtask_id,
                    involved_agents=list(interps.keys()),
                    details=interps,
                )
                conflicts.append(conflict)
                self.detected_conflicts.append(conflict)

        return conflicts

    def detect_dependency_conflicts(
        self,
        dependency_views: dict[str, dict[str, Any]]
    ) -> list[Conflict]:
        """
        Detect conflicts in dependency understanding between agents.

        Args:
            dependency_views: Dict mapping agent_id to dependency view
                            (must include 'subtask_id' and 'dependencies' keys)

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Group dependency views by subtask
        subtask_deps: dict[str, dict[str, Any]] = {}
        for agent_id, dep_data in dependency_views.items():
            subtask_id = dep_data.get("subtask_id")
            if not subtask_id:
                continue

            if subtask_id not in subtask_deps:
                subtask_deps[subtask_id] = {}

            subtask_deps[subtask_id][agent_id] = dep_data.get("dependencies", [])

        # Check for conflicts within each subtask
        for subtask_id, deps in subtask_deps.items():
            if len(deps) <= 1:
                continue

            # Compare dependency sets
            dependency_sets = [set(dep_list) for dep_list in deps.values()]

            # Check if all sets are equal
            if not all(dep_set == dependency_sets[0] for dep_set in dependency_sets):
                conflict = Conflict(
                    conflict_type=ConflictType.DEPENDENCY_MISMATCH,
                    subtask_id=subtask_id,
                    involved_agents=list(deps.keys()),
                    details=deps,
                )
                conflicts.append(conflict)
                self.detected_conflicts.append(conflict)

        return conflicts

    def resolve_conflict(
        self,
        conflict: Conflict,
        strategy: ResolutionStrategy | str,
        agent_priorities: dict[str, int] | None = None
    ) -> ConflictResolution:
        """
        Resolve a conflict using the specified strategy.

        Args:
            conflict: Conflict to resolve
            strategy: Resolution strategy to use
            agent_priorities: Optional priority mapping for priority-based resolution

        Returns:
            ConflictResolution with winning output and metadata

        Raises:
            ValueError: If strategy is invalid
        """
        # Convert string to enum if needed
        if isinstance(strategy, str):
            try:
                strategy = ResolutionStrategy(strategy)
            except ValueError:
                raise ValueError(f"Unknown resolution strategy: {strategy}")

        if strategy == ResolutionStrategy.VOTING:
            resolution = self._resolve_by_voting(conflict)
        elif strategy == ResolutionStrategy.PRIORITY_BASED:
            resolution = self._resolve_by_priority(conflict, agent_priorities)
        elif strategy == ResolutionStrategy.RE_EVALUATION:
            resolution = self._resolve_by_re_evaluation(conflict)
        else:
            raise ValueError(f"Unknown resolution strategy: {strategy}")

        self.resolutions.append(resolution)
        return resolution

    def _resolve_by_voting(self, conflict: Conflict) -> ConflictResolution:
        """
        Resolve conflict by voting (majority wins).

        Args:
            conflict: Conflict to resolve

        Returns:
            ConflictResolution with voting results
        """
        # Count votes for each output
        outputs = [str(output) for output in conflict.details.values()]
        vote_counts = Counter(outputs)

        # Find the most common output
        most_common = vote_counts.most_common(1)[0]
        winning_output = most_common[0]
        vote_count = most_common[1]
        total_votes = len(outputs)

        # Calculate confidence based on vote percentage
        confidence = vote_count / total_votes

        # Check for tie
        requires_escalation = False
        if vote_count <= total_votes / 2:
            # No clear majority
            requires_escalation = True
            confidence = 0.4

        # Find winning agent
        winning_agent = None
        for agent_id, output in conflict.details.items():
            if str(output) == winning_output:
                winning_agent = agent_id
                break

        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.VOTING,
            winning_output=winning_output,
            winning_agent=winning_agent,
            confidence=confidence,
            requires_escalation=requires_escalation,
            metadata={
                "vote_counts": dict(vote_counts),
                "total_votes": total_votes,
            }
        )

    def _resolve_by_priority(
        self,
        conflict: Conflict,
        agent_priorities: dict[str, int] | None
    ) -> ConflictResolution:
        """
        Resolve conflict by agent priority (highest priority wins).

        Args:
            conflict: Conflict to resolve
            agent_priorities: Priority mapping (higher number = higher priority)

        Returns:
            ConflictResolution with priority-based result
        """
        # Use default priorities if none provided
        if agent_priorities is None:
            agent_priorities = {
                agent_id: 0 for agent_id in conflict.involved_agents
            }

        # Find agent with highest priority
        highest_priority = -1
        winning_agent = None
        winning_output = None

        for agent_id in conflict.involved_agents:
            priority = agent_priorities.get(agent_id, 0)
            if priority > highest_priority:
                highest_priority = priority
                winning_agent = agent_id
                winning_output = conflict.details.get(agent_id)

        # Confidence based on priority gap
        priorities = [agent_priorities.get(aid, 0) for aid in conflict.involved_agents]
        sorted_priorities = sorted(priorities, reverse=True)

        if len(sorted_priorities) > 1:
            priority_gap = sorted_priorities[0] - sorted_priorities[1]
            confidence = min(0.9, 0.5 + (priority_gap / 20))
        else:
            confidence = 1.0

        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.PRIORITY_BASED,
            winning_output=winning_output,
            winning_agent=winning_agent,
            confidence=confidence,
            metadata={
                "priorities": agent_priorities,
                "highest_priority": highest_priority,
            }
        )

    def _resolve_by_re_evaluation(self, conflict: Conflict) -> ConflictResolution:
        """
        Mark conflict for re-evaluation by a different agent.

        Args:
            conflict: Conflict to resolve

        Returns:
            ConflictResolution marking need for re-evaluation
        """
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.RE_EVALUATION,
            requires_re_evaluation=True,
            confidence=0.0,
            metadata={
                "reason": "Conflict requires external review",
            }
        )

    def get_conflict_summary(self) -> dict[str, Any]:
        """
        Get summary of detected conflicts and resolutions.

        Returns:
            Summary statistics
        """
        return {
            "total_conflicts": len(self.detected_conflicts),
            "total_resolutions": len(self.resolutions),
            "conflicts_by_type": {
                conflict_type: sum(
                    1 for c in self.detected_conflicts
                    if c.conflict_type == conflict_type
                )
                for conflict_type in ConflictType
            },
            "resolutions_by_strategy": {
                strategy: sum(
                    1 for r in self.resolutions
                    if r.strategy_used == strategy
                )
                for strategy in ResolutionStrategy
            },
        }
