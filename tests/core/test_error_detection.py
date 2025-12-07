"""Tests for error detection framework."""

import time
from datetime import datetime

from src.core.error_detection import (
    ErrorContext,
    ErrorSeverity,
    ErrorType,
    FailureDetector,
    OutputValidator,
    ValidationRule,
)


class TestErrorType:
    """Test the ErrorType enum."""

    def test_error_types_exist(self):
        """Test that all required error types are defined."""
        assert hasattr(ErrorType, "CRASH")
        assert hasattr(ErrorType, "TIMEOUT")
        assert hasattr(ErrorType, "INVALID_OUTPUT")
        assert hasattr(ErrorType, "PARTIAL_COMPLETION")
        assert hasattr(ErrorType, "VALIDATION_FAILURE")

    def test_error_type_values(self):
        """Test error type values are strings."""
        assert isinstance(ErrorType.CRASH.value, str)
        assert isinstance(ErrorType.TIMEOUT.value, str)


class TestErrorSeverity:
    """Test the ErrorSeverity enum."""

    def test_severity_levels_exist(self):
        """Test that all severity levels are defined."""
        assert hasattr(ErrorSeverity, "CRITICAL")
        assert hasattr(ErrorSeverity, "HIGH")
        assert hasattr(ErrorSeverity, "MEDIUM")
        assert hasattr(ErrorSeverity, "LOW")

    def test_severity_ordering(self):
        """Test that severities have numeric values for comparison."""
        assert ErrorSeverity.CRITICAL.value > ErrorSeverity.HIGH.value
        assert ErrorSeverity.HIGH.value > ErrorSeverity.MEDIUM.value
        assert ErrorSeverity.MEDIUM.value > ErrorSeverity.LOW.value


class TestErrorContext:
    """Test the ErrorContext dataclass."""

    def test_create_error_context(self):
        """Test creating an error context."""
        ctx = ErrorContext(
            error_type=ErrorType.CRASH,
            severity=ErrorSeverity.CRITICAL,
            message="Test error",
            agent_id="test-agent-1",
            task_id="test-task-1",
        )
        assert ctx.error_type == ErrorType.CRASH
        assert ctx.severity == ErrorSeverity.CRITICAL
        assert ctx.message == "Test error"
        assert ctx.agent_id == "test-agent-1"
        assert ctx.task_id == "test-task-1"
        assert isinstance(ctx.timestamp, datetime)

    def test_error_context_with_stack_trace(self):
        """Test error context with stack trace."""
        ctx = ErrorContext(
            error_type=ErrorType.CRASH,
            severity=ErrorSeverity.CRITICAL,
            message="Test error",
            agent_id="test-agent-1",
            task_id="test-task-1",
            stack_trace="Traceback: ...",
        )
        assert ctx.stack_trace == "Traceback: ..."

    def test_error_context_with_metadata(self):
        """Test error context with metadata."""
        ctx = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.HIGH,
            message="Operation timed out",
            agent_id="test-agent-1",
            task_id="test-task-1",
            metadata={"timeout_seconds": 30, "operation": "API call"},
        )
        assert ctx.metadata["timeout_seconds"] == 30
        assert ctx.metadata["operation"] == "API call"


