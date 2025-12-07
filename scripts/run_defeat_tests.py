#!/usr/bin/env python3
"""
Run defeat tests against agent sessions.

This script can be used:
1. Manually to check agent sessions
2. In pre-commit hooks to prevent anti-patterns
3. In CI/CD to validate agent behavior

Usage:
    python scripts/run_defeat_tests.py --session-file sessions/session-123.json
    python scripts/run_defeat_tests.py --all-sessions
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.testing.defeat_tests import (
    DefeatTest,
    DefeatTestRunner,
    AgentSession,
    AgentAction,
)
from src.testing.defeat_patterns import (
    detect_retry_loop,
    detect_context_drift,
    detect_breaking_working_code,
    detect_over_engineering,
)


def load_session_from_json(filepath: Path) -> AgentSession:
    """Load an agent session from a JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)

    session = AgentSession(
        session_id=data["session_id"],
        agent_name=data["agent_name"],
        context=data.get("context", {}),
    )

    for action_data in data.get("actions", []):
        action = AgentAction(
            timestamp=datetime.fromisoformat(action_data["timestamp"]),
            action_type=action_data["action_type"],
            details=action_data["details"],
            outcome=action_data["outcome"],
        )
        session.add_action(action)

    return session


def create_defeat_tests() -> List[DefeatTest]:
    """Create all defeat tests."""
    return [
        DefeatTest(
            name="retry_loop",
            description="Detect when agent retries same approach >3 times",
            pattern_name="retry_loop",
            check_function=detect_retry_loop,
        ),
        DefeatTest(
            name="context_drift",
            description="Detect when agent drifts from original goal",
            pattern_name="context_drift",
            check_function=detect_context_drift,
        ),
        DefeatTest(
            name="breaking_working_code",
            description="Detect when agent breaks previously passing tests",
            pattern_name="breaking_working_code",
            check_function=detect_breaking_working_code,
        ),
        DefeatTest(
            name="over_engineering",
            description="Detect when agent over-engineers simple solutions",
            pattern_name="over_engineering",
            check_function=detect_over_engineering,
        ),
    ]


def main():
    parser = argparse.ArgumentParser(description="Run defeat tests against agent sessions")
    parser.add_argument(
        "--session-file",
        type=Path,
        help="Path to a session JSON file",
    )
    parser.add_argument(
        "--all-sessions",
        action="store_true",
        help="Run tests against all sessions in sessions/ directory",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit immediately on first failure",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if not args.session_file and not args.all_sessions:
        print("Error: Must specify either --session-file or --all-sessions")
        parser.print_help()
        sys.exit(1)

    # Create defeat tests
    tests = create_defeat_tests()
    runner = DefeatTestRunner()

    # Load sessions
    sessions_to_test: List[tuple] = []  # (filepath, session)

    if args.session_file:
        if not args.session_file.exists():
            print(f"Error: Session file not found: {args.session_file}")
            sys.exit(1)
        session = load_session_from_json(args.session_file)
        sessions_to_test.append((args.session_file, session))
    elif args.all_sessions:
        sessions_dir = Path("sessions")
        if not sessions_dir.exists():
            print(f"Error: Sessions directory not found: {sessions_dir}")
            sys.exit(1)
        for session_file in sessions_dir.glob("*.json"):
            session = load_session_from_json(session_file)
            sessions_to_test.append((session_file, session))

    if not sessions_to_test:
        print("No sessions found to test")
        sys.exit(0)

    # Run tests
    print(f"Running {len(tests)} defeat tests against {len(sessions_to_test)} session(s)...\n")

    all_passed = True
    total_sessions = len(sessions_to_test)
    sessions_passed = 0

    for filepath, session in sessions_to_test:
        if args.verbose:
            print(f"\n{'=' * 60}")
            print(f"Testing session: {filepath}")
            print(f"Agent: {session.agent_name}, Actions: {len(session.actions)}")
            print(f"{'=' * 60}")

        results = runner.run_tests(tests, session)

        # Check results
        session_passed = all(r.passed for r in results)
        if session_passed:
            sessions_passed += 1
            if args.verbose:
                print(f"✅ Session {session.session_id}: ALL TESTS PASSED")
        else:
            all_passed = False
            print(f"❌ Session {session.session_id} from {filepath}: FAILURES DETECTED")
            for result in results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.message}")

            if args.fail_fast:
                sys.exit(1)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    print(f"Sessions tested: {total_sessions}")
    print(f"Sessions passed: {sessions_passed}")
    print(f"Sessions failed: {total_sessions - sessions_passed}")

    if all_passed:
        print("\n✅ All defeat tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some defeat tests failed. See details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
