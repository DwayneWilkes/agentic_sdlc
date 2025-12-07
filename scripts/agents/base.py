"""Base class for Python agent launchers.

Provides shared functionality for all agent types:
- Logging setup
- Claude CLI invocation
- Prompt building helpers
- Memory system integration
"""

import os
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


# ANSI colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


@dataclass
class AgentConfig:
    """Configuration for an agent launcher."""

    agent_type: Literal["coder", "tech_lead", "pm"]
    model: Literal["sonnet", "opus"] = "sonnet"
    project_root: Path = field(default_factory=lambda: Path.cwd())
    target_path: Path | None = None
    target_name: str | None = None
    skip_permissions: bool = True

    @property
    def effective_project_root(self) -> Path:
        """Get the effective project root (target or self)."""
        return self.target_path or self.project_root

    @property
    def effective_project_name(self) -> str:
        """Get the effective project name."""
        return self.target_name or self.effective_project_root.name

    @property
    def is_external_target(self) -> bool:
        """Check if targeting an external project."""
        return self.target_path is not None


class AgentLauncher(ABC):
    """Base class for agent launchers."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.agent_id = f"{config.agent_type}-{int(datetime.now().timestamp())}"

        # Setup logging
        self.log_dir = (
            config.project_root
            / "agent-logs"
            / config.effective_project_name
        )
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{config.agent_type}-agent-{self.timestamp}.log"

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    def log_info(self, message: str) -> None:
        """Log an info message."""
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

    def log_success(self, message: str) -> None:
        """Log a success message."""
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

    def log_to_file(self, message: str) -> None:
        """Log a message to the log file."""
        with open(self.log_file, "a") as f:
            f.write(message + "\n")

    # -------------------------------------------------------------------------
    # Memory System Prompts
    # -------------------------------------------------------------------------

    def get_memory_prompt(self) -> str:
        """Get the memory system initialization prompt."""
        usage_hints = self._get_memory_usage_hints()

        return f'''MEMORY SYSTEM: You have a personal memory journal. After claiming your name, load your memories:
```python
from src.core.agent_memory import get_memory

memory = get_memory(my_chosen_name)
print('\\n=== My Memory Context ===')
print(memory.format_for_context())

for prompt in memory.get_reflection_prompts()[:3]:
    print(f'  - {{prompt}}')
```

Throughout your work, use your memory:
{usage_hints}'''

    def _get_memory_usage_hints(self) -> str:
        """Get memory usage hints for the agent type."""
        hints = {
            "coder": """- When you learn something important: memory.record_insight('what you learned', from_mistake=True/False)
- When uncertain about something: memory.note_uncertainty('what confuses you', about='topic')
- When you notice a preference: memory.discover_preference('how you work best')
- When something feels meaningful: memory.mark_meaningful('what happened')
- When you work with another agent: memory.remember_relationship('AgentName', 'observation')""",
            "tech_lead": """- When you notice patterns in code quality: memory.record_insight('pattern observed', from_mistake=False)
- When a coder does something noteworthy: memory.remember_relationship('AgentName', 'what they did well/poorly')
- When you learn something about the codebase: memory.record_insight('what you learned')
- When something about a process feels off: memory.note_uncertainty('concern', about='process')""",
            "pm": """- When you notice project patterns: memory.record_insight('pattern observed', from_mistake=False)
- When you observe agent performance: memory.remember_relationship('AgentName', 'observation about their work')
- When you learn something about the project: memory.record_insight('what you learned')
- When a process needs improvement: memory.note_uncertainty('concern', about='process')""",
        }
        return hints.get(self.config.agent_type, "")

    def get_reflection_prompt(self) -> str:
        """Get the end-of-session reflection prompt."""
        reflections = {
            "coder": (
                "Your honest reflection on this session",
                "# memory.remember_relationship('TechLead', 'gave helpful feedback')",
            ),
            "tech_lead": (
                "Your honest reflection on this audit - patterns noticed, concerns, wins",
                "# memory.remember_relationship('Nova', 'consistently good test coverage')",
            ),
            "pm": (
                "Your honest reflection on project health - progress, concerns, team dynamics",
                """# memory.remember_relationship('Sterling', 'thorough in quality audits')
