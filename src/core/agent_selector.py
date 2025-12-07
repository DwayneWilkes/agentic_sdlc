"""Agent selector for intelligent agent reuse.

Selects the best available agent for a given phase based on:
- Experience with similar phases (batch affinity)
- Work history
- Current availability
"""

import json
import random
from pathlib import Path


class AgentSelector:
    """Selects agents for phase assignments based on experience and availability."""

    def __init__(
        self,
        agent_names_path: Path | None = None,
        work_history_path: Path | None = None,
    ):
        """
        Initialize the agent selector.

        Args:
            agent_names_path: Path to agent_names.json
            work_history_path: Path to work_history.json
        """
        project_root = Path(__file__).parent.parent.parent
        self.agent_names_path = agent_names_path or project_root / "config" / "agent_names.json"
        self.work_history_path = work_history_path or project_root / "config" / "work_history.json"

    def _load_agents(self) -> dict:
        """Load registered agents from config."""
        if not self.agent_names_path.exists():
            return {}
        with open(self.agent_names_path) as f:
            data = json.load(f)
        return data.get("assigned_names", {})

    def _load_work_history(self) -> dict:
        """Load work history from config."""
        if not self.work_history_path.exists():
            return {}
        with open(self.work_history_path) as f:
            return json.load(f)

    def get_available_agents(self) -> list[dict]:
        """
        Get list of available agents with their details.

        Returns:
            List of agent dicts with id, name, role
        """
        agents = self._load_agents()
        return [
            {"id": agent_id, "name": info["name"], "role": info["role"]}
            for agent_id, info in agents.items()
        ]

    def get_agent_experience(self, agent_name: str) -> list[str]:
        """
        Get phases completed by an agent.

        Args:
            agent_name: Personal name of the agent

        Returns:
            List of phase IDs completed
        """
        history = self._load_work_history()
        agent_data = history.get("agents", {}).get(agent_name, {})
        projects = agent_data.get("projects", {})

        completed = []
        for project_data in projects.values():
            for entry in project_data.get("completed", []):
                completed.append(entry["phase_id"])

        return completed

    def calculate_affinity(self, agent_name: str, phase_id: str) -> float:
        """
        Calculate affinity score between an agent and a phase.

        Higher score = better match based on:
        - Same batch experience (e.g., agent did 2.1, phase is 2.3)
        - Adjacent batch experience
        - Total experience

        Args:
            agent_name: Personal name of the agent
            phase_id: Phase to evaluate (e.g., "4.2")

        Returns:
            Affinity score (0.0 to 1.0)
        """
        experience = self.get_agent_experience(agent_name)
        if not experience:
            return 0.1  # Base score for agents without history

        target_batch = phase_id.split(".")[0]

        # Count same-batch phases
        same_batch = sum(1 for p in experience if p.startswith(f"{target_batch}."))

        # Count adjacent batch phases
        try:
            batch_num = int(target_batch)
            adjacent_batches = [str(batch_num - 1), str(batch_num + 1)]
            adjacent = sum(
                1 for p in experience
                if any(p.startswith(f"{b}.") for b in adjacent_batches)
            )
        except ValueError:
            adjacent = 0

        # Calculate score
        score = 0.1  # Base
        score += same_batch * 0.3  # High weight for same batch
        score += adjacent * 0.1  # Lower weight for adjacent
        score += len(experience) * 0.05  # Small bonus for total experience

        return min(score, 1.0)  # Cap at 1.0

    def select_agent(self, phase_id: str) -> dict | None:
        """
        Select the best agent for a phase.

        Args:
            phase_id: Phase to assign (e.g., "4.2")

        Returns:
            Agent dict with id, name, role, or None if no agents available
        """
        agents = self.get_available_agents()
        if not agents:
            return None

        # Calculate affinity scores
        scored = []
        for agent in agents:
            affinity = self.calculate_affinity(agent["name"], phase_id)
            scored.append((agent, affinity))

        # Sort by affinity (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)

        # If top agents have same score, pick randomly among them
        top_score = scored[0][1]
        top_agents = [a for a, s in scored if s == top_score]

        selected = random.choice(top_agents)
        return selected

    def select_agent_id(self, phase_id: str) -> str | None:
        """
        Select the best agent ID for a phase.

        Convenience method that returns just the agent ID.

        Args:
            phase_id: Phase to assign (e.g., "4.2")

        Returns:
            Agent ID string, or None if no agents available
        """
        agent = self.select_agent(phase_id)
        return agent["id"] if agent else None

    def should_hire_new_agent(self, phase_id: str, threshold: float = 0.2) -> bool:
        """
        Determine if a new agent should be hired instead of reusing.

        Only hire new if:
        - No agents available, OR
        - All existing agents have very low affinity

        Args:
            phase_id: Phase to evaluate
            threshold: Minimum affinity score to reuse (default 0.2)

        Returns:
            True if should hire new, False if should reuse
        """
        agents = self.get_available_agents()
        if not agents:
            return True

        # Check max affinity
        max_affinity = max(
            self.calculate_affinity(a["name"], phase_id)
            for a in agents
        )

        return max_affinity < threshold


# Singleton instance
_selector_instance: AgentSelector | None = None


def get_selector() -> AgentSelector:
    """Get the global agent selector instance."""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = AgentSelector()
    return _selector_instance


def select_agent_for_phase(phase_id: str) -> dict | None:
    """
    Convenience function to select an agent for a phase.

    Args:
        phase_id: Phase to assign

    Returns:
        Agent dict or None
    """
    return get_selector().select_agent(phase_id)


def get_agent_id_for_phase(phase_id: str) -> str | None:
    """
    Convenience function to get agent ID for a phase.

    Args:
        phase_id: Phase to assign

    Returns:
        Agent ID or None
    """
    return get_selector().select_agent_id(phase_id)
