"""
TokenManager - Phase 7.4

Manages token budgets, tracks usage per agent, and enforces conservation modes.

Features:
1. Session-level budget tracking
2. Per-agent token usage tracking
3. Automatic mode transitions (NORMAL → CONSERVATION → EMERGENCY)
4. Burn rate calculation and runway estimation
5. Budget enforcement (can_afford checks)
6. Thread-safe for concurrent updates
7. Mode change callbacks for external integration

Usage:
    manager = TokenManager(session_budget=1000000)

    # Record usage
    manager.record_usage("agent-1", tokens=50000)

    # Check budget
    if manager.can_afford(estimated_tokens):
        # Proceed with task
        pass

    # Monitor mode
    mode = manager.get_mode()
    if mode == ConservationMode.CONSERVATION:
        # Reduce context windows, concise responses
        pass
"""

import threading
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

from src.models.budget import (
    BudgetConstraints,
    ConservationMode,
    TokenBudget,
    TokenUsageSnapshot,
)


class TokenManager:
    """
    Manages token budgets and tracks usage per agent.

    Thread-safe implementation for concurrent agent updates.
    """

    def __init__(
        self,
        session_budget: int | None = None,
        constraints: BudgetConstraints | None = None,
    ):
        """
        Initialize token manager.

        Args:
            session_budget: Optional session budget (creates default constraints)
            constraints: Optional BudgetConstraints (takes precedence)
        """
        if constraints is not None:
            self._budget = TokenBudget.from_constraints(constraints)
        elif session_budget is not None:
            self._budget = TokenBudget(session_budget=session_budget)
        else:
            self._budget = TokenBudget()  # Default 1M tokens

        # Per-agent tracking
        self._agent_tokens: dict[str, int] = defaultdict(int)

        # Usage history for burn rate calculation
        self._usage_history: list[dict] = []

        # Mode change callbacks
        self._mode_callbacks: list[Callable[[ConservationMode, ConservationMode], None]] = []

        # Thread safety
        self._lock = threading.RLock()

        # Track current mode to detect transitions
        self._current_mode = ConservationMode.NORMAL

    @property
    def session_budget(self) -> int:
        """Get session budget."""
        return self._budget.session_budget

    def record_usage(self, agent_id: str, tokens: int) -> None:
        """
        Record token usage for an agent.

        Automatically triggers mode transitions if thresholds are crossed.

        Args:
            agent_id: Unique agent identifier
            tokens: Number of tokens consumed
        """
        with self._lock:
            # Record in budget
            old_mode = self._budget.mode
            self._budget.record_usage(tokens)
            new_mode = self._budget.mode

            # Update agent tracking
            self._agent_tokens[agent_id] += tokens

            # Record in history for burn rate
            self._usage_history.append(
                {
                    "agent_id": agent_id,
                    "tokens": tokens,
                    "timestamp": datetime.now(),
                }
            )

            # Trigger mode change callbacks if mode changed
            if old_mode != new_mode:
                self._current_mode = new_mode
                for callback in self._mode_callbacks:
                    try:
                        callback(old_mode, new_mode)
                    except Exception:
                        # Don't let callback errors break token tracking
                        pass

    def get_used_tokens(self) -> int:
        """Get total tokens used across all agents."""
        with self._lock:
            return self._budget.used

    def get_agent_tokens(self, agent_id: str) -> int:
        """
        Get tokens used by a specific agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Tokens used by this agent, or 0 if unknown
        """
        with self._lock:
            return self._agent_tokens.get(agent_id, 0)

    def can_afford(self, estimated_tokens: int) -> bool:
        """
        Check if budget can afford estimated tokens.

        Args:
            estimated_tokens: Number of tokens needed

        Returns:
            True if remaining budget >= estimated tokens
        """
        with self._lock:
            return self._budget.can_afford(estimated_tokens)

    def is_budget_exceeded(self) -> bool:
        """Check if budget has been exceeded (>= 100% used)."""
        with self._lock:
            return self._budget.is_exhausted

    def get_mode(self) -> ConservationMode:
        """Get current conservation mode."""
        with self._lock:
            return self._budget.mode

    def on_mode_change(
        self, callback: Callable[[ConservationMode, ConservationMode], None]
    ) -> None:
        """
        Register a callback for mode changes.

        Args:
            callback: Function called with (old_mode, new_mode) when mode changes
        """
        with self._lock:
            self._mode_callbacks.append(callback)

    def get_burn_rate(self) -> float:
        """
        Calculate token burn rate (tokens per hour).

        Uses recent usage history to estimate current consumption rate.

        Returns:
            Tokens per hour, or 0.0 if insufficient data
        """
        with self._lock:
            if len(self._usage_history) < 2:
                return 0.0

            # Calculate time span across all history
            oldest = min(entry["timestamp"] for entry in self._usage_history)
            newest = max(entry["timestamp"] for entry in self._usage_history)
            time_span = (newest - oldest).total_seconds() / 3600.0  # Hours

            if time_span == 0:
                return 0.0

            # Calculate tokens used in this span
            tokens_used: int = sum(entry["tokens"] for entry in self._usage_history)  # type: ignore[misc]

            return float(tokens_used) / time_span  # type: ignore[no-any-return]

    def estimate_runway(self) -> float | None:
        """
        Estimate remaining time (runway) in hours based on burn rate.

        Returns:
            Hours remaining, or None if burn rate is 0 or unknown
        """
        with self._lock:
            burn_rate = self.get_burn_rate()
            if burn_rate == 0:
                return None

            remaining = self._budget.remaining
            if remaining <= 0:
                return 0.0

            return remaining / burn_rate

    def snapshot(self) -> TokenUsageSnapshot:
        """
        Create an immutable snapshot of current token usage.

        Includes per-agent breakdown, burn rate, and runway.

        Returns:
            TokenUsageSnapshot with current state
        """
        with self._lock:
            return TokenUsageSnapshot(
                session_budget=self._budget.session_budget,
                used=self._budget.used,
                remaining=self._budget.remaining,
                percentage=self._budget.percentage,
                mode=self._budget.mode,
                by_agent=dict(self._agent_tokens),
                burn_rate=self.get_burn_rate(),
                estimated_runway=self.estimate_runway(),
            )


# =============================================================================
# Singleton and Convenience Functions
# =============================================================================

_token_manager_instance: TokenManager | None = None


def get_token_manager(
    session_budget: int | None = None,
    constraints: BudgetConstraints | None = None,
) -> TokenManager:
    """
    Get the singleton token manager instance.

    Args:
        session_budget: Optional session budget (only used on first call)
        constraints: Optional BudgetConstraints (only used on first call)

    Returns:
        Singleton TokenManager instance
    """
    global _token_manager_instance
    if _token_manager_instance is None:
        _token_manager_instance = TokenManager(
            session_budget=session_budget,
            constraints=constraints,
        )
    return _token_manager_instance


def record_token_usage(agent_id: str, tokens: int) -> None:
    """
    Convenience function to record token usage.

    Args:
        agent_id: Unique agent identifier
        tokens: Number of tokens consumed
    """
    get_token_manager().record_usage(agent_id, tokens)


def check_budget_affordability(estimated_tokens: int) -> bool:
    """
    Convenience function to check budget affordability.

    Args:
        estimated_tokens: Number of tokens needed

    Returns:
        True if budget can afford the tokens
    """
    return get_token_manager().can_afford(estimated_tokens)


def get_current_conservation_mode() -> ConservationMode:
    """
    Convenience function to get current conservation mode.

    Returns:
        Current ConservationMode
    """
    return get_token_manager().get_mode()
