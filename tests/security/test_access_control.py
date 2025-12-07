"""Tests for access control policies."""

from src.security.access_control import (
    AccessControlPolicy,
    AccessDecision,
    Action,
    ActionType,
    Permission,
    PermissionLevel,
    Resource,
    ResourceType,
)


class TestPermissionLevel:
    """Test PermissionLevel enum."""

    def test_permission_levels_exist(self):
        """Test all permission levels are defined."""
        assert PermissionLevel.NONE
        assert PermissionLevel.READ
        assert PermissionLevel.WRITE
        assert PermissionLevel.EXECUTE
        assert PermissionLevel.ADMIN

    def test_permission_level_ordering(self):
        """Test permission levels can be compared."""
        assert PermissionLevel.NONE.value < PermissionLevel.READ.value
        assert PermissionLevel.READ.value < PermissionLevel.WRITE.value
        assert PermissionLevel.WRITE.value < PermissionLevel.EXECUTE.value
        assert PermissionLevel.EXECUTE.value < PermissionLevel.ADMIN.value


class TestResourceType:
    """Test ResourceType enum."""

    def test_resource_types_exist(self):
        """Test all resource types are defined."""
        assert ResourceType.FILE
        assert ResourceType.DIRECTORY
        assert ResourceType.COMMAND
        assert ResourceType.NETWORK
        assert ResourceType.MEMORY
        assert ResourceType.AGENT


class TestActionType:
    """Test ActionType enum."""

    def test_action_types_exist(self):
        """Test all action types are defined."""
        assert ActionType.READ
        assert ActionType.WRITE
        assert ActionType.EXECUTE
        assert ActionType.DELETE
        assert ActionType.CREATE
        assert ActionType.MODIFY


class TestResource:
    """Test Resource dataclass."""

    def test_resource_creation(self):
        """Test creating a resource."""
        resource = Resource(
            resource_type=ResourceType.FILE,
            path="/tmp/test.txt",
            metadata={"size": 1024},
        )
        assert resource.resource_type == ResourceType.FILE
        assert resource.path == "/tmp/test.txt"
        assert resource.metadata["size"] == 1024

    def test_resource_without_metadata(self):
        """Test creating a resource without metadata."""
        resource = Resource(
            resource_type=ResourceType.DIRECTORY,
            path="/tmp/workspace",
        )
        assert resource.resource_type == ResourceType.DIRECTORY
        assert resource.metadata == {}


class TestAction:
    """Test Action dataclass."""

    def test_action_creation(self):
        """Test creating an action."""
        resource = Resource(ResourceType.FILE, "/tmp/test.txt")
        action = Action(
            action_type=ActionType.READ,
            resource=resource,
            agent_id="test-agent",
        )
        assert action.action_type == ActionType.READ
        assert action.resource == resource
        assert action.agent_id == "test-agent"


class TestPermission:
    """Test Permission dataclass."""

    def test_permission_creation(self):
        """Test creating a permission."""
        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        assert permission.agent_id == "test-agent"
        assert permission.resource_type == ResourceType.FILE
        assert permission.level == PermissionLevel.READ
        assert "/tmp" in permission.allowed_paths

    def test_permission_with_commands(self):
        """Test creating a permission with allowed commands."""
        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.COMMAND,
            level=PermissionLevel.EXECUTE,
            allowed_commands=["git", "pytest"],
        )
        assert "git" in permission.allowed_commands
        assert "pytest" in permission.allowed_commands


class TestAccessDecision:
    """Test AccessDecision dataclass."""

    def test_access_allowed(self):
        """Test creating an allowed access decision."""
        decision = AccessDecision(
            allowed=True,
            reason="Agent has READ permission for this path",
        )
        assert decision.allowed is True
        assert "READ permission" in decision.reason

    def test_access_denied(self):
        """Test creating a denied access decision."""
        decision = AccessDecision(
            allowed=False,
            reason="Agent lacks WRITE permission",
            required_permission=PermissionLevel.WRITE,
        )
        assert decision.allowed is False
        assert decision.required_permission == PermissionLevel.WRITE


