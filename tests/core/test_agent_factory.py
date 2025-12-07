"""Tests for the Agent Factory module."""

import pytest

from src.core.agent_factory import (
    AgentConfiguration,
    AgentFactory,
    InstructionGenerator,
    ResourceLimits,
)
from src.core.role_registry import RoleRegistry
from src.models.agent import Agent, AgentRole
from src.models.task import Subtask


class TestResourceLimits:
    """Test ResourceLimits dataclass."""

    def test_resource_limits_creation(self):
        """Test creating resource limits with all parameters."""
        limits = ResourceLimits(
            max_time_seconds=3600,
            max_api_calls=1000,
            max_tokens=100000,
            max_memory_mb=512,
        )
        assert limits.max_time_seconds == 3600
        assert limits.max_api_calls == 1000
        assert limits.max_tokens == 100000
        assert limits.max_memory_mb == 512

    def test_resource_limits_defaults(self):
        """Test ResourceLimits with default values."""
        limits = ResourceLimits()
        assert limits.max_time_seconds is None
        assert limits.max_api_calls is None
        assert limits.max_tokens is None
        assert limits.max_memory_mb is None

    def test_resource_limits_partial(self):
        """Test ResourceLimits with partial parameters."""
        limits = ResourceLimits(max_time_seconds=1800, max_tokens=50000)
        assert limits.max_time_seconds == 1800
        assert limits.max_api_calls is None
        assert limits.max_tokens == 50000
        assert limits.max_memory_mb is None


class TestAgentConfiguration:
    """Test AgentConfiguration dataclass."""

    def test_configuration_with_all_fields(self):
        """Test creating configuration with all fields."""
        limits = ResourceLimits(max_time_seconds=3600, max_tokens=100000)
        config = AgentConfiguration(
            tools=["git", "python", "pytest"],
            context={"project_root": "/path/to/project"},
            permissions=["read", "write", "execute"],
            resource_limits=limits,
            dependencies=["task-1", "task-2"],
        )
        assert config.tools == ["git", "python", "pytest"]
        assert config.context == {"project_root": "/path/to/project"}
        assert config.permissions == ["read", "write", "execute"]
        assert config.resource_limits == limits
        assert config.dependencies == ["task-1", "task-2"]

    def test_configuration_defaults(self):
        """Test AgentConfiguration with default values."""
        config = AgentConfiguration()
        assert config.tools == []
        assert config.context == {}
        assert config.permissions == []
        assert config.resource_limits.max_time_seconds is None
        assert config.dependencies == []


