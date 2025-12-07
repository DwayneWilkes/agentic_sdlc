"""Undo awareness framework for the orchestrator system.

This module provides comprehensive undo tracking, snapshot management, and
automatic rollback capabilities to ensure all changes are reversible and
no orphaned modifications occur.

Before doing any action X, the system knows how to undo X.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.core.error_detection import ErrorContext, ErrorSeverity


class RiskLevel(str, Enum):
    """Risk levels for actions (determines rollback sensitivity)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class UndoAction:
    """
    Represents a single action with its undo capability.

    Every action captures exactly how to reverse it, ensuring
    no irreversible changes are made without documentation.
    """

    action: str
    undo_command: str
    description: str
    risk_level: RiskLevel
    files_affected: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ActionSnapshot:
    """
    Captures state before a risky operation.

    Snapshots enable restoration to previous state if the
    operation fails or causes regressions.
    """

    action_description: str
    files_affected: list[str]
    snapshot_data: dict[str, Any]
    risk_level: RiskLevel
    timestamp: datetime = field(default_factory=datetime.now)
    verified: bool = False


class UndoChain:
    """
    Tracks a sequence of actions with undo capability.

    Maintains a bounded history of actions, automatically
    removing oldest when maximum depth is exceeded.
    """

    def __init__(self, max_depth: int = 100) -> None:
        """
        Initialize the undo chain.

        Args:
            max_depth: Maximum number of actions to track (default 100)
        """
        self._actions: list[UndoAction] = []
        self._max_depth = max_depth

    def add(self, action: UndoAction) -> None:
        """
        Add an action to the chain.

        Args:
            action: The action to add
        """
        self._actions.append(action)

        # Enforce maximum depth by removing oldest actions
        if len(self._actions) > self._max_depth:
            self._actions.pop(0)

    def pop(self) -> UndoAction | None:
        """
        Remove and return the last action.

        Returns:
            The last action, or None if chain is empty
        """
        if self._actions:
            return self._actions.pop()
        return None

    def get_last(self) -> UndoAction | None:
        """
        Get the last action without removing it.

        Returns:
            The last action, or None if chain is empty
        """
        if self._actions:
            return self._actions[-1]
        return None

    def get_all(self) -> list[UndoAction]:
        """
        Get all actions in the chain.

        Returns:
            List of all actions (oldest to newest)
        """
        return self._actions.copy()

    def depth(self) -> int:
        """
        Get the current depth of the chain.

        Returns:
            Number of actions in the chain
        """
        return len(self._actions)

    def is_empty(self) -> bool:
        """
        Check if the chain is empty.

        Returns:
            True if no actions exist
        """
        return len(self._actions) == 0

    def clear(self) -> None:
        """Clear all actions from the chain."""
        self._actions.clear()


