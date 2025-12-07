"""
Tests for the defeat test framework itself.

This is meta-TDD: we write tests for the framework that will test agents.
"""

from datetime import datetime

# These imports will fail until we create the infrastructure
from src.testing.defeat_tests import (
    AgentAction,
    AgentSession,
    DefeatTest,
    DefeatTestResult,
    DefeatTestRunner,
)


class TestDefeatTestFramework:
    """Test the core defeat test infrastructure."""

    def test_defeat_test_can_be_created(self):
        """A defeat test can be instantiated with name and description."""
        test = DefeatTest(
            name="test_example",
            description="Example defeat test",
            pattern_name="example_pattern",
        )
        assert test.name == "test_example"
        assert test.description == "Example defeat test"
        assert test.pattern_name == "example_pattern"

    def test_defeat_test_result_tracks_pass_fail(self):
        """Defeat test results track whether test passed."""
        result_pass = DefeatTestResult(
            test_name="test_example", passed=True, message="Test passed"
        )
        assert result_pass.passed is True
        assert result_pass.message == "Test passed"

        result_fail = DefeatTestResult(
            test_name="test_example",
            passed=False,
            message="Pattern detected: retry loop",
        )
        assert result_fail.passed is False
        assert "retry loop" in result_fail.message

    def test_agent_action_captures_operation(self):
        """AgentAction records what an agent did."""
        action = AgentAction(
            timestamp=datetime.now(),
            action_type="file_edit",
            details={"file": "test.py", "changes": 10},
            outcome="success",
        )
        assert action.action_type == "file_edit"
        assert action.details["file"] == "test.py"
        assert action.outcome == "success"

    def test_agent_session_tracks_actions(self):
        """AgentSession accumulates agent actions over time."""
        session = AgentSession(session_id="test-session-1", agent_name="TestAgent")

        action1 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_read",
            details={"file": "example.py"},
            outcome="success",
        )
        action2 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_edit",
            details={"file": "example.py", "changes": 5},
            outcome="success",
        )

        session.add_action(action1)
        session.add_action(action2)

        assert len(session.actions) == 2
        assert session.actions[0].action_type == "file_read"
        assert session.actions[1].action_type == "file_edit"

    def test_defeat_test_runner_executes_tests(self):
        """DefeatTestRunner can execute defeat tests against sessions."""
        runner = DefeatTestRunner()

        # Create a simple session
        session = AgentSession(session_id="test-session", agent_name="TestAgent")
        action = AgentAction(
            timestamp=datetime.now(),
            action_type="test",
            details={},
            outcome="success",
        )
        session.add_action(action)

        # Create a simple defeat test
        def simple_check(session: AgentSession) -> DefeatTestResult:
            return DefeatTestResult(
                test_name="simple_test", passed=True, message="All good"
            )

        test = DefeatTest(
            name="simple_test",
            description="Simple test",
            pattern_name="simple",
            check_function=simple_check,
        )

        # Run the test
        results = runner.run_test(test, session)
        assert results.passed is True

    def test_defeat_test_runner_collects_multiple_results(self):
        """DefeatTestRunner can run multiple tests and collect results."""
        runner = DefeatTestRunner()
        session = AgentSession(session_id="test", agent_name="Agent")

        # Create two tests
        def test1_check(session: AgentSession) -> DefeatTestResult:
            return DefeatTestResult(test_name="test1", passed=True, message="Pass")

        def test2_check(session: AgentSession) -> DefeatTestResult:
            return DefeatTestResult(test_name="test2", passed=False, message="Fail")

        test1 = DefeatTest(
            name="test1",
            description="First test",
            pattern_name="pattern1",
            check_function=test1_check,
        )
        test2 = DefeatTest(
            name="test2",
            description="Second test",
            pattern_name="pattern2",
            check_function=test2_check,
        )

        results = runner.run_tests([test1, test2], session)
        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False

    def test_defeat_test_runner_reports_summary(self):
        """DefeatTestRunner provides summary of results."""
        runner = DefeatTestRunner()
        session = AgentSession(session_id="test", agent_name="Agent")

        def pass_check(session: AgentSession) -> DefeatTestResult:
            return DefeatTestResult(test_name="pass", passed=True, message="Pass")

        def fail_check(session: AgentSession) -> DefeatTestResult:
            return DefeatTestResult(test_name="fail", passed=False, message="Fail")

        test_pass = DefeatTest(
            name="pass", description="Pass", pattern_name="p", check_function=pass_check
        )
        test_fail = DefeatTest(
            name="fail", description="Fail", pattern_name="f", check_function=fail_check
        )

        results = runner.run_tests([test_pass, test_fail], session)
        summary = runner.get_summary(results)

        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1


