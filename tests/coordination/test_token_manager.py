"""
Tests for TokenManager - Phase 7.4

Tests for:
- Token budget initialization
- Agent token tracking
- Budget enforcement
- Mode transitions
- Burn rate and runway calculation
- Emergency procedures
- Thread safety
"""

import threading
from datetime import datetime, timedelta

from src.coordination.token_manager import TokenManager, get_token_manager
from src.models.budget import BudgetConstraints, ConservationMode


class TestTokenManagerInitialization:
    """Tests for TokenManager initialization."""

    def test_create_with_default_budget(self) -> None:
        """Test creating TokenManager with default budget."""
        manager = TokenManager()
        assert manager.session_budget > 0
        assert manager.get_used_tokens() == 0
        assert manager.get_mode() == ConservationMode.NORMAL

    def test_create_with_constraints(self) -> None:
        """Test creating TokenManager with custom constraints."""
        constraints = BudgetConstraints(
            session_budget=500000,
            conservation_threshold=0.75,
            emergency_threshold=0.90,
        )
        manager = TokenManager(constraints=constraints)
        assert manager.session_budget == 500000

    def test_create_with_session_budget(self) -> None:
        """Test creating TokenManager with just session budget."""
        manager = TokenManager(session_budget=800000)
        assert manager.session_budget == 800000


