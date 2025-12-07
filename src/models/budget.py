"""
Budget Data Models - Phase 7.4

Data models for token budget tracking and conservation modes.

Models:
- ConservationMode: Enum for budget conservation states
- BudgetConstraints: Configuration for budget limits and thresholds
- TokenBudget: Tracks token usage and manages conservation modes
- TokenUsageSnapshot: Immutable snapshot of token usage at a point in time
"""

from dataclasses import dataclass, field
from enum import Enum


class ConservationMode(str, Enum):
    """
    Token conservation modes based on budget usage.

    NORMAL: 0-79% budget used - full functionality
    CONSERVATION: 80-95% budget used - reduced context, concise responses
    EMERGENCY: 95-100% budget used - checkpoint and shutdown
    """

    NORMAL = "normal"
    CONSERVATION = "conservation"
    EMERGENCY = "emergency"


@dataclass
class BudgetConstraints:
    """
    Configuration for token budget constraints.

    Defines the session budget and thresholds for mode transitions.
    """

    session_budget: int = 1000000  # Total tokens allowed for session
    conservation_threshold: float = 0.80  # Enter conservation mode at 80%
    emergency_threshold: float = 0.95  # Enter emergency mode at 95%

    def __post_init__(self) -> None:
        """Validate constraints."""
        if self.session_budget <= 0:
            raise ValueError("session_budget must be positive")

        if not (0 <= self.conservation_threshold <= 1):
            raise ValueError("conservation_threshold must be between 0 and 1")

        if not (0 <= self.emergency_threshold <= 1):
            raise ValueError("emergency_threshold must be between 0 and 1")

        if self.emergency_threshold <= self.conservation_threshold:
            raise ValueError(
                "emergency_threshold must be greater than conservation_threshold"
            )


@dataclass
class TokenUsageSnapshot:
    """
    Immutable snapshot of token usage at a point in time.

    Used for reporting and monitoring.
    """

    session_budget: int
    used: int
    remaining: int
    percentage: float
    mode: ConservationMode
    by_agent: dict[str, int] = field(default_factory=dict)
    burn_rate: float | None = None  # Tokens per hour
    estimated_runway: float | None = None  # Hours remaining


class TokenBudget:
    """
    Tracks token usage and manages conservation modes.

    Thread-safe token budget tracking with automatic mode transitions.
    """

    def __init__(
        self,
        session_budget: int = 1000000,
        conservation_threshold: float = 0.80,
        emergency_threshold: float = 0.95,
    ):
        """
        Initialize token budget.

        Args:
            session_budget: Total tokens allowed
            conservation_threshold: Percentage to enter conservation mode
            emergency_threshold: Percentage to enter emergency mode
        """
        self.constraints = BudgetConstraints(
            session_budget=session_budget,
            conservation_threshold=conservation_threshold,
            emergency_threshold=emergency_threshold,
        )
        self._used = 0

    @classmethod
    def from_constraints(cls, constraints: BudgetConstraints) -> "TokenBudget":
        """Create TokenBudget from constraints."""
        return cls(
            session_budget=constraints.session_budget,
            conservation_threshold=constraints.conservation_threshold,
            emergency_threshold=constraints.emergency_threshold,
        )

    @property
    def session_budget(self) -> int:
        """Get session budget."""
        return self.constraints.session_budget

    @property
    def used(self) -> int:
        """Get tokens used."""
        return self._used

    @property
    def remaining(self) -> int:
        """Get tokens remaining."""
        return self.session_budget - self._used

    @property
    def percentage(self) -> float:
        """Get percentage of budget used."""
        if self.session_budget == 0:
            return 0.0
        return (self._used / self.session_budget) * 100.0

    @property
    def mode(self) -> ConservationMode:
        """Get current conservation mode based on usage."""
        usage_ratio = self._used / self.session_budget if self.session_budget > 0 else 0

        if usage_ratio >= self.constraints.emergency_threshold:
            return ConservationMode.EMERGENCY
        elif usage_ratio >= self.constraints.conservation_threshold:
            return ConservationMode.CONSERVATION
        else:
            return ConservationMode.NORMAL

    @property
    def is_exhausted(self) -> bool:
        """Check if budget is exhausted (>= 100% used)."""
        return self._used >= self.session_budget

    def record_usage(self, tokens: int) -> None:
        """
        Record token usage.

        Args:
            tokens: Number of tokens to record
        """
        self._used += tokens

    def can_afford(self, estimated_tokens: int) -> bool:
        """
        Check if budget can afford estimated tokens.

        Args:
            estimated_tokens: Number of tokens needed

        Returns:
            True if remaining budget >= estimated tokens
        """
        return self.remaining >= estimated_tokens

    def snapshot(self) -> TokenUsageSnapshot:
        """
        Create an immutable snapshot of current usage.

        Returns:
            TokenUsageSnapshot with current state
        """
        return TokenUsageSnapshot(
            session_budget=self.session_budget,
            used=self.used,
            remaining=self.remaining,
            percentage=self.percentage,
            mode=self.mode,
        )
