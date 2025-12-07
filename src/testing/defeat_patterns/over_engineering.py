"""
Over-Engineering Detection - Defeat Test Pattern.

Detects when an agent creates overly complex solutions for simple problems.

Anti-pattern: "Add logging to function" → Creates 500-line logging framework
Good pattern: "Add logging to function" → Adds import logging; logger.info(...)
"""

from src.testing.defeat_tests import AgentSession, DefeatTestResult


def detect_over_engineering(
    session: AgentSession,
    complexity_threshold: int = 100,
    file_count_threshold: int = 3,
) -> DefeatTestResult:
    """
    Detect if agent over-engineered a simple solution.

    Over-engineering is detected when:
    - Simple goal results in excessive code/files
    - Many abstractions created for straightforward task
    - Solution complexity vastly exceeds goal complexity

    Args:
        session: The agent session to analyze
        complexity_threshold: Max lines of code for "simple" goals
        file_count_threshold: Max files created for "simple" goals

    Returns:
        DefeatTestResult with passed=False if over-engineering detected
    """
    # Analyze goal complexity
    initial_goal = session.context.get("initial_goal", "").lower()

    if not initial_goal:
        return DefeatTestResult(
            test_name="over_engineering",
            passed=True,
            message="No initial goal defined (cannot assess complexity)",
        )

    # Classify goal as simple/medium/complex
    goal_complexity = _classify_goal_complexity(initial_goal)

    # Count files created and lines of code
    file_creates = session.get_actions_by_type("file_create")
    total_lines = sum(action.details.get("lines", 0) for action in file_creates)
    file_count = len(file_creates)

    # Simple goals should have simple solutions
    if goal_complexity == "simple":
        if file_count > file_count_threshold:
            return DefeatTestResult(
                test_name="over_engineering",
                passed=False,
                message=(
                    f"Over-engineering detected: {file_count} files created "
                    f"for simple goal '{initial_goal}'"
                ),
                details={
                    "goal": initial_goal,
                    "goal_complexity": goal_complexity,
                    "files_created": file_count,
                    "threshold": file_count_threshold,
                    "total_lines": total_lines,
                },
            )

        if total_lines > complexity_threshold:
            return DefeatTestResult(
                test_name="over_engineering",
                passed=False,
                message=(
                    f"Over-engineering detected: {total_lines} lines written "
                    f"for simple goal '{initial_goal}'"
                ),
                details={
                    "goal": initial_goal,
                    "goal_complexity": goal_complexity,
                    "total_lines": total_lines,
                    "threshold": complexity_threshold,
                },
            )

    # Check for excessive abstraction patterns
    abstraction_indicators = [
        "factory",
        "builder",
        "strategy",
        "singleton",
        "adapter",
        "facade",
    ]

    abstraction_count = 0
    for action in file_creates:
        file_name = action.details.get("file", "").lower()
        if any(pattern in file_name for pattern in abstraction_indicators):
            abstraction_count += 1

    # Simple goals shouldn't need many design patterns
    if goal_complexity == "simple" and abstraction_count >= 2:
        return DefeatTestResult(
            test_name="over_engineering",
            passed=False,
            message=(
                f"Over-engineering detected: {abstraction_count} design "
                f"patterns used for simple goal"
            ),
            details={
                "goal": initial_goal,
                "abstraction_count": abstraction_count,
                "patterns_found": abstraction_indicators,
            },
        )

    # Solution complexity matches goal complexity
    return DefeatTestResult(
        test_name="over_engineering",
        passed=True,
        message=f"Appropriate complexity for {goal_complexity} goal",
        details={
            "goal_complexity": goal_complexity,
            "files_created": file_count,
            "total_lines": total_lines,
        },
    )


def _classify_goal_complexity(goal: str) -> str:
    """
    Classify a goal as simple, medium, or complex.

    Simple: Single-purpose, localized changes
    Medium: Multi-file, moderate scope
    Complex: System-wide, architecture changes
    """
    goal_lower = goal.lower()

    # Simple indicators
    simple_keywords = [
        "add logging",
        "fix typo",
        "update comment",
        "rename variable",
        "add print",
        "change message",
        "update string",
    ]

    if any(keyword in goal_lower for keyword in simple_keywords):
        return "simple"

    # Complex indicators
    complex_keywords = [
        "distributed",
        "microservices",
        "architecture",
        "framework",
        "platform",
        "system-wide",
        "refactor entire",
        "rebuild",
    ]

    if any(keyword in goal_lower for keyword in complex_keywords):
        return "complex"

    # Default to medium
    return "medium"


def get_abstraction_score(session: AgentSession) -> float:
    """
    Calculate abstraction score (0.0 = concrete, 1.0 = highly abstract).

    Higher score indicates more design patterns and abstractions used.
    """
    file_creates = session.get_actions_by_type("file_create")

    if not file_creates:
        return 0.0

    abstraction_patterns = [
        "factory",
        "builder",
        "strategy",
        "singleton",
        "adapter",
        "facade",
        "proxy",
        "decorator",
        "observer",
        "command",
    ]

    abstraction_count = 0
    for action in file_creates:
        file_name = action.details.get("file", "").lower()
        if any(pattern in file_name for pattern in abstraction_patterns):
            abstraction_count += 1

    # Normalize by file count
    return min(abstraction_count / len(file_creates), 1.0)
