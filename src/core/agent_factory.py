"""Agent Factory for instantiating and configuring agents."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.core.role_registry import RoleRegistry
from src.models.agent import Agent, AgentCapability, AgentRole
from src.models.task import Subtask


@dataclass
class ResourceLimits:
    """
    Resource limits for agent execution.

    Defines constraints on time, API calls, tokens, and memory usage
    to prevent resource exhaustion and enable budget tracking.
    """

    max_time_seconds: int | None = None
    max_api_calls: int | None = None
    max_tokens: int | None = None
    max_memory_mb: int | None = None


@dataclass
class AgentConfiguration:
    """
    Configuration for agent instantiation.

    Specifies tools, context, permissions, resource limits, and dependencies
    that the agent should use during task execution.
    """

    tools: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    dependencies: list[str] = field(default_factory=list)


class InstructionGenerator:
    """
    Generates clear, unambiguous instructions for agents.

    Creates detailed instructions that include role description, assigned tasks,
    available tools, resource constraints, and context.
    """

    def generate_instructions(
        self,
        role: AgentRole,
        subtasks: list[Subtask],
        configuration: AgentConfiguration,
    ) -> str:
        """
        Generate instructions for an agent.

        Args:
            role: The agent's role definition
            subtasks: List of subtasks assigned to the agent
            configuration: Agent configuration with tools, context, etc.

        Returns:
            Formatted instruction string for the agent
        """
        sections = []

        # Role and capabilities section
        sections.append(f"# Agent Role: {role.name.title()}")
        sections.append(f"\n{role.description}")
        sections.append("\n## Capabilities")
        for capability in role.capabilities:
            sections.append(f"- {capability}")

        # Tools section
        if configuration.tools or role.tools:
            sections.append("\n## Available Tools")
            tools = configuration.tools if configuration.tools else role.tools
            for tool in tools:
                sections.append(f"- {tool}")

        # Tasks section
        if subtasks:
            sections.append("\n## Assigned Tasks")
            for i, task in enumerate(subtasks, 1):
                sections.append(f"\n### Task {i}: {task.id}")
                sections.append(f"{task.description}")
                if task.requirements:
                    sections.append(f"Requirements: {task.requirements}")
        else:
            sections.append("\n## Assigned Tasks")
            sections.append("No specific tasks assigned. Stand by for instructions.")

        # Dependencies section
        if configuration.dependencies:
            sections.append("\n## Dependencies")
            sections.append(
                "The following tasks must be completed before you can start:"
            )
            for dep in configuration.dependencies:
                sections.append(f"- {dep}")

        # Context section
        if configuration.context:
            sections.append("\n## Context")
            for key, value in configuration.context.items():
                sections.append(f"- {key}: {value}")

        # Resource limits section
        limits = configuration.resource_limits
        if any(
            [
                limits.max_time_seconds,
                limits.max_api_calls,
                limits.max_tokens,
                limits.max_memory_mb,
            ]
        ):
            sections.append("\n## Resource Limits")
            if limits.max_time_seconds:
                minutes = limits.max_time_seconds // 60
                sections.append(
                    f"- Time limit: {limits.max_time_seconds} seconds ({minutes} minutes)"
                )
            if limits.max_api_calls:
                sections.append(f"- Maximum API calls: {limits.max_api_calls}")
            if limits.max_tokens:
                sections.append(f"- Maximum tokens: {limits.max_tokens}")
            if limits.max_memory_mb:
                sections.append(f"- Memory limit: {limits.max_memory_mb} MB")

        # Permissions section
        if configuration.permissions:
            sections.append("\n## Permissions")
            for permission in configuration.permissions:
                sections.append(f"- {permission}")

        # Domain knowledge section
        if role.domain_knowledge:
            sections.append("\n## Domain Knowledge")
            for knowledge in role.domain_knowledge:
                sections.append(f"- {knowledge}")

        return "\n".join(sections)


class AgentFactory:
    """
    Factory for creating configured agent instances.

    The AgentFactory creates Agent instances from AgentRole definitions,
    applying configuration such as tools, context, permissions, and resource limits.
    """

    def __init__(self, registry: RoleRegistry):
        """
        Initialize the agent factory.

        Args:
            registry: RoleRegistry containing available agent roles
        """
        self._registry = registry
        self._instruction_generator = InstructionGenerator()

    def create_agent(
        self,
        role_name: str,
        subtasks: list[Subtask],
        configuration: AgentConfiguration | None = None,
    ) -> Agent:
        """
        Create a configured agent instance.

        Args:
            role_name: Name of the role to instantiate
            subtasks: List of subtasks to assign to the agent
            configuration: Optional configuration for the agent

        Returns:
            Configured Agent instance

        Raises:
            ValueError: If role_name is not found in registry
        """
        # Get role from registry
        role = self._registry.get_role(role_name)
        if role is None:
            raise ValueError(
                f"Role '{role_name}' not found in registry. "
                f"Available roles: {[r.name for r in self._registry.list_roles()]}"
            )

        # Use default configuration if none provided
        if configuration is None:
            configuration = AgentConfiguration()

        # Generate unique agent ID
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        # Convert role capabilities to agent capabilities
        capabilities = self._create_capabilities(role, configuration)

        # Generate instructions
        instructions = self._instruction_generator.generate_instructions(
            role, subtasks, configuration
        )

        # Extract task IDs for assignment
        assigned_task_ids = [task.id for task in subtasks]

        # Serialize configuration to metadata
        config_dict = self._serialize_configuration(configuration)

        # Create agent
        agent = Agent(
            id=agent_id,
            role=role.name,
            capabilities=capabilities,
            assigned_tasks=assigned_task_ids,
            metadata={
                "instructions": instructions,
                "configuration": config_dict,
                "tools": configuration.tools if configuration.tools else role.tools,
                "domain_knowledge": role.domain_knowledge,
            },
        )

        return agent

    def _create_capabilities(
        self, role: AgentRole, configuration: AgentConfiguration
    ) -> list[AgentCapability]:
        """
        Create AgentCapability objects from role definition.

        Args:
            role: The agent role
            configuration: Agent configuration

        Returns:
            List of AgentCapability objects
        """
        capabilities = []
        tools = configuration.tools if configuration.tools else role.tools

        for cap_name in role.capabilities:
            capability = AgentCapability(
                name=cap_name,
                description=f"{cap_name} capability for {role.name}",
                tools=tools,
            )
            capabilities.append(capability)

        return capabilities

    def _serialize_configuration(
        self, configuration: AgentConfiguration
    ) -> dict[str, Any]:
        """
        Serialize AgentConfiguration to a dictionary.

        Args:
            configuration: AgentConfiguration to serialize

        Returns:
            Dictionary representation of configuration
        """
        # Convert ResourceLimits to dict
        limits_dict = {
            "max_time_seconds": configuration.resource_limits.max_time_seconds,
            "max_api_calls": configuration.resource_limits.max_api_calls,
            "max_tokens": configuration.resource_limits.max_tokens,
            "max_memory_mb": configuration.resource_limits.max_memory_mb,
        }

        return {
            "tools": configuration.tools,
            "context": configuration.context,
            "permissions": configuration.permissions,
            "resource_limits": limits_dict,
            "dependencies": configuration.dependencies,
        }
