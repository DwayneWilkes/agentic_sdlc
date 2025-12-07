"""Tests for the recovery strategy engine."""

import time

from src.core.error_detection import ErrorContext, ErrorSeverity, ErrorType
from src.core.recovery_strategy import (
    CircuitBreaker,
    CircuitState,
    FallbackStrategy,
    GracefulDegradation,
    RecoveryStrategy,
    RecoveryStrategyEngine,
    RetryPolicy,
)
from src.models.agent import Agent, AgentCapability
from src.models.enums import TaskStatus, TaskType
from src.models.task import Subtask, Task


class TestRetryPolicy:
    """Test retry policy configurations and behavior."""

    def test_retry_policy_creation(self):
        """Test creating a retry policy with default values."""
        policy = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=60.0)
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.backoff_multiplier == 2.0  # default

    def test_retry_policy_with_custom_backoff(self):
        """Test retry policy with custom backoff multiplier."""
        policy = RetryPolicy(
            max_attempts=5, base_delay=0.5, max_delay=30.0, backoff_multiplier=3.0
        )
        assert policy.backoff_multiplier == 3.0

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, backoff_multiplier=2.0)

        # First retry: 1.0 * 2^0 = 1.0
        assert policy.calculate_delay(0) == 1.0

        # Second retry: 1.0 * 2^1 = 2.0
        assert policy.calculate_delay(1) == 2.0

        # Third retry: 1.0 * 2^2 = 4.0
        assert policy.calculate_delay(2) == 4.0

    def test_calculate_delay_respects_max_delay(self):
        """Test that delay calculation respects max_delay."""
        policy = RetryPolicy(max_attempts=10, base_delay=1.0, max_delay=10.0)

        # Should cap at max_delay
        delay = policy.calculate_delay(10)  # Would be 1024 without cap
        assert delay == 10.0

    def test_should_retry_within_max_attempts(self):
        """Test that retry is allowed within max attempts."""
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(0) is True
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False

    def test_should_retry_respects_error_severity(self):
        """Test that critical errors prevent retry."""
        policy = RetryPolicy(max_attempts=3)

        error = ErrorContext(
            error_type=ErrorType.CRASH,
            severity=ErrorSeverity.CRITICAL,
            message="Critical failure",
            agent_id="test-agent",
            task_id="test-task"
        )

        # Critical errors should not be retried
        assert policy.should_retry(0, error) is False

    def test_should_retry_allows_non_critical_errors(self):
        """Test that non-critical errors allow retry."""
        policy = RetryPolicy(max_attempts=3)

        error = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message="Timeout",
            agent_id="test-agent",
            task_id="test-task"
        )

        assert policy.should_retry(0, error) is True
        assert policy.should_retry(2, error) is True
        assert policy.should_retry(3, error) is False


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_creation(self):
        """Test creating a circuit breaker."""
        cb = CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout_seconds=60
        )
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_circuit_opens_after_threshold_failures(self):
        """Test that circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_allows_request_when_closed(self):
        """Test that requests are allowed when circuit is closed."""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.allow_request() is True

    def test_circuit_blocks_request_when_open(self):
        """Test that requests are blocked when circuit is open."""
        cb = CircuitBreaker(failure_threshold=1, timeout_seconds=60)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_circuit_enters_half_open_after_timeout(self):
        """Test that circuit enters half-open state after timeout."""
        cb = CircuitBreaker(failure_threshold=1, timeout_seconds=0.1)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)

        # Should enter half-open state
        assert cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_closes_after_success_threshold_in_half_open(self):
        """Test that circuit closes after success threshold in half-open."""
        cb = CircuitBreaker(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1
        )

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)
        cb.allow_request()  # Enter half-open

        # Record successes
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_reopens_on_failure_in_half_open(self):
        """Test that circuit reopens on failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, timeout_seconds=0.1)

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait and enter half-open
        time.sleep(0.15)
        cb.allow_request()
        assert cb.state == CircuitState.HALF_OPEN

        # Failure in half-open should reopen
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestFallbackStrategy:
    """Test fallback agent selection strategy."""

    def test_select_fallback_agent_by_capability(self):
        """Test selecting fallback agent based on capabilities."""
        failed_agent = Agent(
            id="agent-1",
            role="developer",
            capabilities=[
                AgentCapability(name="python", description="Python dev", tools=[])
            ]
        )

        available_agents = [
            Agent(
                id="agent-2",
                role="developer",
                capabilities=[
                    AgentCapability(name="python", description="Python dev", tools=[])
                ]
            ),
            Agent(
                id="agent-3",
                role="reviewer",
                capabilities=[
                    AgentCapability(name="review", description="Code review", tools=[])
                ]
            )
        ]

        strategy = FallbackStrategy()
        fallback = strategy.select_fallback_agent(
            failed_agent, available_agents, required_capabilities=["python"]
        )

        assert fallback is not None
        assert fallback.id == "agent-2"

    def test_select_fallback_agent_excludes_failed_agent(self):
        """Test that fallback selection excludes the failed agent."""
        failed_agent = Agent(
            id="agent-1",
            role="developer",
            capabilities=[
                AgentCapability(name="python", description="Python dev", tools=[])
            ]
        )

        available_agents = [
            failed_agent,  # Same agent
            Agent(
                id="agent-2",
                role="developer",
                capabilities=[
                    AgentCapability(name="python", description="Python dev", tools=[])
                ]
            )
        ]

        strategy = FallbackStrategy()
        fallback = strategy.select_fallback_agent(
            failed_agent, available_agents, required_capabilities=["python"]
        )

        assert fallback is not None
        assert fallback.id == "agent-2"

    def test_select_fallback_agent_returns_none_if_no_match(self):
        """Test that None is returned if no suitable fallback exists."""
        failed_agent = Agent(
            id="agent-1",
            role="developer",
            capabilities=[
                AgentCapability(name="python", description="Python dev", tools=[])
            ]
        )

        available_agents = [
            Agent(
                id="agent-2",
                role="reviewer",
                capabilities=[
                    AgentCapability(name="review", description="Code review", tools=[])
                ]
            )
        ]

        strategy = FallbackStrategy()
        fallback = strategy.select_fallback_agent(
            failed_agent, available_agents, required_capabilities=["python"]
        )

        assert fallback is None


