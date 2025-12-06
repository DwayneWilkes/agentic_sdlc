"""
Live Agent Dashboard - Real-time view of all agents with interactive controls.

Features:
- Live status updates via NATS subscription
- Agent list with status, work stream, duration
- Interactive commands: stop, query, update goal
- Keyboard shortcuts for quick actions
"""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from src.coordination.nats_bus import AgentMessage, MessageType, NATSMessageBus, get_message_bus
from src.orchestrator.agent_runner import AgentRunner, get_coordinator


@dataclass
class AgentInfo:
    """Tracked information about an agent."""
    agent_id: str
    personal_name: str | None = None
    work_stream_id: str | None = None
    status: str = "unknown"
    started_at: datetime | None = None
    last_update: datetime | None = None
    details: dict = field(default_factory=dict)

    @property
    def duration(self) -> str:
        """Get human-readable duration."""
        if not self.started_at:
            return "-"
        delta = datetime.now() - self.started_at
        if delta.total_seconds() < 60:
            return f"{int(delta.total_seconds())}s"
        elif delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds() / 60)}m"
        else:
            hours = int(delta.total_seconds() / 3600)
            mins = int((delta.total_seconds() % 3600) / 60)
            return f"{hours}h {mins}m"

    @property
    def status_emoji(self) -> str:
        """Get emoji for status."""
        return {
            "started": "🔄",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "stopped": "⏹️",
            "unknown": "❓",
        }.get(self.status, "❓")


