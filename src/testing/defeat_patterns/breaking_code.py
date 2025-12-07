"""
Breaking Working Code Detection - Defeat Test Pattern.

Detects when an agent's "fix" actually makes things worse by breaking
previously working functionality.

Anti-pattern: Fix 1 bug → Break 3 other things → Net negative progress
Good pattern: Fix 1 bug → All previously passing tests still pass → Net positive
"""


from src.testing.defeat_tests import AgentSession, DefeatTestResult


def detect_breaking_working_code(session: AgentSession) -> DefeatTestResult:
    """
    Detect if agent broke working code while making changes.

    Breaking code is detected when:
    - Tests that were passing before now fail
    - The number of passing tests decreases
    - Net test progress is negative

    Args:
        session: The agent session to analyze

    Returns:
        DefeatTestResult with passed=False if code was broken
    """
    # Get all test run actions
    test_runs = session.get_actions_by_type("test_run")

    if len(test_runs) < 2:
        # Need at least 2 test runs to compare
        return DefeatTestResult(
            test_name="breaking_working_code",
            passed=True,
            message="Insufficient test runs to detect regressions",
        )

    # Track test pass/fail counts over time
    test_history: list[tuple[int, int]] = []  # (tests_passed, tests_failed)

    for test_run in test_runs:
        passed = test_run.details.get("tests_passed", 0)
        failed = test_run.details.get("tests_failed", 0)
        test_history.append((passed, failed))

    # Check for regressions (decreased pass count)
    regressions_detected = []

    for i in range(1, len(test_history)):
        prev_passed, prev_failed = test_history[i - 1]
        curr_passed, curr_failed = test_history[i]

        # Regression if:
        # 1. Fewer tests passing than before
        # 2. More tests failing than before
        # 3. Net change is negative
        net_change = curr_passed - prev_passed

        if curr_passed < prev_passed:
            regressions_detected.append(
                {
                    "index": i,
                    "prev_passed": prev_passed,
                    "curr_passed": curr_passed,
                    "tests_broken": prev_passed - curr_passed,
                    "net_change": net_change,
                }
            )

    if regressions_detected:
        # Found regressions
        worst_regression = max(regressions_detected, key=lambda r: r["tests_broken"])

        return DefeatTestResult(
            test_name="breaking_working_code",
            passed=False,
            message=(
                f"Regression detected: {worst_regression['tests_broken']} "
                "previously passing tests now fail"
            ),
            details={
                "regressions": regressions_detected,
                "worst_regression": worst_regression,
                "test_history": test_history,
            },
        )

    # Check final state - did we make net progress?
    initial_passed, initial_failed = test_history[0]
    final_passed, final_failed = test_history[-1]

    net_progress = final_passed - initial_passed

    if net_progress < 0:
        return DefeatTestResult(
            test_name="breaking_working_code",
            passed=False,
            message=f"Net negative progress: {abs(net_progress)} fewer tests passing than at start",
            details={
                "initial_passed": initial_passed,
                "final_passed": final_passed,
                "net_progress": net_progress,
            },
        )

    # No regressions detected, net progress is positive or neutral
    return DefeatTestResult(
        test_name="breaking_working_code",
        passed=True,
        message=f"No regressions detected. Net progress: +{net_progress} tests",
        details={
            "initial_passed": initial_passed,
            "final_passed": final_passed,
            "net_progress": net_progress,
        },
    )


def calculate_test_health_score(session: AgentSession) -> float:
    """
    Calculate overall test health score (0.0 to 1.0).

    Higher score = more tests passing, better trend.
    """
    test_runs = session.get_actions_by_type("test_run")

    if not test_runs:
        return 1.0  # No tests = assume healthy (benefit of doubt)

    # Use most recent test run
    latest = test_runs[-1]
    passed = latest.details.get("tests_passed", 0)
    failed = latest.details.get("tests_failed", 0)
    total = passed + failed

    if total == 0:
        return 1.0

    return float(passed / total)
