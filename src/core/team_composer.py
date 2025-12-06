"""Team Composition Engine for creating balanced agent teams."""

import uuid
from typing import Any

from src.core.role_registry import RoleMatcher, RoleRegistry
from src.models.agent import Agent, AgentCapability, AgentRole
from src.models.task import Subtask
from src.models.team import Team


class TeamComposer:
    """
    Composes balanced teams of agents based on task requirements.

    The TeamComposer analyzes subtasks, determines optimal team size,
    selects complementary roles, and balances specialization vs generalization.
    """

    def __init__(
        self,
        registry: RoleRegistry,
        default_max_team_size: int = 10,
        tasks_per_agent: float = 2.5,
    ):
        """
        Initialize the team composer.

        Args:
            registry: RoleRegistry containing available agent roles
            default_max_team_size: Maximum team size limit (default: 10)
            tasks_per_agent: Average tasks per agent for sizing (default: 2.5)
        """
        self._registry = registry
        self._matcher = RoleMatcher(registry)
        self._default_max_team_size = default_max_team_size
        self._tasks_per_agent = tasks_per_agent

    def compose_team(
        self,
        subtasks: list[Subtask],
        team_name: str | None = None,
        max_team_size: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Team:
        """
        Compose a balanced team for the given subtasks.

        Args:
            subtasks: List of subtasks that need to be completed
            team_name: Optional name for the team (auto-generated if None)
            max_team_size: Maximum team size (uses default if None)
            metadata: Optional metadata for the team

        Returns:
            Team object with balanced agent assignments
        """
        # Handle empty subtasks
        if not subtasks:
            team_id = f"team-{uuid.uuid4().hex[:8]}"
            name = team_name or "Empty Team"
            return Team(
                id=team_id,
                name=name,
                agents=[],
                metadata=metadata or {},
            )

        # Determine team size
        max_size = max_team_size or self._default_max_team_size
        ideal_size = self._calculate_team_size(subtasks, max_size)

        # Identify required roles based on subtask requirements
        role_requirements = self._analyze_role_requirements(subtasks)

        # Select agents with complementary roles
        agents = self._select_agents(role_requirements, ideal_size)

        # Assign subtasks to agents with workload balancing
        agents = self._assign_tasks(agents, subtasks)

        # Create team
        team_id = f"team-{uuid.uuid4().hex[:8]}"
        name = team_name or f"Team {team_id[:6]}"

        return Team(
            id=team_id,
            name=name,
            agents=agents,
            metadata=metadata or {},
        )

    def _calculate_team_size(self, subtasks: list[Subtask], max_size: int) -> int:
        """
        Calculate optimal team size based on subtask count and complexity.

        Args:
            subtasks: List of subtasks
            max_size: Maximum allowed team size

        Returns:
            Optimal team size (1 to max_size)
        """
        if not subtasks:
            return 0

        # Base calculation: number of tasks / tasks per agent
        base_size = len(subtasks) / self._tasks_per_agent

        # Round up for small teams, round to nearest for larger
        if base_size < 2:
            ideal_size = max(1, int(base_size + 0.5))
        else:
            ideal_size = max(1, round(base_size))

        # Check if tasks are diverse (require different capabilities)
        # If diverse, ensure at least 2 agents for specialization
        unique_capabilities = set()
        for subtask in subtasks:
            requirements = subtask.requirements or {}
            capabilities = requirements.get("capabilities", [])
            unique_capabilities.update(capabilities)

        # If we have 3+ different capability types, ensure at least 2 agents
        if len(unique_capabilities) >= 3 and ideal_size < 2:
            ideal_size = 2

        # Apply min/max constraints
        ideal_size = max(1, min(ideal_size, max_size))

        # Ensure we don't over-staff (max 1 agent per task)
        ideal_size = min(ideal_size, len(subtasks))

        return ideal_size

    def _analyze_role_requirements(
        self, subtasks: list[Subtask]
    ) -> dict[str, dict[str, Any]]:
        """
        Analyze subtasks to identify required roles and their priority.

        Args:
            subtasks: List of subtasks

        Returns:
            Dict mapping role names to requirement details:
                {
                    "developer": {
                        "priority": 0.9,
                        "complexity": "high",
                        "count": 3
                    },
                    ...
                }
        """
        role_scores: dict[str, dict[str, Any]] = {}

        for subtask in subtasks:
            requirements = subtask.requirements or {}

            # Find matching roles for this subtask
            matches = self._matcher.find_matching_roles(requirements, min_score=0.1)

            for match in matches:
                role = match["role"]
                score = match["score"]
                role_name = role.name

                if role_name not in role_scores:
                    role_scores[role_name] = {
                        "role": role,
                        "total_score": 0.0,
                        "count": 0,
                        "max_score": 0.0,
                    }

                role_scores[role_name]["total_score"] += score
                role_scores[role_name]["count"] += 1
                role_scores[role_name]["max_score"] = max(
                    role_scores[role_name]["max_score"], score
                )

        # Calculate priorities
        for role_name in role_scores:
            stats = role_scores[role_name]
            # Priority based on frequency and quality of matches
            stats["priority"] = (stats["total_score"] / len(subtasks)) + (
                stats["count"] / len(subtasks)
            )
            # Complexity based on max score (high score = specialist needed)
            stats["complexity"] = "high" if stats["max_score"] > 0.7 else "medium"

        return role_scores

    def _select_agents(
        self, role_requirements: dict[str, dict[str, Any]], team_size: int
    ) -> list[Agent]:
        """
        Select agents with complementary roles based on requirements.

        Args:
            role_requirements: Dict of role requirements from analysis
            team_size: Target team size

        Returns:
            List of Agent objects
        """
        agents = []

        if not role_requirements:
            # No specific requirements, create generalist developers
            dev_role = self._registry.get_role("developer")
            if dev_role:
                for _ in range(team_size):
                    agent = self._create_agent_from_role(dev_role)
                    agents.append(agent)
            return agents

        # Sort roles by priority (descending)
        sorted_roles = sorted(
            role_requirements.items(),
            key=lambda x: x[1]["priority"],
            reverse=True,
        )

        # Select top roles up to team size
        # Balance between specialists (high-priority roles) and coverage
        selected_roles: list[AgentRole] = []
        for role_name, stats in sorted_roles:
            if len(selected_roles) >= team_size:
                break

            role = stats["role"]
            complexity = stats["complexity"]

            # For high complexity tasks, prefer specialists
            if complexity == "high":
                selected_roles.append(role)
            # For medium complexity, add if we have room
            elif len(selected_roles) < team_size:
                selected_roles.append(role)

        # If we need more agents of the same role (e.g., multiple developers)
        # duplicate the top-priority role until we reach team size
        while len(selected_roles) < team_size:
            if sorted_roles:
                # Add another instance of the highest priority role
                top_role = sorted_roles[0][1]["role"]
                selected_roles.append(top_role)
            else:
                break

        # Create agents from selected roles
        for role in selected_roles:
            agent = self._create_agent_from_role(role)
            agents.append(agent)

        return agents

    def _create_agent_from_role(self, role: AgentRole) -> Agent:
        """
        Create an Agent instance from an AgentRole definition.

        Args:
            role: AgentRole to instantiate

        Returns:
            Agent instance
        """
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        # Convert role capabilities to agent capabilities
        capabilities = []
        for cap_name in role.capabilities:
            capability = AgentCapability(
                name=cap_name,
                description=f"{cap_name} capability",
                tools=role.tools,
            )
            capabilities.append(capability)

        agent = Agent(
            id=agent_id,
            role=role.name,
            capabilities=capabilities,
            assigned_tasks=[],
            metadata={
                "tools": role.tools,
                "domain_knowledge": role.domain_knowledge,
            },
        )

        return agent

    def _assign_tasks(
        self, agents: list[Agent], subtasks: list[Subtask]
    ) -> list[Agent]:
        """
        Assign subtasks to agents with workload balancing.

        Args:
            agents: List of agents to assign tasks to
            subtasks: List of subtasks to assign

        Returns:
            List of agents with assigned_tasks populated
        """
        if not agents:
            return agents

        # Create a list to track workload per agent
        agent_workload = [0 for _ in agents]

        # Assign each subtask to the best available agent
        for subtask in subtasks:
            # Find best matching agent with lowest workload
            best_agent_idx = self._find_best_agent(
                agents, agent_workload, subtask.requirements or {}
            )

            # Assign task
            agents[best_agent_idx].assigned_tasks.append(subtask.id)
            agent_workload[best_agent_idx] += 1

        return agents

    def _find_best_agent(
        self,
        agents: list[Agent],
        workload: list[int],
        requirements: dict[str, Any],
    ) -> int:
        """
        Find the best agent for a task based on role match and workload balance.

        Args:
            agents: List of available agents
            workload: Current workload per agent
            requirements: Task requirements

        Returns:
            Index of best agent
        """
        if not agents:
            return 0

        best_idx = 0
        best_score = -1.0

        for idx, agent in enumerate(agents):
            # Calculate match score for this agent's role
            role = self._registry.get_role(agent.role)
            if role:
                match_score = self._matcher._calculate_match_score(
                    role,
                    [c.lower() for c in requirements.get("capabilities", [])],
                    [t.lower() for t in requirements.get("tools", [])],
                    [k.lower() for k in requirements.get("domain_knowledge", [])],
                )
            else:
                match_score = 0.0

            # Factor in workload balance (prefer less loaded agents)
            # Normalize workload (inverse: lower workload = higher score)
            max_workload = max(workload) if max(workload) > 0 else 1
            workload_score = 1.0 - (workload[idx] / max_workload)

            # Combined score: 70% match, 30% workload balance
            combined_score = (0.7 * match_score) + (0.3 * workload_score)

            if combined_score > best_score:
                best_score = combined_score
                best_idx = idx

        return best_idx