class UndoAwarenessEngine:
    """
    Main orchestrator for undo operations.

    Provides action recording, snapshot management, rollback plan generation,
    and automatic rollback decision-making based on error severity.
    """

    def __init__(self, max_chain_depth: int = 100) -> None:
        """
        Initialize the undo awareness engine.

        Args:
            max_chain_depth: Maximum undo chain depth (default 100)
        """
        self._chain = UndoChain(max_depth=max_chain_depth)
        self._snapshots: list[ActionSnapshot] = []

    def record_action(
        self,
        action: str,
        undo_command: str,
        description: str,
        risk_level: RiskLevel,
        files_affected: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UndoAction:
        """
        Record an action with its undo capability.

        Args:
            action: Description of the action being performed
            undo_command: Command to undo this action
            description: Detailed description of why this action is needed
            risk_level: Risk level of this action
            files_affected: List of files affected by this action
            metadata: Additional metadata about the action

        Returns:
            The created UndoAction
        """
        undo_action = UndoAction(
            action=action,
            undo_command=undo_command,
            description=description,
            risk_level=risk_level,
            files_affected=files_affected or [],
            metadata=metadata or {},
        )
        self._chain.add(undo_action)
        return undo_action

    def get_last_action(self) -> UndoAction | None:
        """
        Get the most recent action.

        Returns:
            The last action, or None if no actions exist
        """
        return self._chain.get_last()

    def get_undo_command(self) -> str | None:
        """
        Get the undo command for the last action.

        Returns:
            The undo command, or None if no actions exist
        """
        last_action = self._chain.get_last()
        return last_action.undo_command if last_action else None

    def get_chain_depth(self) -> int:
        """
        Get the current undo chain depth.

        Returns:
            Number of actions that can be undone
        """
        return self._chain.depth()

    def can_rollback(self) -> bool:
        """
        Check if rollback is possible.

        Returns:
            True if at least one action exists that can be undone
        """
        return not self._chain.is_empty()

    def create_snapshot(
        self,
        action_description: str,
        files_affected: list[str],
        snapshot_data: dict[str, Any],
        risk_level: RiskLevel,
    ) -> ActionSnapshot:
        """
        Create a snapshot before a risky operation.

        Args:
            action_description: Description of the action about to be performed
            files_affected: Files that will be affected
            snapshot_data: Data to capture (e.g., git hash, file contents)
            risk_level: Risk level of the operation

        Returns:
            The created snapshot
        """
        snapshot = ActionSnapshot(
            action_description=action_description,
            files_affected=files_affected,
            snapshot_data=snapshot_data,
            risk_level=risk_level,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def verify_snapshot(self, snapshot: ActionSnapshot) -> None:
        """
        Mark a snapshot as verified (operation succeeded).

        Args:
            snapshot: The snapshot to verify
        """
        snapshot.verified = True

    def generate_rollback_plan(
        self, error_context: ErrorContext | None = None
    ) -> str:
        """
        Generate a rollback plan from the action history.

        The plan lists undo commands in reverse order (most recent first),
        allowing step-by-step restoration to previous state.

        Args:
            error_context: Optional error context that triggered rollback

        Returns:
            Formatted rollback plan as a string
        """
        if self._chain.is_empty():
            return "Rollback Plan: No actions to rollback (empty chain)"

        lines = ["=== Rollback Plan ===", ""]

        if error_context:
            lines.extend(
                [
                    f"Triggered by: {error_context.error_type.value}",
                    f"Severity: {error_context.severity.name}",
                    f"Message: {error_context.message}",
                    "",
                ]
            )

        lines.append("Execute these commands in order (most recent first):")
        lines.append("")

        # Get actions in reverse order (newest first)
        actions = self._chain.get_all()
        for i, action in enumerate(reversed(actions), 1):
            lines.append(f"{i}. {action.action}")
            lines.append(f"   Command: {action.undo_command}")
            lines.append(f"   Risk: {action.risk_level.value}")
            if action.files_affected:
                lines.append(f"   Files: {', '.join(action.files_affected)}")
            lines.append("")

        return "\n".join(lines)

    def should_auto_rollback(self, error: ErrorContext) -> bool:
        """
        Decide if automatic rollback should be triggered.

        Rollback is triggered when:
        - Error severity is CRITICAL or HIGH, OR
        - Error severity is MEDIUM and last action risk is HIGH/CRITICAL

        Args:
            error: The error context to evaluate

        Returns:
            True if automatic rollback should occur
        """
        if self._chain.is_empty():
            return False

        # Always rollback on critical errors
        if error.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.HIGH):
            return True

        # For medium severity, check action risk level
        if error.severity == ErrorSeverity.MEDIUM:
            last_action = self._chain.get_last()
            if last_action and last_action.risk_level in (
                RiskLevel.HIGH,
                RiskLevel.CRITICAL,
            ):
                return True

        return False

    def export_to_handoff(self) -> dict[str, Any]:
        """
        Export rollback plan in handoff document format.

        Returns:
            Dictionary suitable for inclusion in HandoffDocument
        """
        last_action = self._chain.get_last()
        return {
            "rollback_plan": self.generate_rollback_plan(),
            "action_count": self._chain.depth(),
            "can_rollback": self.can_rollback(),
            "last_action": asdict(last_action) if last_action else None,
        }

    def export_to_json(self) -> str:
        """
        Export the entire undo chain to JSON format.

        Returns:
            JSON string representation of the undo chain
        """
        actions_list = [asdict(action) for action in self._chain.get_all()]

        # Convert datetime objects to ISO format strings
        for action_dict in actions_list:
            ts = action_dict.get("timestamp")
            if isinstance(ts, datetime):
                action_dict["timestamp"] = ts.isoformat()

        data: dict[str, Any] = {
            "action_count": self._chain.depth(),
            "can_rollback": self.can_rollback(),
            "actions": actions_list,
        }

        return json.dumps(data, indent=2, default=str)

    def clear_history(self) -> None:
        """Clear all undo history and snapshots."""
        self._chain.clear()
        self._snapshots.clear()
