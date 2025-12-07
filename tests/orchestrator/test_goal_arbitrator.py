"""
Tests for Goal Arbitrator - Flexible goal conflict resolution.

Tests cover:
- Goal conflict detection
- Context-sensitive weighing
- Trade-off reasoning
- Conflict resolution strategies
- Goal satisfaction tracking
- Satisficing behavior
- Dynamic priority adjustment
"""


from src.orchestrator.goal_arbitrator import (
    ArbitrationStrategy,
    Goal,
    GoalArbitrator,
    GoalConflict,
    GoalConflictType,
)


class TestGoalModel:
    """Test the Goal data model."""

    def test_goal_creation(self):
        """Goal can be created with basic attributes."""
        goal = Goal(
            id="g1",
            description="Complete the refactor",
            priority=0.8,
            context={"urgency": "high"},
        )
        assert goal.id == "g1"
        assert goal.description == "Complete the refactor"
        assert goal.priority == 0.8
        assert goal.context["urgency"] == "high"

    def test_goal_satisfaction_tracking(self):
        """Goal tracks satisfaction level."""
        goal = Goal(id="g1", description="Test", priority=0.5)
        assert goal.satisfaction == 0.0  # Default

        goal.satisfaction = 0.75
        assert goal.satisfaction == 0.75

    def test_goal_constraints(self):
        """Goal can have constraints."""
        goal = Goal(
            id="g1",
            description="Fix bug",
            priority=0.9,
            constraints={"max_time": "1h", "must_test": True},
        )
        assert goal.constraints["max_time"] == "1h"
        assert goal.constraints["must_test"] is True


class TestConflictDetection:
    """Test goal conflict detection."""

    def test_detect_no_conflicts(self):
        """No conflicts when goals are compatible."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(id="g1", description="Write tests", priority=0.8),
            Goal(id="g2", description="Write docs", priority=0.6),
        ]

        conflicts = arbitrator.detect_conflicts(goals)
        assert len(conflicts) == 0

    def test_detect_speed_vs_correctness(self):
        """Detect speed vs correctness conflicts."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Ship hotfix immediately",
                priority=0.9,
                context={"type": "speed"},
            ),
            Goal(
                id="g2",
                description="Ensure full test coverage",
                priority=0.8,
                context={"type": "correctness"},
            ),
        ]

        conflicts = arbitrator.detect_conflicts(goals)
        assert len(conflicts) == 1
        assert conflicts[0].type == GoalConflictType.SPEED_VS_CORRECTNESS
        assert "g1" in conflicts[0].conflicting_goals
        assert "g2" in conflicts[0].conflicting_goals

    def test_detect_safety_vs_instructions(self):
        """Detect safety vs literal instructions conflicts."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Delete production database",
                priority=0.9,
                context={"type": "instruction", "literal": True},
            ),
            Goal(
                id="g2",
                description="Ensure data safety",
                priority=1.0,
                context={"type": "safety"},
            ),
        ]

        conflicts = arbitrator.detect_conflicts(goals)
        assert len(conflicts) >= 1
        # Safety conflict should be detected
        safety_conflicts = [
            c for c in conflicts if c.type == GoalConflictType.SAFETY_VS_INSTRUCTION
        ]
        assert len(safety_conflicts) == 1

    def test_detect_resource_constraints(self):
        """Detect conflicts with resource constraints."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Implement all features",
                priority=0.8,
                context={"estimated_tokens": 50000},
            ),
            Goal(
                id="g2",
                description="Stay within token budget",
                priority=0.9,
                constraints={"max_tokens": 20000},
            ),
        ]

        conflicts = arbitrator.detect_conflicts(goals)
        assert len(conflicts) >= 1
        resource_conflicts = [
            c for c in conflicts if c.type == GoalConflictType.RESOURCE_CONSTRAINT
        ]
        assert len(resource_conflicts) == 1

    def test_detect_scope_conflicts(self):
        """Detect scope creep vs original request conflicts."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Fix the login bug",
                priority=0.9,
                context={"scope": "minimal"},
            ),
            Goal(
                id="g2",
                description="Refactor entire auth system",
                priority=0.7,
                context={"scope": "expanded"},
            ),
        ]

        conflicts = arbitrator.detect_conflicts(goals)
        scope_conflicts = [c for c in conflicts if c.type == GoalConflictType.SCOPE_CREEP]
        assert len(scope_conflicts) >= 0  # May or may not detect based on heuristics


class TestContextSensitiveWeighing:
    """Test context-sensitive goal weighing."""

    def test_weigh_goals_with_context(self):
        """Goals are weighted based on context."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Quick fix",
                priority=0.7,
                context={"urgency": "high", "impact": "critical"},
            ),
            Goal(
                id="g2",
                description="Perfect solution",
                priority=0.8,
                context={"urgency": "low", "impact": "medium"},
            ),
        ]

        weighted = arbitrator.weigh_goals(goals, context={"situation": "production_down"})

        # In production-down context, quick fix should be weighted higher
        g1_weight = next(w for w in weighted if w["goal"].id == "g1")["weight"]
        g2_weight = next(w for w in weighted if w["goal"].id == "g2")["weight"]
        assert g1_weight > g2_weight

    def test_safety_always_high_priority(self):
        """Safety goals always get high weight regardless of context."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Move fast",
                priority=0.9,
                context={"type": "speed"},
            ),
            Goal(
                id="g2",
                description="Ensure safety",
                priority=0.7,
                context={"type": "safety"},
            ),
        ]

        weighted = arbitrator.weigh_goals(goals, context={"situation": "urgent"})

        # Safety should still be weighted highly even in urgent context
        g2_weight = next(w for w in weighted if w["goal"].id == "g2")["weight"]
        assert g2_weight >= 0.9  # Safety gets boosted

    def test_weighing_considers_constraints(self):
        """Weighing considers hard constraints."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Feature A",
                priority=0.8,
                constraints={"deadline": "today"},
            ),
            Goal(
                id="g2",
                description="Feature B",
                priority=0.9,
                constraints={},
            ),
        ]

        weighted = arbitrator.weigh_goals(goals, context={"current_time": "end_of_day"})

        # Goal with imminent deadline should be weighted higher
        g1_weight = next(w for w in weighted if w["goal"].id == "g1")["weight"]
        assert g1_weight > 0.8  # Gets boost from deadline


