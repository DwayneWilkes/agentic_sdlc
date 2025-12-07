"""Recovery strategy engine for handling agent and task failures.

This module provides comprehensive recovery mechanisms including retry policies,
circuit breakers, fallback agent selection, and graceful degradation to ensure
robust task execution and prevent cascading failures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.core.error_detection import ErrorContext, ErrorSeverity, ErrorType
from src.models.agent import Agent
from src.models.enums import TaskStatus
from src.models.task import Task


class RecoveryStrategy(str, Enum):
    """Types of recovery strategies available."""

    RETRY = "retry"
    FALLBACK_AGENT = "fallback_agent"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CIRCUIT_BREAKER = "circuit_breaker"
    NONE = "none"


class CircuitState(str, Enum):
    """States of a circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior.

    Implements exponential backoff with configurable max attempts and delays.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given retry attempt using exponential backoff."""
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)

    def should_retry(
        self, attempt: int, error: ErrorContext | None = None
    ) -> bool:
        """Determine if retry should be attempted."""
        # Never retry critical errors
        if error and error.severity == ErrorSeverity.CRITICAL:
            return False

        return attempt < self.max_attempts


@dataclass
class CircuitBreaker:
    """
    Circuit breaker to prevent resource exhaustion.

    Implements the circuit breaker pattern with three states: CLOSED, OPEN, HALF_OPEN.
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: datetime | None = None

    def allow_request(self) -> bool:
        """Check if a request should be allowed based on circuit state."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False

        # HALF_OPEN state: allow request to test recovery
        return True

    def record_failure(self) -> None:
        """Record a failure and update circuit state."""
        self.last_failure_time = datetime.now()
        self.failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open -> reopen circuit
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif self.failure_count >= self.failure_threshold:
            # Threshold exceeded -> open circuit
            self.state = CircuitState.OPEN

    def record_success(self) -> None:
        """Record a success and update circuit state."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                # Enough successes -> close circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout_seconds


@dataclass
class FallbackStrategy:
    """
    Strategy for selecting fallback agents when primary agent fails.
    """

    def select_fallback_agent(
        self,
        failed_agent: Agent,
        available_agents: list[Agent],
        required_capabilities: list[str] | None = None,
    ) -> Agent | None:
        """Select a fallback agent based on capabilities."""
        required_capabilities = required_capabilities or []

        for agent in available_agents:
            # Don't select the same agent that failed
            if agent.id == failed_agent.id:
                continue

            # Check if agent has required capabilities
            agent_capability_names = {cap.name for cap in agent.capabilities}

            if all(cap in agent_capability_names for cap in required_capabilities):
                return agent

        return None


@dataclass
class PartialResult:
    """
    Represents a partial result from graceful degradation.

    Captures what was completed, what failed, and what remains.
    """

    task_id: str
    completed_subtasks: list[str] = field(default_factory=list)
    failed_subtasks: list[str] = field(default_factory=list)
    pending_subtasks: list[str] = field(default_factory=list)
    completion_percentage: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GracefulDegradation:
    """
    Strategy for graceful degradation with partial results.

    Allows tasks to complete partially when full completion isn't possible.
    """

    def create_partial_result(self, task: Task) -> PartialResult:
        """Create a partial result from task state."""
        completed = []
        failed = []
        pending = []

        for subtask in task.subtasks:
            if subtask.status == TaskStatus.COMPLETED:
                completed.append(subtask.id)
            elif subtask.status == TaskStatus.FAILED:
                failed.append(subtask.id)
            else:
                pending.append(subtask.id)

        total = len(task.subtasks)
        completion_pct = (len(completed) / total * 100.0) if total > 0 else 0.0

        return PartialResult(
            task_id=task.id,
            completed_subtasks=completed,
            failed_subtasks=failed,
            pending_subtasks=pending,
            completion_percentage=completion_pct,
        )

    def is_acceptable_partial_result(
        self, partial_result: PartialResult, min_threshold: float = 0.5
    ) -> bool:
        """Determine if partial result meets minimum acceptable threshold."""
        return partial_result.completion_percentage >= (min_threshold * 100.0)


