"""Tests for action validation framework."""

from src.security.access_control import (
    Action,
    ActionType,
    Resource,
    ResourceType,
)
from src.security.action_validator import (
    ActionValidator,
    RiskLevel,
    SafetyBoundary,
    ValidationResult,
)


def test_risk_level_enum():
    """Test that RiskLevel enum has expected values."""
    assert RiskLevel.SAFE.value == "safe"
    assert RiskLevel.MODERATE.value == "moderate"
    assert RiskLevel.DESTRUCTIVE.value == "destructive"


def test_validation_result_creation():
    """Test ValidationResult dataclass creation."""
    result = ValidationResult(
        allowed=True,
        risk_level=RiskLevel.SAFE,
        reason="Read operation is safe",
    )
    assert result.allowed is True
    assert result.risk_level == RiskLevel.SAFE
    assert result.reason == "Read operation is safe"
    assert result.requires_approval is False
    assert result.boundary_violations == []


def test_classify_safe_action():
    """Test that read actions are classified as SAFE."""
    validator = ActionValidator()

    action = Action(
        action_type=ActionType.READ,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    risk = validator.classify_risk(action)
    assert risk == RiskLevel.SAFE


def test_classify_moderate_action():
    """Test that write/create actions are classified as MODERATE."""
    validator = ActionValidator()

    # Test WRITE
    action = Action(
        action_type=ActionType.WRITE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )
    assert validator.classify_risk(action) == RiskLevel.MODERATE

    # Test CREATE
    action = Action(
        action_type=ActionType.CREATE,
        resource=Resource(ResourceType.DIRECTORY, "/tmp/newdir"),
        agent_id="test-agent",
    )
    assert validator.classify_risk(action) == RiskLevel.MODERATE


def test_classify_destructive_action():
    """Test that delete/modify actions are classified as DESTRUCTIVE."""
    validator = ActionValidator()

    # Test DELETE
    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )
    assert validator.classify_risk(action) == RiskLevel.DESTRUCTIVE

    # Test MODIFY on critical file
    action = Action(
        action_type=ActionType.MODIFY,
        resource=Resource(ResourceType.FILE, "/etc/passwd"),
        agent_id="test-agent",
    )
    assert validator.classify_risk(action) == RiskLevel.DESTRUCTIVE


def test_safety_boundary_violation():
    """Test that actions violating safety boundaries are blocked."""
    validator = ActionValidator()

    # Add boundary: no deletion of /etc/* files
    boundary = SafetyBoundary(
        name="protect_system_files",
        description="Prevent deletion of system files",
        forbidden_action_types=[ActionType.DELETE],
        forbidden_paths=["/etc/*"],
    )
    validator.add_boundary(boundary)

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/etc/hosts"),
        agent_id="test-agent",
    )

    result = validator.validate_action(action, access_control_policy=None)
    assert result.allowed is False
    assert len(result.boundary_violations) == 1
    assert result.boundary_violations[0] == "protect_system_files"


def test_no_boundary_violation():
    """Test that actions not violating boundaries are allowed."""
    validator = ActionValidator()

    # Add boundary: no deletion of /etc/* files
    boundary = SafetyBoundary(
        name="protect_system_files",
        description="Prevent deletion of system files",
        forbidden_action_types=[ActionType.DELETE],
        forbidden_paths=["/etc/*"],
    )
    validator.add_boundary(boundary)

    # Try deleting from /tmp (allowed)
    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )

    result = validator.validate_action(action, access_control_policy=None)
    # Should not have boundary violation (may still fail access control)
    assert len(result.boundary_violations) == 0


def test_destructive_action_requires_approval():
    """Test that destructive actions require approval."""
    validator = ActionValidator()

    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/important.txt"),
        agent_id="test-agent",
    )

    result = validator.validate_action(action, access_control_policy=None)
    assert result.risk_level == RiskLevel.DESTRUCTIVE
    assert result.requires_approval is True


def test_access_control_integration():
    """Test that action validator integrates with access control policy."""
    from src.security.access_control import (
        AccessControlPolicy,
        Permission,
        PermissionLevel,
    )

    validator = ActionValidator()
    policy = AccessControlPolicy()

    # Grant READ permission to agent
    policy.grant_permission(
        Permission(
            agent_id="test-agent",
            resource_type=ResourceType.FILE,
            level=PermissionLevel.READ,
            allowed_paths=["/tmp/*"],
        )
    )

    # Try READ action (should be allowed)
    action = Action(
        action_type=ActionType.READ,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )
    result = validator.validate_action(action, access_control_policy=policy)
    assert result.allowed is True

    # Try WRITE action (should be denied - insufficient permission)
    action = Action(
        action_type=ActionType.WRITE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )
    result = validator.validate_action(action, access_control_policy=policy)
    assert result.allowed is False


def test_multiple_boundary_violations():
    """Test that multiple boundary violations are tracked."""
    validator = ActionValidator()

    # Add two boundaries
    boundary1 = SafetyBoundary(
        name="no_root_delete",
        description="Prevent deletion of root directory",
        forbidden_action_types=[ActionType.DELETE],
        forbidden_paths=["/"],
    )
    boundary2 = SafetyBoundary(
        name="no_system_delete",
        description="Prevent deletion of system files",
        forbidden_action_types=[ActionType.DELETE],
        forbidden_paths=["/etc/*", "/usr/*", "/var/*"],
    )
    validator.add_boundary(boundary1)
    validator.add_boundary(boundary2)

    # Try deleting /etc/hosts (violates both boundaries)
    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/etc/hosts"),
        agent_id="test-agent",
    )

    result = validator.validate_action(action, access_control_policy=None)
    assert result.allowed is False
    # Should violate at least boundary2
    assert "no_system_delete" in result.boundary_violations


def test_remove_boundary():
    """Test that boundaries can be removed."""
    validator = ActionValidator()

    boundary = SafetyBoundary(
        name="test_boundary",
        description="Test boundary",
        forbidden_action_types=[ActionType.DELETE],
        forbidden_paths=["/tmp/*"],
    )
    validator.add_boundary(boundary)

    # Should have violation
    action = Action(
        action_type=ActionType.DELETE,
        resource=Resource(ResourceType.FILE, "/tmp/test.txt"),
        agent_id="test-agent",
    )
    result = validator.validate_action(action, access_control_policy=None)
    assert len(result.boundary_violations) > 0

    # Remove boundary
    validator.remove_boundary("test_boundary")

    # Should not have violation now
    result = validator.validate_action(action, access_control_policy=None)
    assert len(result.boundary_violations) == 0


def test_get_all_boundaries():
    """Test retrieving all configured boundaries."""
    validator = ActionValidator()

    boundary1 = SafetyBoundary(
        name="boundary1",
        description="First boundary",
        forbidden_action_types=[ActionType.DELETE],
        forbidden_paths=["/etc/*"],
    )
    boundary2 = SafetyBoundary(
        name="boundary2",
        description="Second boundary",
        forbidden_action_types=[ActionType.MODIFY],
        forbidden_paths=["/var/*"],
    )

    validator.add_boundary(boundary1)
    validator.add_boundary(boundary2)

    boundaries = validator.get_all_boundaries()
    assert len(boundaries) == 2
    assert "boundary1" in boundaries
    assert "boundary2" in boundaries
