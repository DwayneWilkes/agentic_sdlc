"""
Agent naming system - Enables agents to choose their own personal names.

Agents freely choose names that feel meaningful to them.
The system ensures uniqueness and persists mappings for lookup.
"""

import json
import random
from datetime import datetime
from pathlib import Path


class AgentNaming:
    """Manages personal names for autonomous agents."""

    def __init__(self, config_path: Path | None = None, project_id: str | None = None):
        """
        Initialize the agent naming system.

        Args:
            config_path: Path to agent_names.json config file.
                        Defaults to config/agent_names.json
            project_id: Project identifier for tracking experience.
                       Defaults to parent directory name of config file.
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "agent_names.json"

        self.config_path = config_path
        self.project_id = project_id or config_path.parent.parent.name
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load naming configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Agent naming config not found: {self.config_path}"
            )

        with open(self.config_path) as f:
            return json.load(f)

    def _save_config(self) -> None:
        """Save updated configuration back to JSON file."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def is_name_available(self, name: str) -> bool:
        """
        Check if a name is available.

        Args:
            name: The name to check

        Returns:
            True if available, False if already taken
        """
        assigned = {
            entry["name"]
            for entry in self.config["assigned_names"].values()
        }
        return name not in assigned

    def get_taken_names(self) -> list[str]:
        """
        Get list of all currently taken names.

        Returns:
            List of names that are already claimed
        """
        return [
            entry["name"]
            for entry in self.config["assigned_names"].values()
        ]

    def claim_name(
        self, agent_id: str, chosen_name: str, role: str = "default"
    ) -> tuple[bool, str]:
        """
        Claim a name chosen by the agent.

        The agent freely chooses their own name. If taken, returns False
        so the agent can choose a different name.

        Args:
            agent_id: Unique technical ID of the agent
            chosen_name: The name the agent has chosen for themselves
            role: Agent role type (for reference)

        Returns:
            Tuple of (success, message)
            - (True, name) if claimed successfully
            - (False, "Name 'X' is already taken. Taken names: [...]") if collision

        Example:
            >>> naming = AgentNaming()
            >>> success, result = naming.claim_name("coder-123", "Aurora")
            >>> if success:
            ...     print(f"I am {result}")
            ... else:
            ...     print(result)  # "Name 'Aurora' is already taken..."
        """
        # Check if agent already has a name
        if agent_id in self.config["assigned_names"]:
            existing = self.config["assigned_names"][agent_id]["name"]
            return True, existing

        # Check if chosen name is available
        if not self.is_name_available(chosen_name):
            taken = self.get_taken_names()
            return False, f"Name '{chosen_name}' is already taken. Currently taken names: {taken}"

        # Claim the name
        self.config["assigned_names"][agent_id] = {
            "name": chosen_name,
            "role": role,
            "claimed_at": datetime.now().isoformat(),
        }

        # Persist to disk
        if self.config["naming_config"]["persistent"]:
            self._save_config()

        return True, chosen_name

    def claim_name_from_pool(
        self, agent_id: str, role: str = "default", preferred_name: str | None = None
    ) -> str:
        """
        Legacy function: Claim a name from the predefined pool.

        Prefer using claim_name() which lets agents choose freely.

        Args:
            agent_id: Unique technical ID of the agent
            role: Agent role type
            preferred_name: Optional preferred name from the pool

        Returns:
            Personal name for the agent
        """
        # Check if agent already has a name
        if agent_id in self.config["assigned_names"]:
            return self.config["assigned_names"][agent_id]["name"]

        # Get name pool for role
        name_pool = self.config["name_pools"].get(
            role, self.config["name_pools"]["default"]
        )

        # Get already assigned names
        assigned = {
            entry["name"]
            for entry in self.config["assigned_names"].values()
        }

        # Try to use preferred name if available
        if preferred_name:
            if preferred_name not in assigned:
                name = preferred_name
            elif self.config["naming_config"]["add_numeric_suffix_on_conflict"]:
                name = self._make_unique(preferred_name, assigned)
            else:
                name = self._pick_available_name(name_pool, assigned)
        else:
            name = self._pick_available_name(name_pool, assigned)

        # Record the assignment
        self.config["assigned_names"][agent_id] = {
            "name": name,
            "role": role,
            "claimed_at": datetime.now().isoformat(),
        }

        # Persist to disk
        if self.config["naming_config"]["persistent"]:
            self._save_config()

        return name

    def _pick_available_name(self, name_pool: list[str], assigned: set[str]) -> str:
        """Pick a random available name from the pool."""
        available = [name for name in name_pool if name not in assigned]

        if not available:
            # All names in pool are taken, add numeric suffix
            base_name = random.choice(name_pool)
            return self._make_unique(base_name, assigned)

        return random.choice(available)

    def _make_unique(self, base_name: str, assigned: set[str]) -> str:
        """Make a name unique by adding numeric suffix."""
        if base_name not in assigned:
            return base_name

        counter = 2
        while f"{base_name}-{counter}" in assigned:
            counter += 1

        return f"{base_name}-{counter}"

    def get_name(self, agent_id: str) -> str | None:
        """
        Get the personal name for an agent.

        Args:
            agent_id: Technical agent ID

        Returns:
            Personal name if assigned, None otherwise
        """
        entry = self.config["assigned_names"].get(agent_id)
        return entry["name"] if entry else None

    def get_agent_id(self, personal_name: str) -> str | None:
        """
        Reverse lookup: Get agent ID from personal name.

        Args:
            personal_name: Personal name (e.g., "Ada")

        Returns:
            Agent ID if found, None otherwise
        """
        for agent_id, entry in self.config["assigned_names"].items():
            if entry["name"] == personal_name:
                return agent_id
        return None

    def release_name(self, agent_id: str) -> bool:
        """
        Release a name back to the pool.

        Args:
            agent_id: Agent ID to release

        Returns:
            True if name was released, False if agent had no name
        """
        if agent_id not in self.config["assigned_names"]:
            return False

        del self.config["assigned_names"][agent_id]

        if self.config["naming_config"]["persistent"]:
            self._save_config()

        return True

    def list_assigned_names(self) -> dict[str, dict]:
        """
        List all currently assigned names.

        Returns:
            Dict mapping agent_id -> {name, role, claimed_at, completed_phases}
        """
        return self.config["assigned_names"].copy()

    def record_completed_phase(
        self, personal_name: str, phase_id: str, project_id: str | None = None
    ) -> bool:
        """
        Record that an agent completed a phase.

        Args:
            personal_name: Agent's personal name (e.g., "Aria")
            phase_id: The phase ID completed (e.g., "2.3")
            project_id: Project identifier. Defaults to self.project_id.

        Returns:
            True if recorded, False if agent not found
        """
        agent_id = self.get_agent_id(personal_name)
        if not agent_id or agent_id not in self.config["assigned_names"]:
            return False

        project = project_id or self.project_id
        entry = self.config["assigned_names"][agent_id]

        # Migrate from old list format to new dict format if needed
        if "completed_phases" not in entry:
            entry["completed_phases"] = {}
        elif isinstance(entry["completed_phases"], list):
            # Migrate legacy format: assume old phases were from current project
            old_phases = entry["completed_phases"]
            entry["completed_phases"] = {project: old_phases}

        # Ensure project key exists
        if project not in entry["completed_phases"]:
            entry["completed_phases"][project] = []

        if phase_id not in entry["completed_phases"][project]:
            entry["completed_phases"][project].append(phase_id)

            if self.config["naming_config"]["persistent"]:
                self._save_config()

        return True

    def get_completed_phases(
        self, personal_name: str, project_id: str | None = None
    ) -> list[str]:
        """
        Get list of phases completed by an agent for a specific project.

        Args:
            personal_name: Agent's personal name
            project_id: Project identifier. Defaults to self.project_id.

        Returns:
            List of phase IDs completed by this agent for the project
        """
        agent_id = self.get_agent_id(personal_name)
        if not agent_id or agent_id not in self.config["assigned_names"]:
            return []

        project = project_id or self.project_id
        entry = self.config["assigned_names"][agent_id]
        completed = entry.get("completed_phases", {})

        # Handle legacy list format
        if isinstance(completed, list):
            return completed if project == self.project_id else []

        return completed.get(project, [])

    def get_agent_experience(
        self, project_id: str | None = None
    ) -> dict[str, list[str]]:
        """
        Get all agents' completed phases for a specific project.

        Args:
            project_id: Project identifier. Defaults to self.project_id.

        Returns:
            Dict mapping personal_name -> list of completed phase IDs
        """
        project = project_id or self.project_id
        experience = {}
        for entry in self.config["assigned_names"].values():
            name = entry.get("name")
            completed = entry.get("completed_phases", {})

            # Handle legacy list format
            if isinstance(completed, list):
                phases = completed if project == self.project_id else []
            else:
                phases = completed.get(project, [])

            if name:
                experience[name] = phases
        return experience

    def get_all_experience(self) -> dict[str, dict[str, list[str]]]:
        """
        Get all agents' completed phases across all projects.

        Returns:
            Dict mapping personal_name -> {project_id -> list of phase IDs}
        """
        experience = {}
        for entry in self.config["assigned_names"].values():
            name = entry.get("name")
            completed = entry.get("completed_phases", {})

            # Handle legacy list format
            if isinstance(completed, list):
                completed = {self.project_id: completed}

            if name:
                experience[name] = completed
        return experience

    def get_available_names(self, role: str = "default") -> list[str]:
        """
        Get list of available names for a role.

        Args:
            role: Agent role type

        Returns:
            List of names not currently assigned
        """
        name_pool = self.config["name_pools"].get(
            role, self.config["name_pools"]["default"]
        )

        assigned = {
            entry["name"]
            for entry in self.config["assigned_names"].values()
        }

        return [name for name in name_pool if name not in assigned]


# Singleton instance
_naming_instance: AgentNaming | None = None


def get_naming() -> AgentNaming:
    """Get the global agent naming instance."""
    global _naming_instance
    if _naming_instance is None:
        _naming_instance = AgentNaming()
    return _naming_instance


def claim_agent_name(agent_id: str, chosen_name: str, role: str = "default") -> tuple[bool, str]:
    """
    Convenience function to claim a name chosen by the agent.

    Args:
        agent_id: Unique technical ID
        chosen_name: The name the agent has chosen
        role: Agent role

    Returns:
        Tuple of (success, result)
        - (True, name) if claimed
        - (False, error_message) if name taken
    """
    naming = get_naming()
    return naming.claim_name(agent_id, chosen_name, role)


def is_name_available(name: str) -> bool:
    """Check if a name is available."""
    naming = get_naming()
    return naming.is_name_available(name)


def get_taken_names() -> list[str]:
    """Get list of currently taken names."""
    naming = get_naming()
    return naming.get_taken_names()