class TestInstructionGenerator:
    """Test InstructionGenerator class."""

    def test_generate_basic_instructions(self):
        """Test generating basic instructions for an agent."""
        role = AgentRole(
            name="developer",
            description="Software developer",
            capabilities=["coding", "debugging"],
            tools=["git", "python"],
            domain_knowledge=["software_engineering"],
        )
        subtasks = [
            Subtask(
                id="task-1",
                description="Implement login function",
                requirements={"capabilities": ["coding"]},
            )
        ]
        config = AgentConfiguration(tools=["git", "python", "pytest"])

        generator = InstructionGenerator()
        instructions = generator.generate_instructions(role, subtasks, config)

        assert isinstance(instructions, str)
        assert len(instructions) > 0
        assert "developer" in instructions.lower()
        assert "coding" in instructions.lower() or "implement" in instructions.lower()

    def test_generate_instructions_with_dependencies(self):
        """Test instruction generation includes dependencies."""
        role = AgentRole(
            name="tester",
            description="QA tester",
            capabilities=["testing"],
            tools=["pytest"],
            domain_knowledge=["qa_methodology"],
        )
        subtasks = [
            Subtask(
                id="task-2",
                description="Write tests for login function",
                requirements={},
            )
        ]
        config = AgentConfiguration(
            tools=["pytest"],
            dependencies=["task-1"],
        )

        generator = InstructionGenerator()
        instructions = generator.generate_instructions(role, subtasks, config)

        assert "task-1" in instructions or "depend" in instructions.lower()

    def test_generate_instructions_with_resource_limits(self):
        """Test instruction generation includes resource limits."""
        role = AgentRole(
            name="developer",
            description="Software developer",
            capabilities=["coding"],
            tools=["python"],
            domain_knowledge=["software_engineering"],
        )
        subtasks = [
            Subtask(id="task-1", description="Quick bug fix", requirements={})
        ]
        limits = ResourceLimits(max_time_seconds=1800, max_tokens=50000)
        config = AgentConfiguration(resource_limits=limits)

        generator = InstructionGenerator()
        instructions = generator.generate_instructions(role, subtasks, config)

        assert "1800" in instructions or "30" in instructions  # 30 minutes
        assert "50000" in instructions or "token" in instructions.lower()

    def test_generate_instructions_with_context(self):
        """Test instruction generation includes context."""
        role = AgentRole(
            name="developer",
            description="Software developer",
            capabilities=["coding"],
            tools=["python"],
            domain_knowledge=["software_engineering"],
        )
        subtasks = [Subtask(id="task-1", description="Fix auth bug", requirements={})]
        config = AgentConfiguration(
            context={
                "project_root": "/home/user/project",
                "branch": "feature/auth-fix",
            }
        )

        generator = InstructionGenerator()
        instructions = generator.generate_instructions(role, subtasks, config)

        assert "/home/user/project" in instructions or "project_root" in instructions
        assert "feature/auth-fix" in instructions or "branch" in instructions

    def test_generate_instructions_no_tasks(self):
        """Test instruction generation with no tasks."""
        role = AgentRole(
            name="developer",
            description="Software developer",
            capabilities=["coding"],
            tools=["python"],
            domain_knowledge=["software_engineering"],
        )
        config = AgentConfiguration()

        generator = InstructionGenerator()
        instructions = generator.generate_instructions(role, [], config)

        assert isinstance(instructions, str)
        # Should still provide role-based context even without tasks
        assert "developer" in instructions.lower()

    def test_generate_instructions_multiple_tasks(self):
        """Test instruction generation with multiple tasks."""
        role = AgentRole(
            name="developer",
            description="Software developer",
            capabilities=["coding"],
            tools=["python"],
            domain_knowledge=["software_engineering"],
        )
        subtasks = [
            Subtask(id="task-1", description="Fix login bug", requirements={}),
            Subtask(id="task-2", description="Add password validation", requirements={}),
            Subtask(id="task-3", description="Update tests", requirements={}),
        ]
        config = AgentConfiguration()

        generator = InstructionGenerator()
        instructions = generator.generate_instructions(role, subtasks, config)

        # Should mention all tasks
        assert "task-1" in instructions or "login" in instructions.lower()
        assert "task-2" in instructions or "password" in instructions.lower()
        assert "task-3" in instructions or "test" in instructions.lower()


