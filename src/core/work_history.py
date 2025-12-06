"""
Work History - Tracks agent work completions across projects.

Separated from agent naming to keep concerns distinct:
- agent_naming.py: Identity (who is this agent?)
- work_history.py: Work (what did they complete?)

History is stored in config/work_history.json, keyed by personal name.
"""

import json
from datetime import datetime
from pathlib import Path


class WorkHistory:
    """Tracks completed work by agents across projects."""

    def __init__(self, config_path: Path | None = None, project_id: str | None = None):
        """
        Initialize work history tracking.

        Args:
            config_path: Path to work_history.json. Defaults to config/work_history.json.
            project_id: Current project identifier. Defaults to parent directory name.
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "work_history.json"

        self.config_path = config_path
        self.project_id = project_id or config_path.parent.parent.name
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load work history from JSON file."""
        if not self.config_path.exists():
            # Initialize with empty structure
            return {"agents": {}, "last_updated": None}

        with open(self.config_path) as f:
            return json.load(f)

    def _save_data(self) -> None:
        """Save work history to JSON file."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.config_path, "w") as f:
            json.dump(self.data, f, indent=2)
            f.write("\n")  # Trailing newline

    def record_completion(
        self,
        personal_name: str,
        phase_id: str,
        project_id: str | None = None,
        details: dict | None = None,
    ) -> bool:
        """
        Record that an agent completed a phase.

        Args:
            personal_name: Agent's personal name (e.g., "Aria", "Cipher")
            phase_id: The phase ID completed (e.g., "2.1", "2.3")
            project_id: Project identifier. Defaults to current project.
            details: Optional additional details (duration, commit hash, etc.)

        Returns:
            True if recorded successfully
        """
        project = project_id or self.project_id

        # Initialize agent entry if needed
        if personal_name not in self.data["agents"]:
            self.data["agents"][personal_name] = {"projects": {}}

        agent_data = self.data["agents"][personal_name]

        # Initialize project entry if needed
        if project not in agent_data["projects"]:
            agent_data["projects"][project] = {"completed": []}

        project_data = agent_data["projects"][project]

        # Check if already recorded
        existing = next(
            (c for c in project_data["completed"] if c["phase_id"] == phase_id),
            None
        )
        if existing:
            return True  # Already recorded

        # Record the completion
        completion = {
            "phase_id": phase_id,
            "completed_at": datetime.now().isoformat(),
        }
        if details:
            completion.update(details)

        project_data["completed"].append(completion)
        self._save_data()
        return True

    def get_completed_phases(
        self,
        personal_name: str,
        project_id: str | None = None,
    ) -> list[str]:
        """
        Get list of phase IDs completed by an agent.

        Args:
            personal_name: Agent's personal name
            project_id: Project identifier. Defaults to current project.

        Returns:
            List of completed phase IDs (e.g., ["1.2", "2.1"])
        """
        project = project_id or self.project_id

        if personal_name not in self.data["agents"]:
            return []

        agent_data = self.data["agents"][personal_name]
        project_data = agent_data.get("projects", {}).get(project, {})
        completed = project_data.get("completed", [])

        return [c["phase_id"] for c in completed]

    def get_completion_details(
        self,
        personal_name: str,
        phase_id: str,
        project_id: str | None = None,
    ) -> dict | None:
        """
        Get details of a specific completion.

        Args:
            personal_name: Agent's personal name
            phase_id: The phase ID to look up
            project_id: Project identifier. Defaults to current project.

        Returns:
            Completion details dict or None if not found
        """
        project = project_id or self.project_id

        if personal_name not in self.data["agents"]:
            return None

        agent_data = self.data["agents"][personal_name]
        project_data = agent_data.get("projects", {}).get(project, {})
        completed = project_data.get("completed", [])

        return next(
            (c for c in completed if c["phase_id"] == phase_id),
            None
        )

    def get_agent_experience(
        self,
        project_id: str | None = None,
    ) -> dict[str, list[str]]:
        """
        Get all agents' completed phases for a project.

        Args:
            project_id: Project identifier. Defaults to current project.

        Returns:
            Dict mapping personal_name -> list of completed phase IDs
        """
        project = project_id or self.project_id
        experience = {}

        for name, agent_data in self.data["agents"].items():
            project_data = agent_data.get("projects", {}).get(project, {})
            completed = project_data.get("completed", [])
            experience[name] = [c["phase_id"] for c in completed]

        return experience

    def get_all_experience(self) -> dict[str, dict[str, list[str]]]:
        """
        Get all agents' completed phases across all projects.

        Returns:
            Dict mapping personal_name -> {project_id -> list of phase IDs}
        """
        experience = {}

        for name, agent_data in self.data["agents"].items():
            experience[name] = {}
            for project, project_data in agent_data.get("projects", {}).items():
                completed = project_data.get("completed", [])
                experience[name][project] = [c["phase_id"] for c in completed]

        return experience

    def migrate_from_agent_names(self, agent_names_path: Path) -> int:
        """
        Migrate completed_phases data from agent_names.json.

        Args:
            agent_names_path: Path to agent_names.json

        Returns:
            Number of completions migrated
        """
        if not agent_names_path.exists():
            return 0

        with open(agent_names_path) as f:
            agent_names = json.load(f)

        migrated = 0
        assigned = agent_names.get("assigned_names", {})

        for agent_id, info in assigned.items():
            personal_name = info.get("name")
            if not personal_name:
                continue

            completed_phases = info.get("completed_phases", {})

            # Handle legacy list format
            if isinstance(completed_phases, list):
                for phase_id in completed_phases:
                    self.record_completion(personal_name, phase_id)
                    migrated += 1
            elif isinstance(completed_phases, dict):
                for project, phases in completed_phases.items():
                    for phase_id in phases:
                        self.record_completion(personal_name, phase_id, project)
                        migrated += 1

        return migrated


# Singleton instance
_history_instance: WorkHistory | None = None


def get_work_history() -> WorkHistory:
    """Get the global work history instance."""
    global _history_instance
    if _history_instance is None:
        _history_instance = WorkHistory()
    return _history_instance


def record_phase_completion(
    personal_name: str,
    phase_id: str,
    project_id: str | None = None,
    details: dict | None = None,
) -> bool:
    """
    Convenience function to record a phase completion.

    Args:
        personal_name: Agent's personal name
        phase_id: Completed phase ID
        project_id: Project identifier (optional)
        details: Additional details (optional)

    Returns:
        True if recorded
    """
    history = get_work_history()
    return history.record_completion(personal_name, phase_id, project_id, details)


def get_agent_completed_phases(
    personal_name: str,
    project_id: str | None = None,
) -> list[str]:
    """
    Convenience function to get an agent's completed phases.

    Args:
        personal_name: Agent's personal name
        project_id: Project identifier (optional)

    Returns:
        List of completed phase IDs
    """
    history = get_work_history()
    return history.get_completed_phases(personal_name, project_id)
