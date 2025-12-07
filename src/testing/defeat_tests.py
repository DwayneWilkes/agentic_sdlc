"""
Defeat Test Framework for Agent Anti-Pattern Detection.

This framework implements "defeat tests" - tests that detect and prevent
agent anti-patterns before they reach production.

Inspired by Test-Driven Development, but for agent behavior:
    Traditional TDD: Red → Green → Refactor
    Agent TDD:       Pattern Found → Defeat Test Written → Agent Trained → Pattern Defeated
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ActionOutcome(Enum):
    """Possible outcomes of an agent action."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    SKIPPED = "skipped"


@dataclass
class AgentAction:
    """
    Records a single action taken by an agent.

    This captures what the agent did, when, and what the result was.
    """

    timestamp: datetime
    action_type: str  # e.g., "file_edit", "test_run", "file_read", "file_create"
    details: dict[str, Any]  # Action-specific details
    outcome: str  # "success", "failure", "partial_success"

    def __post_init__(self) -> None:
        """Validate action_type and outcome."""
        if not self.action_type:
            raise ValueError("action_type cannot be empty")
        if not self.outcome:
            raise ValueError("outcome cannot be empty")


@dataclass
class AgentSession:
    """
    Tracks all actions taken by an agent during a session.

    A session represents a complete agent execution, from start to finish.
    """

    session_id: str
    agent_name: str
    actions: list[AgentAction] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    start_time: datetime | None = field(default_factory=datetime.now)
    end_time: datetime | None = None

    def add_action(self, action: AgentAction) -> None:
        """Add an action to this session."""
        self.actions.append(action)

    def get_actions_by_type(self, action_type: str) -> list[AgentAction]:
        """Get all actions of a specific type."""
        return [a for a in self.actions if a.action_type == action_type]

    def get_failed_actions(self) -> list[AgentAction]:
        """Get all actions that failed."""
        return [a for a in self.actions if a.outcome == "failure"]


@dataclass
class DefeatTestResult:
    """
    Result of running a defeat test.

    A defeat test PASSES if the anti-pattern is NOT detected.
    A defeat test FAILS if the anti-pattern IS detected.
    """

    test_name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DefeatTest:
    """
    A test that detects an agent anti-pattern.

    Each defeat test checks for a specific problematic behavior pattern.
    """

    name: str
    description: str
    pattern_name: str  # Name of the anti-pattern being tested
    check_function: Callable[[AgentSession], DefeatTestResult] | None = None

    def run(self, session: AgentSession) -> DefeatTestResult:
        """
        Run this defeat test against a session.

        Returns DefeatTestResult with passed=True if pattern NOT detected.
        """
        if self.check_function is None:
            return DefeatTestResult(
                test_name=self.name,
                passed=True,
                message="No check function defined (test skipped)",
            )
        return self.check_function(session)


class DefeatTestRunner:
    """
    Runs defeat tests against agent sessions.

    This is the main entry point for executing defeat tests.
    """

    def __init__(self) -> None:
        """Initialize the defeat test runner."""
        self.test_registry: list[DefeatTest] = []

    def register_test(self, test: DefeatTest) -> None:
        """Register a defeat test."""
        self.test_registry.append(test)

    def run_test(self, test: DefeatTest, session: AgentSession) -> DefeatTestResult:
        """Run a single defeat test against a session."""
        return test.run(session)

    def run_tests(
        self, tests: list[DefeatTest], session: AgentSession
    ) -> list[DefeatTestResult]:
        """Run multiple defeat tests against a session."""
        results = []
        for test in tests:
            result = self.run_test(test, session)
            results.append(result)
        return results

    def run_all_registered_tests(
        self, session: AgentSession
    ) -> list[DefeatTestResult]:
        """Run all registered defeat tests against a session."""
        return self.run_tests(self.test_registry, session)

    def get_summary(self, results: list[DefeatTestResult]) -> dict[str, Any]:
        """
        Generate a summary of test results.

        Returns:
            Dictionary with keys:
            - total: Total number of tests
            - passed: Number of tests passed (patterns NOT detected)
            - failed: Number of tests failed (patterns detected)
            - pass_rate: Percentage of tests passed
        """
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0.0,
        }

    def print_results(self, results: list[DefeatTestResult]) -> None:
        """Print test results in a human-readable format."""
        summary = self.get_summary(results)

        print("\n" + "=" * 60)
        print("DEFEAT TEST RESULTS")
        print("=" * 60)

        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} {result.test_name}")
            if not result.passed:
                print(f"  └─ {result.message}")

        print("\n" + "-" * 60)
        print(
            f"Total: {summary['total']} | Passed: {summary['passed']} | "
            f"Failed: {summary['failed']}"
        )
        print(f"Pass Rate: {summary['pass_rate']:.1f}%")
        print("=" * 60 + "\n")
