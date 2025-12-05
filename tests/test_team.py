"""Tests for Team model."""

from src.models.agent import Agent, AgentCapability
from src.models.enums import AgentStatus
from src.models.team import Team


class TestTeam:
    """Test Team model."""

    def test_team_creation_minimal(self):
        """Test creating a team with minimal fields."""
        team = Team(
            id="team-1",
            name="Development Team",
            agents=[],
        )
        assert team.id == "team-1"
        assert team.name == "Development Team"
        assert team.agents == []
        assert team.metadata == {}

    def test_team_creation_with_agents(self):
        """Test creating a team with agents."""
        agents = [
            Agent(id="agent-1", role="developer", capabilities=[]),
            Agent(id="agent-2", role="tester", capabilities=[]),
            Agent(id="agent-3", role="reviewer", capabilities=[]),
        ]
        team = Team(
            id="team-2",
            name="Backend Team",
            agents=agents,
        )
        assert len(team.agents) == 3
        assert team.agents[0].role == "developer"
        assert team.agents[1].role == "tester"
        assert team.agents[2].role == "reviewer"

    def test_team_add_agent(self):
        """Test adding an agent to a team."""
        team = Team(id="team-3", name="Research Team", agents=[])
        assert len(team.agents) == 0

        agent = Agent(id="agent-10", role="researcher", capabilities=[])
        team.agents.append(agent)
        assert len(team.agents) == 1
        assert team.agents[0].id == "agent-10"

    def test_team_remove_agent(self):
        """Test removing an agent from a team."""
        agents = [
            Agent(id="agent-20", role="developer", capabilities=[]),
            Agent(id="agent-21", role="tester", capabilities=[]),
        ]
        team = Team(id="team-4", name="QA Team", agents=agents)
        assert len(team.agents) == 2

        team.agents = [a for a in team.agents if a.id != "agent-20"]
        assert len(team.agents) == 1
        assert team.agents[0].id == "agent-21"

    def test_team_with_metadata(self):
        """Test team with metadata."""
        team = Team(
            id="team-5",
            name="Frontend Team",
            agents=[],
            metadata={
                "project": "E-commerce Platform",
                "sprint": 5,
                "budget": 50000,
            },
        )
        assert team.metadata["project"] == "E-commerce Platform"
        assert team.metadata["sprint"] == 5
        assert team.metadata["budget"] == 50000

    def test_team_with_diverse_agents(self):
        """Test team with agents having different roles and capabilities."""
        agents = [
            Agent(
                id="agent-30",
                role="architect",
                capabilities=[
                    AgentCapability(
                        name="system_design",
                        description="System architecture design",
                        tools=["draw.io", "mermaid"],
                    )
                ],
            ),
            Agent(
                id="agent-31",
                role="developer",
                capabilities=[
                    AgentCapability(
                        name="python_dev",
                        description="Python development",
                        tools=["pytest", "mypy"],
                    )
                ],
            ),
            Agent(
                id="agent-32",
                role="devops",
                capabilities=[
                    AgentCapability(
                        name="deployment",
                        description="Deployment and infrastructure",
                        tools=["docker", "kubernetes"],
                    )
                ],
            ),
        ]
        team = Team(
            id="team-6",
            name="Full Stack Team",
            agents=agents,
            metadata={"specialization": "microservices"},
        )
        assert len(team.agents) == 3
        assert team.agents[0].role == "architect"
        assert len(team.agents[1].capabilities) == 1
        assert team.metadata["specialization"] == "microservices"

    def test_team_agent_status_tracking(self):
        """Test tracking agent statuses within a team."""
        agents = [
            Agent(id="agent-40", role="dev1", capabilities=[], status=AgentStatus.IDLE),
            Agent(
                id="agent-41",
                role="dev2",
                capabilities=[],
                status=AgentStatus.WORKING,
            ),
            Agent(
                id="agent-42",
                role="dev3",
                capabilities=[],
                status=AgentStatus.COMPLETED,
            ),
        ]
        team = Team(id="team-7", name="Status Team", agents=agents)

        idle_agents = [a for a in team.agents if a.status == AgentStatus.IDLE]
        working_agents = [a for a in team.agents if a.status == AgentStatus.WORKING]
        completed_agents = [a for a in team.agents if a.status == AgentStatus.COMPLETED]

        assert len(idle_agents) == 1
        assert len(working_agents) == 1
        assert len(completed_agents) == 1

    def test_team_workload_distribution(self):
        """Test team with workload distribution across agents."""
        agents = [
            Agent(
                id="agent-50",
                role="developer",
                capabilities=[],
                assigned_tasks=["task-1", "task-2"],
            ),
            Agent(
                id="agent-51",
                role="developer",
                capabilities=[],
                assigned_tasks=["task-3"],
            ),
            Agent(id="agent-52", role="developer", capabilities=[], assigned_tasks=[]),
        ]
        team = Team(id="team-8", name="Balanced Team", agents=agents)

        total_tasks = sum(len(agent.assigned_tasks) for agent in team.agents)
        assert total_tasks == 3

        # Check distribution
        assert len(team.agents[0].assigned_tasks) == 2
        assert len(team.agents[1].assigned_tasks) == 1
        assert len(team.agents[2].assigned_tasks) == 0

    def test_team_empty_then_populated(self):
        """Test team starting empty and getting populated."""
        team = Team(id="team-9", name="Growing Team", agents=[])
        assert len(team.agents) == 0

        # Add agents one by one
        for i in range(5):
            agent = Agent(id=f"agent-{60+i}", role=f"role-{i}", capabilities=[])
            team.agents.append(agent)

        assert len(team.agents) == 5
        assert team.agents[0].id == "agent-60"
        assert team.agents[4].id == "agent-64"