@dataclass
class RecoveryResult:
    """
    Result of applying a recovery strategy.

    Captures the recovery decision, actions taken, and outcome.
    """

    strategy: RecoveryStrategy
    success: bool = False
    retry_count: int = 0
    should_retry: bool = False
    circuit_breaker_blocked: bool = False
    fallback_agent_id: str | None = None
    partial_result: PartialResult | None = None
    error_context: ErrorContext | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class RecoveryStrategyEngine:
    """
    Main engine for applying recovery strategies.

    Coordinates retry logic, circuit breakers, fallback selection,
    and graceful degradation based on error context.
    """

    def __init__(
        self,
        default_strategy: RecoveryStrategy = RecoveryStrategy.RETRY,
        default_retry_policy: RetryPolicy | None = None,
    ):
        """Initialize the recovery strategy engine."""
        self.default_strategy = default_strategy
        self.default_retry_policy = default_retry_policy or RetryPolicy()
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.recovery_history: dict[str, list[RecoveryResult]] = {}
        self.retry_counts: dict[str, int] = {}

    def select_recovery_strategy(self, error: ErrorContext) -> RecoveryStrategy:
        """Select appropriate recovery strategy based on error context."""
        # Critical errors: no recovery
        if error.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.NONE

        # Strategy selection based on error type
        if error.error_type == ErrorType.TIMEOUT:
            return RecoveryStrategy.RETRY

        if error.error_type == ErrorType.INVALID_OUTPUT:
            return RecoveryStrategy.FALLBACK_AGENT

        if error.error_type == ErrorType.PARTIAL_COMPLETION:
            return RecoveryStrategy.GRACEFUL_DEGRADATION

        if error.error_type == ErrorType.CRASH:
            return RecoveryStrategy.FALLBACK_AGENT

        return self.default_strategy

    def apply_recovery(
        self,
        error: ErrorContext,
        task: Task,
        strategy: RecoveryStrategy | None = None,
        failed_agent: Agent | None = None,
        available_agents: list[Agent] | None = None,
        required_capabilities: list[str] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> RecoveryResult:
        """Apply the selected recovery strategy."""
        strategy = strategy or self.select_recovery_strategy(error)
        retry_policy = retry_policy or self.default_retry_policy

        result = RecoveryResult(strategy=strategy, error_context=error)

        # Track recovery attempt
        if task.id not in self.recovery_history:
            self.recovery_history[task.id] = []

        if strategy == RecoveryStrategy.RETRY:
            result = self._apply_retry(error, task, retry_policy, result)

        elif strategy == RecoveryStrategy.FALLBACK_AGENT:
            result = self._apply_fallback(
                error, task, failed_agent, available_agents, required_capabilities, result
            )

        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            result = self._apply_graceful_degradation(error, task, result)

        self.recovery_history[task.id].append(result)
        return result

    def _apply_retry(
        self,
        error: ErrorContext,
        task: Task,
        retry_policy: RetryPolicy,
        result: RecoveryResult,
    ) -> RecoveryResult:
        """Apply retry recovery strategy."""
        # Check circuit breaker
        circuit_key = f"{error.agent_id}:{error.task_id}"
        circuit = self._get_or_create_circuit_breaker(circuit_key)

        if not circuit.allow_request():
            result.circuit_breaker_blocked = True
            result.should_retry = False
            return result

        # Get current retry count
        retry_key = f"{error.agent_id}:{error.task_id}"
        current_retry = self.retry_counts.get(retry_key, 0)

        # Check if should retry
        if retry_policy.should_retry(current_retry, error):
            result.should_retry = True
            result.retry_count = current_retry + 1
            self.retry_counts[retry_key] = current_retry + 1
        else:
            result.should_retry = False

        return result

    def _apply_fallback(
        self,
        error: ErrorContext,
        task: Task,
        failed_agent: Agent | None,
        available_agents: list[Agent] | None,
        required_capabilities: list[str] | None,
        result: RecoveryResult,
    ) -> RecoveryResult:
        """Apply fallback agent recovery strategy."""
        if not failed_agent or not available_agents:
            result.success = False
            return result

        fallback_strategy = FallbackStrategy()
        fallback_agent = fallback_strategy.select_fallback_agent(
            failed_agent, available_agents, required_capabilities
        )

        if fallback_agent:
            result.fallback_agent_id = fallback_agent.id
            result.success = True
        else:
            result.success = False

        return result

    def _apply_graceful_degradation(
        self, error: ErrorContext, task: Task, result: RecoveryResult
    ) -> RecoveryResult:
        """Apply graceful degradation recovery strategy."""
        degradation = GracefulDegradation()
        partial_result = degradation.create_partial_result(task)

        result.partial_result = partial_result
        result.success = degradation.is_acceptable_partial_result(partial_result)

        return result

    def _get_or_create_circuit_breaker(self, key: str) -> CircuitBreaker:
        """Get or create a circuit breaker for the given key."""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker()
        return self.circuit_breakers[key]

    def get_recovery_history(self, task_id: str) -> list[RecoveryResult]:
        """Get recovery history for a task."""
        return self.recovery_history.get(task_id, [])

    def reset_circuit_breaker(self, agent_id: str, task_id: str) -> None:
        """Manually reset a circuit breaker."""
        key = f"{agent_id}:{task_id}"
        if key in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker()

    def get_circuit_breaker_state(
        self, agent_id: str, task_id: str
    ) -> CircuitState | None:
        """Get the current state of a circuit breaker."""
        key = f"{agent_id}:{task_id}"
        circuit = self.circuit_breakers.get(key)
        return circuit.state if circuit else None