class TestFailureDetector:
    """Test the FailureDetector class."""

    def test_create_detector(self):
        """Test creating a failure detector."""
        detector = FailureDetector()
        assert detector is not None

    def test_detect_crash(self):
        """Test detecting a crash error."""
        detector = FailureDetector()

        def failing_function():
            raise RuntimeError("Simulated crash")

        error = detector.detect_crash(
            func=failing_function,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is not None
        assert error.error_type == ErrorType.CRASH
        assert error.severity == ErrorSeverity.CRITICAL
        assert "Simulated crash" in error.message
        assert error.agent_id == "agent-1"
        assert error.task_id == "task-1"

    def test_detect_crash_no_error(self):
        """Test detect_crash when function succeeds."""
        detector = FailureDetector()

        def successful_function():
            return "success"

        error = detector.detect_crash(
            func=successful_function,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is None

    def test_detect_timeout(self):
        """Test detecting a timeout error."""
        detector = FailureDetector()

        def slow_function():
            time.sleep(0.2)
            return "done"

        error = detector.detect_timeout(
            func=slow_function,
            timeout_seconds=0.1,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is not None
        assert error.error_type == ErrorType.TIMEOUT
        assert error.severity == ErrorSeverity.HIGH
        assert error.agent_id == "agent-1"
        assert error.task_id == "task-1"

    def test_detect_timeout_no_error(self):
        """Test detect_timeout when function completes in time."""
        detector = FailureDetector()

        def fast_function():
            return "done"

        error = detector.detect_timeout(
            func=fast_function,
            timeout_seconds=1.0,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is None

    def test_detect_invalid_output_with_type(self):
        """Test detecting invalid output based on type."""
        detector = FailureDetector()

        result = "string instead of dict"
        error = detector.detect_invalid_output(
            output=result,
            expected_type=dict,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is not None
        assert error.error_type == ErrorType.INVALID_OUTPUT
        assert error.severity == ErrorSeverity.MEDIUM

    def test_detect_invalid_output_valid_type(self):
        """Test detect_invalid_output when type is correct."""
        detector = FailureDetector()

        result = {"status": "ok"}
        error = detector.detect_invalid_output(
            output=result,
            expected_type=dict,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is None

    def test_detect_invalid_output_with_schema(self):
        """Test detecting invalid output based on schema."""
        detector = FailureDetector()

        result = {"status": "ok"}  # Missing required "result" field
        schema = {"required_fields": ["status", "result"]}

        error = detector.detect_invalid_output(
            output=result,
            schema=schema,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is not None
        assert error.error_type == ErrorType.INVALID_OUTPUT

    def test_detect_partial_completion(self):
        """Test detecting partial completion."""
        detector = FailureDetector()

        completed_items = ["item1", "item2"]
        required_items = ["item1", "item2", "item3", "item4"]

        error = detector.detect_partial_completion(
            completed_items=completed_items,
            required_items=required_items,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is not None
        assert error.error_type == ErrorType.PARTIAL_COMPLETION
        assert error.severity == ErrorSeverity.MEDIUM
        assert "2 of 4" in error.message or "50%" in error.message

    def test_detect_partial_completion_full_completion(self):
        """Test detect_partial_completion when all items completed."""
        detector = FailureDetector()

        completed_items = ["item1", "item2", "item3"]
        required_items = ["item1", "item2", "item3"]

        error = detector.detect_partial_completion(
            completed_items=completed_items,
            required_items=required_items,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is None

    def test_get_error_history(self):
        """Test retrieving error history."""
        detector = FailureDetector()

        # Trigger some errors
        detector.detect_crash(
            func=lambda: 1 / 0,
            agent_id="agent-1",
            task_id="task-1",
        )

        history = detector.get_error_history()
        assert len(history) == 1
        assert history[0].error_type == ErrorType.CRASH

    def test_get_error_history_filtered_by_agent(self):
        """Test retrieving error history filtered by agent."""
        detector = FailureDetector()

        # Trigger errors for different agents
        detector.detect_crash(
            func=lambda: 1 / 0,
            agent_id="agent-1",
            task_id="task-1",
        )
        detector.detect_crash(
            func=lambda: 1 / 0,
            agent_id="agent-2",
            task_id="task-2",
        )

        history = detector.get_error_history(agent_id="agent-1")
        assert len(history) == 1
        assert history[0].agent_id == "agent-1"


class TestValidationRule:
    """Test the ValidationRule dataclass."""

    def test_create_validation_rule(self):
        """Test creating a validation rule."""
        rule = ValidationRule(
            name="output_type",
            description="Output must be a dictionary",
            validator=lambda x: isinstance(x, dict),
        )
        assert rule.name == "output_type"
        assert rule.validator({"key": "value"}) is True
        assert rule.validator("string") is False

    def test_validation_rule_with_severity(self):
        """Test validation rule with custom severity."""
        rule = ValidationRule(
            name="critical_check",
            description="Critical validation",
            validator=lambda x: x > 0,
            severity=ErrorSeverity.CRITICAL,
        )
        assert rule.severity == ErrorSeverity.CRITICAL


class TestOutputValidator:
    """Test the OutputValidator class."""

    def test_create_validator(self):
        """Test creating an output validator."""
        validator = OutputValidator()
        assert validator is not None

    def test_add_validation_rule(self):
        """Test adding a validation rule."""
        validator = OutputValidator()

        rule = ValidationRule(
            name="type_check",
            description="Must be dict",
            validator=lambda x: isinstance(x, dict),
        )

        validator.add_rule(rule)
        assert len(validator.rules) == 1

    def test_validate_against_rules_success(self):
        """Test validation against rules that pass."""
        validator = OutputValidator()

        validator.add_rule(
            ValidationRule(
                name="type_check",
                description="Must be dict",
                validator=lambda x: isinstance(x, dict),
            )
        )

        validator.add_rule(
            ValidationRule(
                name="has_status",
                description="Must have status key",
                validator=lambda x: "status" in x,
            )
        )

        output = {"status": "ok", "result": 42}
        error = validator.validate(
            output=output,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is None

    def test_validate_against_rules_failure(self):
        """Test validation against rules that fail."""
        validator = OutputValidator()

        validator.add_rule(
            ValidationRule(
                name="type_check",
                description="Must be dict",
                validator=lambda x: isinstance(x, dict),
            )
        )

        output = "not a dict"
        error = validator.validate(
            output=output,
            agent_id="agent-1",
            task_id="task-1",
        )

        assert error is not None
        assert error.error_type == ErrorType.VALIDATION_FAILURE
        assert "type_check" in error.message

    def test_validate_against_success_criteria(self):
        """Test validation against task success criteria."""
        validator = OutputValidator()

        success_criteria = {
            "required_fields": ["status", "result"],
            "status_values": ["ok", "completed"],
        }

        # Valid output
        output = {"status": "ok", "result": 42}
        error = validator.validate_against_criteria(
            output=output,
            success_criteria=success_criteria,
            agent_id="agent-1",
            task_id="task-1",
        )
        assert error is None

        # Invalid - missing field
        output = {"status": "ok"}
        error = validator.validate_against_criteria(
            output=output,
            success_criteria=success_criteria,
            agent_id="agent-1",
            task_id="task-1",
        )
        assert error is not None
        assert "required_fields" in error.message

        # Invalid - wrong status value
        output = {"status": "failed", "result": 42}
        error = validator.validate_against_criteria(
            output=output,
            success_criteria=success_criteria,
            agent_id="agent-1",
            task_id="task-1",
        )
        assert error is not None

    def test_no_silent_failures(self):
        """Test that validation failures are always logged (no silent failures)."""
        validator = OutputValidator()

        validator.add_rule(
            ValidationRule(
                name="always_fail",
                description="This rule always fails",
                validator=lambda x: False,
            )
        )

        output = "anything"
        error = validator.validate(
            output=output,
            agent_id="agent-1",
            task_id="task-1",
        )

        # Error must be returned, not silently ignored
        assert error is not None
        assert error.error_type == ErrorType.VALIDATION_FAILURE

        # Error must be in history
        history = validator.get_validation_history()
        assert len(history) > 0
        assert any(e.error_type == ErrorType.VALIDATION_FAILURE for e in history)
