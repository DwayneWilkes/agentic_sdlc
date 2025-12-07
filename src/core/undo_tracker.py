"""
Undo awareness and rollback tracking for agent actions.

This module provides comprehensive undo tracking capabilities to ensure that
agents can always reverse their actions. It implements the principle:
"Before doing X, know how to undo X".

Key components:
- ActionType: Enumeration of action types that can be tracked
- RollbackCommand: Complete specification for reversing an action
- UndoChain: Tracks the sequence of actions for rollback
- UndoTracker: Main interface for tracking actions and generating rollback plans
- RollbackPlanner: Generates rollback commands for different action types
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    """Types of actions that can be tracked for undo."""

    FILE_EDIT = "file_edit"
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    CONFIG_CHANGE = "config_change"
    PACKAGE_INSTALL = "package_install"
    DATABASE_MIGRATION = "database_migration"
    API_DEPLOYMENT = "api_deployment"


class RiskLevel(int, Enum):
    """Risk levels for actions (higher values = more risk)."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RollbackCommand:
    """
    Complete specification for reversing an action.

    Captures everything needed to undo a change, including the action type,
    description, undo command, affected files, and risk assessment.
    """

    action: ActionType
    description: str
    undo_command: str
    files_affected: list[str]
    risk_level: RiskLevel
    rollback_verified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Snapshot:
    """
    Snapshot of system state at a point in time.

    Used for "before" snapshots prior to risky operations, allowing
    full state restoration if needed.
    """

    timestamp: datetime
    description: str
    state: dict[str, Any]


class UndoChain:
    """
    Tracks the sequence of actions for rollback.

    Maintains a stack of rollback commands in reverse chronological order,
    allowing agents to undo actions step by step.
    """

    def __init__(self) -> None:
        """Initialize an empty undo chain."""
        self._commands: list[RollbackCommand] = []

    def add(self, command: RollbackCommand) -> None:
        """
        Add a rollback command to the chain.

        Args:
            command: The rollback command to add
        """
        self._commands.append(command)

    def get_last(self) -> RollbackCommand | None:
        """
        Get the most recent rollback command.

        Returns:
            The most recent command, or None if chain is empty
        """
        if not self._commands:
            return None
        return self._commands[-1]

    def get_all(self) -> list[RollbackCommand]:
        """
        Get all rollback commands in reverse chronological order.

        Returns:
            List of commands, most recent first
        """
        return list(reversed(self._commands))

    def depth(self) -> int:
        """
        Get the number of commands in the chain.

        Returns:
            Number of rollback commands tracked
        """
        return len(self._commands)

    def is_empty(self) -> bool:
        """
        Check if the chain is empty.

        Returns:
            True if no commands are tracked
        """
        return len(self._commands) == 0