class TestGracefulDegradation:
    """Test graceful degradation with partial results."""

    def test_create_partial_result_from_subtasks(self):
        """Test creating partial result from completed subtasks."""
        task = Task(
            id="task-1",
            description="Build feature",
            task_type=TaskType.SOFTWARE,
            subtasks=[
                Subtask(id="sub-1", description="Step 1", status=TaskStatus.COMPLETED),
                Subtask(id="sub-2", description="Step 2", status=TaskStatus.COMPLETED),
                Subtask(id="sub-3", description="Step 3", status=TaskStatus.FAILED),
                Subtask(id="sub-4", description="Step 4", status=TaskStatus.PENDING),
            ]
        )

        degradation = GracefulDegradation()
        result = degradation.create_partial_result(task)

        assert result.task_id == "task-1"
        assert result.completed_subtasks == ["sub-1", "sub-2"]
        assert result.failed_subtasks == ["sub-3"]
        assert result.pending_subtasks == ["sub-4"]
        assert result.completion_percentage == 50.0  # 2 out of 4

    def test_is_acceptable_partial_result(self):
        """Test determining if partial result meets minimum threshold."""
        task = Task(
            id="task-1",
            description="Build feature",
            task_type=TaskType.SOFTWARE,
            subtasks=[
                Subtask(id="sub-1", description="Step 1", status=TaskStatus.COMPLETED),
                Subtask(id="sub-2", description="Step 2", status=TaskStatus.COMPLETED),
                Subtask(id="sub-3", description="Step 3", status=TaskStatus.COMPLETED),
                Subtask(id="sub-4", description="Step 4", status=TaskStatus.FAILED),
            ]
        )

        degradation = GracefulDegradation()
        result = degradation.create_partial_result(task)

        # 75% completion should be acceptable with 60% threshold
        assert degradation.is_acceptable_partial_result(result, min_threshold=0.6) is True

        # 75% completion should not be acceptable with 80% threshold
        assert degradation.is_acceptable_partial_result(result, min_threshold=0.8) is False

    def test_partial_result_with_no_completed_subtasks(self):
        """Test partial result when no subtasks completed."""
        task = Task(
            id="task-1",
            description="Build feature",
            task_type=TaskType.SOFTWARE,
            subtasks=[
                Subtask(id="sub-1", description="Step 1", status=TaskStatus.FAILED),
                Subtask(id="sub-2", description="Step 2", status=TaskStatus.PENDING),
            ]
        )

        degradation = GracefulDegradation()
        result = degradation.create_partial_result(task)

        assert result.completion_percentage == 0.0
        assert result.completed_subtasks == []