class TestAgentFactory:
    """Test AgentFactory class."""

    def test_factory_initialization(self):
        """Test factory initialization with registry."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)
        assert factory is not None

    def test_create_agent_basic(self):
        """Test creating an agent with minimal configuration."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        agent = factory.create_agent(
            role_name="developer",
            subtasks=[],
        )

        assert isinstance(agent, Agent)
        assert agent.role == "developer"
        assert len(agent.capabilities) > 0
        assert agent.id.startswith("agent-")

    def test_create_agent_with_configuration(self):
        """Test creating an agent with full configuration."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        subtasks = [
            Subtask(
                id="task-1",
                description="Implement feature X",
                requirements={"capabilities": ["coding"]},
            )
        ]

        limits = ResourceLimits(max_time_seconds=3600, max_tokens=100000)
        config = AgentConfiguration(
            tools=["git", "python", "pytest"],
            context={"project": "auth-service"},
            permissions=["read", "write"],
            resource_limits=limits,
            dependencies=["task-0"],
        )

        agent = factory.create_agent(
            role_name="developer",
            subtasks=subtasks,
            configuration=config,
        )

        assert agent.role == "developer"
        assert agent.assigned_tasks == ["task-1"]
        # Check metadata contains configuration
        assert "instructions" in agent.metadata
        assert "configuration" in agent.metadata
        assert agent.metadata["configuration"]["tools"] == ["git", "python", "pytest"]
        assert agent.metadata["configuration"]["context"] == {"project": "auth-service"}

    def test_create_agent_invalid_role(self):
        """Test creating agent with non-existent role raises error."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        with pytest.raises(ValueError, match="Role 'invalid_role' not found"):
            factory.create_agent(role_name="invalid_role", subtasks=[])

    def test_create_agent_with_multiple_tasks(self):
        """Test creating agent with multiple assigned tasks."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        subtasks = [
            Subtask(id="task-1", description="Task 1", requirements={}),
            Subtask(id="task-2", description="Task 2", requirements={}),
            Subtask(id="task-3", description="Task 3", requirements={}),
        ]

        agent = factory.create_agent(role_name="developer", subtasks=subtasks)

        assert agent.assigned_tasks == ["task-1", "task-2", "task-3"]

    def test_create_agent_metadata_includes_resource_limits(self):
        """Test that agent metadata includes resource limits."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        limits = ResourceLimits(
            max_time_seconds=1800,
            max_api_calls=500,
            max_tokens=50000,
            max_memory_mb=256,
        )
        config = AgentConfiguration(resource_limits=limits)

        agent = factory.create_agent(
            role_name="developer",
            subtasks=[],
            configuration=config,
        )

        assert "configuration" in agent.metadata
        assert "resource_limits" in agent.metadata["configuration"]
        limits_data = agent.metadata["configuration"]["resource_limits"]
        assert limits_data["max_time_seconds"] == 1800
        assert limits_data["max_api_calls"] == 500
        assert limits_data["max_tokens"] == 50000
        assert limits_data["max_memory_mb"] == 256

    def test_create_agent_includes_instructions(self):
        """Test that created agent includes generated instructions."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        subtasks = [
            Subtask(id="task-1", description="Write unit tests", requirements={})
        ]

        agent = factory.create_agent(role_name="tester", subtasks=subtasks)

        assert "instructions" in agent.metadata
        instructions = agent.metadata["instructions"]
        assert isinstance(instructions, str)
        assert len(instructions) > 0
        assert "tester" in instructions.lower() or "test" in instructions.lower()

    def test_create_agent_with_permissions(self):
        """Test creating agent with specific permissions."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        config = AgentConfiguration(permissions=["read", "write", "execute"])

        agent = factory.create_agent(
            role_name="developer",
            subtasks=[],
            configuration=config,
        )

        assert agent.metadata["configuration"]["permissions"] == [
            "read",
            "write",
            "execute",
        ]

    def test_create_agent_preserves_role_capabilities(self):
        """Test that agent capabilities match role capabilities."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        agent = factory.create_agent(role_name="developer", subtasks=[])

        # Developer role should have coding, debugging, etc.
        capability_names = [cap.name for cap in agent.capabilities]
        assert "coding" in capability_names
        assert "debugging" in capability_names

    def test_create_multiple_agents_unique_ids(self):
        """Test that multiple agents get unique IDs."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        agent1 = factory.create_agent(role_name="developer", subtasks=[])
        agent2 = factory.create_agent(role_name="developer", subtasks=[])
        agent3 = factory.create_agent(role_name="tester", subtasks=[])

        assert agent1.id != agent2.id
        assert agent2.id != agent3.id
        assert agent1.id != agent3.id

    def test_create_agent_from_custom_role(self):
        """Test creating agent from a custom role."""
        registry = RoleRegistry()
        custom_role = AgentRole(
            name="custom_specialist",
            description="Custom specialist role",
            capabilities=["special_task"],
            tools=["special_tool"],
            domain_knowledge=["special_domain"],
        )
        registry.register_role(custom_role)

        factory = AgentFactory(registry)
        agent = factory.create_agent(role_name="custom_specialist", subtasks=[])

        assert agent.role == "custom_specialist"
        capability_names = [cap.name for cap in agent.capabilities]
        assert "special_task" in capability_names

    def test_configuration_serialization(self):
        """Test that configuration serializes correctly to metadata."""
        registry = RoleRegistry.create_standard_registry()
        factory = AgentFactory(registry)

        limits = ResourceLimits(max_time_seconds=3600)
        config = AgentConfiguration(
            tools=["git"],
            context={"key": "value"},
            permissions=["read"],
            resource_limits=limits,
            dependencies=["dep-1"],
        )

        agent = factory.create_agent(
            role_name="developer",
            subtasks=[],
            configuration=config,
        )

        config_data = agent.metadata["configuration"]
        assert config_data["tools"] == ["git"]
        assert config_data["context"] == {"key": "value"}
        assert config_data["permissions"] == ["read"]
        assert config_data["resource_limits"]["max_time_seconds"] == 3600
        assert config_data["dependencies"] == ["dep-1"]
