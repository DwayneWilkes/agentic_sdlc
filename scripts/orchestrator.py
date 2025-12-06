#!/usr/bin/env python3
"""
Orchestrator CLI - Coordinate autonomous agent teams.

Usage:
    python scripts/orchestrator.py status          # Show roadmap status
    python scripts/orchestrator.py run             # Run next available work stream
    python scripts/orchestrator.py run 1.2         # Run specific work stream
    python scripts/orchestrator.py parallel        # Run available work in parallel
    python scripts/orchestrator.py parallel -n 3   # Run with max 3 agents
    python scripts/orchestrator.py batch           # Complete all available work
    python scripts/orchestrator.py stop            # Stop all running agents
    python scripts/orchestrator.py report          # Show detailed report
    python scripts/orchestrator.py goal "..."      # Run based on natural language goal
    python scripts/orchestrator.py interactive     # Interactive mode with the orchestrator
"""

import argparse
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    OrchestratorMode,
    parse_roadmap,
    WorkStreamStatus,
)
from src.orchestrator.goal_interpreter import interpret_goal, format_interpretation, CommandType
from src.orchestrator.roadmap_gardener import garden_roadmap, check_roadmap_health

# ANSI colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def colored(text: str, color: str) -> str:
    """Apply ANSI color to text."""
    return f"{color}{text}{Colors.ENDC}"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{colored('═' * 60, Colors.BLUE)}")
    print(colored(f"  {text}", Colors.BOLD + Colors.BLUE))
    print(colored('═' * 60, Colors.BLUE))


def print_event(event) -> None:
    """Print an orchestrator event."""
    timestamp = event.timestamp.strftime("%H:%M:%S")
    color = {
        "spawning_agent": Colors.CYAN,
        "agent_running": Colors.BLUE,
        "agent_completed": Colors.GREEN,
        "agent_failed": Colors.RED,
        "verification_complete": Colors.GREEN if event.data.get("results", {}).get("passed") else Colors.RED,
    }.get(event.event_type, Colors.YELLOW)

    print(f"[{timestamp}] {colored(event.message, color)}")


def print_output(agent_id: str, line: str) -> None:
    """Print agent output line."""
    # Truncate agent_id for display
    short_id = agent_id.split("-")[-1][:8]
    print(f"  [{colored(short_id, Colors.CYAN)}] {line}")


def cmd_status(args) -> int:
    """Show roadmap status."""
    print_header("Roadmap Status")

    roadmap = parse_roadmap(PROJECT_ROOT / "plans" / "roadmap.md")

    # Group by status
    by_status = {}
    for ws in roadmap:
        if ws.status not in by_status:
            by_status[ws.status] = []
        by_status[ws.status].append(ws)

    status_emoji = {
        WorkStreamStatus.NOT_STARTED: "⚪",
        WorkStreamStatus.IN_PROGRESS: "🔄",
        WorkStreamStatus.COMPLETE: "✅",
        WorkStreamStatus.BLOCKED: "🔴",
    }

    status_color = {
        WorkStreamStatus.NOT_STARTED: Colors.YELLOW,
        WorkStreamStatus.IN_PROGRESS: Colors.BLUE,
        WorkStreamStatus.COMPLETE: Colors.GREEN,
        WorkStreamStatus.BLOCKED: Colors.RED,
    }

    # Print summary
    print(f"\n{colored('Summary:', Colors.BOLD)}")
    for status in WorkStreamStatus:
        count = len(by_status.get(status, []))
        emoji = status_emoji[status]
        color = status_color[status]
        print(f"  {emoji} {colored(status.value.replace('_', ' ').title(), color)}: {count}")

    # Print available work
    available = [ws for ws in roadmap if ws.is_claimable]
    if available:
        print(f"\n{colored('Available to claim:', Colors.BOLD)}")
        for ws in available[:10]:
            print(f"  • Phase {ws.id}: {ws.name} [{ws.effort}]")
    else:
        print(f"\n{colored('No work streams available to claim.', Colors.YELLOW)}")

    # Print in-progress
    in_progress = by_status.get(WorkStreamStatus.IN_PROGRESS, [])
    if in_progress:
        print(f"\n{colored('In Progress:', Colors.BOLD)}")
        for ws in in_progress:
            assigned = ws.assigned_to or "unassigned"
            print(f"  • Phase {ws.id}: {ws.name} [{assigned}]")

    return 0


