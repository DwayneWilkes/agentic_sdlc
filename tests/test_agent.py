"""Tests for Agent model."""

from src.models.agent import Agent, AgentCapability
from src.models.enums import AgentStatus


class TestAgentCapability:
    """Test AgentCapability model."""

    def test_capability_creation(self):
        """Test creating an agent capability."""
        capability = AgentCapability(
            name="python_development",
            description="Proficient in Python development",
            tools=["pytest", "mypy", "black"],
        )
        assert capability.name == "python_development"
        assert capability.description == "Proficient in Python development"
        assert "pytest" in capability.tools
        assert len(capability.tools) == 3

    def test_capability_with_metadata(self):
        """Test capability with metadata."""
        capability = AgentCapability(
            name="research",
            description="Research and analysis",
            tools=["web_search", "pdf_parser"],
            metadata={"proficiency": "expert", "domains": ["ML", "AI"]},
        )
        assert capability.metadata["proficiency"] == "expert"
        assert "ML" in capability.metadata["domains"]

    def test_capability_minimal(self):
        """Test capability with minimal fields."""
        capability = AgentCapability(
            name="code_review",
            description="Code review and quality checks",
            tools=[],
        )
        assert capability.tools == []
        assert capability.metadata == {}


class TestAgent:
    """Test Agent model."""

    def test_agent_creation_minimal(self):
        """Test creating an agent with minimal fields."""
        agent = Agent(
            id="agent-1",
            role="developer",
            capabilities=[],
        )
        assert agent.id == "agent-1"
        assert agent.role == "developer"
        assert agent.status == AgentStatus.IDLE
        assert agent.capabilities == []
        assert agent.current_task is None
        assert agent.assigned_tasks == []

    def test_agent_creation_full(self):
        """Test creating an agent with all fields."""
        capabilities = [
            AgentCapability(
                name="python_dev",
                description="Python development",
                tools=["pytest", "mypy"],
            ),
            AgentCapability(
                name="api_design",
                description="REST API design",
                tools=["openapi"],
            ),
        ]
        agent = Agent(
            id="agent-2",
            role="senior_developer",
            capabilities=capabilities,
            status=AgentStatus.WORKING,
            current_task="task-123",
            assigned_tasks=["task-123", "task-124"],
            metadata={"team": "backend", "experience_years": 5},
        )
        assert len(agent.capabilities) == 2
        assert agent.status == AgentStatus.WORKING
        assert agent.current_task == "task-123"
        assert len(agent.assigned_tasks) == 2
        assert agent.metadata["team"] == "backend"

    def test_agent_status_transitions(self):
        """Test agent status transitions."""
        agent = Agent(id="agent-3", role="tester", capabilities=[])
        assert agent.status == AgentStatus.IDLE

        agent.status = AgentStatus.WORKING
        assert agent.status == AgentStatus.WORKING

        agent.status = AgentStatus.COMPLETED
        assert agent.status == AgentStatus.COMPLETED

    def test_agent_task_assignment(self):
        """Test assigning tasks to agent."""
        agent = Agent(id="agent-4", role="researcher", capabilities=[])
        assert len(agent.assigned_tasks) == 0

        agent.assigned_tasks.append("task-1")
        agent.assigned_tasks.append("task-2")
        assert len(agent.assigned_tasks) == 2
        assert "task-1" in agent.assigned_tasks

    def test_agent_current_task_update(self):
        """Test updating agent's current task."""
        agent = Agent(id="agent-5", role="analyst", capabilities=[])
        assert agent.current_task is None

        agent.current_task = "task-100"
        assert agent.current_task == "task-100"

        agent.current_task = None
        assert agent.current_task is None

    def test_agent_with_multiple_capabilities(self):
        """Test agent with multiple capabilities."""
        capabilities = [
            AgentCapability(
                name="frontend",
                description="Frontend development",
                tools=["react", "typescript"],
            ),
            AgentCapability(
                name="backend",
                description="Backend development",
                tools=["fastapi", "postgresql"],
            ),
            AgentCapability(
                name="devops",
                description="DevOps and deployment",
                tools=["docker", "kubernetes"],
            ),
        ]
        agent = Agent(
            id="agent-6",
            role="full_stack_developer",
            capabilities=capabilities,
        )
        assert len(agent.capabilities) == 3
        assert agent.capabilities[0].name == "frontend"
        assert agent.capabilities[1].name == "backend"
        assert agent.capabilities[2].name == "devops"

    def test_agent_blocked_status(self):
        """Test agent in blocked status."""
        agent = Agent(
            id="agent-7",
            role="developer",
            capabilities=[],
            status=AgentStatus.BLOCKED,
            metadata={"blocker": "Waiting for API credentials"},
        )
        assert agent.status == AgentStatus.BLOCKED
        assert agent.metadata["blocker"] == "Waiting for API credentials"

    def test_agent_resource_limits(self):
        """Test agent with resource limits."""
        agent = Agent(
            id="agent-8",
            role="compute_agent",
            capabilities=[],
            metadata={
                "max_time_hours": 2,
                "max_api_calls": 1000,
                "max_memory_mb": 4096,
            },
        )
        assert agent.metadata["max_time_hours"] == 2
        assert agent.metadata["max_api_calls"] == 1000
        assert agent.metadata["max_memory_mb"] == 4096
