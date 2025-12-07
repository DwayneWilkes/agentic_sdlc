"""Tests for undo tracking and rollback planning."""

from datetime import datetime

from src.core.error_detection import ErrorContext, ErrorSeverity, ErrorType
from src.core.undo_tracker import (
    ActionType,
    RiskLevel,
    RollbackCommand,
    RollbackPlanner,
    Snapshot,
    UndoChain,
    UndoTracker,
)


class TestActionType:
    """Test ActionType enum."""

    def test_action_type_enum_values(self) -> None:
        """Test that ActionType enum has expected values."""
        assert ActionType.FILE_EDIT == "file_edit"
        assert ActionType.FILE_CREATE == "file_create"
        assert ActionType.FILE_DELETE == "file_delete"
        assert ActionType.CONFIG_CHANGE == "config_change"
        assert ActionType.PACKAGE_INSTALL == "package_install"
        assert ActionType.DATABASE_MIGRATION == "database_migration"
        assert ActionType.API_DEPLOYMENT == "api_deployment"


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_level_enum_values(self) -> None:
        """Test that RiskLevel enum has expected numeric values."""
        assert RiskLevel.LOW == 1
        assert RiskLevel.MEDIUM == 2
        assert RiskLevel.HIGH == 3
        assert RiskLevel.CRITICAL == 4

    def test_risk_level_comparison(self) -> None:
        """Test that RiskLevel values can be compared."""
        assert RiskLevel.CRITICAL > RiskLevel.HIGH
        assert RiskLevel.HIGH > RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM > RiskLevel.LOW


class TestRollbackCommand:
    """Test RollbackCommand dataclass."""

    def test_rollback_command_creation(self) -> None:
        """Test creating a rollback command."""
        rollback = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit authentication module",
            undo_command="git checkout abc123 -- src/auth.py",
            files_affected=["src/auth.py"],
            risk_level=RiskLevel.HIGH,
            rollback_verified=True,
        )
        assert rollback.action == ActionType.FILE_EDIT
        assert rollback.description == "Edit authentication module"
        assert rollback.undo_command == "git checkout abc123 -- src/auth.py"
        assert rollback.files_affected == ["src/auth.py"]
        assert rollback.risk_level == RiskLevel.HIGH
        assert rollback.rollback_verified is True

    def test_rollback_command_with_metadata(self) -> None:
        """Test rollback command with additional metadata."""
        rollback = RollbackCommand(
            action=ActionType.PACKAGE_INSTALL,
            description="Install numpy",
            undo_command="pip uninstall -y numpy",
            files_affected=[],
            risk_level=RiskLevel.LOW,
            metadata={"package": "numpy", "version": "1.24.0"},
        )
        assert rollback.metadata["package"] == "numpy"
        assert rollback.metadata["version"] == "1.24.0"


class TestSnapshot:
    """Test Snapshot dataclass."""

    def test_snapshot_creation(self) -> None:
        """Test creating a snapshot."""
        snapshot = Snapshot(
            timestamp=datetime.now(),
            description="Before refactoring auth module",
            state={"git_commit": "abc123", "files": ["src/auth.py"]},
        )
        assert snapshot.description == "Before refactoring auth module"
        assert snapshot.state["git_commit"] == "abc123"
        assert "src/auth.py" in snapshot.state["files"]


class TestUndoChain:
    """Test UndoChain class."""

    def test_undo_chain_creation(self) -> None:
        """Test creating an undo chain."""
        chain = UndoChain()
        assert chain.depth() == 0
        assert chain.is_empty() is True

    def test_add_rollback_command(self) -> None:
        """Test adding rollback commands to chain."""
        chain = UndoChain()
        rollback1 = RollbackCommand(
            action=ActionType.FILE_CREATE,
            description="Create new file",
            undo_command="rm src/new.py",
            files_affected=["src/new.py"],
            risk_level=RiskLevel.LOW,
        )
        rollback2 = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit file",
            undo_command="git checkout -- src/old.py",
            files_affected=["src/old.py"],
            risk_level=RiskLevel.MEDIUM,
        )
        chain.add(rollback1)
        chain.add(rollback2)

        assert chain.depth() == 2
        assert chain.is_empty() is False

    def test_get_last_rollback(self) -> None:
        """Test getting the most recent rollback command."""
        chain = UndoChain()
        rollback1 = RollbackCommand(
            action=ActionType.FILE_CREATE,
            description="Create file",
            undo_command="rm file1.py",
            files_affected=["file1.py"],
            risk_level=RiskLevel.LOW,
        )
        rollback2 = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit file",
            undo_command="git checkout file2.py",
            files_affected=["file2.py"],
            risk_level=RiskLevel.MEDIUM,
        )
        chain.add(rollback1)
        chain.add(rollback2)

        last = chain.get_last()
        assert last is not None
        assert last.description == "Edit file"

    def test_get_last_on_empty_chain(self) -> None:
        """Test getting last rollback on empty chain returns None."""
        chain = UndoChain()
        assert chain.get_last() is None

    def test_get_all_rollbacks(self) -> None:
        """Test getting all rollback commands in reverse order."""
        chain = UndoChain()
        rollback1 = RollbackCommand(
            action=ActionType.FILE_CREATE,
            description="First",
            undo_command="rm file1.py",
            files_affected=["file1.py"],
            risk_level=RiskLevel.LOW,
        )
        rollback2 = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Second",
            undo_command="git checkout file2.py",
            files_affected=["file2.py"],
            risk_level=RiskLevel.MEDIUM,
        )
        chain.add(rollback1)
        chain.add(rollback2)

        all_rollbacks = chain.get_all()
        assert len(all_rollbacks) == 2
        # Should be in reverse order (most recent first)
        assert all_rollbacks[0].description == "Second"
        assert all_rollbacks[1].description == "First"