def cmd_run(args) -> int:
    """Run a single work stream."""
    print_header("Running Single Work Stream")

    config = OrchestratorConfig(
        mode=OrchestratorMode.SINGLE,
        dry_run=args.dry_run,
    )
    orchestrator = Orchestrator(PROJECT_ROOT, config)
    orchestrator.add_event_callback(print_event)

    try:
        agent = orchestrator.run(
            work_stream_id=args.work_stream,
            on_output=lambda line: print_output("agent", line),
        )

        if agent is None:
            return 0  # Dry run

        print(f"\n{colored('Agent spawned:', Colors.CYAN)} {agent.agent_id}")
        print(f"Work stream: Phase {agent.work_stream_id}")
        print("\nWaiting for completion...")

        # Wait for agent
        orchestrator.runner.wait_for_all()

        # Print result
        if agent.state.value == "completed":
            print(f"\n{colored('✓ Agent completed successfully!', Colors.GREEN)}")

            if args.verify:
                print("\nVerifying completion...")
                results = orchestrator.verify_completion(agent)
                if results["passed"]:
                    print(colored("✓ All verification checks passed!", Colors.GREEN))
                else:
                    print(colored("✗ Some verification checks failed:", Colors.RED))
                    for check, result in results["checks"].items():
                        status = colored("✓", Colors.GREEN) if result["passed"] else colored("✗", Colors.RED)
                        print(f"  {status} {check}")
        else:
            print(f"\n{colored(f'✗ Agent {agent.state.value}', Colors.RED)}")
            if agent.exit_code:
                print(f"Exit code: {agent.exit_code}")
            return 1

        return 0

    except Exception as e:
        print(colored(f"\nError: {e}", Colors.RED))
        return 1


def cmd_parallel(args) -> int:
    """Run multiple work streams in parallel."""
    print_header("Running Parallel Work Streams")

    config = OrchestratorConfig(
        mode=OrchestratorMode.PARALLEL,
        max_concurrent_agents=args.num_agents,
        dry_run=args.dry_run,
    )
    orchestrator = Orchestrator(PROJECT_ROOT, config)
    orchestrator.add_event_callback(print_event)

    try:
        agents = orchestrator.run_parallel(
            max_agents=args.num_agents,
            on_output=lambda agent_id, line: print_output(agent_id, line),
        )

        if not agents:
            print(colored("No agents spawned (no available work)", Colors.YELLOW))
            return 0

        print(f"\n{colored(f'Spawned {len(agents)} agents', Colors.CYAN)}")
        for agent in agents:
            print(f"  • {agent.agent_id} → Phase {agent.work_stream_id}")

        print("\nWaiting for completion...")
        orchestrator.runner.wait_for_all()

        # Print results
        print_header("Results")
        for agent in agents:
            status_color = Colors.GREEN if agent.state.value == "completed" else Colors.RED
            print(f"  [{colored(agent.state.value, status_color)}] {agent.work_stream_id}")
            if agent.personal_name:
                print(f"      Agent: {agent.personal_name}")
            if agent.duration_seconds:
                print(f"      Duration: {agent.duration_seconds:.1f}s")

        return 0

    except Exception as e:
        print(colored(f"\nError: {e}", Colors.RED))
        return 1


def cmd_batch(args) -> int:
    """Complete all available work in the current batch."""
    print_header("Running Batch Execution")

    config = OrchestratorConfig(
        mode=OrchestratorMode.BATCH,
        max_concurrent_agents=args.num_agents,
        dry_run=args.dry_run,
    )
    orchestrator = Orchestrator(PROJECT_ROOT, config)
    orchestrator.add_event_callback(print_event)

    try:
        print("Starting batch execution...")
        agents = orchestrator.run_batch(
            on_output=lambda agent_id, line: print_output(agent_id, line),
            wait=True,
        )

        print_header("Batch Complete")
        print(f"Total agents run: {len(agents)}")

        # Summary
        completed = sum(1 for a in agents if a.state.value == "completed")
        failed = sum(1 for a in agents if a.state.value != "completed")

        print(f"  {colored(f'✓ Completed: {completed}', Colors.GREEN)}")
        if failed:
            print(f"  {colored(f'✗ Failed: {failed}', Colors.RED)}")

        return 0 if failed == 0 else 1

    except KeyboardInterrupt:
        print(colored("\n\nInterrupted! Stopping agents...", Colors.YELLOW))
        orchestrator.stop()
        return 130


def cmd_stop(args) -> int:
    """Stop all running agents."""
    print_header("Stopping All Agents")

    orchestrator = Orchestrator(PROJECT_ROOT)
    killed = orchestrator.stop()

    print(f"Stopped {killed} agent(s)")
    return 0