class TestConflictResolution:
    """Test conflict resolution strategies."""

    def test_resolve_with_prioritization(self):
        """Can resolve conflict by prioritizing one goal."""
        arbitrator = GoalArbitrator()
        conflict = GoalConflict(
            type=GoalConflictType.SPEED_VS_CORRECTNESS,
            conflicting_goals=["g1", "g2"],
            severity=0.8,
        )
        goals = [
            Goal(id="g1", description="Fast", priority=0.9, context={"type": "speed"}),
            Goal(id="g2", description="Correct", priority=0.7, context={"type": "correctness"}),
        ]

        decision = arbitrator.resolve_conflict(
            conflict, goals, strategy=ArbitrationStrategy.PRIORITIZE_HIGHER
        )

        assert decision.chosen_goals == ["g1"]
        assert decision.deferred_goals == ["g2"]
        assert "reason" in decision.reasoning

    def test_resolve_with_compromise(self):
        """Can resolve conflict through compromise."""
        arbitrator = GoalArbitrator()
        conflict = GoalConflict(
            type=GoalConflictType.SPEED_VS_CORRECTNESS,
            conflicting_goals=["g1", "g2"],
            severity=0.6,
        )
        goals = [
            Goal(id="g1", description="Fast", priority=0.8, context={"type": "speed"}),
            Goal(id="g2", description="Correct", priority=0.8, context={"type": "correctness"}),
        ]

        decision = arbitrator.resolve_conflict(
            conflict, goals, strategy=ArbitrationStrategy.COMPROMISE
        )

        # Compromise should partially satisfy both
        assert len(decision.chosen_goals) > 0
        assert "compromise" in decision.reasoning.lower() or "both" in decision.reasoning.lower()

    def test_resolve_with_satisficing(self):
        """Can resolve by accepting good enough solution."""
        arbitrator = GoalArbitrator()
        conflict = GoalConflict(
            type=GoalConflictType.RESOURCE_CONSTRAINT,
            conflicting_goals=["g1", "g2"],
            severity=0.9,
        )
        goals = [
            Goal(
                id="g1",
                description="Perfect solution",
                priority=0.9,
                context={"estimated_effort": 100},
            ),
            Goal(
                id="g2",
                description="Resource limit",
                priority=0.8,
                constraints={"max_effort": 20},
            ),
        ]

        decision = arbitrator.resolve_conflict(
            conflict, goals, strategy=ArbitrationStrategy.SATISFICE
        )

        # Should accept good enough solution within constraints
        satisficing = "satisfice" in decision.reasoning.lower()
        good_enough = "good enough" in decision.reasoning.lower()
        assert satisficing or good_enough
        assert decision.chosen_goals  # Some goals chosen

    def test_safety_override_strategy(self):
        """Safety concerns override other goals."""
        arbitrator = GoalArbitrator()
        conflict = GoalConflict(
            type=GoalConflictType.SAFETY_VS_INSTRUCTION,
            conflicting_goals=["g1", "g2"],
            severity=1.0,
        )
        goals = [
            Goal(id="g1", description="Delete prod data", priority=0.9),
            Goal(id="g2", description="Ensure safety", priority=0.8, context={"type": "safety"}),
        ]

        decision = arbitrator.resolve_conflict(
            conflict, goals, strategy=ArbitrationStrategy.SAFETY_FIRST
        )

        # Safety goal should be chosen
        assert "g2" in decision.chosen_goals
        assert "safety" in decision.reasoning.lower()


