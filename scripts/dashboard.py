#!/usr/bin/env python3
"""
Live Agent Dashboard - Real-time monitoring and control of agents.

Usage:
    python scripts/dashboard.py           # Start live dashboard
    python scripts/dashboard.py --watch   # Watch mode (no interaction)
    python scripts/dashboard.py --status  # One-time status report
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import re
import subprocess

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from src.orchestrator.agent_runner import AgentRunner, AgentState, get_coordinator

console = Console()


def get_roadmap_assignments(project_root: Path) -> dict[str, str]:
    """
    Read roadmap.md to find work streams assigned to agents.

    Returns dict mapping personal_name -> work_stream_id
    """
    roadmap_path = project_root / "plans" / "roadmap.md"
    assignments = {}

    if not roadmap_path.exists():
        return assignments

    try:
        content = roadmap_path.read_text()
        # Split into sections by phase header, then find in-progress ones
        section_pattern = re.compile(r"(### Phase \d+\.\d+:.*?)(?=### Phase|\Z)", re.DOTALL)

        for section_match in section_pattern.finditer(content):
            section = section_match.group(1)
            # Check if this section is In Progress
            if "🔄 In Progress" not in section:
                continue

            # Extract phase ID from header
            phase_match = re.match(r"### Phase (\d+\.\d+):", section)
            if not phase_match:
                continue
            phase_id = phase_match.group(1)

            # Extract assigned agent
            assigned_match = re.search(r"\*\*Assigned To:\*\*\s*(\w+)", section)
            if assigned_match:
                agent_name = assigned_match.group(1)
                if agent_name and agent_name != "-":
                    assignments[agent_name] = phase_id
    except Exception:
        pass

    return assignments


def detect_running_agents(project_root: Path | None = None) -> list[dict]:
    """
    Detect running agents by checking multiple sources:
    1. Recent log files with active writes
    2. Running claude processes
    3. Recently claimed agent names
    4. Roadmap assignments

    Returns list of detected agent info dicts.
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    detected = []
    project_name = project_root.name
    log_dir = project_root / "agent-logs" / project_name  # Project-specific logs
    config_file = project_root / "config" / "agent_names.json"

    # Check for running claude processes
    try:
        result = subprocess.run(
            ["pgrep", "-f", "claude.*dangerously-skip-permissions"],
            capture_output=True, text=True
        )
        running_pids = result.stdout.strip().split() if result.returncode == 0 else []
    except Exception:
        running_pids = []

    # Check recent log files (modified in last 5 minutes)
    recent_logs = []
    if log_dir.exists():
        now = datetime.now().timestamp()
        for log_file in log_dir.glob("autonomous-agent-*.log"):
            mtime = log_file.stat().st_mtime
            if now - mtime < 300:  # Modified in last 5 minutes
                recent_logs.append(log_file)

    # Get work stream assignments from roadmap
    roadmap_assignments = get_roadmap_assignments(project_root)

    # Check agent_names.json for recent claims
    recent_claims = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            assigned = config.get("assigned_names", {})
            now = datetime.now()
            for agent_id, info in assigned.items():
                claimed_at_str = info.get("claimed_at", "")
                if claimed_at_str:
                    claimed_at = datetime.fromisoformat(claimed_at_str)
                    # If claimed in last 30 minutes, might be running
                    if (now - claimed_at).total_seconds() < 1800:
                        recent_claims[agent_id] = info
        except Exception:
            pass

    # Combine info: running processes + recent claims = likely active agent
    for agent_id, info in recent_claims.items():
        # Try to find matching log
        log_file = None
        personal_name = info.get("name")

        # Look up work stream from roadmap assignments
        work_stream = roadmap_assignments.get(personal_name)

        # Check for active log by timestamp in agent_id
        for log in recent_logs:
            if log.stat().st_mtime > datetime.now().timestamp() - 60:  # Active in last minute
                log_file = log
                break

        # Determine if likely running:
        # - Process running + recent claim, OR
        # - Active log file, OR
        # - Assigned in roadmap (in progress)
        is_running = (
            len(running_pids) > 0 or
            (log_file is not None) or
            (work_stream is not None)  # Assigned in roadmap = likely running
        )

        detected.append({
            "agent_id": agent_id,
            "personal_name": personal_name,
            "role": info.get("role"),
            "claimed_at": info.get("claimed_at"),
            "work_stream": work_stream,
            "log_file": str(log_file) if log_file else None,
            "is_running": is_running,
            "source": "detected",
        })

    return detected