class TestUndoTracker:
    """Test UndoTracker class."""

    def test_undo_tracker_creation(self) -> None:
        """Test creating an undo tracker."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")
        assert tracker.agent_id == "agent-1"
        assert tracker.task_id == "task-1"
        assert tracker.get_undo_chain_depth() == 0

    def test_track_action(self) -> None:
        """Test tracking an action."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")
        rollback = RollbackCommand(
            action=ActionType.FILE_CREATE,
            description="Create new module",
            undo_command="rm src/module.py",
            files_affected=["src/module.py"],
            risk_level=RiskLevel.LOW,
        )
        tracker.track_action(rollback)

        assert tracker.get_undo_chain_depth() == 1
        assert tracker.get_last_action() is not None

    def test_get_last_action(self) -> None:
        """Test getting the last tracked action."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")
        rollback = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit config",
            undo_command="git checkout config.py",
            files_affected=["config.py"],
            risk_level=RiskLevel.MEDIUM,
        )
        tracker.track_action(rollback)

        last = tracker.get_last_action()
        assert last is not None
        assert last.description == "Edit config"

    def test_get_rollback_plan(self) -> None:
        """Test generating a rollback plan."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")
        rollback1 = RollbackCommand(
            action=ActionType.FILE_CREATE,
            description="Create file",
            undo_command="rm file1.py",
            files_affected=["file1.py"],
            risk_level=RiskLevel.LOW,
        )
        rollback2 = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit file",
            undo_command="git checkout file2.py",
            files_affected=["file2.py"],
            risk_level=RiskLevel.MEDIUM,
        )
        tracker.track_action(rollback1)
        tracker.track_action(rollback2)

        plan = tracker.get_rollback_plan()
        assert len(plan) == 2
        # Most recent first
        assert plan[0].description == "Edit file"
        assert plan[1].description == "Create file"

    def test_can_rollback_steps(self) -> None:
        """Test checking if we can rollback N steps."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")
        rollback = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit",
            undo_command="undo",
            files_affected=["file.py"],
            risk_level=RiskLevel.LOW,
        )
        tracker.track_action(rollback)

        assert tracker.can_rollback_steps(1) is True
        assert tracker.can_rollback_steps(2) is False

    def test_create_snapshot(self) -> None:
        """Test creating a snapshot of current state."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")
        snapshot = tracker.create_snapshot(
            description="Before risky operation",
            state={"git_commit": "abc123"},
        )

        assert snapshot.description == "Before risky operation"
        assert snapshot.state["git_commit"] == "abc123"
        assert tracker.get_snapshot_count() == 1

    def test_get_latest_snapshot(self) -> None:
        """Test getting the most recent snapshot."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")
        tracker.create_snapshot("First", {"commit": "1"})
        tracker.create_snapshot("Second", {"commit": "2"})

        latest = tracker.get_latest_snapshot()
        assert latest is not None
        assert latest.description == "Second"


class TestRollbackPlanner:
    """Test RollbackPlanner class."""

    def test_rollback_planner_creation(self) -> None:
        """Test creating a rollback planner."""
        planner = RollbackPlanner()
        assert planner is not None

    def test_generate_file_edit_rollback(self) -> None:
        """Test generating rollback for file edit."""
        planner = RollbackPlanner()
        rollback = planner.generate_rollback(
            action=ActionType.FILE_EDIT,
            description="Edit auth module",
            files=["src/auth.py"],
            git_commit="abc123",
        )

        assert rollback.action == ActionType.FILE_EDIT
        assert rollback.description == "Edit auth module"
        assert "git checkout abc123 -- src/auth.py" in rollback.undo_command
        assert rollback.files_affected == ["src/auth.py"]
        assert rollback.risk_level == RiskLevel.MEDIUM

    def test_generate_file_create_rollback(self) -> None:
        """Test generating rollback for file creation."""
        planner = RollbackPlanner()
        rollback = planner.generate_rollback(
            action=ActionType.FILE_CREATE,
            description="Create new module",
            files=["src/new_module.py"],
        )

        assert rollback.action == ActionType.FILE_CREATE
        assert "rm" in rollback.undo_command
        assert "src/new_module.py" in rollback.undo_command
        assert rollback.risk_level == RiskLevel.LOW

    def test_generate_file_delete_rollback(self) -> None:
        """Test generating rollback for file deletion."""
        planner = RollbackPlanner()
        rollback = planner.generate_rollback(
            action=ActionType.FILE_DELETE,
            description="Delete old file",
            files=["src/old.py"],
            git_commit="abc123",
        )

        assert rollback.action == ActionType.FILE_DELETE
        assert "git checkout abc123 -- src/old.py" in rollback.undo_command
        assert rollback.risk_level == RiskLevel.HIGH

    def test_generate_package_install_rollback(self) -> None:
        """Test generating rollback for package installation."""
        planner = RollbackPlanner()
        rollback = planner.generate_rollback(
            action=ActionType.PACKAGE_INSTALL,
            description="Install numpy",
            metadata={"package": "numpy"},
        )

        assert rollback.action == ActionType.PACKAGE_INSTALL
        assert "pip uninstall" in rollback.undo_command or "npm uninstall" in rollback.undo_command
        assert rollback.risk_level == RiskLevel.LOW

    def test_generate_config_change_rollback(self) -> None:
        """Test generating rollback for config change."""
        planner = RollbackPlanner()
        rollback = planner.generate_rollback(
            action=ActionType.CONFIG_CHANGE,
            description="Update database config",
            files=["config.json"],
            git_commit="abc123",
        )

        assert rollback.action == ActionType.CONFIG_CHANGE
        assert rollback.risk_level == RiskLevel.HIGH

    def test_assess_risk_level(self) -> None:
        """Test risk level assessment for different actions."""
        planner = RollbackPlanner()

        # Low risk: file creation
        assert planner.assess_risk_level(ActionType.FILE_CREATE, []) == RiskLevel.LOW

        # Medium risk: file edit
        assert planner.assess_risk_level(ActionType.FILE_EDIT, ["file.py"]) == RiskLevel.MEDIUM

        # High risk: file deletion
        assert planner.assess_risk_level(ActionType.FILE_DELETE, ["file.py"]) == RiskLevel.HIGH

        # High risk: config change
        assert (
            planner.assess_risk_level(ActionType.CONFIG_CHANGE, ["config.json"])
            == RiskLevel.HIGH
        )

        # Critical risk: database migration
        assert planner.assess_risk_level(ActionType.DATABASE_MIGRATION, []) == RiskLevel.CRITICAL

    def test_verify_rollback_command(self) -> None:
        """Test verifying that a rollback command is valid."""
        planner = RollbackPlanner()
        rollback = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit file",
            undo_command="git checkout abc123 -- file.py",
            files_affected=["file.py"],
            risk_level=RiskLevel.MEDIUM,
        )

        # Should return True for valid rollback
        assert planner.verify_rollback(rollback) is True

    def test_verify_rollback_command_invalid(self) -> None:
        """Test that invalid rollback commands are detected."""
        planner = RollbackPlanner()
        rollback = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit file",
            undo_command="",  # Empty undo command
            files_affected=["file.py"],
            risk_level=RiskLevel.MEDIUM,
        )

        # Should return False for invalid rollback
        assert planner.verify_rollback(rollback) is False


class TestIntegrationWithErrorDetection:
    """Test integration with error detection framework."""

    def test_automatic_rollback_on_error(self) -> None:
        """Test automatic rollback when error is detected."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")

        # Track some actions
        rollback = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Edit file",
            undo_command="git checkout -- file.py",
            files_affected=["file.py"],
            risk_level=RiskLevel.MEDIUM,
        )
        tracker.track_action(rollback)

        # Simulate error detection
        _error = ErrorContext(
            error_type=ErrorType.VALIDATION_FAILURE,
            severity=ErrorSeverity.HIGH,
            message="Tests failed after change",
            agent_id="agent-1",
            task_id="task-1",
        )

        # Get rollback plan for the error
        plan = tracker.get_rollback_plan()
        assert len(plan) > 0
        assert plan[0].description == "Edit file"

    def test_rollback_plan_in_handoff_document(self) -> None:
        """Test that rollback plans can be included in handoff documents."""
        tracker = UndoTracker(agent_id="agent-1", task_id="task-1")

        rollback = RollbackCommand(
            action=ActionType.FILE_EDIT,
            description="Refactor auth",
            undo_command="git checkout abc123 -- src/auth.py",
            files_affected=["src/auth.py"],
            risk_level=RiskLevel.HIGH,
        )
        tracker.track_action(rollback)

        # Get rollback plan for handoff
        plan = tracker.get_rollback_plan()
        rollback_info = {
            "rollback_plan": [
                {
                    "action": str(cmd.action),
                    "description": cmd.description,
                    "undo_command": cmd.undo_command,
                    "risk_level": str(cmd.risk_level),
                }
                for cmd in plan
            ]
        }

        assert len(rollback_info["rollback_plan"]) == 1
        assert rollback_info["rollback_plan"][0]["description"] == "Refactor auth"
