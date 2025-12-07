"""
Context Drift Detection - Defeat Test Pattern.

Detects when an agent loses track of its original goal and starts
working on unrelated things.

Anti-pattern: Agent starts fixing auth bug → drifts to optimizing database → forgets auth
Good pattern: Agent maintains focus on auth, notes database optimization for later
"""

from src.testing.defeat_tests import AgentSession, DefeatTestResult


def detect_context_drift(
    session: AgentSession, drift_threshold: float = 0.5
) -> DefeatTestResult:
    """
    Detect if agent has drifted away from original context.

    Context drift is detected when:
    - Agent's recent actions are unrelated to initial goal
    - Working on files outside the key files identified
    - Actions don't reference the original problem domain

    Args:
        session: The agent session to analyze
        drift_threshold: Fraction of recent actions that must be related (default: 0.5)

    Returns:
        DefeatTestResult with passed=False if context drift detected
    """
    # Get initial context
    initial_goal = session.context.get("initial_goal", "").lower()
    key_files = session.context.get("key_files", [])

    if not initial_goal and not key_files:
        # No initial context to compare against
        return DefeatTestResult(
            test_name="context_drift",
            passed=True,
            message="No initial context defined (cannot detect drift)",
        )

    # Analyze recent actions (last 50% of actions)
    total_actions = len(session.actions)
    if total_actions == 0:
        return DefeatTestResult(
            test_name="context_drift",
            passed=True,
            message="No actions to analyze",
        )

    # Look at second half of actions to detect drift
    midpoint = total_actions // 2
    recent_actions = session.actions[midpoint:]

    if len(recent_actions) == 0:
        # Not enough actions yet
        return DefeatTestResult(
            test_name="context_drift",
            passed=True,
            message="Insufficient actions to detect drift",
        )

    # Count how many recent actions relate to original context
    related_actions = 0
    total_analyzed = len(recent_actions)

    # Extract key terms from initial goal (filter out common words)
    stop_words = {'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but'}
    goal_terms = set(word for word in initial_goal.split() if word not in stop_words)

    for action in recent_actions:
        is_related = False

        # Check if action involves key files
        file_name = action.details.get("file", "")
        if file_name in key_files:
            is_related = True

        # Check if file name contains goal-related terms
        # (for dependencies like auth.py → session.py)
        if not is_related and file_name:
            # Extract base name without extension
            file_base = file_name.replace('.py', '').replace('.js', '').replace('.ts', '')
            # Check if any goal term is in the filename or vice versa
            for term in goal_terms:
                if term in file_base.lower() or file_base.lower() in term:
                    is_related = True
                    break

        # Check if action mentions goal-related terms (word boundaries)
        if not is_related:
            reason = action.details.get("reason", "").lower()
            reason_words = set(reason.split())
            if goal_terms & reason_words:  # Set intersection
                is_related = True

        # Check if action mentions goal terms or key files in reason/details
        if not is_related:
            for key, value in action.details.items():
                if isinstance(value, str):
                    value_lower = value.lower()
                    value_words = set(value_lower.split())

                    # Check word boundaries
                    if goal_terms & value_words:
                        is_related = True
                        break

                    # Check if any key file is mentioned
                    if any(kf in value_lower for kf in key_files):
                        is_related = True
                        break

        if is_related:
            related_actions += 1

    # Calculate drift ratio
    related_ratio = related_actions / total_analyzed if total_analyzed > 0 else 0.0

    if related_ratio < drift_threshold:
        return DefeatTestResult(
            test_name="context_drift",
            passed=False,
            message=(
                f"Context drift detected: Only {related_ratio:.1%} of recent "
                f"actions relate to original goal '{initial_goal}'"
            ),
            details={
                "initial_goal": initial_goal,
                "related_actions": related_actions,
                "total_recent_actions": total_analyzed,
                "related_ratio": related_ratio,
                "threshold": drift_threshold,
            },
        )

    # No drift detected
    return DefeatTestResult(
        test_name="context_drift",
        passed=True,
        message=(
            f"Context maintained: {related_ratio:.1%} of recent actions "
            f"relate to original goal"
        ),
    )


def extract_file_domain(file_path: str) -> str:
    """
    Extract the domain from a file path.

    Examples:
        auth/login.py → auth
        database/migrations/001.py → database
        utils/helpers.py → utils
    """
    if "/" in file_path:
        return file_path.split("/")[0]
    return file_path.split(".")[0] if "." in file_path else file_path