class TestRetryLoopDetection:
    """Test the retry loop defeat test pattern."""

    def test_detects_retry_loop_same_error_multiple_times(self):
        """Detect when agent retries same approach >3 times with same error."""
        from src.testing.defeat_patterns.retry_loop import detect_retry_loop

        session = AgentSession(session_id="test", agent_name="Agent")

        # Add 4 identical failed attempts
        for i in range(4):
            action = AgentAction(
                timestamp=datetime.now(),
                action_type="test_run",
                details={"approach": "fix_null_check", "error": "NullPointerException"},
                outcome="failure",
            )
            session.add_action(action)

        result = detect_retry_loop(session)
        assert result.passed is False
        assert "retry loop" in result.message.lower()

    def test_allows_different_approaches(self):
        """Don't flag as retry loop if agent tries different approaches."""
        from src.testing.defeat_patterns.retry_loop import detect_retry_loop

        session = AgentSession(session_id="test", agent_name="Agent")

        # Add 4 different approaches
        approaches = ["approach_a", "approach_b", "approach_c", "approach_d"]
        for approach in approaches:
            action = AgentAction(
                timestamp=datetime.now(),
                action_type="test_run",
                details={"approach": approach, "error": "TestFailure"},
                outcome="failure",
            )
            session.add_action(action)

        result = detect_retry_loop(session)
        assert result.passed is True


class TestContextDriftDetection:
    """Test the context drift defeat test pattern."""

    def test_detects_context_loss(self):
        """Detect when agent loses important context mid-session."""
        from src.testing.defeat_patterns.context_drift import detect_context_drift

        session = AgentSession(session_id="test", agent_name="Agent")

        # Agent starts with context about auth module
        session.context = {
            "initial_goal": "Fix auth bug in login flow",
            "key_files": ["auth.py", "login.py"],
        }

        # Early actions show awareness of context
        action1 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_read",
            details={"file": "auth.py"},
            outcome="success",
        )
        session.add_action(action1)

        # Later action shows context drift (working on unrelated file)
        action2 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_edit",
            details={
                "file": "database.py",  # Unrelated to auth!
                "reason": "optimizing queries",
            },
            outcome="success",
        )
        session.add_action(action2)

        result = detect_context_drift(session)
        # Should detect drift since we're no longer focused on auth
        assert result.passed is False

    def test_allows_context_evolution(self):
        """Allow context to evolve naturally when discovering dependencies."""
        from src.testing.defeat_patterns.context_drift import detect_context_drift

        session = AgentSession(session_id="test", agent_name="Agent")
        session.context = {
            "initial_goal": "Fix auth bug",
            "key_files": ["auth.py"],
        }

        # Agent discovers auth depends on session.py
        action1 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_read",
            details={"file": "auth.py"},
            outcome="success",
        )
        action2 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_read",
            details={
                "file": "session.py",  # Related dependency
                "reason": "auth.py imports session handling",
            },
            outcome="success",
        )
        session.add_action(action1)
        session.add_action(action2)

        result = detect_context_drift(session)
        # Should pass - natural context evolution
        assert result.passed is True