class UndoTracker:
    """
    Main interface for tracking actions and generating rollback plans.

    Tracks all actions performed by an agent on a task, maintaining
    both an undo chain and snapshots for safe rollback.
    """

    def __init__(self, agent_id: str, task_id: str) -> None:
        """
        Initialize the undo tracker.

        Args:
            agent_id: ID of the agent performing actions
            task_id: ID of the task being worked on
        """
        self.agent_id = agent_id
        self.task_id = task_id
        self._undo_chain = UndoChain()
        self._snapshots: list[Snapshot] = []

    def track_action(self, rollback: RollbackCommand) -> None:
        """
        Track an action by recording its rollback command.

        Args:
            rollback: The rollback command for the action
        """
        self._undo_chain.add(rollback)

    def get_last_action(self) -> RollbackCommand | None:
        """
        Get the most recent action tracked.

        Returns:
            The most recent rollback command, or None if none tracked
        """
        return self._undo_chain.get_last()

    def get_rollback_plan(self) -> list[RollbackCommand]:
        """
        Generate a complete rollback plan for all tracked actions.

        Returns:
            List of rollback commands in reverse chronological order
        """
        return self._undo_chain.get_all()

    def get_undo_chain_depth(self) -> int:
        """
        Get the depth of the undo chain.

        Returns:
            Number of actions that can be rolled back
        """
        return self._undo_chain.depth()

    def can_rollback_steps(self, n: int) -> bool:
        """
        Check if we can rollback N steps.

        Args:
            n: Number of steps to check

        Returns:
            True if we can rollback at least N steps
        """
        return self._undo_chain.depth() >= n

    def create_snapshot(self, description: str, state: dict[str, Any]) -> Snapshot:
        """
        Create a snapshot of current system state.

        Args:
            description: Description of what this snapshot captures
            state: Dictionary containing state information

        Returns:
            The created snapshot
        """
        snapshot = Snapshot(
            timestamp=datetime.now(),
            description=description,
            state=state,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_snapshot_count(self) -> int:
        """
        Get the number of snapshots created.

        Returns:
            Number of snapshots
        """
        return len(self._snapshots)

    def get_latest_snapshot(self) -> Snapshot | None:
        """
        Get the most recent snapshot.

        Returns:
            The most recent snapshot, or None if none exist
        """
        if not self._snapshots:
            return None
        return self._snapshots[-1]


class RollbackPlanner:
    """
    Generates rollback commands for different action types.

    Implements the logic for determining how to undo various types of
    actions, including risk assessment and rollback verification.
    """

    def __init__(self) -> None:
        """Initialize the rollback planner."""
        pass

    def generate_rollback(
        self,
        action: ActionType,
        description: str,
        files: list[str] | None = None,
        git_commit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RollbackCommand:
        """
        Generate a rollback command for an action.

        Args:
            action: Type of action to generate rollback for
            description: Description of the action
            files: List of files affected by the action
            git_commit: Git commit hash for git-based rollbacks
            metadata: Additional metadata for the action

        Returns:
            A complete rollback command
        """
        files = files or []
        metadata = metadata or {}

        # Generate undo command based on action type
        undo_command = self._generate_undo_command(action, files, git_commit, metadata)

        # Assess risk level
        risk_level = self.assess_risk_level(action, files)

        # Create rollback command
        rollback = RollbackCommand(
            action=action,
            description=description,
            undo_command=undo_command,
            files_affected=files,
            risk_level=risk_level,
            rollback_verified=self._can_verify_rollback(action),
            metadata=metadata,
        )

        return rollback

    def _generate_undo_command(
        self,
        action: ActionType,
        files: list[str],
        git_commit: str | None,
        metadata: dict[str, Any],
    ) -> str:
        """Generate the specific undo command for an action type."""
        if action == ActionType.FILE_EDIT:
            if git_commit and files:
                files_str = " ".join(files)
                return f"git checkout {git_commit} -- {files_str}"
            return "# Manual rollback required"

        elif action == ActionType.FILE_CREATE:
            if files:
                files_str = " ".join(files)
                return f"rm {files_str}"
            return "# Manual rollback required"

        elif action == ActionType.FILE_DELETE:
            if git_commit and files:
                files_str = " ".join(files)
                return f"git checkout {git_commit} -- {files_str}"
            return "# Manual rollback required"

        elif action == ActionType.PACKAGE_INSTALL:
            package = metadata.get("package", "")
            if package:
                # Assume pip for Python packages
                return f"pip uninstall -y {package}"
            return "npm uninstall <package>"

        elif action == ActionType.CONFIG_CHANGE:
            if git_commit and files:
                files_str = " ".join(files)
                return f"git checkout {git_commit} -- {files_str}"
            return "# Restore from backup or previous config"

        elif action == ActionType.DATABASE_MIGRATION:
            return "# Run rollback migration script"

        elif action == ActionType.API_DEPLOYMENT:
            return "# Redeploy previous version"

        return "# Manual rollback required"

    def assess_risk_level(self, action: ActionType, files: list[str]) -> RiskLevel:
        """
        Assess the risk level of an action.

        Args:
            action: Type of action
            files: Files affected by the action

        Returns:
            Risk level for the action
        """
        # High-risk actions
        if action in [
            ActionType.DATABASE_MIGRATION,
            ActionType.API_DEPLOYMENT,
        ]:
            return RiskLevel.CRITICAL

        if action in [
            ActionType.FILE_DELETE,
            ActionType.CONFIG_CHANGE,
        ]:
            return RiskLevel.HIGH

        # Medium-risk actions
        if action == ActionType.FILE_EDIT:
            return RiskLevel.MEDIUM

        # Low-risk actions
        return RiskLevel.LOW

    def verify_rollback(self, rollback: RollbackCommand) -> bool:
        """
        Verify that a rollback command is valid and executable.

        Args:
            rollback: The rollback command to verify

        Returns:
            True if the rollback command is valid
        """
        # Basic validation: ensure undo command is not empty
        if not rollback.undo_command or rollback.undo_command.strip() == "":
            return False

        # Ensure it's not just a placeholder comment
        if rollback.undo_command.strip().startswith("#"):
            return False

        return True

    def _can_verify_rollback(self, action: ActionType) -> bool:
        """Check if rollback can be automatically verified for an action type."""
        # Git-based actions can be verified
        if action in [
            ActionType.FILE_EDIT,
            ActionType.FILE_DELETE,
            ActionType.CONFIG_CHANGE,
        ]:
            return True

        # File creation rollback is simple
        if action == ActionType.FILE_CREATE:
            return True

        # Package operations can be verified
        if action == ActionType.PACKAGE_INSTALL:
            return True

        # Complex operations need manual verification
        return False
