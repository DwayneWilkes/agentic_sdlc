"""
Retry Loop Detection - Defeat Test Pattern.

Detects when an agent keeps trying the same failed approach repeatedly
without making progress.

Anti-pattern: Agent tries fix → fails → tries same fix again → fails → repeat
Good pattern: Agent tries fix → fails → analyzes why → tries DIFFERENT approach
"""

from collections import Counter

from src.testing.defeat_tests import AgentSession, DefeatTestResult


def detect_retry_loop(
    session: AgentSession, max_retries: int = 3
) -> DefeatTestResult:
    """
    Detect if agent is stuck in a retry loop.

    A retry loop is detected when:
    - Same approach is tried more than max_retries times
    - With the same (or very similar) error
    - Without meaningful progress

    Args:
        session: The agent session to analyze
        max_retries: Maximum number of retries before flagging (default: 3)

    Returns:
        DefeatTestResult with passed=False if retry loop detected
    """
    # Get all failed actions
    failed_actions = session.get_failed_actions()

    if len(failed_actions) < max_retries:
        # Not enough failures to constitute a loop
        return DefeatTestResult(
            test_name="retry_loop",
            passed=True,
            message="No retry loop detected (insufficient failures)",
        )

    # Track approach + error combinations
    approach_error_pairs: list[tuple] = []

    for action in failed_actions:
        # Extract approach identifier and error message
        approach = action.details.get("approach", "unknown")
        error = action.details.get("error", "unknown")

        # Create a signature for this failure
        signature = (approach, error)
        approach_error_pairs.append(signature)

    # Count occurrences of each signature
    signature_counts = Counter(approach_error_pairs)

    # Find the most common retry pattern
    most_common = signature_counts.most_common(1)

    if most_common:
        (approach, error), count = most_common[0]

        if count > max_retries:
            return DefeatTestResult(
                test_name="retry_loop",
                passed=False,
                message=f"Retry loop detected: '{approach}' failed {count} times with error '{error}'",
                details={
                    "approach": approach,
                    "error": error,
                    "retry_count": count,
                    "max_allowed": max_retries,
                },
            )

    # No retry loop detected
    return DefeatTestResult(
        test_name="retry_loop",
        passed=True,
        message="No retry loop detected (agent tried different approaches)",
    )


def get_approach_diversity(session: AgentSession) -> float:
    """
    Calculate how diverse the agent's approaches were.

    Returns a score from 0.0 (all same approach) to 1.0 (all different).
    """
    failed_actions = session.get_failed_actions()

    if len(failed_actions) <= 1:
        return 1.0  # Not enough data, assume diverse

    approaches = [action.details.get("approach", "unknown") for action in failed_actions]
    unique_approaches = len(set(approaches))
    total_attempts = len(approaches)

    return unique_approaches / total_attempts if total_attempts > 0 else 1.0