class TestBreakingWorkingCodeDetection:
    """Test detection of breaking working code during fixes."""

    def test_detects_breaking_passing_tests(self):
        """Detect when a fix breaks previously passing tests."""
        from src.testing.defeat_patterns.breaking_code import detect_breaking_working_code

        session = AgentSession(session_id="test", agent_name="Agent")

        # Initial state: tests passing
        action1 = AgentAction(
            timestamp=datetime.now(),
            action_type="test_run",
            details={"tests_passed": 10, "tests_failed": 1},
            outcome="partial_success",
        )
        session.add_action(action1)

        # Agent makes changes
        action2 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_edit",
            details={"file": "auth.py", "changes": 20},
            outcome="success",
        )
        session.add_action(action2)

        # After fix: original failing test passes BUT others break
        action3 = AgentAction(
            timestamp=datetime.now(),
            action_type="test_run",
            details={"tests_passed": 8, "tests_failed": 3},  # Net negative!
            outcome="partial_success",
        )
        session.add_action(action3)

        result = detect_breaking_working_code(session)
        assert result.passed is False
        assert "broke" in result.message.lower() or "regression" in result.message.lower()

    def test_allows_genuine_progress(self):
        """Allow fixes that improve test pass rate."""
        from src.testing.defeat_patterns.breaking_code import detect_breaking_working_code

        session = AgentSession(session_id="test", agent_name="Agent")

        action1 = AgentAction(
            timestamp=datetime.now(),
            action_type="test_run",
            details={"tests_passed": 10, "tests_failed": 2},
            outcome="partial_success",
        )
        action2 = AgentAction(
            timestamp=datetime.now(),
            action_type="file_edit",
            details={"file": "auth.py"},
            outcome="success",
        )
        action3 = AgentAction(
            timestamp=datetime.now(),
            action_type="test_run",
            details={"tests_passed": 12, "tests_failed": 0},  # Improvement!
            outcome="success",
        )
        session.add_action(action1)
        session.add_action(action2)
        session.add_action(action3)

        result = detect_breaking_working_code(session)
        assert result.passed is True


class TestOverEngineeringDetection:
    """Test detection of over-engineering simple solutions."""

    def test_detects_excessive_abstraction(self):
        """Detect when simple task gets over-engineered."""
        from src.testing.defeat_patterns.over_engineering import detect_over_engineering

        session = AgentSession(session_id="test", agent_name="Agent")
        session.context = {"initial_goal": "Add logging to function foo()"}

        # Agent creates excessive infrastructure for simple task
        actions = [
            AgentAction(
                timestamp=datetime.now(),
                action_type="file_create",
                details={"file": "logger_factory.py", "lines": 150},
                outcome="success",
            ),
            AgentAction(
                timestamp=datetime.now(),
                action_type="file_create",
                details={"file": "log_config_builder.py", "lines": 200},
                outcome="success",
            ),
            AgentAction(
                timestamp=datetime.now(),
                action_type="file_create",
                details={"file": "log_formatter_strategy.py", "lines": 100},
                outcome="success",
            ),
        ]
        for action in actions:
            session.add_action(action)

        result = detect_over_engineering(session)
        assert result.passed is False
        assert "over" in result.message.lower() or "complex" in result.message.lower()

    def test_allows_appropriate_complexity(self):
        """Allow complexity when it's warranted."""
        from src.testing.defeat_patterns.over_engineering import detect_over_engineering

        session = AgentSession(session_id="test", agent_name="Agent")
        session.context = {
            "initial_goal": "Build distributed logging system for microservices"
        }

        # Appropriate complexity for complex goal
        actions = [
            AgentAction(
                timestamp=datetime.now(),
                action_type="file_create",
                details={"file": "log_aggregator.py", "lines": 150},
                outcome="success",
            ),
            AgentAction(
                timestamp=datetime.now(),
                action_type="file_create",
                details={"file": "log_shipper.py", "lines": 200},
                outcome="success",
            ),
        ]
        for action in actions:
            session.add_action(action)

        result = detect_over_engineering(session)
        assert result.passed is True