def get_agent_table(runner: AgentRunner, project_root: Path | None = None) -> Table:
    """Build a table of all agents (tracked + detected)."""
    table = Table(
        title="🤖 Agents",
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("St", width=2)
    table.add_column("Name", style="cyan", width=12)
    table.add_column("Work Stream", style="green", width=10)
    table.add_column("Agent ID", style="dim", width=25)
    table.add_column("Duration", justify="right", width=8)
    table.add_column("Exit", justify="center", width=4)

    status_emoji = {
        AgentState.PENDING: "⏳",
        AgentState.RUNNING: "🔄",
        AgentState.COMPLETED: "✅",
        AgentState.FAILED: "❌",
        AgentState.TIMEOUT: "⏰",
        AgentState.KILLED: "⏹️",
    }

    # Track agent IDs we've already shown
    shown_ids = set()

    # First, show agents from the runner (tracked by this process)
    for agent_id, process in sorted(
        runner.agents.items(),
        key=lambda x: x[1].started_at or datetime.min,
        reverse=True,
    ):
        shown_ids.add(agent_id)

        duration = "-"
        if process.duration_seconds:
            secs = int(process.duration_seconds)
            if secs < 60:
                duration = f"{secs}s"
            elif secs < 3600:
                duration = f"{secs // 60}m {secs % 60}s"
            else:
                duration = f"{secs // 3600}h {(secs % 3600) // 60}m"

        exit_code = str(process.exit_code) if process.exit_code is not None else "-"

        table.add_row(
            status_emoji.get(process.state, "❓"),
            process.personal_name or "-",
            process.work_stream_id or "-",
            agent_id[:25] + "..." if len(agent_id) > 25 else agent_id,
            duration,
            exit_code,
        )

    # Then, add detected agents (from other processes)
    detected = detect_running_agents(project_root)
    for agent in detected:
        agent_id = agent["agent_id"]
        if agent_id in shown_ids:
            continue  # Already shown from runner

        # Calculate duration from claimed_at
        duration = "-"
        if agent.get("claimed_at"):
            try:
                claimed = datetime.fromisoformat(agent["claimed_at"])
                secs = int((datetime.now() - claimed).total_seconds())
                if secs < 60:
                    duration = f"{secs}s"
                elif secs < 3600:
                    duration = f"{secs // 60}m {secs % 60}s"
                else:
                    duration = f"{secs // 3600}h {(secs % 3600) // 60}m"
            except Exception:
                pass

        # Status based on detection
        status = "🔄" if agent.get("is_running") else "❓"

        table.add_row(
            status,
            agent.get("personal_name") or "-",
            agent.get("work_stream") or "-",
            agent_id[:25] + "..." if len(agent_id) > 25 else agent_id,
            duration,
            "-",
        )

    if not runner.agents and not detected:
        table.add_row("-", "[dim]No agents[/dim]", "-", "-", "-", "-")

    return table


def get_claims_table(project_root: Path | None = None) -> Table:
    """Build a table of claimed work streams from roadmap."""
    if project_root is None:
        project_root = Path(__file__).parent.parent

    # Get assignments from roadmap (more reliable than in-memory coordinator)
    assignments = get_roadmap_assignments(project_root)

    # Also check coordinator for any additional claims
    coordinator = get_coordinator()
    claimed = coordinator.get_claimed_streams()

    table = Table(title="📋 Claimed Work Streams", show_header=True, expand=True)
    table.add_column("Work Stream", style="green")
    table.add_column("Claimed By", style="cyan")

    # Combine roadmap and coordinator claims
    all_claims = {}
    for agent_name, phase_id in assignments.items():
        all_claims[phase_id] = agent_name
    for ws, agent_id in claimed.items():
        if ws not in all_claims:
            all_claims[ws] = agent_id[:30]

    if all_claims:
        for ws, agent in sorted(all_claims.items()):
            table.add_row(ws, agent)
    else:
        table.add_row("-", "[dim]None[/dim]")

    return table


def get_stats_panel(runner: AgentRunner, project_root: Path | None = None) -> Panel:
    """Build stats panel."""
    running = sum(1 for a in runner.agents.values() if a.state == AgentState.RUNNING)
    completed = sum(1 for a in runner.agents.values() if a.state == AgentState.COMPLETED)
    failed = sum(1 for a in runner.agents.values() if a.state == AgentState.FAILED)
    pending = sum(1 for a in runner.agents.values() if a.state == AgentState.PENDING)

    # Also count detected agents
    detected = detect_running_agents(project_root)
    detected_running = sum(
        1 for d in detected
        if d.get("is_running") and d["agent_id"] not in runner.agents
    )
    detected_new = [d for d in detected if d["agent_id"] not in runner.agents]
    total = len(runner.agents) + len(detected_new)

    return Panel(
        Text.from_markup(
            f"[yellow]Pending: {pending}[/yellow]  "
            f"[green]Running: {running + detected_running}[/green]  "
            f"[blue]Completed: {completed}[/blue]  "
            f"[red]Failed: {failed}[/red]  "
            f"[dim]Total: {total}[/dim]"
        ),
        title="Stats",
        border_style="green",
    )


def build_layout(runner: AgentRunner, project_root: Path | None = None) -> Layout:
    """Build the dashboard layout."""
    layout = Layout()

    layout.split_column(
        Layout(
            Panel(
                Text("🤖 Agent Dashboard", style="bold cyan", justify="center"),
                subtitle=f"Updated: {datetime.now().strftime('%H:%M:%S')}",
            ),
            size=3,
        ),
        Layout(get_stats_panel(runner, project_root), size=3),
        Layout(get_agent_table(runner, project_root), name="agents"),
        Layout(get_claims_table(project_root), size=8),
        Layout(
            Panel(
                Text.from_markup(
                    "[bold]Commands:[/bold] "
                    "[cyan]s[/cyan]=stop agent  "
                    "[cyan]S[/cyan]=stop all  "
                    "[cyan]q[/cyan]=query  "
                    "[cyan]g[/cyan]=update goal  "
                    "[cyan]c[/cyan]=clear done  "
                    "[cyan]Ctrl+C[/cyan]=exit"
                ),
                border_style="blue",
            ),
            size=3,
        ),
    )

    return layout


def status_report(runner: AgentRunner, project_root: Path | None = None) -> None:
    """Print one-time status report."""
    console.print(get_stats_panel(runner, project_root))
    console.print(get_agent_table(runner, project_root))
    console.print(get_claims_table(project_root))


def stop_agent_prompt(runner: AgentRunner) -> None:
    """Interactive stop agent."""
    running = [(aid, a) for aid, a in runner.agents.items() if a.state == AgentState.RUNNING]

    if not running:
        console.print("[yellow]No running agents[/yellow]")
        return

    console.print("\n[bold]Running agents:[/bold]")
    for i, (aid, agent) in enumerate(running):
        console.print(f"  {i+1}. {agent.personal_name or aid[:20]} ({agent.work_stream_id})")

    try:
        choice = Prompt.ask("Agent # to stop (or 'all')")
        if choice.lower() == "all":
            if Confirm.ask("Stop ALL agents?"):
                count = runner.stop_all_agents(graceful=True)
                console.print(f"[green]Stopped {count} agents[/green]")
        else:
            idx = int(choice) - 1
            if 0 <= idx < len(running):
                agent_id = running[idx][0]
                graceful = Confirm.ask("Graceful?", default=True)
                runner.send_stop_command(agent_id, graceful=graceful)
                console.print("[green]Stop sent[/green]")
    except (ValueError, KeyboardInterrupt):
        pass


def query_agent_prompt(runner: AgentRunner) -> None:
    """Interactive query agent."""
    agents = list(runner.agents.items())

    if not agents:
        console.print("[yellow]No agents[/yellow]")
        return

    console.print("\n[bold]Agents:[/bold]")
    for i, (aid, agent) in enumerate(agents):
        console.print(f"  {i+1}. {agent.personal_name or aid[:20]}")

    try:
        choice = Prompt.ask("Agent #")
        idx = int(choice) - 1
        if 0 <= idx < len(agents):
            aid, agent = agents[idx]
            console.print(Panel(
                f"[bold]ID:[/bold] {aid}\n"
                f"[bold]Name:[/bold] {agent.personal_name}\n"
                f"[bold]Work Stream:[/bold] {agent.work_stream_id}\n"
                f"[bold]State:[/bold] {agent.state.value}\n"
                f"[bold]Duration:[/bold] {agent.duration_seconds:.1f}s\n"
                f"[bold]Exit Code:[/bold] {agent.exit_code}\n"
                f"[bold]Errors:[/bold] {len(agent.error_lines)}\n"
                f"[bold]Important Lines:[/bold]\n" +
                "\n".join(agent.important_lines[-5:] or ["None"]),
                title=agent.personal_name or aid[:20],
            ))
    except (ValueError, KeyboardInterrupt):
        pass


def update_goal_prompt(runner: AgentRunner) -> None:
    """Interactive update goal."""
    running = [(aid, a) for aid, a in runner.agents.items() if a.state == AgentState.RUNNING]

    if not running:
        console.print("[yellow]No running agents[/yellow]")
        return

    console.print("\n[bold]Running agents:[/bold]")
    for i, (aid, agent) in enumerate(running):
        console.print(f"  {i+1}. {agent.personal_name or aid[:20]}")

    try:
        choice = Prompt.ask("Agent #")
        idx = int(choice) - 1
        if 0 <= idx < len(running):
            agent_id = running[idx][0]
            new_goal = Prompt.ask("New goal")
            runner.send_update_goal_command(agent_id, new_goal)
            console.print("[green]Goal update sent[/green]")
    except (ValueError, KeyboardInterrupt):
        pass


def clear_completed(runner: AgentRunner) -> None:
    """Clear completed/failed agents from tracker."""
    to_remove = [
        aid for aid, a in runner.agents.items()
        if a.state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.KILLED)
    ]
    for aid in to_remove:
        del runner.agents[aid]
    console.print(f"[green]Cleared {len(to_remove)} agents[/green]")


