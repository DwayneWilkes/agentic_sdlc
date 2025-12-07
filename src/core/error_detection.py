"""Error detection framework for the orchestrator system.

This module provides comprehensive error detection, classification, and validation
capabilities to prevent silent failures and ensure robust agent execution.
"""

import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorType(str, Enum):
    """Types of errors that can occur during agent execution."""

    CRASH = "crash"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"
    PARTIAL_COMPLETION = "partial_completion"
    VALIDATION_FAILURE = "validation_failure"


class ErrorSeverity(int, Enum):
    """Severity levels for errors (higher values = more severe)."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ErrorContext:
    """
    Captures comprehensive context about an error.

    This includes error classification, affected agent/task, timing,
    and detailed diagnostic information.
    """

    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    agent_id: str
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FailureDetector:
    """
    Detects and classifies failures during agent execution.

    Provides detection hooks for crashes, timeouts, invalid outputs,
    and partial completions. Maintains error history to prevent silent failures.
    """

    def __init__(self) -> None:
        """Initialize the failure detector."""
        self._error_history: list[ErrorContext] = []

    def detect_crash(
        self,
        func: Callable[[], Any],
        agent_id: str,
        task_id: str,
    ) -> ErrorContext | None:
        """
        Detect crash errors by executing a function and catching exceptions.

        Args:
            func: Function to execute
            agent_id: ID of the agent executing the function
            task_id: ID of the task being executed

        Returns:
            ErrorContext if a crash occurred, None if successful
        """
        try:
            func()
            return None
        except Exception as e:
            error = ErrorContext(
                error_type=ErrorType.CRASH,
                severity=ErrorSeverity.CRITICAL,
                message=f"Crash detected: {type(e).__name__}: {str(e)}",
                agent_id=agent_id,
                task_id=task_id,
                stack_trace=traceback.format_exc(),
                metadata={"exception_type": type(e).__name__},
            )
            self._error_history.append(error)
            return error

    def detect_timeout(
        self,
        func: Callable[[], Any],
        timeout_seconds: float,
        agent_id: str,
        task_id: str,
    ) -> ErrorContext | None:
        """
        Detect timeout errors by executing a function with a time limit.

        Args:
            func: Function to execute
            timeout_seconds: Maximum allowed execution time
            agent_id: ID of the agent executing the function
            task_id: ID of the task being executed

        Returns:
            ErrorContext if a timeout occurred, None if completed in time
        """
        import signal
        from types import FrameType

        def timeout_handler(_signum: int, _frame: FrameType | None) -> None:
            raise TimeoutError(f"Operation exceeded {timeout_seconds}s timeout")

        # Set up the timeout signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_seconds)

        try:
            func()
            signal.setitimer(signal.ITIMER_REAL, 0)  # Cancel the timer
            return None
        except TimeoutError:
            error = ErrorContext(
                error_type=ErrorType.TIMEOUT,
                severity=ErrorSeverity.HIGH,
                message=f"Timeout after {timeout_seconds}s",
                agent_id=agent_id,
                task_id=task_id,
                metadata={"timeout_seconds": timeout_seconds},
            )
            self._error_history.append(error)
            signal.setitimer(signal.ITIMER_REAL, 0)  # Cancel the timer
            return error
        except Exception:
            # Cancel timer and re-raise non-timeout exceptions
            signal.setitimer(signal.ITIMER_REAL, 0)
            raise

    def detect_invalid_output(
        self,
        output: Any,
        agent_id: str,
        task_id: str,
        expected_type: type | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ErrorContext | None:
        """
        Detect invalid output based on type or schema validation.

        Args:
            output: The output to validate
            agent_id: ID of the agent that produced the output
            task_id: ID of the task
            expected_type: Expected output type (optional)
            schema: Schema to validate against (optional)

        Returns:
            ErrorContext if output is invalid, None if valid
        """
        # Type validation
        if expected_type is not None and not isinstance(output, expected_type):
            error = ErrorContext(
                error_type=ErrorType.INVALID_OUTPUT,
                severity=ErrorSeverity.MEDIUM,
                message=f"Invalid output type: expected {expected_type.__name__}, "
                f"got {type(output).__name__}",
                agent_id=agent_id,
                task_id=task_id,
                metadata={
                    "expected_type": expected_type.__name__,
                    "actual_type": type(output).__name__,
                },
            )
            self._error_history.append(error)
            return error

        # Schema validation
        if schema is not None:
            required_fields = schema.get("required_fields", [])
            if isinstance(output, dict):
                missing_fields = [f for f in required_fields if f not in output]
                if missing_fields:
                    error = ErrorContext(
                        error_type=ErrorType.INVALID_OUTPUT,
                        severity=ErrorSeverity.MEDIUM,
                        message=f"Missing required fields: {missing_fields}",
                        agent_id=agent_id,
                        task_id=task_id,
                        metadata={"missing_fields": missing_fields},
                    )
                    self._error_history.append(error)
                    return error

        return None

    def detect_partial_completion(
        self,
        completed_items: list[str],
        required_items: list[str],
        agent_id: str,
        task_id: str,
    ) -> ErrorContext | None:
        """
        Detect partial completion when not all required items are completed.

        Args:
            completed_items: List of completed item IDs
            required_items: List of all required item IDs
            agent_id: ID of the agent
            task_id: ID of the task

        Returns:
            ErrorContext if only partially complete, None if fully complete
        """
        completed_set = set(completed_items)
        required_set = set(required_items)

        if completed_set == required_set:
            return None

        missing_items = required_set - completed_set
        completion_rate = len(completed_set) / len(required_set) if required_set else 0

        error = ErrorContext(
            error_type=ErrorType.PARTIAL_COMPLETION,
            severity=ErrorSeverity.MEDIUM,
            message=f"Partial completion: {len(completed_items)} of "
            f"{len(required_items)} items completed ({completion_rate:.0%})",
            agent_id=agent_id,
            task_id=task_id,
            metadata={
                "completed_items": completed_items,
                "missing_items": list(missing_items),
                "completion_rate": completion_rate,
            },
        )
        self._error_history.append(error)
        return error

    def get_error_history(
        self,
        agent_id: str | None = None,
        task_id: str | None = None,
        error_type: ErrorType | None = None,
    ) -> list[ErrorContext]:
        """
        Retrieve error history with optional filtering.

        Args:
            agent_id: Filter by agent ID (optional)
            task_id: Filter by task ID (optional)
            error_type: Filter by error type (optional)

        Returns:
            List of ErrorContext objects matching the filters
        """
        errors = self._error_history

        if agent_id is not None:
            errors = [e for e in errors if e.agent_id == agent_id]

        if task_id is not None:
            errors = [e for e in errors if e.task_id == task_id]

        if error_type is not None:
            errors = [e for e in errors if e.error_type == error_type]

        return errors


@dataclass
class ValidationRule:
    """
    Defines a validation rule for output checking.

    Each rule has a name, description, validator function, and severity level.
    """

    name: str
    description: str
    validator: Callable[[Any], bool]
    severity: ErrorSeverity = ErrorSeverity.MEDIUM


class OutputValidator:
    """
    Validates agent outputs against rules and success criteria.

    Provides flexible validation through custom rules and schema-based checking.
    Maintains validation history to ensure no silent failures.
    """

    def __init__(self) -> None:
        """Initialize the output validator."""
        self.rules: list[ValidationRule] = []
        self._validation_history: list[ErrorContext] = []

    def add_rule(self, rule: ValidationRule) -> None:
        """
        Add a validation rule.

        Args:
            rule: The validation rule to add
        """
        self.rules.append(rule)

    def validate(
        self,
        output: Any,
        agent_id: str,
        task_id: str,
    ) -> ErrorContext | None:
        """
        Validate output against all registered rules.

        Args:
            output: The output to validate
            agent_id: ID of the agent that produced the output
            task_id: ID of the task

        Returns:
            ErrorContext if validation fails, None if all rules pass
        """
        for rule in self.rules:
            try:
                if not rule.validator(output):
                    error = ErrorContext(
                        error_type=ErrorType.VALIDATION_FAILURE,
                        severity=rule.severity,
                        message=f"Validation failed: {rule.name} - {rule.description}",
                        agent_id=agent_id,
                        task_id=task_id,
                        metadata={"rule_name": rule.name},
                    )
                    self._validation_history.append(error)
                    return error
            except Exception as e:
                # Validator itself raised an exception
                error = ErrorContext(
                    error_type=ErrorType.VALIDATION_FAILURE,
                    severity=ErrorSeverity.HIGH,
                    message=f"Validator {rule.name} raised exception: {str(e)}",
                    agent_id=agent_id,
                    task_id=task_id,
                    metadata={"rule_name": rule.name, "exception": str(e)},
                )
                self._validation_history.append(error)
                return error

        return None

    def validate_against_criteria(
        self,
        output: Any,
        success_criteria: dict[str, Any],
        agent_id: str,
        task_id: str,
    ) -> ErrorContext | None:
        """
        Validate output against task success criteria.

        Args:
            output: The output to validate
            success_criteria: Dictionary defining success criteria
            agent_id: ID of the agent
            task_id: ID of the task

        Returns:
            ErrorContext if validation fails, None if criteria met
        """
        # Validate required fields
        required_fields = success_criteria.get("required_fields", [])
        if isinstance(output, dict):
            missing_fields = [f for f in required_fields if f not in output]
            if missing_fields:
                error = ErrorContext(
                    error_type=ErrorType.VALIDATION_FAILURE,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Missing required_fields from success criteria: "
                    f"{missing_fields}",
                    agent_id=agent_id,
                    task_id=task_id,
                    metadata={"missing_fields": missing_fields},
                )
                self._validation_history.append(error)
                return error

        # Validate status values
        status_values = success_criteria.get("status_values", [])
        if isinstance(output, dict) and "status" in output:
            if status_values and output["status"] not in status_values:
                error = ErrorContext(
                    error_type=ErrorType.VALIDATION_FAILURE,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Invalid status value: {output['status']} "
                    f"not in allowed values {status_values}",
                    agent_id=agent_id,
                    task_id=task_id,
                    metadata={
                        "actual_status": output["status"],
                        "allowed_statuses": status_values,
                    },
                )
                self._validation_history.append(error)
                return error

        return None

    def get_validation_history(
        self,
        agent_id: str | None = None,
        task_id: str | None = None,
    ) -> list[ErrorContext]:
        """
        Retrieve validation error history with optional filtering.

        Args:
            agent_id: Filter by agent ID (optional)
            task_id: Filter by task ID (optional)

        Returns:
            List of ErrorContext objects from validation failures
        """
        errors = self._validation_history

        if agent_id is not None:
            errors = [e for e in errors if e.agent_id == agent_id]

        if task_id is not None:
            errors = [e for e in errors if e.task_id == task_id]

        return errors