class AgentDashboard:
    """
    Live dashboard for monitoring and controlling agents.

    Subscribes to NATS for real-time updates and provides
    interactive controls for agent management.
    """

    def __init__(self, runner: AgentRunner | None = None):
        """
        Initialize the dashboard.

        Args:
            runner: Optional AgentRunner instance. If not provided,
                   dashboard operates in monitor-only mode.
        """
        self.runner = runner or AgentRunner()
        self.console = Console()
        self.agents: dict[str, AgentInfo] = {}
        self._lock = threading.Lock()
        self._running = False
        self._nats_bus: NATSMessageBus | None = None
        self._command_queue: asyncio.Queue = asyncio.Queue()
        self._last_refresh = datetime.now()

    async def start(self) -> None:
        """Start the dashboard with NATS subscription."""
        self._running = True

        # Connect to NATS
        try:
            self._nats_bus = await get_message_bus()
            await self._subscribe_to_updates()
            self.console.print("[green]Connected to NATS[/green]")
        except Exception as e:
            self.console.print(f"[yellow]NATS unavailable: {e}[/yellow]")
            self.console.print("[yellow]Running in local-only mode[/yellow]")

        # Start the live display
        await self._run_live_display()

    async def _subscribe_to_updates(self) -> None:
        """Subscribe to agent status updates via NATS."""
        if not self._nats_bus:
            return

        # Subscribe to all broadcasts
        await self._nats_bus.subscribe(
            subject="orchestrator.broadcast.>",
            callback=self._handle_message
        )

    async def _handle_message(self, msg: AgentMessage) -> None:
        """Handle incoming NATS message."""
        with self._lock:
            agent_id = msg.from_agent
            content = msg.content

            # Get or create agent info
            if agent_id not in self.agents:
                self.agents[agent_id] = AgentInfo(agent_id=agent_id)

            agent = self.agents[agent_id]
            agent.last_update = datetime.now()

            # Update based on message type
            if msg.message_type == MessageType.STATUS_UPDATE:
                status = content.get("status", "unknown")
                agent.status = status
                agent.work_stream_id = content.get("work_stream_id")
                agent.personal_name = content.get("personal_name")
                agent.details = content

                if status == "started":
                    agent.started_at = datetime.now()

            elif msg.message_type == MessageType.TASK_ASSIGNED:
                agent.work_stream_id = content.get("work_stream_id")
                agent.status = "claimed"

            elif msg.message_type == MessageType.TASK_COMPLETE:
                agent.status = "completed"

            elif msg.message_type == MessageType.TASK_FAILED:
                agent.status = "failed"

    def _sync_from_runner(self) -> None:
        """Sync agent info from the runner."""
        if not self.runner:
            return

        with self._lock:
            for agent_id, process in self.runner.agents.items():
                if agent_id not in self.agents:
                    self.agents[agent_id] = AgentInfo(agent_id=agent_id)

                agent = self.agents[agent_id]
                agent.personal_name = process.personal_name
                agent.work_stream_id = process.work_stream_id
                agent.started_at = process.started_at
                agent.status = process.state.value
                agent.last_update = datetime.now()

    def _build_display(self) -> Layout:
        """Build the dashboard display."""
        layout = Layout()

        # Create header
        header = Panel(
            Text("🤖 Agent Dashboard", style="bold cyan", justify="center"),
            subtitle=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}",
        )

        # Create agent table
        table = Table(
            title="Active Agents",
            show_header=True,
            header_style="bold magenta",
            expand=True,
        )
        table.add_column("Status", width=3)
        table.add_column("Name", style="cyan")
        table.add_column("Agent ID", style="dim")
        table.add_column("Work Stream", style="green")
        table.add_column("Duration", justify="right")
        table.add_column("Last Update", style="dim")

        # Sync from runner
        self._sync_from_runner()

        # Add rows
        with self._lock:
            sorted_agents = sorted(
                self.agents.items(),
                key=lambda x: x[1].started_at or datetime.min,
                reverse=True,
            )
            for agent_id, agent in sorted_agents:
                last_update = ""
                if agent.last_update:
                    delta = datetime.now() - agent.last_update
                    if delta.total_seconds() < 60:
                        last_update = f"{int(delta.total_seconds())}s ago"
                    else:
                        last_update = f"{int(delta.total_seconds() / 60)}m ago"

                table.add_row(
                    agent.status_emoji,
                    agent.personal_name or "-",
                    agent_id[:30] + "..." if len(agent_id) > 30 else agent_id,
                    agent.work_stream_id or "-",
                    agent.duration,
                    last_update,
                )

        # Add claimed streams
        coordinator = get_coordinator()
        claimed = coordinator.get_claimed_streams()

        claims_text = ""
        if claimed:
            claims_text = "Claimed: " + ", ".join(f"{ws}→{aid[:8]}" for ws, aid in claimed.items())
        else:
            claims_text = "No work streams claimed"

        # Create commands panel
        commands = Panel(
            Text.from_markup(
                "[bold]Commands:[/bold]\n"
                "  [cyan]s[/cyan] - Stop agent (select from list)\n"
                "  [cyan]S[/cyan] - Stop ALL agents\n"
                "  [cyan]q[/cyan] - Query agent status\n"
                "  [cyan]g[/cyan] - Update agent goal\n"
                "  [cyan]r[/cyan] - Refresh\n"
                "  [cyan]c[/cyan] - Clear completed\n"
                "  [cyan]Ctrl+C[/cyan] - Exit\n\n"
                f"[dim]{claims_text}[/dim]"
            ),
            title="Controls",
            border_style="blue",
        )

        # Stats
        with self._lock:
            running = sum(1 for a in self.agents.values() if a.status in ("started", "running"))
            completed = sum(1 for a in self.agents.values() if a.status == "completed")
            failed = sum(1 for a in self.agents.values() if a.status == "failed")

        stats = Panel(
            Text.from_markup(
                f"[green]Running: {running}[/green]  "
                f"[blue]Completed: {completed}[/blue]  "
                f"[red]Failed: {failed}[/red]  "
                f"Total: {len(self.agents)}"
            ),
            title="Stats",
            border_style="green",
        )

        # Compose layout
        layout.split_column(
            Layout(header, size=3),
            Layout(stats, size=3),
            Layout(table, name="agents"),
            Layout(commands, size=12),
        )

        return layout

    async def _run_live_display(self) -> None:
        """Run the live updating display."""
        try:
            with Live(self._build_display(), console=self.console, refresh_per_second=2) as live:
                while self._running:
                    # Update display
                    self._last_refresh = datetime.now()
                    live.update(self._build_display())

                    # Check for keyboard input (non-blocking)
                    await asyncio.sleep(0.5)

        except KeyboardInterrupt:
            self._running = False
            self.console.print("\n[yellow]Dashboard stopped[/yellow]")

    def stop_agent_interactive(self) -> None:
        """Interactive prompt to stop an agent."""
        with self._lock:
            running_agents = [
                (aid, a) for aid, a in self.agents.items()
                if a.status in ("started", "running")
            ]

        if not running_agents:
            self.console.print("[yellow]No running agents to stop[/yellow]")
            return

        self.console.print("\n[bold]Running agents:[/bold]")
        for i, (aid, agent) in enumerate(running_agents):
            name = agent.personal_name or aid[:20]
            self.console.print(f"  {i+1}. {name} ({agent.work_stream_id})")

        try:
            choice = Prompt.ask("Select agent to stop (number or 'all')")

            if choice.lower() == "all":
                if Confirm.ask("Stop ALL agents?"):
                    count = self.runner.stop_all_agents(graceful=True)
                    self.console.print(f"[green]Sent stop to {count} agents[/green]")
            else:
                idx = int(choice) - 1
                if 0 <= idx < len(running_agents):
                    agent_id = running_agents[idx][0]
                    graceful = Confirm.ask("Graceful stop?", default=True)
                    if self.runner.send_stop_command(agent_id, graceful=graceful):
                        self.console.print("[green]Stop command sent[/green]")
                    else:
                        self.console.print("[red]Failed to send stop[/red]")
        except (ValueError, KeyboardInterrupt):
            pass

    def query_agent_interactive(self) -> None:
        """Interactive prompt to query agent details."""
        with self._lock:
            agents_list = list(self.agents.items())

        if not agents_list:
            self.console.print("[yellow]No agents to query[/yellow]")
            return

        self.console.print("\n[bold]Agents:[/bold]")
        for i, (aid, agent) in enumerate(agents_list):
            name = agent.personal_name or aid[:20]
            self.console.print(f"  {i+1}. {agent.status_emoji} {name}")

        try:
            choice = Prompt.ask("Select agent (number)")
            idx = int(choice) - 1
            if 0 <= idx < len(agents_list):
                agent_id, agent = agents_list[idx]

                self.console.print(Panel(
                    f"[bold]Agent ID:[/bold] {agent_id}\n"
                    f"[bold]Name:[/bold] {agent.personal_name or 'N/A'}\n"
                    f"[bold]Work Stream:[/bold] {agent.work_stream_id or 'N/A'}\n"
                    f"[bold]Status:[/bold] {agent.status}\n"
                    f"[bold]Duration:[/bold] {agent.duration}\n"
                    f"[bold]Details:[/bold] {agent.details}",
                    title=f"Agent: {agent.personal_name or agent_id[:20]}",
                ))
        except (ValueError, KeyboardInterrupt):
            pass

    def update_goal_interactive(self) -> None:
        """Interactive prompt to update agent goal."""
        with self._lock:
            running_agents = [
                (aid, a) for aid, a in self.agents.items()
                if a.status in ("started", "running")
            ]

        if not running_agents:
            self.console.print("[yellow]No running agents[/yellow]")
            return

        self.console.print("\n[bold]Running agents:[/bold]")
        for i, (aid, agent) in enumerate(running_agents):
            name = agent.personal_name or aid[:20]
            self.console.print(f"  {i+1}. {name} ({agent.work_stream_id})")

        try:
            choice = Prompt.ask("Select agent (number)")
            idx = int(choice) - 1
            if 0 <= idx < len(running_agents):
                agent_id = running_agents[idx][0]
                new_goal = Prompt.ask("New goal/task")
                reason = Prompt.ask("Reason", default="Priority change")

                if self.runner.send_update_goal_command(agent_id, new_goal, reason):
                    self.console.print("[green]Goal update sent[/green]")
                else:
                    self.console.print("[red]Failed to send update[/red]")
        except (ValueError, KeyboardInterrupt):
            pass

    def clear_completed(self) -> None:
        """Remove completed/failed agents from display."""
        with self._lock:
            to_remove = [
                aid for aid, a in self.agents.items()
                if a.status in ("completed", "failed", "stopped")
            ]
            for aid in to_remove:
                del self.agents[aid]

        self.console.print(f"[green]Cleared {len(to_remove)} agents[/green]")


async def run_dashboard(runner: AgentRunner | None = None) -> None:
    """Run the live dashboard."""
    dashboard = AgentDashboard(runner)
    await dashboard.start()


def main():
    """Entry point for the dashboard."""
    import argparse

    parser = argparse.ArgumentParser(description="Live Agent Dashboard")
    parser.add_argument("--no-nats", action="store_true", help="Run without NATS")
    _args = parser.parse_args()  # Currently unused, reserved for future flags

    console = Console()
    console.print("[bold cyan]Starting Agent Dashboard...[/bold cyan]")

    try:
        asyncio.run(run_dashboard())
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")


if __name__ == "__main__":
    main()