async def watch_mode(runner: AgentRunner, project_root: Path | None = None) -> None:
    """Run in watch mode (auto-refresh, no interaction)."""
    try:
        layout = build_layout(runner, project_root)
        with Live(layout, console=console, refresh_per_second=1) as live:
            while True:
                live.update(build_layout(runner, project_root))
                await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/yellow]")


async def interactive_mode(runner: AgentRunner, project_root: Path | None = None) -> None:
    """Run in interactive mode."""
    import select
    import termios
    import tty

    console.print("[bold cyan]Agent Dashboard[/bold cyan]")
    console.print("Commands: [s]top [S]top-all [q]uery [g]oal [c]lear [r]efresh [x]exit")
    console.print()

    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Set terminal to raw mode for single-key input
        tty.setcbreak(sys.stdin.fileno())

        while True:
            # Show current status
            status_report(runner, project_root)
            console.print("\n[dim]Press key for command...[/dim]", end="", markup=True)

            # Wait for input with timeout
            while True:
                if select.select([sys.stdin], [], [], 2.0)[0]:
                    key = sys.stdin.read(1)
                    console.print()  # Newline after prompt

                    if key == "s":
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        stop_agent_prompt(runner)
                        tty.setcbreak(sys.stdin.fileno())
                    elif key == "S":
                        if runner.stop_all_agents():
                            console.print("[green]Stop all sent[/green]")
                    elif key == "q":
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        query_agent_prompt(runner)
                        tty.setcbreak(sys.stdin.fileno())
                    elif key == "g":
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        update_goal_prompt(runner)
                        tty.setcbreak(sys.stdin.fileno())
                    elif key == "c":
                        clear_completed(runner)
                    elif key == "r":
                        console.clear()
                    elif key in ("x", "X", "\x03"):  # x or Ctrl+C
                        raise KeyboardInterrupt

                    break
                else:
                    # Timeout - refresh display
                    console.clear()
                    break

    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/yellow]")
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def main():
    parser = argparse.ArgumentParser(description="Live Agent Dashboard")
    parser.add_argument("--watch", "-w", action="store_true",
                        help="Watch mode (auto-refresh)")
    parser.add_argument("--status", "-s", action="store_true",
                        help="One-time status")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode (default)")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    runner = AgentRunner(project_root=project_root)

    if args.status:
        status_report(runner, project_root)
    elif args.watch:
        asyncio.run(watch_mode(runner, project_root))
    else:
        asyncio.run(interactive_mode(runner, project_root))


if __name__ == "__main__":
    main()