class TestRecoveryStrategyEngine:
    """Test the recovery strategy engine integration."""

    def test_engine_creation_with_default_strategy(self):
        """Test creating engine with default recovery strategy."""
        engine = RecoveryStrategyEngine()
        assert engine.default_strategy == RecoveryStrategy.RETRY

    def test_select_recovery_strategy_for_timeout(self):
        """Test selecting retry strategy for timeout errors."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message="Request timeout",
            agent_id="agent-1",
            task_id="task-1"
        )

        strategy = engine.select_recovery_strategy(error)
        assert strategy == RecoveryStrategy.RETRY

    def test_select_recovery_strategy_for_invalid_output(self):
        """Test selecting fallback strategy for invalid output."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.INVALID_OUTPUT,
            severity=ErrorSeverity.HIGH,
            message="Output validation failed",
            agent_id="agent-1",
            task_id="task-1"
        )

        strategy = engine.select_recovery_strategy(error)
        assert strategy == RecoveryStrategy.FALLBACK_AGENT

    def test_select_recovery_strategy_for_critical_error(self):
        """Test selecting no recovery for critical errors."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.CRASH,
            severity=ErrorSeverity.CRITICAL,
            message="Fatal crash",
            agent_id="agent-1",
            task_id="task-1"
        )

        strategy = engine.select_recovery_strategy(error)
        assert strategy == RecoveryStrategy.NONE

    def test_select_recovery_strategy_for_partial_completion(self):
        """Test selecting degradation strategy for partial completion."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.PARTIAL_COMPLETION,
            severity=ErrorSeverity.MEDIUM,
            message="Partially completed",
            agent_id="agent-1",
            task_id="task-1"
        )

        strategy = engine.select_recovery_strategy(error)
        assert strategy == RecoveryStrategy.GRACEFUL_DEGRADATION

    def test_apply_recovery_with_retry(self):
        """Test applying retry recovery strategy."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message="Timeout",
            agent_id="agent-1",
            task_id="task-1"
        )

        task = Task(
            id="task-1",
            description="Test task",
            task_type=TaskType.SOFTWARE
        )

        result = engine.apply_recovery(
            error=error,
            task=task,
            strategy=RecoveryStrategy.RETRY
        )

        assert result.strategy == RecoveryStrategy.RETRY
        assert result.retry_count == 1
        assert result.should_retry is True

    def test_apply_recovery_respects_circuit_breaker(self):
        """Test that recovery respects circuit breaker state."""
        engine = RecoveryStrategyEngine()

        # Set up circuit breaker for this agent/task
        circuit_key = "agent-1:task-1"
        engine.circuit_breakers[circuit_key] = CircuitBreaker(failure_threshold=1)
        engine.circuit_breakers[circuit_key].record_failure()  # Open circuit

        error = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message="Timeout",
            agent_id="agent-1",
            task_id="task-1"
        )

        task = Task(
            id="task-1",
            description="Test task",
            task_type=TaskType.SOFTWARE
        )

        result = engine.apply_recovery(
            error=error,
            task=task,
            strategy=RecoveryStrategy.RETRY
        )

        # Circuit is open, should not retry
        assert result.should_retry is False
        assert result.circuit_breaker_blocked is True

    def test_apply_recovery_with_fallback_agent(self):
        """Test applying fallback agent recovery strategy."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.INVALID_OUTPUT,
            severity=ErrorSeverity.HIGH,
            message="Invalid output",
            agent_id="agent-1",
            task_id="task-1"
        )

        task = Task(
            id="task-1",
            description="Test task",
            task_type=TaskType.SOFTWARE
        )

        failed_agent = Agent(
            id="agent-1",
            role="developer",
            capabilities=[
                AgentCapability(name="python", description="Python dev", tools=[])
            ]
        )

        available_agents = [
            Agent(
                id="agent-2",
                role="developer",
                capabilities=[
                    AgentCapability(name="python", description="Python dev", tools=[])
                ]
            )
        ]

        result = engine.apply_recovery(
            error=error,
            task=task,
            strategy=RecoveryStrategy.FALLBACK_AGENT,
            failed_agent=failed_agent,
            available_agents=available_agents,
            required_capabilities=["python"]
        )

        assert result.strategy == RecoveryStrategy.FALLBACK_AGENT
        assert result.fallback_agent_id == "agent-2"

    def test_apply_recovery_with_graceful_degradation(self):
        """Test applying graceful degradation recovery strategy."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.PARTIAL_COMPLETION,
            severity=ErrorSeverity.MEDIUM,
            message="Partial completion",
            agent_id="agent-1",
            task_id="task-1"
        )

        task = Task(
            id="task-1",
            description="Test task",
            task_type=TaskType.SOFTWARE,
            subtasks=[
                Subtask(id="sub-1", description="Step 1", status=TaskStatus.COMPLETED),
                Subtask(id="sub-2", description="Step 2", status=TaskStatus.COMPLETED),
                Subtask(id="sub-3", description="Step 3", status=TaskStatus.FAILED),
            ]
        )

        result = engine.apply_recovery(
            error=error,
            task=task,
            strategy=RecoveryStrategy.GRACEFUL_DEGRADATION
        )

        assert result.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION
        assert result.partial_result is not None
        assert result.partial_result.completion_percentage > 0.0

    def test_recovery_history_tracking(self):
        """Test that recovery attempts are tracked in history."""
        engine = RecoveryStrategyEngine()

        error = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            message="Timeout",
            agent_id="agent-1",
            task_id="task-1"
        )

        task = Task(
            id="task-1",
            description="Test task",
            task_type=TaskType.SOFTWARE
        )

        # Apply recovery multiple times
        engine.apply_recovery(error=error, task=task, strategy=RecoveryStrategy.RETRY)
        engine.apply_recovery(error=error, task=task, strategy=RecoveryStrategy.RETRY)

        history = engine.get_recovery_history("task-1")
        assert len(history) == 2
        assert all(h.strategy == RecoveryStrategy.RETRY for h in history)