class TestTokenTracking:
    """Tests for token usage tracking."""

    def test_record_agent_usage(self) -> None:
        """Test recording token usage for an agent."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=50000)

        assert manager.get_used_tokens() == 50000
        assert manager.get_agent_tokens("agent-1") == 50000

    def test_record_multiple_agents(self) -> None:
        """Test recording tokens for multiple agents."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=50000)
        manager.record_usage("agent-2", tokens=30000)
        manager.record_usage("agent-3", tokens=20000)

        assert manager.get_used_tokens() == 100000
        assert manager.get_agent_tokens("agent-1") == 50000
        assert manager.get_agent_tokens("agent-2") == 30000
        assert manager.get_agent_tokens("agent-3") == 20000

    def test_record_multiple_usage_same_agent(self) -> None:
        """Test recording multiple usages for the same agent."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=50000)
        manager.record_usage("agent-1", tokens=30000)
        manager.record_usage("agent-1", tokens=20000)

        assert manager.get_used_tokens() == 100000
        assert manager.get_agent_tokens("agent-1") == 100000

    def test_get_agent_tokens_unknown_agent(self) -> None:
        """Test getting tokens for unknown agent returns 0."""
        manager = TokenManager(session_budget=1000000)
        assert manager.get_agent_tokens("unknown") == 0


class TestBudgetEnforcement:
    """Tests for budget enforcement."""

    def test_can_afford_within_budget(self) -> None:
        """Test checking affordability within budget."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=300000)

        assert manager.can_afford(500000) is True
        assert manager.can_afford(700000) is True

    def test_cannot_afford_over_budget(self) -> None:
        """Test checking affordability when over budget."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=800000)

        assert manager.can_afford(300000) is False

    def test_budget_exceeded(self) -> None:
        """Test detecting when budget is exceeded."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=1100000)

        assert manager.is_budget_exceeded() is True

    def test_budget_not_exceeded(self) -> None:
        """Test detecting when budget is not exceeded."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=500000)

        assert manager.is_budget_exceeded() is False


class TestModeTransitions:
    """Tests for conservation mode transitions."""

    def test_normal_mode_initially(self) -> None:
        """Test that manager starts in NORMAL mode."""
        manager = TokenManager(session_budget=1000000)
        assert manager.get_mode() == ConservationMode.NORMAL

    def test_transition_to_conservation_mode(self) -> None:
        """Test transition from NORMAL to CONSERVATION at 80%."""
        constraints = BudgetConstraints(
            session_budget=1000000,
            conservation_threshold=0.80,
        )
        manager = TokenManager(constraints=constraints)

        # Use 79% - should stay NORMAL
        manager.record_usage("agent-1", tokens=790000)
        assert manager.get_mode() == ConservationMode.NORMAL

        # Use 1% more to hit 80% - should transition to CONSERVATION
        manager.record_usage("agent-1", tokens=10000)
        assert manager.get_mode() == ConservationMode.CONSERVATION

    def test_transition_to_emergency_mode(self) -> None:
        """Test transition from CONSERVATION to EMERGENCY at 95%."""
        constraints = BudgetConstraints(
            session_budget=1000000,
            conservation_threshold=0.80,
            emergency_threshold=0.95,
        )
        manager = TokenManager(constraints=constraints)

        # Use 94% - should be CONSERVATION
        manager.record_usage("agent-1", tokens=940000)
        assert manager.get_mode() == ConservationMode.CONSERVATION

        # Use 1% more to hit 95% - should transition to EMERGENCY
        manager.record_usage("agent-1", tokens=10000)
        assert manager.get_mode() == ConservationMode.EMERGENCY

    def test_mode_change_callback(self) -> None:
        """Test that mode change callback is triggered."""
        manager = TokenManager(session_budget=1000000)
        modes_entered = []

        def callback(old_mode: ConservationMode, new_mode: ConservationMode) -> None:
            modes_entered.append((old_mode, new_mode))

        manager.on_mode_change(callback)

        # Trigger CONSERVATION mode
        manager.record_usage("agent-1", tokens=800000)
        assert (ConservationMode.NORMAL, ConservationMode.CONSERVATION) in modes_entered

        # Trigger EMERGENCY mode
        manager.record_usage("agent-1", tokens=150000)
        assert (ConservationMode.CONSERVATION, ConservationMode.EMERGENCY) in modes_entered


class TestBurnRateAndRunway:
    """Tests for burn rate and runway estimation."""

    def test_burn_rate_with_no_history(self) -> None:
        """Test burn rate when no usage history exists."""
        manager = TokenManager(session_budget=1000000)
        burn_rate = manager.get_burn_rate()
        assert burn_rate == 0.0

    def test_burn_rate_calculation(self) -> None:
        """Test burn rate calculation from usage history."""
        manager = TokenManager(session_budget=1000000)

        # Record usage over time
        manager.record_usage("agent-1", tokens=100000)  # t=0
        manager._usage_history[-1]["timestamp"] = datetime.now() - timedelta(hours=1)

        manager.record_usage("agent-2", tokens=50000)  # t=1hr

        # Burn rate should be ~150k tokens/hour
        burn_rate = manager.get_burn_rate()
        assert burn_rate > 0

    def test_runway_estimation(self) -> None:
        """Test estimating remaining time (runway) based on burn rate."""
        manager = TokenManager(session_budget=1000000)

        # Simulate usage: 200k tokens over 1 hour = 200k/hr burn rate
        manager.record_usage("agent-1", tokens=100000)
        manager._usage_history[-1]["timestamp"] = datetime.now() - timedelta(hours=1)

        manager.record_usage("agent-2", tokens=100000)  # Second entry at t=now

        # 800k remaining / 200k per hour = 4 hours runway
        runway = manager.estimate_runway()
        assert runway is not None
        assert runway > 0

    def test_runway_when_no_burn_rate(self) -> None:
        """Test runway estimation when burn rate is 0."""
        manager = TokenManager(session_budget=1000000)
        runway = manager.estimate_runway()
        assert runway is None  # Can't estimate without usage data


class TestSnapshot:
    """Tests for token usage snapshots."""

    def test_create_snapshot(self) -> None:
        """Test creating a usage snapshot."""
        manager = TokenManager(session_budget=1000000)
        manager.record_usage("agent-1", tokens=400000)
        manager.record_usage("agent-2", tokens=200000)

        snapshot = manager.snapshot()
        assert snapshot.session_budget == 1000000
        assert snapshot.used == 600000
        assert snapshot.remaining == 400000
        assert snapshot.percentage == 60.0
        assert snapshot.mode == ConservationMode.NORMAL
        assert snapshot.by_agent["agent-1"] == 400000
        assert snapshot.by_agent["agent-2"] == 200000


class TestThreadSafety:
    """Tests for thread safety of TokenManager."""

    def test_concurrent_recording(self) -> None:
        """Test that concurrent token recording is thread-safe."""
        manager = TokenManager(session_budget=10000000)
        num_threads = 10
        tokens_per_thread = 10000
        iterations = 100

        def record_tokens(agent_id: str) -> None:
            for _ in range(iterations):
                manager.record_usage(agent_id, tokens=tokens_per_thread)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=record_tokens, args=(f"agent-{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Total should be: num_threads * iterations * tokens_per_thread
        expected_total = num_threads * iterations * tokens_per_thread
        assert manager.get_used_tokens() == expected_total


class TestSingletonAccess:
    """Tests for singleton access to TokenManager."""

    def test_get_singleton(self) -> None:
        """Test getting singleton TokenManager instance."""
        manager1 = get_token_manager()
        manager2 = get_token_manager()
        assert manager1 is manager2

    def test_singleton_persists_data(self) -> None:
        """Test that singleton persists data across calls."""
        manager1 = get_token_manager()
        manager1.record_usage("agent-1", tokens=50000)

        manager2 = get_token_manager()
        assert manager2.get_used_tokens() == 50000