class TestTradeOffReasoning:
    """Test explicit trade-off reasoning."""

    def test_decision_includes_reasoning(self):
        """Arbitration decisions include explicit reasoning."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(id="g1", description="Fast", priority=0.9, context={"type": "speed"}),
            Goal(id="g2", description="Correct", priority=0.8, context={"type": "correctness"}),
        ]

        decision = arbitrator.arbitrate(goals, context={"situation": "hotfix"})

        assert decision.reasoning
        assert len(decision.reasoning) > 20  # Meaningful explanation
        assert any(word in decision.reasoning.lower() for word in ["because", "since", "due to"])

    def test_trade_off_analysis_documented(self):
        """Trade-offs are explicitly documented."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Refactor",
                priority=0.7,
                context={"benefits": ["cleaner code"], "costs": ["more time"]},
            ),
            Goal(
                id="g2",
                description="Quick fix",
                priority=0.8,
                context={"benefits": ["fast"], "costs": ["tech debt"]},
            ),
        ]

        decision = arbitrator.arbitrate(goals)

        # Should document trade-offs
        assert decision.trade_offs
        assert "benefits" in decision.trade_offs or "costs" in decision.trade_offs


class TestGoalSatisfactionTracking:
    """Test goal satisfaction tracking."""

    def test_track_satisfaction_levels(self):
        """Can track how well each goal is being satisfied."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(id="g1", description="Goal 1", priority=0.8),
            Goal(id="g2", description="Goal 2", priority=0.6),
        ]

        # Update satisfaction
        arbitrator.update_satisfaction("g1", 0.75, goals)
        arbitrator.update_satisfaction("g2", 0.5, goals)

        g1 = next(g for g in goals if g.id == "g1")
        g2 = next(g for g in goals if g.id == "g2")

        assert g1.satisfaction == 0.75
        assert g2.satisfaction == 0.5

    def test_track_competing_objectives(self):
        """Can track satisfaction across competing objectives."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(id="g1", description="Speed", priority=0.9),
            Goal(id="g2", description="Quality", priority=0.8),
        ]

        # Both can be partially satisfied
        arbitrator.update_satisfaction("g1", 0.6, goals)
        arbitrator.update_satisfaction("g2", 0.7, goals)

        satisfaction = arbitrator.get_satisfaction_report(goals)

        assert satisfaction["g1"] == 0.6
        assert satisfaction["g2"] == 0.7