def cmd_garden(args=None) -> int:
    """Garden the roadmap - clear blockers and update status."""
    print_header("Roadmap Gardening")

    # Check health first
    health = check_roadmap_health()
    print(f"\n{colored('Current Health:', Colors.BOLD)}")
    print(f"  Total phases: {health['total_phases']}")
    print(f"  Available for work: {health['available_for_work']}")

    if health['issues']:
        print(f"\n{colored('Issues Found:', Colors.YELLOW)}")
        for issue in health['issues']:
            print(f"  ⚠️  {issue}")

    # Apply gardening
    print(f"\n{colored('Applying gardening...', Colors.BOLD)}")
    results = garden_roadmap()

    if results['unblocked']:
        print(f"\n{colored('✅ Unblocked Phases:', Colors.GREEN)}")
        for item in results['unblocked']:
            print(f"  • Phase {item['id']}: {item['name']}")
            print(f"    Reason: {item['reason']}")

    if results['still_blocked']:
        print(f"\n{colored('🔴 Still Blocked:', Colors.YELLOW)}")
        for item in results['still_blocked'][:5]:  # Show first 5
            deps = ", ".join(item.get('pending_deps', []))
            print(f"  • Phase {item['id']}: {item['name']}")
            print(f"    Waiting on: {deps}")
        if len(results['still_blocked']) > 5:
            print(f"  ... and {len(results['still_blocked']) - 5} more")

    if not results['unblocked'] and not health['issues']:
        print(colored("\n✓ Roadmap is healthy - no changes needed.", Colors.GREEN))

    return 0


def cmd_agents(args=None) -> int:
    """List available agents."""
    print_header("Available Agents")

    try:
        from src.orchestrator.agent_runner import AgentRunner
        runner = AgentRunner(PROJECT_ROOT)
        available = runner.get_available_agents()

        if available:
            print(f"\n{colored('Known Agents:', Colors.BOLD)}")
            for name, info in available.items():
                print(f"\n  {colored(name, Colors.CYAN)}")
                print(f"    Role: {info.get('role', 'unknown')}")
                print(f"    Memory entries: {info.get('memory_count', 0)}")
                completed = info.get('completed_phases', [])
                if completed:
                    print(f"    Completed phases: {', '.join(completed)}")
        else:
            print("\nNo agents have claimed names yet.")
            print("Agents will claim names when they start working.")
    except Exception as e:
        print(colored(f"Error loading agents: {e}", Colors.RED))

    return 0


def cmd_report(args) -> int:
    """Show detailed report."""
    print_header("Orchestrator Report")

    orchestrator = Orchestrator(PROJECT_ROOT)
    report = orchestrator.get_report()

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"\n{colored('Configuration:', Colors.BOLD)}")
        print(f"  Mode: {report['config']['mode']}")
        print(f"  Max concurrent: {report['config']['max_concurrent']}")
        print(f"  Timeout: {report['config']['timeout']}s")

        print(f"\n{colored('Roadmap:', Colors.BOLD)}")
        print(f"  Total work streams: {report['roadmap_status']['total']}")
        print(f"  Available: {report['roadmap_status']['available']}")

        if report['roadmap_status']['next_available']:
            print(f"\n{colored('Next available:', Colors.BOLD)}")
            for ws in report['roadmap_status']['next_available']:
                print(f"  • {ws}")

        print(f"\n{colored('Agents:', Colors.BOLD)}")
        agent_status = report['agent_status']
        print(f"  Total: {agent_status['total']}")
        print(f"  Running: {agent_status['running']}")
        print(f"  Completed: {agent_status['completed']}")
        print(f"  Failed: {agent_status['failed']}")

    return 0