class TestAccessControlPolicy:
    """Test AccessControlPolicy class."""

    def test_policy_creation(self):
        """Test creating an access control policy."""
        policy = AccessControlPolicy()
        assert policy.permissions == {}

    def test_grant_permission(self):
        """Test granting a permission."""
        policy = AccessControlPolicy()
        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        policy.grant_permission(permission)

        # Verify permission was stored
        assert "test-agent" in policy.permissions
        assert ResourceType.FILE in policy.permissions["test-agent"]

    def test_grant_multiple_permissions(self):
        """Test granting multiple permissions to same agent."""
        policy = AccessControlPolicy()

        perm1 = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        perm2 = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.COMMAND,
            level=PermissionLevel.EXECUTE,
            allowed_commands=["git"],
        )

        policy.grant_permission(perm1)
        policy.grant_permission(perm2)

        assert ResourceType.FILE in policy.permissions["test-agent"]
        assert ResourceType.COMMAND in policy.permissions["test-agent"]

    def test_revoke_permission(self):
        """Test revoking a permission."""
        policy = AccessControlPolicy()

        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        policy.grant_permission(permission)
        policy.revoke_permission("test-agent", ResourceType.FILE)

        # Permission should be removed
        assert ResourceType.FILE not in policy.permissions.get("test-agent", {})

    def test_check_access_allowed(self):
        """Test checking access for allowed action."""
        policy = AccessControlPolicy()

        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        policy.grant_permission(permission)

        resource = Resource(ResourceType.FILE, "/tmp/test.txt")
        action = Action(ActionType.READ, resource, "test-agent")

        decision = policy.check_access(action)
        assert decision.allowed is True

    def test_check_access_denied_no_permission(self):
        """Test checking access when agent has no permission."""
        policy = AccessControlPolicy()

        resource = Resource(ResourceType.FILE, "/tmp/test.txt")
        action = Action(ActionType.READ, resource, "test-agent")

        decision = policy.check_access(action)
        assert decision.allowed is False
        assert "no permission" in decision.reason.lower()

    def test_check_access_denied_insufficient_level(self):
        """Test checking access when permission level is insufficient."""
        policy = AccessControlPolicy()

        # Grant READ permission
        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        policy.grant_permission(permission)

        # Try to WRITE (requires higher permission)
        resource = Resource(ResourceType.FILE, "/tmp/test.txt")
        action = Action(ActionType.WRITE, resource, "test-agent")

        decision = policy.check_access(action)
        assert decision.allowed is False
        assert decision.required_permission == PermissionLevel.WRITE

    def test_check_access_denied_path_not_allowed(self):
        """Test checking access for path outside allowed paths."""
        policy = AccessControlPolicy()

        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        policy.grant_permission(permission)

        # Try to access file outside allowed path
        resource = Resource(ResourceType.FILE, "/etc/passwd")
        action = Action(ActionType.READ, resource, "test-agent")

        decision = policy.check_access(action)
        assert decision.allowed is False
        assert "not in allowed paths" in decision.reason.lower()

    def test_check_access_command_allowed(self):
        """Test checking access for allowed command."""
        policy = AccessControlPolicy()

        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.COMMAND,
            level=PermissionLevel.EXECUTE,
            allowed_commands=["git", "pytest"],
        )
        policy.grant_permission(permission)

        resource = Resource(ResourceType.COMMAND, "git status")
        action = Action(ActionType.EXECUTE, resource, "test-agent")

        decision = policy.check_access(action)
        assert decision.allowed is True

    def test_check_access_command_denied(self):
        """Test checking access for forbidden command."""
        policy = AccessControlPolicy()

        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.COMMAND,
            level=PermissionLevel.EXECUTE,
            allowed_commands=["git"],
        )
        policy.grant_permission(permission)

        # Try to execute command not in allowed list
        resource = Resource(ResourceType.COMMAND, "rm -rf /")
        action = Action(ActionType.EXECUTE, resource, "test-agent")

        decision = policy.check_access(action)
        assert decision.allowed is False

    def test_get_agent_permissions_empty(self):
        """Test getting permissions for agent with no permissions."""
        policy = AccessControlPolicy()
        permissions = policy.get_agent_permissions("test-agent")
        assert permissions == {}

    def test_get_agent_permissions(self):
        """Test getting all permissions for an agent."""
        policy = AccessControlPolicy()

        perm1 = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        perm2 = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.COMMAND,
            level=PermissionLevel.EXECUTE,
            allowed_commands=["git"],
        )

        policy.grant_permission(perm1)
        policy.grant_permission(perm2)

        permissions = policy.get_agent_permissions("test-agent")
        assert ResourceType.FILE in permissions
        assert ResourceType.COMMAND in permissions
        assert permissions[ResourceType.FILE] == perm1
        assert permissions[ResourceType.COMMAND] == perm2

    def test_isolation_between_agents(self):
        """Test that permissions are isolated between agents."""
        policy = AccessControlPolicy()

        perm1 = Permission(
            agent_id="agent-1",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.WRITE,
            allowed_paths=["/tmp/agent1"],
        )
        perm2 = Permission(
            agent_id="agent-2",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp/agent2"],
        )

        policy.grant_permission(perm1)
        policy.grant_permission(perm2)

        # agent-1 should not be able to access agent-2's path
        resource = Resource(ResourceType.FILE, "/tmp/agent2/data.txt")
        action = Action(ActionType.READ, resource, "agent-1")
        decision = policy.check_access(action)
        assert decision.allowed is False

    def test_wildcard_path_matching(self):
        """Test wildcard path matching for permissions."""
        policy = AccessControlPolicy()

        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp/*"],
        )
        policy.grant_permission(permission)

        # Should allow access to any file under /tmp
        resource = Resource(ResourceType.FILE, "/tmp/subdir/test.txt")
        action = Action(ActionType.READ, resource, "test-agent")

        decision = policy.check_access(action)
        assert decision.allowed is True

    def test_action_type_to_permission_level_mapping(self):
        """Test that action types correctly map to required permission levels."""
        policy = AccessControlPolicy()

        # Grant READ permission
        permission = Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp"],
        )
        policy.grant_permission(permission)

        resource = Resource(ResourceType.FILE, "/tmp/test.txt")

        # READ action should work with READ permission
        read_action = Action(ActionType.READ, resource, "test-agent")
        assert policy.check_access(read_action).allowed is True

        # WRITE action should fail with READ permission
        write_action = Action(ActionType.WRITE, resource, "test-agent")
        assert policy.check_access(write_action).allowed is False

        # DELETE action should fail with READ permission
        delete_action = Action(ActionType.DELETE, resource, "test-agent")
        assert policy.check_access(delete_action).allowed is False
