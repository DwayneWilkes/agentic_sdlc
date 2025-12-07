"""Action validation framework for pre-execution safety checks.

This module provides a validation layer on top of access control that:
- Classifies actions by risk level (safe, moderate, destructive)
- Enforces safety boundaries that cannot be crossed
- Determines when human approval is required
"""

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from src.security.access_control import (
    AccessControlPolicy,
    Action,
    ActionType,
)


class RiskLevel(Enum):
    """Risk level classification for actions."""

    SAFE = "safe"  # Read-only operations
    MODERATE = "moderate"  # Write/create operations
    DESTRUCTIVE = "destructive"  # Delete/modify operations with high risk


@dataclass
class SafetyBoundary:
    """Definition of a safety boundary that cannot be crossed.

    Safety boundaries are hard constraints that prevent certain types
    of actions regardless of access control permissions.
    """

    name: str
    """Unique name for this boundary."""

    description: str
    """Human-readable description of what this boundary protects."""

    forbidden_action_types: list[ActionType] = field(default_factory=list)
    """Action types that are forbidden by this boundary."""

    forbidden_paths: list[str] = field(default_factory=list)
    """Path patterns that are protected (supports wildcards)."""


@dataclass
class ValidationResult:
    """Result of action validation."""

    allowed: bool
    """Whether the action is allowed to proceed."""

    risk_level: RiskLevel
    """Risk level of the action."""

    reason: str
    """Explanation for the decision."""

    requires_approval: bool = False
    """Whether human approval is required."""

    boundary_violations: list[str] = field(default_factory=list)
    """Names of safety boundaries that were violated."""


class ActionValidator:
    """Validates actions before execution.

    The validator provides a pre-execution safety layer that:
    1. Classifies actions by risk level
    2. Checks safety boundary violations
    3. Integrates with access control policy
    4. Determines approval requirements
    """

    def __init__(self) -> None:
        """Initialize action validator."""
        self.boundaries: dict[str, SafetyBoundary] = {}
        """Registry of safety boundaries."""

    def classify_risk(self, action: Action) -> RiskLevel:
        """Classify the risk level of an action.

        Args:
            action: Action to classify

        Returns:
            Risk level classification
        """
        # DELETE is always destructive
        if action.action_type == ActionType.DELETE:
            return RiskLevel.DESTRUCTIVE

        # MODIFY is destructive (changes existing data)
        if action.action_type == ActionType.MODIFY:
            return RiskLevel.DESTRUCTIVE

        # READ is safe
        if action.action_type == ActionType.READ:
            return RiskLevel.SAFE

        # WRITE, CREATE are moderate risk
        if action.action_type in (ActionType.WRITE, ActionType.CREATE):
            return RiskLevel.MODERATE

        # EXECUTE is moderate risk
        if action.action_type == ActionType.EXECUTE:
            return RiskLevel.MODERATE

        # Default to destructive for unknown action types
        return RiskLevel.DESTRUCTIVE

    def validate_action(
        self,
        action: Action,
        access_control_policy: AccessControlPolicy | None,
    ) -> ValidationResult:
        """Validate an action before execution.

        Args:
            action: Action to validate
            access_control_policy: Optional access control policy to check

        Returns:
            ValidationResult with decision and reasoning
        """
        # Classify risk level
        risk_level = self.classify_risk(action)

        # Check for boundary violations
        violations = self._check_boundaries(action)
        if violations:
            return ValidationResult(
                allowed=False,
                risk_level=risk_level,
                reason=f"Violates safety boundaries: {', '.join(violations)}",
                boundary_violations=violations,
            )

        # If access control policy is provided, check it
        if access_control_policy:
            decision = access_control_policy.check_access(action)
            if not decision.allowed:
                return ValidationResult(
                    allowed=False,
                    risk_level=risk_level,
                    reason=decision.reason,
                )

        # Destructive actions require approval
        requires_approval = risk_level == RiskLevel.DESTRUCTIVE

        return ValidationResult(
            allowed=True,
            risk_level=risk_level,
            reason=f"{risk_level.value.capitalize()} operation validated",
            requires_approval=requires_approval,
        )

    def add_boundary(self, boundary: SafetyBoundary) -> None:
        """Add a safety boundary.

        Args:
            boundary: Safety boundary to add
        """
        self.boundaries[boundary.name] = boundary

    def remove_boundary(self, name: str) -> None:
        """Remove a safety boundary.

        Args:
            name: Name of boundary to remove
        """
        self.boundaries.pop(name, None)

    def get_all_boundaries(self) -> dict[str, SafetyBoundary]:
        """Get all configured safety boundaries.

        Returns:
            Dictionary of boundary name -> SafetyBoundary
        """
        return self.boundaries.copy()

    def _check_boundaries(self, action: Action) -> list[str]:
        """Check if action violates any safety boundaries.

        Args:
            action: Action to check

        Returns:
            List of violated boundary names
        """
        violations = []

        for boundary in self.boundaries.values():
            # Check if action type is forbidden
            if action.action_type not in boundary.forbidden_action_types:
                continue

            # Check if path matches forbidden patterns
            if self._path_matches_patterns(
                action.resource.path,
                boundary.forbidden_paths,
            ):
                violations.append(boundary.name)

        return violations

    def _path_matches_patterns(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches any of the forbidden patterns.

        Args:
            path: Path to check
            patterns: List of path patterns (may include wildcards)

        Returns:
            True if path matches any pattern
        """
        if not patterns:
            return False

        try:
            abs_path = Path(path).resolve()
        except (OSError, RuntimeError):
            # If we can't resolve the path, treat it as a potential match
            # to err on the side of caution
            abs_path_str = path
        else:
            abs_path_str = str(abs_path)

        for pattern in patterns:
            # Handle wildcard patterns
            if "*" in pattern:
                if fnmatch.fnmatch(abs_path_str, pattern):
                    return True
                # Also check if path starts with the pattern prefix
                prefix = pattern.split("*")[0].rstrip("/")
                if abs_path_str.startswith(prefix):
                    return True
            else:
                # Exact or prefix match
                try:
                    pattern_abs = Path(pattern).resolve()
                    if abs_path == pattern_abs or pattern_abs in abs_path.parents:
                        return True
                except (OSError, RuntimeError):
                    # Compare as strings if we can't resolve pattern
                    if abs_path_str == pattern or abs_path_str.startswith(
                        pattern.rstrip("/") + "/"
                    ):
                        return True

        return False