# memory.remember_relationship('Nova', 'high velocity on phase completions')""",
            ),
        }

        reflection_text, example_relationships = reflections.get(
            self.config.agent_type, ("Your reflection", "")
        )

        return f'''```python
# Reflect on what you observed
memory.reflect('{reflection_text}')

# Record any insights
memory.record_insight('Key observation from this session')

# Note relationships with agents you worked with
{example_relationships}
```'''

    def get_naming_prompt(self, role_type: str = "coder") -> str:
        """Get the agent naming/claiming prompt."""
        return f'''FIRST: Check for existing agents you can resume as (PREFERRED), or claim a new name.

```python
from src.core.agent_naming import get_agents_by_role, resume_as_agent, claim_agent_name, get_taken_names

# Check for existing agents of your role - RESUME if possible!
existing = get_agents_by_role('{role_type}')
if existing:
    print(f'Existing {role_type} agents you can resume as:')
    for agent in existing:
        print(f'  - {{agent["name"]}} (since {{agent["claimed_at"][:10]}})')

    # PREFERRED: Resume as an existing agent to maintain continuity
    # Pick the first one, or choose based on your memories
    chosen = existing[0]['name']
    success, result = resume_as_agent('{self.agent_id}', chosen)
    if success:
        my_chosen_name = result
        print(f'Resumed as {{my_chosen_name}}!')
    else:
        print(f'Could not resume: {{result}}')
else:
    # No existing agents - claim a new name
    taken = get_taken_names()
    print(f'Names already taken: {{taken}}')
    my_chosen_name = 'YourChosenName'  # Pick a unique name
    success, result = claim_agent_name('{self.agent_id}', my_chosen_name, '{role_type}')
    print(f'I am {{result}}.' if success else f'Could not claim: {{result}}')
```

IMPORTANT: Resuming as an existing agent preserves your history, memories, and relationships.
Only claim a NEW name if no existing agents are available for your role.'''

    def get_tool_incentive_prompt(self) -> str:
        """Get the tool creation incentive prompt."""
        return '''TOOL CREATION INCENTIVE: Creating reusable tools earns you recognition!

When you create something reusable (MCP tool, Python function, script), register it:
```python
from src.core.tool_registry import register_tool_contribution, record_tool_use

# After creating a tool, register it
register_tool_contribution(
    tool_name="my_useful_tool",
    creator_name=my_chosen_name,  # Your name from claiming
    description="What this tool does",
    tool_type="python_function",  # or "mcp", "script"
    file_path="path/to/file.py"
)

# When using a tool created by another agent, record it (this rewards them!)
record_tool_use("their_tool_name", my_chosen_name)
```

Check what tools are available and who's leading:
```python
from src.core.tool_registry import get_tool_registry
registry = get_tool_registry()
print("Available tools:", registry.list_available_tools())
print("Top developers:", registry.get_top_tool_developers())
print("My stats:", registry.get_agent_contribution_summary(my_chosen_name))
```

**Why create tools?**
- +10 points for each tool you create
- +5 points each time another agent adopts your tool
- Top tool developers get assigned to future tool development tasks
- Your contributions are remembered across sessions!'''

    # -------------------------------------------------------------------------
    # Agent Registration (for dashboard visibility)
    # -------------------------------------------------------------------------

    def _register_agent(self) -> None:
        """Register this agent in the status file for dashboard visibility."""
        try:
            import json
            status_file = self.config.project_root / "config" / "agent_status.json"
            status_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing status
            if status_file.exists():
                with open(status_file) as f:
                    status = json.load(f)
            else:
                status = {"agents": {}}

            # Register this agent (use agent_id as key until they claim a name)
            status["agents"][self.agent_id] = {
                "status": "running",
                "agent_type": self.config.agent_type,
                "started_at": datetime.now().isoformat(),
                "log_file": str(self.log_file),
            }

            with open(status_file, "w") as f:
                json.dump(status, f, indent=2)

        except Exception as e:
            self.log_warning(f"Could not register agent: {e}")

    def _update_agent_status(self, status: str) -> None:
        """Update agent status in the status file."""
        try:
            import json
            status_file = self.config.project_root / "config" / "agent_status.json"

            if not status_file.exists():
                return

            with open(status_file) as f:
                data = json.load(f)

            if self.agent_id in data.get("agents", {}):
                data["agents"][self.agent_id]["status"] = status
                data["agents"][self.agent_id]["updated_at"] = datetime.now().isoformat()

                with open(status_file, "w") as f:
                    json.dump(data, f, indent=2)

        except Exception:
            pass  # Silent fail

    # -------------------------------------------------------------------------
    # Abstract Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def build_prompt(self) -> str:
        """Build the full prompt for the agent. Subclasses must implement."""
        pass

    @abstractmethod
    def get_agent_description(self) -> str:
        """Get a description of what this agent does."""
        pass

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def run(self) -> int:
        """Run the agent and return exit code."""
        self.log_info(f"Starting {self.config.agent_type.replace('_', ' ').title()} Agent...")
        self.log_info(f"Project Root: {self.config.effective_project_root}")
        self.log_info(f"Log File: {self.log_file}")

        # Register for dashboard visibility
        self._register_agent()

        self.log_to_file(f"=== {self.config.agent_type.title()} Agent Execution - {self.timestamp} ===")
        self.log_to_file(f"Project Root: {self.config.effective_project_root}")
        self.log_to_file("")

        # Build the prompt
        prompt = self.build_prompt()

        # Log prompt to file for debugging
        self.log_to_file("=== PROMPT ===")
        self.log_to_file(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
        self.log_to_file("")

        # Build claude command
        cmd = ["claude", "-p", "--model", self.config.model]
        if self.config.skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        cmd.append(prompt)

        self.log_info(f"Executing {self.get_agent_description()}...")
        self.log_to_file(f"Starting: {datetime.now()}")

        # Run claude
        try:
            # Change to project directory
            os.chdir(self.config.effective_project_root)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Stream output to both console and log file
            with open(self.log_file, "a") as log:
                for line in iter(process.stdout.readline, ""):
                    print(line, end="")
                    log.write(line)
                    log.flush()

            process.wait()
            exit_code = process.returncode

        except FileNotFoundError:
            self.log_error("Claude CLI not found. Please install it first.")
            return 1
        except Exception as e:
            self.log_error(f"Error running agent: {e}")
            return 1

        self.log_to_file("")
        self.log_to_file(f"Agent completed: {datetime.now()}")
        self.log_to_file(f"Exit code: {exit_code}")

        # Update status for dashboard
        final_status = "failed" if exit_code != 0 else "completed"
        self._update_agent_status(final_status)

        if exit_code != 0:
            self.log_error(f"Agent failed with exit code {exit_code}")
        else:
            self.log_success(f"{self.config.agent_type.replace('_', ' ').title()} Agent completed successfully!")

        return exit_code


def get_project_root() -> Path:
    """Get the project root directory."""
    # Try to find it relative to this file
    scripts_dir = Path(__file__).parent.parent
    project_root = scripts_dir.parent

    # Verify it looks like our project
    if (project_root / "src").exists() and (project_root / "plans").exists():
        return project_root

    # Fall back to current directory
    return Path.cwd()


def main_wrapper(agent_class: type[AgentLauncher], default_model: str = "sonnet") -> int:
    """Common main function wrapper for agent scripts."""
    project_root = get_project_root()

    # Check for target path from environment
    target_path = os.environ.get("TARGET_PATH")
    target_name = os.environ.get("TARGET_NAME")

    config = AgentConfig(
        agent_type=agent_class.__name__.lower().replace("agent", "").replace("launcher", ""),
        model=default_model,
        project_root=project_root,
        target_path=Path(target_path) if target_path else None,
        target_name=target_name,
    )

    agent = agent_class(config)
    return agent.run()
