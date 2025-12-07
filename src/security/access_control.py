"""Access control policies for agent actions.

This module defines fine-grained access control policies that determine
what actions agents can perform on different resource types.
"""

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PermissionLevel(Enum):
    """Permission levels in increasing order of privilege."""

    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


class ResourceType(Enum):
    """Types of resources that can be accessed."""

    FILE = "file"
    DIRECTORY = "directory"
    COMMAND = "command"
    NETWORK = "network"
    MEMORY = "memory"
    AGENT = "agent"


class ActionType(Enum):
    """Types of actions that can be performed."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    CREATE = "create"
    MODIFY = "modify"


@dataclass
class Resource:
    """A resource that can be accessed."""

    resource_type: ResourceType
    """Type of the resource."""

    path: str
    """Path or identifier for the resource."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the resource."""


@dataclass
class Action:
    """An action to be performed on a resource."""

    action_type: ActionType
    """Type of action."""

    resource: Resource
    """Resource to act upon."""

    agent_id: str
    """Agent requesting the action."""


@dataclass
class Permission:
    """Permission granted to an agent for a resource type."""

    agent_id: str
    """Agent this permission applies to."""

    resource_type: ResourceType
    """Type of resource this permission covers."""

    level: PermissionLevel
    """Level of access granted."""

    allowed_paths: list[str] = field(default_factory=list)
    """Specific paths allowed (for FILE/DIRECTORY resources)."""

    allowed_commands: list[str] = field(default_factory=list)
    """Specific commands allowed (for COMMAND resources)."""


@dataclass
class AccessDecision:
    """Decision on whether to allow an action."""

    allowed: bool
    """Whether the action is allowed."""

    reason: str
    """Explanation for the decision."""

    required_permission: PermissionLevel | None = None
    """Required permission level if access was denied."""


class AccessControlPolicy:
    """Manages access control permissions for agents.

    The policy maintains a registry of permissions for each agent and
    provides methods to check whether specific actions are allowed.
    """

    def __init__(self) -> None:
        """Initialize access control policy."""
        self.permissions: dict[str, dict[ResourceType, Permission]] = {}
        """Map of agent_id -> resource_type -> permission."""

    def grant_permission(self, permission: Permission) -> None:
        """Grant a permission to an agent.

        Args:
            permission: Permission to grant
        """
        if permission.agent_id not in self.permissions:
            self.permissions[permission.agent_id] = {}

        self.permissions[permission.agent_id][permission.resource_type] = permission

    def revoke_permission(self, agent_id: str, resource_type: ResourceType) -> None:
        """Revoke a permission from an agent.

        Args:
            agent_id: Agent to revoke permission from
            resource_type: Type of resource permission to revoke
        """
        if agent_id in self.permissions:
            self.permissions[agent_id].pop(resource_type, None)

    def check_access(self, action: Action) -> AccessDecision:
        """Check if an action is allowed.

        Args:
            action: Action to check

        Returns:
            AccessDecision with allowed flag and reason
        """
        # Check if agent has any permissions
        if action.agent_id not in self.permissions:
            return AccessDecision(
                allowed=False,
                reason=f"Agent {action.agent_id} has no permissions",
            )

        # Check if agent has permission for this resource type
        resource_type = action.resource.resource_type
        if resource_type not in self.permissions[action.agent_id]:
            return AccessDecision(
                allowed=False,
                reason=(
                    f"Agent {action.agent_id} has no permission for "
                    f"{resource_type.value} resources"
                ),
            )

        permission = self.permissions[action.agent_id][resource_type]

        # Check if permission level is sufficient
        required_level = self._get_required_permission_level(action.action_type)
        if permission.level.value < required_level.value:
            return AccessDecision(
                allowed=False,
                reason=(
                    f"Agent has {permission.level.name} but needs "
                    f"{required_level.name} permission"
                ),
                required_permission=required_level,
            )

        # For file/directory resources, check path permissions
        if resource_type in (ResourceType.FILE, ResourceType.DIRECTORY):
            if not self._check_path_permission(action.resource.path, permission.allowed_paths):
                return AccessDecision(
                    allowed=False,
                    reason=f"Path {action.resource.path} not in allowed paths",
                )

        # For command resources, check command permissions
        if resource_type == ResourceType.COMMAND:
            if not self._check_command_permission(
                action.resource.path, permission.allowed_commands
            ):
                return AccessDecision(
                    allowed=False,
                    reason="Command not in allowed commands list",
                )

        return AccessDecision(
            allowed=True,
            reason=f"Agent has {permission.level.name} permission for {resource_type.value}",
        )

    def get_agent_permissions(self, agent_id: str) -> dict[ResourceType, Permission]:
        """Get all permissions for an agent.

        Args:
            agent_id: Agent to get permissions for

        Returns:
            Dictionary of resource_type -> permission
        """
        return self.permissions.get(agent_id, {}).copy()

    def _get_required_permission_level(self, action_type: ActionType) -> PermissionLevel:
        """Get required permission level for an action type.

        Args:
            action_type: Type of action

        Returns:
            Required permission level
        """
        # Map action types to required permission levels
        action_level_map = {
            ActionType.READ: PermissionLevel.READ,
            ActionType.WRITE: PermissionLevel.WRITE,
            ActionType.CREATE: PermissionLevel.WRITE,
            ActionType.MODIFY: PermissionLevel.WRITE,
            ActionType.EXECUTE: PermissionLevel.EXECUTE,
            ActionType.DELETE: PermissionLevel.WRITE,
        }
        return action_level_map.get(action_type, PermissionLevel.ADMIN)

    def _check_path_permission(self, path: str, allowed_paths: list[str]) -> bool:
        """Check if path is allowed.

        Args:
            path: Path to check
            allowed_paths: List of allowed paths (may include wildcards)

        Returns:
            True if path is allowed
        """
        if not allowed_paths:
            return False

        try:
            abs_path = Path(path).resolve()
        except (OSError, RuntimeError):
            return False

        for allowed_pattern in allowed_paths:
            # Handle wildcard patterns
            if "*" in allowed_pattern:
                if fnmatch.fnmatch(str(abs_path), allowed_pattern):
                    return True
                # Also check if path starts with the pattern prefix
                prefix = allowed_pattern.split("*")[0].rstrip("/")
                if str(abs_path).startswith(prefix):
                    return True
            else:
                # Exact or prefix match
                try:
                    allowed_abs = Path(allowed_pattern).resolve()
                    if abs_path == allowed_abs or allowed_abs in abs_path.parents:
                        return True
                except (OSError, RuntimeError):
                    continue

        return False

    def _check_command_permission(self, command: str, allowed_commands: list[str]) -> bool:
        """Check if command is allowed.

        Args:
            command: Command to check (e.g., "git status")
            allowed_commands: List of allowed base commands (e.g., ["git", "pytest"])

        Returns:
            True if command is allowed
        """
        if not allowed_commands:
            return False

        # Extract base command (first word)
        base_command = command.split()[0] if command else ""

        return base_command in allowed_commands
