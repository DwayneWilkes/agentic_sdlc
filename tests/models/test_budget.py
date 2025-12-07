"""
Tests for budget data models - Phase 7.4

Tests for:
- BudgetConstraints
- TokenBudget
- ConservationMode
"""

import pytest

from src.models.budget import (
    BudgetConstraints,
    ConservationMode,
    TokenBudget,
    TokenUsageSnapshot,
)


class TestConservationMode:
    """Tests for ConservationMode enum."""

    def test_modes_exist(self) -> None:
        """Test that all required modes exist."""
        assert ConservationMode.NORMAL
        assert ConservationMode.CONSERVATION
        assert ConservationMode.EMERGENCY

    def test_mode_values(self) -> None:
        """Test mode string values."""
        assert ConservationMode.NORMAL.value == "normal"
        assert ConservationMode.CONSERVATION.value == "conservation"
        assert ConservationMode.EMERGENCY.value == "emergency"


class TestBudgetConstraints:
    """Tests for BudgetConstraints dataclass."""

    def test_create_default_constraints(self) -> None:
        """Test creating constraints with default values."""
        constraints = BudgetConstraints()
        assert constraints.session_budget > 0
        assert constraints.conservation_threshold == 0.80
        assert constraints.emergency_threshold == 0.95

    def test_create_custom_constraints(self) -> None:
        """Test creating constraints with custom values."""
        constraints = BudgetConstraints(
            session_budget=500000,
            conservation_threshold=0.75,
            emergency_threshold=0.90,
        )
        assert constraints.session_budget == 500000
        assert constraints.conservation_threshold == 0.75
        assert constraints.emergency_threshold == 0.90

    def test_invalid_threshold_order(self) -> None:
        """Test that emergency threshold must be > conservation threshold."""
        with pytest.raises(ValueError, match="emergency_threshold.*conservation_threshold"):
            BudgetConstraints(
                session_budget=1000000,
                conservation_threshold=0.90,
                emergency_threshold=0.80,
            )

    def test_threshold_out_of_range(self) -> None:
        """Test that thresholds must be between 0 and 1."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            BudgetConstraints(conservation_threshold=1.5)

        with pytest.raises(ValueError, match="between 0 and 1"):
            BudgetConstraints(emergency_threshold=-0.1)

    def test_negative_budget(self) -> None:
        """Test that session budget must be positive."""
        with pytest.raises(ValueError, match="positive"):
            BudgetConstraints(session_budget=-1000)


class TestTokenBudget:
    """Tests for TokenBudget class."""

    def test_initialize_budget(self) -> None:
        """Test budget initialization."""
        budget = TokenBudget(session_budget=1000000)
        assert budget.session_budget == 1000000
        assert budget.used == 0
        assert budget.remaining == 1000000
        assert budget.percentage == 0.0
        assert budget.mode == ConservationMode.NORMAL

    def test_record_usage(self) -> None:
        """Test recording token usage."""
        budget = TokenBudget(session_budget=1000000)
        budget.record_usage(100000)
        assert budget.used == 100000
        assert budget.remaining == 900000
        assert budget.percentage == 10.0
        assert budget.mode == ConservationMode.NORMAL

    def test_record_multiple_usage(self) -> None:
        """Test recording multiple token usages."""
        budget = TokenBudget(session_budget=1000000)
        budget.record_usage(100000)
        budget.record_usage(200000)
        budget.record_usage(50000)
        assert budget.used == 350000
        assert budget.remaining == 650000
        assert budget.percentage == 35.0

    def test_mode_transition_to_conservation(self) -> None:
        """Test mode transition from NORMAL to CONSERVATION."""
        constraints = BudgetConstraints(
            session_budget=1000000,
            conservation_threshold=0.80,
            emergency_threshold=0.95,
        )
        budget = TokenBudget.from_constraints(constraints)

        # Use 80% of budget
        budget.record_usage(800000)
        assert budget.percentage == 80.0
        assert budget.mode == ConservationMode.CONSERVATION

    def test_mode_transition_to_emergency(self) -> None:
        """Test mode transition from CONSERVATION to EMERGENCY."""
        constraints = BudgetConstraints(
            session_budget=1000000,
            conservation_threshold=0.80,
            emergency_threshold=0.95,
        )
        budget = TokenBudget.from_constraints(constraints)

        # Use 95% of budget
        budget.record_usage(950000)
        assert budget.percentage == 95.0
        assert budget.mode == ConservationMode.EMERGENCY

    def test_mode_stays_normal_below_threshold(self) -> None:
        """Test mode stays NORMAL below conservation threshold."""
        constraints = BudgetConstraints(
            session_budget=1000000,
            conservation_threshold=0.80,
        )
        budget = TokenBudget.from_constraints(constraints)

        budget.record_usage(700000)  # 70%
        assert budget.mode == ConservationMode.NORMAL

    def test_budget_exhausted(self) -> None:
        """Test handling budget exhaustion."""
        budget = TokenBudget(session_budget=1000000)
        budget.record_usage(1000000)
        assert budget.remaining == 0
        assert budget.percentage == 100.0
        assert budget.is_exhausted

    def test_budget_over_limit(self) -> None:
        """Test recording usage beyond budget."""
        budget = TokenBudget(session_budget=1000000)
        budget.record_usage(1100000)
        assert budget.used == 1100000
        assert budget.remaining == -100000
        assert abs(budget.percentage - 110.0) < 0.01  # Float precision tolerance
        assert budget.is_exhausted

    def test_can_afford(self) -> None:
        """Test checking if budget can afford estimated tokens."""
        budget = TokenBudget(session_budget=1000000)
        budget.record_usage(700000)  # 700k used, 300k remaining

        assert budget.can_afford(200000) is True
        assert budget.can_afford(300000) is True
        assert budget.can_afford(400000) is False

    def test_snapshot(self) -> None:
        """Test creating usage snapshot."""
        budget = TokenBudget(session_budget=1000000)
        budget.record_usage(400000)

        snapshot = budget.snapshot()
        assert isinstance(snapshot, TokenUsageSnapshot)
        assert snapshot.session_budget == 1000000
        assert snapshot.used == 400000
        assert snapshot.remaining == 600000
        assert snapshot.percentage == 40.0
        assert snapshot.mode == ConservationMode.NORMAL


class TestTokenUsageSnapshot:
    """Tests for TokenUsageSnapshot dataclass."""

    def test_create_snapshot(self) -> None:
        """Test creating a usage snapshot."""
        snapshot = TokenUsageSnapshot(
            session_budget=1000000,
            used=600000,
            remaining=400000,
            percentage=60.0,
            mode=ConservationMode.NORMAL,
            by_agent={"agent-1": 400000, "agent-2": 200000},
        )
        assert snapshot.session_budget == 1000000
        assert snapshot.used == 600000
        assert snapshot.percentage == 60.0
        assert snapshot.by_agent == {"agent-1": 400000, "agent-2": 200000}

    def test_snapshot_json_serializable(self) -> None:
        """Test that snapshot can be converted to dict."""
        snapshot = TokenUsageSnapshot(
            session_budget=1000000,
            used=600000,
            remaining=400000,
            percentage=60.0,
            mode=ConservationMode.NORMAL,
        )
        # Should be able to convert to dict
        import dataclasses

        data = dataclasses.asdict(snapshot)
        assert data["session_budget"] == 1000000
        assert data["used"] == 600000
