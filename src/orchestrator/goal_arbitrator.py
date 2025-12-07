"""
Goal Arbitrator - Flexible conflict resolution for competing goals.

Handles:
- Goal conflict detection
- Context-sensitive goal weighing
- Explicit trade-off reasoning
- Multiple resolution strategies
- Goal satisfaction tracking
- Satisficing (accepting "good enough")
- Dynamic priority adjustment

Design Philosophy:
- No rigid priorities - decisions depend on context
- Explicit reasoning - all decisions are explained
- Multiple strategies - different conflicts need different approaches
- Transparency - trade-offs are documented
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GoalConflictType(str, Enum):
    """Types of goal conflicts."""

    SPEED_VS_CORRECTNESS = "speed_vs_correctness"
    SAFETY_VS_INSTRUCTION = "safety_vs_instruction"
    RESOURCE_CONSTRAINT = "resource_constraint"
    SCOPE_CREEP = "scope_creep"
    COMPLETENESS_VS_BUDGET = "completeness_vs_budget"
    QUALITY_VS_DEADLINE = "quality_vs_deadline"


class ArbitrationStrategy(str, Enum):
    """Strategies for resolving goal conflicts."""

    PRIORITIZE_HIGHER = "prioritize_higher"  # Choose higher priority goal
    COMPROMISE = "compromise"  # Partially satisfy both
    SATISFICE = "satisfice"  # Accept good enough
    SAFETY_FIRST = "safety_first"  # Always prioritize safety
    CONTEXT_DEPENDENT = "context_dependent"  # Let context decide
    SEQUENTIAL = "sequential"  # Do both, one after another


@dataclass
class Goal:
    """Represents a goal with priority and context."""

    id: str
    description: str
    priority: float  # 0.0 to 1.0
    context: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    satisfaction: float = 0.0  # How well goal is being satisfied (0.0 to 1.0)


@dataclass
class GoalConflict:
    """Represents a detected conflict between goals."""

    type: GoalConflictType
    conflicting_goals: list[str]  # Goal IDs
    severity: float  # 0.0 to 1.0
    description: str = ""


@dataclass
class ArbitrationDecision:
    """Result of goal arbitration."""

    chosen_goals: list[str]  # Goal IDs that were prioritized
    deferred_goals: list[str] = field(default_factory=list)  # Goals postponed
    reasoning: str = ""  # Explanation of decision
    strategy: ArbitrationStrategy = ArbitrationStrategy.CONTEXT_DEPENDENT
    trade_offs: dict[str, Any] = field(default_factory=dict)  # Documented trade-offs
    adjusted_priorities: dict[str, float] = field(default_factory=dict)  # New priorities


class GoalArbitrator:
    """
    Arbitrates between competing goals with context-sensitive reasoning.

    Key Features:
    - Detects goal conflicts automatically
    - Applies context-sensitive weighing
    - Explains decisions with explicit reasoning
    - Tracks goal satisfaction over time
    - Supports satisficing for impossible perfect solutions
    """

    def __init__(self) -> None:
        """Initialize the goal arbitrator."""
        # Safety keywords that boost priority
        self.safety_keywords = [
            "safety",
            "secure",
            "security",
            "protect",
            "dangerous",
            "risk",
            "delete",
            "production",
        ]

        # Speed/urgency keywords
        self.speed_keywords = [
            "fast",
            "quick",
            "immediate",
            "urgent",
            "hotfix",
            "asap",
            "now",
        ]

        # Quality/correctness keywords
        self.quality_keywords = [
            "correct",
            "quality",
            "test",
            "coverage",
            "thorough",
            "complete",
            "perfect",
        ]

    def detect_conflicts(self, goals: list[Goal]) -> list[GoalConflict]:
        """
        Detect conflicts between goals.

        Args:
            goals: List of goals to check

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check each pair of goals
        for i, g1 in enumerate(goals):
            for g2 in goals[i + 1 :]:
                conflict = self._check_goal_pair(g1, g2)
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _check_goal_pair(self, g1: Goal, g2: Goal) -> GoalConflict | None:
        """Check if two goals conflict."""
        # Speed vs Correctness
        if self._is_speed_goal(g1) and self._is_quality_goal(g2):
            return GoalConflict(
                type=GoalConflictType.SPEED_VS_CORRECTNESS,
                conflicting_goals=[g1.id, g2.id],
                severity=0.8,
                description=(
                    f"Speed goal '{g1.description}' conflicts with "
                    f"quality goal '{g2.description}'"
                ),
            )
        if self._is_speed_goal(g2) and self._is_quality_goal(g1):
            return GoalConflict(
                type=GoalConflictType.SPEED_VS_CORRECTNESS,
                conflicting_goals=[g1.id, g2.id],
                severity=0.8,
                description=(
                    f"Speed goal '{g2.description}' conflicts with "
                    f"quality goal '{g1.description}'"
                ),
            )

        # Safety vs Instruction
        if self._is_safety_goal(g1) or self._is_safety_goal(g2):
            if self._is_potentially_dangerous(g1) or self._is_potentially_dangerous(g2):
                return GoalConflict(
                    type=GoalConflictType.SAFETY_VS_INSTRUCTION,
                    conflicting_goals=[g1.id, g2.id],
                    severity=1.0,  # Maximum severity for safety
                    description="Safety concern detected",
                )

        # Resource constraints
        if self._has_resource_conflict(g1, g2):
            return GoalConflict(
                type=GoalConflictType.RESOURCE_CONSTRAINT,
                conflicting_goals=[g1.id, g2.id],
                severity=0.7,
                description="Resource constraint conflict",
            )

        # Scope creep
        if self._is_scope_conflict(g1, g2):
            return GoalConflict(
                type=GoalConflictType.SCOPE_CREEP,
                conflicting_goals=[g1.id, g2.id],
                severity=0.6,
                description="Potential scope creep detected",
            )

        return None

    def _is_speed_goal(self, goal: Goal) -> bool:
        """Check if goal prioritizes speed."""
        if goal.context.get("type") == "speed":
            return True
        return any(
            keyword in goal.description.lower() for keyword in self.speed_keywords
        )

    def _is_quality_goal(self, goal: Goal) -> bool:
        """Check if goal prioritizes quality/correctness."""
        if goal.context.get("type") == "correctness":
            return True
        return any(
            keyword in goal.description.lower() for keyword in self.quality_keywords
        )

    def _is_safety_goal(self, goal: Goal) -> bool:
        """Check if goal is safety-related."""
        if goal.context.get("type") == "safety":
            return True
        return any(
            keyword in goal.description.lower() for keyword in self.safety_keywords
        )

    def _is_potentially_dangerous(self, goal: Goal) -> bool:
        """Check if goal involves potentially dangerous operations."""
        dangerous_keywords = [
            "delete",
            "drop",
            "remove",
            "destroy",
            "production",
            "prod",
        ]
        return any(
            keyword in goal.description.lower() for keyword in dangerous_keywords
        )

    def _has_resource_conflict(self, g1: Goal, g2: Goal) -> bool:
        """Check if goals have conflicting resource requirements."""
        # Check token budget conflicts
        if "max_tokens" in g2.constraints:
            max_tokens = g2.constraints["max_tokens"]
            if "estimated_tokens" in g1.context:
                estimated = g1.context["estimated_tokens"]
                if estimated > max_tokens:
                    return True

        if "max_tokens" in g1.constraints:
            max_tokens = g1.constraints["max_tokens"]
            if "estimated_tokens" in g2.context:
                estimated = g2.context["estimated_tokens"]
                if estimated > max_tokens:
                    return True

        # Check effort constraints
        if "max_effort" in g2.constraints:
            max_effort = g2.constraints["max_effort"]
            if "estimated_effort" in g1.context:
                estimated = g1.context["estimated_effort"]
                if estimated > max_effort:
                    return True

        return False

    def _is_scope_conflict(self, g1: Goal, g2: Goal) -> bool:
        """Check if goals represent scope creep."""
        scope1 = g1.context.get("scope", "")
        scope2 = g2.context.get("scope", "")

        if scope1 == "minimal" and scope2 == "expanded":
            return True
        if scope2 == "minimal" and scope1 == "expanded":
            return True

        return False

    def weigh_goals(
        self, goals: list[Goal], context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Apply context-sensitive weighing to goals.

        Args:
            goals: Goals to weigh
            context: Current context (situation, constraints, etc.)

        Returns:
            List of dicts with goal and computed weight
        """
        context = context or {}
        weighted = []

        for goal in goals:
            # Start with base priority
            weight = goal.priority

            # Safety always gets high weight
            if self._is_safety_goal(goal):
                weight = max(weight, 0.9)

            # Urgency boosts
            if context.get("situation") in ["production_down", "production_issue", "urgent"]:
                if self._is_speed_goal(goal):
                    weight += 0.15

            if goal.context.get("urgency") == "high":
                weight += 0.1
            if goal.context.get("urgency") == "critical":
                weight += 0.2

            # Impact adjustments
            if goal.context.get("impact") == "critical":
                weight += 0.15
            elif goal.context.get("impact") == "high":
                weight += 0.1
            elif goal.context.get("impact") == "low":
                weight -= 0.1

            # Deadline proximity
            if "deadline" in goal.constraints:
                if context.get("current_time") == "end_of_day":
                    if goal.constraints["deadline"] == "today":
                        weight += 0.2

            # Resource pressure
            if context.get("resource_pressure") == "high":
                if goal.context.get("impact") == "low":
                    weight -= 0.1

            # Clamp to valid range
            weight = max(0.0, min(1.0, weight))

            weighted.append({"goal": goal, "weight": weight})

        return weighted

    def resolve_conflict(
        self,
        conflict: GoalConflict,
        goals: list[Goal],
        strategy: ArbitrationStrategy | None = None,
        context: dict[str, Any] | None = None,
    ) -> ArbitrationDecision:
        """
        Resolve a goal conflict using the specified strategy.

        Args:
            conflict: The conflict to resolve
            goals: All goals involved
            strategy: Resolution strategy (auto-selected if None)
            context: Additional context

        Returns:
            Arbitration decision with reasoning
        """
        context = context or {}

        # Auto-select strategy if not provided
        if strategy is None:
            strategy = self._select_strategy(conflict, goals)

        # Get the conflicting goals
        conflicting = [g for g in goals if g.id in conflict.conflicting_goals]

        if strategy == ArbitrationStrategy.SAFETY_FIRST:
            return self._resolve_safety_first(conflicting, conflict)
        elif strategy == ArbitrationStrategy.PRIORITIZE_HIGHER:
            return self._resolve_prioritize(conflicting, conflict)
        elif strategy == ArbitrationStrategy.COMPROMISE:
            return self._resolve_compromise(conflicting, conflict)
        elif strategy == ArbitrationStrategy.SATISFICE:
            return self._resolve_satisfice(conflicting, conflict)
        else:
            # Default: context-dependent
            return self._resolve_context_dependent(conflicting, conflict, context)

    def _select_strategy(
        self, conflict: GoalConflict, goals: list[Goal]
    ) -> ArbitrationStrategy:
        """Auto-select appropriate strategy for conflict."""
        if conflict.type == GoalConflictType.SAFETY_VS_INSTRUCTION:
            return ArbitrationStrategy.SAFETY_FIRST
        elif conflict.severity >= 0.9:
            return ArbitrationStrategy.PRIORITIZE_HIGHER
        elif conflict.severity <= 0.6:
            return ArbitrationStrategy.COMPROMISE
        elif conflict.type == GoalConflictType.RESOURCE_CONSTRAINT:
            return ArbitrationStrategy.SATISFICE
        else:
            return ArbitrationStrategy.CONTEXT_DEPENDENT

    def _resolve_safety_first(
        self, conflicting: list[Goal], conflict: GoalConflict
    ) -> ArbitrationDecision:
        """Resolve by prioritizing safety."""
        safety_goals = [g for g in conflicting if self._is_safety_goal(g)]
        other_goals = [g for g in conflicting if not self._is_safety_goal(g)]

        return ArbitrationDecision(
            chosen_goals=[g.id for g in safety_goals],
            deferred_goals=[g.id for g in other_goals],
            reasoning=(
                "Safety concerns override other goals. "
                "Prioritizing safety to prevent potential harm."
            ),
            strategy=ArbitrationStrategy.SAFETY_FIRST,
            trade_offs={
                "prioritized": "Safety and risk mitigation",
                "deferred": "Speed or literal instruction compliance",
            },
        )

    def _resolve_prioritize(
        self, conflicting: list[Goal], conflict: GoalConflict
    ) -> ArbitrationDecision:
        """Resolve by choosing highest priority goal."""
        sorted_goals = sorted(conflicting, key=lambda g: g.priority, reverse=True)
        chosen = sorted_goals[0]
        deferred = sorted_goals[1:]

        reasoning = (
            f"Prioritized '{chosen.description}' (priority {chosen.priority:.1f}) "
            f"due to higher importance. The reason for this decision is that it "
            f"has the highest priority among conflicting goals."
        )
        return ArbitrationDecision(
            chosen_goals=[chosen.id],
            deferred_goals=[g.id for g in deferred],
            reasoning=reasoning,
            strategy=ArbitrationStrategy.PRIORITIZE_HIGHER,
            trade_offs={
                "chosen_priority": chosen.priority,
                "deferred": [{"id": g.id, "priority": g.priority} for g in deferred],
            },
        )

    def _resolve_compromise(
        self, conflicting: list[Goal], conflict: GoalConflict
    ) -> ArbitrationDecision:
        """Resolve through compromise - partially satisfy both."""
        return ArbitrationDecision(
            chosen_goals=[g.id for g in conflicting],
            deferred_goals=[],
            reasoning=(
                "Seeking compromise to partially satisfy both goals. "
                "Will balance competing concerns."
            ),
            strategy=ArbitrationStrategy.COMPROMISE,
            trade_offs={
                "approach": "Balanced solution",
                "note": "Neither goal fully satisfied, both partially met",
            },
            adjusted_priorities={
                g.id: g.priority * 0.7 for g in conflicting
            },  # Reduce both
        )

    def _resolve_satisfice(
        self, conflicting: list[Goal], conflict: GoalConflict
    ) -> ArbitrationDecision:
        """Resolve by accepting good enough solution."""
        # Prefer goals with explicit minimum satisfaction thresholds
        goals_with_mins = [
            g for g in conflicting if "min_satisfaction" in g.constraints
        ]

        if goals_with_mins:
            chosen = goals_with_mins
        else:
            chosen = conflicting

        return ArbitrationDecision(
            chosen_goals=[g.id for g in chosen],
            deferred_goals=[],
            reasoning=(
                "Perfect solution impossible. Accepting good enough solution "
                "that meets minimum thresholds (satisficing)."
            ),
            strategy=ArbitrationStrategy.SATISFICE,
            trade_offs={
                "approach": "Satisficing - good enough vs perfect",
                "min_satisfaction": "Targeting minimum acceptable levels",
            },
        )

    def _resolve_context_dependent(
        self, conflicting: list[Goal], conflict: GoalConflict, context: dict[str, Any]
    ) -> ArbitrationDecision:
        """Resolve based on context."""
        # Weigh goals with context
        weighted = self.weigh_goals(conflicting, context)
        sorted_weighted = sorted(weighted, key=lambda w: w["weight"], reverse=True)

        chosen = sorted_weighted[0]["goal"]
        deferred = [w["goal"] for w in sorted_weighted[1:]]

        # Build reasoning with causal words
        context_str = (
            ", ".join(f"{k}={v}" for k, v in context.items())
            if context
            else "current situation"
        )
        reasoning = (
            f"Based on {context_str}, prioritizing '{chosen.description}' "
            f"because it has the highest contextual weight "
            f"({sorted_weighted[0]['weight']:.2f}). This decision is made since "
            f"the context indicates this goal is most critical for the current situation."
        )

        return ArbitrationDecision(
            chosen_goals=[chosen.id],
            deferred_goals=[g.id for g in deferred],
            reasoning=reasoning,
            strategy=ArbitrationStrategy.CONTEXT_DEPENDENT,
            trade_offs={
                "context": context,
                "chosen_weight": sorted_weighted[0]["weight"],
                "benefits": "Addresses most critical need in current context",
                "costs": f"Defers {len(deferred)} other goal(s)",
            },
        )

    def arbitrate(
        self, goals: list[Goal], context: dict[str, Any] | None = None
    ) -> ArbitrationDecision:
        """
        Main arbitration method - detect conflicts and resolve them.

        Args:
            goals: Goals to arbitrate between
            context: Current context

        Returns:
            Final arbitration decision
        """
        context = context or {}

        # Detect conflicts
        conflicts = self.detect_conflicts(goals)

        # If no conflicts, choose all goals but still document trade-offs
        if not conflicts:
            # Extract benefits and costs from goal contexts if present
            trade_offs = {}
            for goal in goals:
                if "benefits" in goal.context:
                    trade_offs[f"{goal.id}_benefits"] = goal.context["benefits"]
                if "costs" in goal.context:
                    trade_offs[f"{goal.id}_costs"] = goal.context["costs"]

            # Add general trade-offs summary if any goals have them
            if trade_offs:
                all_benefits = []
                all_costs = []
                for key, val in trade_offs.items():
                    if "benefits" in key:
                        all_benefits.extend(val if isinstance(val, list) else [val])
                    if "costs" in key:
                        all_costs.extend(val if isinstance(val, list) else [val])

                if all_benefits or all_costs:
                    trade_offs["benefits"] = all_benefits
                    trade_offs["costs"] = all_costs

            return ArbitrationDecision(
                chosen_goals=[g.id for g in goals],
                deferred_goals=[],
                reasoning="No conflicts detected. All goals can be pursued.",
                strategy=ArbitrationStrategy.CONTEXT_DEPENDENT,
                trade_offs=trade_offs if trade_offs else {},
            )

        # Resolve highest severity conflict first
        primary_conflict = max(conflicts, key=lambda c: c.severity)
        decision = self.resolve_conflict(primary_conflict, goals, context=context)

        # Add context about additional conflicts
        if len(conflicts) > 1:
            decision.trade_offs["additional_conflicts"] = len(conflicts) - 1

        return decision

    def update_satisfaction(
        self, goal_id: str, satisfaction: float, goals: list[Goal]
    ) -> None:
        """
        Update satisfaction level for a goal.

        Args:
            goal_id: ID of goal to update
            satisfaction: New satisfaction level (0.0 to 1.0)
            goals: List of all goals
        """
        for goal in goals:
            if goal.id == goal_id:
                goal.satisfaction = max(0.0, min(1.0, satisfaction))
                break

    def get_satisfaction_report(self, goals: list[Goal]) -> dict[str, float]:
        """
        Get satisfaction levels for all goals.

        Args:
            goals: Goals to report on

        Returns:
            Dict mapping goal ID to satisfaction level
        """
        return {g.id: g.satisfaction for g in goals}

    def is_satisficing_acceptable(
        self, goals: list[Goal], satisfaction_levels: dict[str, float]
    ) -> bool:
        """
        Check if current satisfaction levels meet minimum thresholds.

        Args:
            goals: Goals with constraints
            satisfaction_levels: Current satisfaction levels

        Returns:
            True if all minimums are met
        """
        for goal in goals:
            min_satisfaction = goal.constraints.get("min_satisfaction", 0.0)
            current = satisfaction_levels.get(goal.id, 0.0)
            if current < min_satisfaction:
                return False
        return True

    def find_satisficing_solution(
        self, goals: list[Goal]
    ) -> dict[str, float] | None:
        """
        Find a satisficing solution that meets minimum thresholds.

        Args:
            goals: Goals to satisfy

        Returns:
            Dict of satisfaction levels, or None if impossible
        """
        # Simple heuristic: distribute satisfaction based on min requirements
        total_min = sum(g.constraints.get("min_satisfaction", 0.6) for g in goals)

        if total_min > len(goals) * 1.0:
            # Impossible to satisfy all minimums
            return None

        # Aim for minimum + small margin
        solution = {}
        for goal in goals:
            min_sat = goal.constraints.get("min_satisfaction", 0.6)
            solution[goal.id] = min(1.0, min_sat + 0.1)

        return solution

    def adjust_priority(
        self, goal: Goal, context: dict[str, Any] | None = None
    ) -> float:
        """
        Dynamically adjust goal priority based on context.

        Args:
            goal: Goal to adjust
            context: Current context

        Returns:
            Adjusted priority (0.0 to 1.0)
        """
        context = context or {}
        adjusted = goal.priority

        # Urgency adjustments
        if context.get("urgency") == "critical":
            adjusted += 0.2
        elif context.get("urgency") == "high":
            adjusted += 0.1

        # Impact adjustments
        if context.get("impact") == "high":
            adjusted += 0.15
        elif context.get("impact") == "low":
            if context.get("resource_pressure") == "high":
                adjusted -= 0.15

        # Deadline proximity
        if "deadline" in goal.constraints:
            if context.get("current_time") == "end_of_day":
                if goal.constraints["deadline"] == "today":
                    adjusted += 0.25

        # Clamp to valid range
        return max(0.0, min(1.0, adjusted))

    def explain_decision(self, decision: ArbitrationDecision) -> str:
        """
        Generate human-readable explanation of arbitration decision.

        Args:
            decision: Decision to explain

        Returns:
            Formatted explanation
        """
        lines = []
        lines.append("=== Goal Arbitration Decision ===\n")
        lines.append(f"Strategy: {decision.strategy.value}")
        lines.append(f"\nChosen Goals: {', '.join(decision.chosen_goals)}")

        if decision.deferred_goals:
            lines.append(f"Deferred Goals: {', '.join(decision.deferred_goals)}")

        lines.append(f"\nReasoning: {decision.reasoning}")

        if decision.trade_offs:
            lines.append("\nTrade-offs:")
            for key, value in decision.trade_offs.items():
                lines.append(f"  - {key}: {value}")

        if decision.adjusted_priorities:
            lines.append("\nAdjusted Priorities:")
            for goal_id, priority in decision.adjusted_priorities.items():
                lines.append(f"  - {goal_id}: {priority:.2f}")

        return "\n".join(lines)
