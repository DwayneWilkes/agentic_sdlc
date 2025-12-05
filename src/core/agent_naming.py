"""
Agent naming system - Assigns human-readable personal names to agents.

Agents can claim unique personal names from predefined pools based on their role.
Names persist across sessions and make logs/communication more readable.
"""

import json
import random
from pathlib import Path
from typing import Optional
from datetime import datetime


class AgentNaming:
    """Manages personal names for autonomous agents."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the agent naming system.

        Args:
            config_path: Path to agent_names.json config file.
                        Defaults to config/agent_names.json
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "agent_names.json"

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load naming configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Agent naming config not found: {self.config_path}"
            )

        with open(self.config_path, "r") as f:
            return json.load(f)

    def _save_config(self) -> None:
        """Save updated configuration back to JSON file."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def claim_name(
        self, agent_id: str, role: str = "default", preferred_name: Optional[str] = None
    ) -> str:
        """
        Claim a personal name for an agent.

        Args:
            agent_id: Unique technical ID of the agent (e.g., "coder-autonomous-123")
            role: Agent role type (e.g., "coder", "architect", "tester")
            preferred_name: Optional preferred name (if available)

        Returns:
            Personal name for the agent (e.g., "Ada", "Grace-2")

        Example:
            >>> naming = AgentNaming()
            >>> name = naming.claim_name("coder-autonomous-123", "coder")
            >>> print(name)  # "Ada" or "Grace" or "Linus"
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
            if preferred_name in name_pool and preferred_name not in assigned:
                name = preferred_name
            elif self.config["naming_config"]["add_numeric_suffix_on_conflict"]:
                name = self._make_unique(preferred_name, assigned)
            else:
                # Preferred name not available, pick random
                name = self._pick_available_name(name_pool, assigned)
        else:
            # Pick a random available name
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

    def get_name(self, agent_id: str) -> Optional[str]:
        """
        Get the personal name for an agent.

        Args:
            agent_id: Technical agent ID

        Returns:
            Personal name if assigned, None otherwise
        """
        entry = self.config["assigned_names"].get(agent_id)
        return entry["name"] if entry else None

    def get_agent_id(self, personal_name: str) -> Optional[str]:
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
            Dict mapping agent_id -> {name, role, claimed_at}
        """
        return self.config["assigned_names"].copy()

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
_naming_instance: Optional[AgentNaming] = None


def get_naming() -> AgentNaming:
    """Get the global agent naming instance."""
    global _naming_instance
    if _naming_instance is None:
        _naming_instance = AgentNaming()
    return _naming_instance


def claim_agent_name(
    agent_id: str, role: str = "default", preferred_name: Optional[str] = None
) -> str:
    """
    Convenience function to claim an agent name.

    Args:
        agent_id: Unique technical ID
        role: Agent role
        preferred_name: Optional preferred name

    Returns:
        Personal name for the agent
    """
    naming = get_naming()
    return naming.claim_name(agent_id, role, preferred_name)