def cmd_goal(args) -> int:
    """Run based on a natural language goal."""
    print_header("Goal-Based Execution")

    goal = args.goal
    print(f"\n{colored('Your goal:', Colors.BOLD)} {goal}\n")

    # Interpret the goal
    result = interpret_goal(goal, PROJECT_ROOT / "plans" / "roadmap.md")

    print(f"{colored('Interpretation:', Colors.BOLD)} {result.explanation}")
    print(f"Confidence: {result.confidence:.0%}")

    if not result.matched_work_streams:
        print(colored("\nNo matching work streams found.", Colors.YELLOW))
        return 0

    print(f"\n{colored('Matched work streams:', Colors.BOLD)}")
    for ws in result.matched_work_streams:
        print(f"  • Phase {ws.id}: {ws.name} [{ws.effort}]")

    # Ask for confirmation unless auto mode
    if not args.auto:
        print(f"\n{colored('Proceed?', Colors.BOLD)} [y/N] ", end="")
        try:
            response = input().strip().lower()
            if response not in ("y", "yes"):
                print("Aborted.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 0

    # Execute based on suggested action
    config = OrchestratorConfig(dry_run=args.dry_run)
    orchestrator = Orchestrator(PROJECT_ROOT, config)
    orchestrator.add_event_callback(print_event)

    if args.dry_run:
        print(colored("\n[Dry run - no agents spawned]", Colors.YELLOW))
        return 0

    if result.suggested_action == "run_single" or len(result.matched_work_streams) == 1:
        ws = result.matched_work_streams[0]
        print(f"\nSpawning agent for Phase {ws.id}...")
        agent = orchestrator.run(
            work_stream_id=ws.id,
            on_output=lambda line: print_output("agent", line),
        )
        orchestrator.runner.wait_for_all()

        if agent.state.value == "completed":
            print(colored("\n✓ Goal accomplished!", Colors.GREEN))
        else:
            print(colored(f"\n✗ Agent {agent.state.value}", Colors.RED))
            return 1

    elif result.suggested_action in ("run_parallel", "run_batch"):
        work_stream_ids = [ws.id for ws in result.matched_work_streams]
        print(f"\nSpawning {len(work_stream_ids)} agents in parallel...")
        agents = orchestrator.run_parallel(
            work_stream_ids=work_stream_ids,
            on_output=lambda agent_id, line: print_output(agent_id, line),
        )
        orchestrator.runner.wait_for_all()

        completed = sum(1 for a in agents if a.state.value == "completed")
        print(f"\n{colored(f'Completed: {completed}/{len(agents)}', Colors.GREEN if completed == len(agents) else Colors.YELLOW)}")

    return 0


def cmd_interactive(args) -> int:
    """Interactive mode - talk to the orchestrator."""
    print_header("Interactive Orchestrator")
    print("""
Welcome to the Interactive Orchestrator!

You can:
  • Express goals in natural language
  • Ask about status
  • Stop or control agents
  • Type 'help' for commands, 'quit' to exit
""")

    orchestrator = Orchestrator(PROJECT_ROOT)
    orchestrator.add_event_callback(print_event)

    while True:
        try:
            print(f"\n{colored('You:', Colors.CYAN)} ", end="")
            user_input = input().strip()

            if not user_input:
                continue

            # Handle special commands
            lower_input = user_input.lower()

            if lower_input in ("quit", "exit", "q"):
                print(colored("Goodbye!", Colors.GREEN))
                break

            elif lower_input == "help":
                print("""
Commands:
  status      - Show roadmap status
  running     - Show running agents
  stop        - Stop all agents
  stop <id>   - Stop specific agent
  report      - Show detailed report
  quit/exit   - Exit interactive mode

Or just type your goal in natural language:
  "Start working on the task parser"
  "Run all available work in parallel"
  "What's the status of phase 1.2?"
""")
                continue

            elif lower_input == "status":
                cmd_status(argparse.Namespace())
                continue

            elif lower_input == "running":
                running = orchestrator.runner.get_running_agents()
                if running:
                    print(f"\n{colored('Running agents:', Colors.BOLD)}")
                    for agent in running:
                        name = agent.personal_name or agent.agent_id
                        print(f"  • {name} → Phase {agent.work_stream_id}")
                        if agent.duration_seconds:
                            print(f"      Running for {agent.duration_seconds:.0f}s")
                else:
                    print("No agents currently running.")
                continue

            elif lower_input == "stop":
                killed = orchestrator.stop()
                print(f"Stopped {killed} agent(s)")
                continue

            elif lower_input.startswith("stop "):
                agent_id = lower_input[5:].strip()
                if orchestrator.runner.kill_agent(agent_id):
                    print(f"Stopped agent {agent_id}")
                else:
                    print(f"Agent {agent_id} not found or not running")
                continue

            elif lower_input == "report":
                cmd_report(argparse.Namespace(json=False))
                continue

            # Interpret as a goal
            result = interpret_goal(user_input, PROJECT_ROOT / "plans" / "roadmap.md")

            print(f"\n{colored('Orchestrator:', Colors.GREEN)}")
            print(f"  {result.explanation}")

            # Handle management commands
            if result.command_type == CommandType.GARDEN:
                cmd_garden()
                continue
            elif result.command_type == CommandType.STATUS:
                cmd_status(argparse.Namespace())
                continue
            elif result.command_type == CommandType.LIST_AGENTS:
                cmd_agents()
                continue
            elif result.command_type == CommandType.STOP:
                killed = orchestrator.stop()
                print(f"  Stopped {killed} agent(s)")
                continue
            elif result.command_type == CommandType.HELP:
                print("""
Commands:
  status      - Show roadmap status
  running     - Show running agents
  agents      - List known agents
  garden      - Clear blockers and update roadmap
  stop        - Stop all agents
  stop <id>   - Stop specific agent
  report      - Show detailed report
  quit/exit   - Exit interactive mode

Or just type your goal in natural language:
  "Start working on the task parser"
  "Run all available work in parallel"
  "Clear the blockers"
  "Show me the agents"
""")
                continue

            if result.matched_work_streams:
                print(f"\n  Matched work streams:")
                for ws in result.matched_work_streams:
                    print(f"    • Phase {ws.id}: {ws.name}")

                if result.confidence >= 0.5:
                    print(f"\n  {colored('Would you like me to start working on this? [y/N]', Colors.BOLD)} ", end="")
                    response = input().strip().lower()

                    if response in ("y", "yes"):
                        if len(result.matched_work_streams) == 1:
                            ws = result.matched_work_streams[0]
                            print(f"\n  Spawning agent for Phase {ws.id}...")
                            try:
                                agent = orchestrator.run(
                                    work_stream_id=ws.id,
                                    on_output=lambda line: print(f"    {line}"),
                                )
                                print(f"  Agent {agent.agent_id} is now working.")
                                print("  (Use 'running' to check status, 'stop' to halt)")
                            except Exception as e:
                                print(colored(f"  Error: {e}", Colors.RED))
                        else:
                            print(f"\n  Spawning {len(result.matched_work_streams)} agents...")
                            try:
                                agents = orchestrator.run_parallel(
                                    work_stream_ids=[ws.id for ws in result.matched_work_streams],
                                )
                                print(f"  {len(agents)} agents are now working.")
                            except Exception as e:
                                print(colored(f"  Error: {e}", Colors.RED))
            else:
                print("  I couldn't match that to any available work.")
                print("  Try 'status' to see what's available.")

        except (EOFError, KeyboardInterrupt):
            print(colored("\n\nInterrupted. Stopping agents...", Colors.YELLOW))
            orchestrator.stop()
            break

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrator CLI - Coordinate autonomous agent teams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # status command
    status_parser = subparsers.add_parser("status", help="Show roadmap status")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a single work stream")
    run_parser.add_argument(
        "work_stream",
        nargs="?",
        help="Work stream ID (e.g., 1.2). Auto-selects if not provided.",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    run_parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip verification after completion",
    )

    # parallel command
    parallel_parser = subparsers.add_parser(
        "parallel",
        help="Run multiple work streams in parallel",
    )
    parallel_parser.add_argument(
        "-n", "--num-agents",
        type=int,
        default=3,
        help="Maximum number of concurrent agents (default: 3)",
    )
    parallel_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )

    # batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Complete all available work in current batch",
    )
    batch_parser.add_argument(
        "-n", "--num-agents",
        type=int,
        default=3,
        help="Maximum number of concurrent agents (default: 3)",
    )
    batch_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop all running agents")

    # report command
    report_parser = subparsers.add_parser("report", help="Show detailed report")
    report_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # goal command
    goal_parser = subparsers.add_parser(
        "goal",
        help="Run based on a natural language goal",
    )
    goal_parser.add_argument(
        "goal",
        help="Your goal in natural language",
    )
    goal_parser.add_argument(
        "--auto",
        action="store_true",
        help="Don't ask for confirmation",
    )
    goal_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )

    # interactive command
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Interactive mode - talk to the orchestrator",
    )

    # garden command
    garden_parser = subparsers.add_parser(
        "garden",
        help="Garden the roadmap - clear blockers and update status",
    )

    # agents command
    agents_parser = subparsers.add_parser(
        "agents",
        help="List known agents",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "status": cmd_status,
        "run": cmd_run,
        "parallel": cmd_parallel,
        "batch": cmd_batch,
        "stop": cmd_stop,
        "report": cmd_report,
        "goal": cmd_goal,
        "interactive": cmd_interactive,
        "garden": cmd_garden,
        "agents": cmd_agents,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