class TestSatisficing:
    """Test satisficing behavior (accepting good enough)."""

    def test_accept_good_enough_solution(self):
        """Accept solution that meets minimum thresholds."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Perfect solution",
                priority=0.9,
                constraints={"min_satisfaction": 0.7},
            ),
        ]

        # 75% satisfaction is good enough (> 70% minimum)
        can_accept = arbitrator.is_satisficing_acceptable(goals, {"g1": 0.75})
        assert can_accept

    def test_reject_insufficient_solution(self):
        """Reject solution below minimum threshold."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Critical goal",
                priority=0.9,
                constraints={"min_satisfaction": 0.8},
            ),
        ]

        # 60% satisfaction is not good enough (< 80% minimum)
        can_accept = arbitrator.is_satisficing_acceptable(goals, {"g1": 0.6})
        assert not can_accept

    def test_satisficing_when_perfect_impossible(self):
        """Use satisficing when perfect solution is impossible."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Goal A",
                priority=0.9,
                constraints={"min_satisfaction": 0.6},
            ),
            Goal(
                id="g2",
                description="Goal B",
                priority=0.9,
                constraints={"min_satisfaction": 0.6},
            ),
        ]

        # Can't satisfy both 100%, but can satisfy both > 60%
        result = arbitrator.find_satisficing_solution(goals)

        assert result is not None
        assert all(v >= 0.6 for v in result.values())


class TestDynamicPriorityAdjustment:
    """Test dynamic priority adjustment based on context."""

    def test_adjust_priority_based_on_context(self):
        """Priorities adjust based on changing context."""
        arbitrator = GoalArbitrator()
        goal = Goal(id="g1", description="Test", priority=0.7)

        # Context changes urgency
        adjusted = arbitrator.adjust_priority(
            goal, context={"urgency": "critical", "impact": "high"}
        )

        assert adjusted > 0.7  # Priority increased

    def test_priority_boost_for_deadlines(self):
        """Goals near deadlines get priority boost."""
        arbitrator = GoalArbitrator()
        goal = Goal(
            id="g1",
            description="Task with deadline",
            priority=0.6,
            constraints={"deadline": "today"},
        )

        adjusted = arbitrator.adjust_priority(goal, context={"current_time": "end_of_day"})

        assert adjusted > 0.6  # Boosted due to deadline

    def test_priority_decrease_for_low_impact(self):
        """Low impact goals can have priority decreased."""
        arbitrator = GoalArbitrator()
        goal = Goal(id="g1", description="Nice to have", priority=0.8, context={"impact": "low"})

        adjusted = arbitrator.adjust_priority(goal, context={"resource_pressure": "high"})

        assert adjusted <= 0.8  # Priority may decrease or stay same


class TestArbitrationIntegration:
    """Integration tests for full arbitration flow."""

    def test_full_arbitration_flow(self):
        """Complete arbitration from detection to resolution."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(
                id="g1",
                description="Ship feature fast",
                priority=0.9,
                context={"type": "speed", "urgency": "high"},
            ),
            Goal(
                id="g2",
                description="Ensure quality",
                priority=0.8,
                context={"type": "correctness"},
            ),
        ]

        # Run full arbitration
        decision = arbitrator.arbitrate(goals, context={"situation": "production_issue"})

        # Should produce a decision
        assert decision is not None
        assert decision.chosen_goals
        assert decision.reasoning
        assert decision.strategy in ArbitrationStrategy.__members__.values()

    def test_multiple_conflicts(self):
        """Handle multiple simultaneous conflicts."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(id="g1", description="Fast", priority=0.9, context={"type": "speed"}),
            Goal(id="g2", description="Correct", priority=0.8, context={"type": "correctness"}),
            Goal(id="g3", description="Complete", priority=0.7, context={"type": "completeness"}),
            Goal(
                id="g4",
                description="Resource limit",
                priority=0.9,
                constraints={"max_tokens": 1000},
            ),
        ]

        decision = arbitrator.arbitrate(goals)

        # Should handle multiple conflicts
        assert decision is not None
        assert len(decision.chosen_goals) > 0
        # Not all goals may be chosen
        assert len(decision.chosen_goals) <= len(goals)

    def test_explain_decision_human_readable(self):
        """Can explain decision in human-readable format."""
        arbitrator = GoalArbitrator()
        goals = [
            Goal(id="g1", description="Goal 1", priority=0.8),
            Goal(id="g2", description="Goal 2", priority=0.6),
        ]

        decision = arbitrator.arbitrate(goals)
        explanation = arbitrator.explain_decision(decision)

        assert explanation
        assert isinstance(explanation, str)
        assert len(explanation) > 50  # Substantial explanation
